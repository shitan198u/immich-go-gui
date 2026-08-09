"""Hidden immich-go process runner for the Monitor subsystem.

Runs immich-go upload commands as hidden subprocesses (no terminal popup),
captures stdout/stderr for logging, and supports cancellation.
"""

import logging
import os
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .monitor_config import MonitorConfig

_log = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of a single folder upload attempt."""

    folder: str
    success: bool
    exit_code: int = 0
    message: str = ""
    log_file: str = ""
    files_uploaded: int = 0
    files_skipped: int = 0
    files_errored: int = 0
    duration_seconds: float = 0

    @property
    def ok(self) -> bool:
        return self.success


@dataclass
class RunnerState:
    """Mutable state for the current batch run (not persisted)."""

    running: bool = False
    paused: bool = False
    cancelled: bool = False
    pause_event: threading.Event = field(default_factory=threading.Event)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    total_folders: int = 0
    completed_folders: int = 0
    current_folder: str = ""
    current_file: str = ""

    def reset(self) -> None:
        self.running = True
        self.paused = False
        self.cancelled = False
        self.pause_event.set()  # not paused initially
        self.cancel_event.clear()
        self.total_folders = 0
        self.completed_folders = 0
        self.current_folder = ""
        self.current_file = ""


def _should_skip_file(
    file_path: str,
    filter_rules,
) -> bool:
    """Apply folder filter rules to decide if a file should be skipped."""
    import fnmatch

    name = os.path.basename(file_path)
    ext = os.path.splitext(name)[1].lower()

    # Hidden files
    if filter_rules.skip_hidden:
        if name.startswith("."):
            return True

    # System files
    if filter_rules.skip_system_files:
        if name.startswith("~$") or name.lower() in ("thumbs.db", "desktop.ini"):
            return True

    # Extension include list (if specified, only these)
    if filter_rules.include_extensions:
        if ext not in [e.lower() for e in filter_rules.include_extensions]:
            return True

    # Extension exclude list
    if ext in [e.lower() for e in filter_rules.exclude_extensions]:
        return True

    # File size limits
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        size_kb = os.path.getsize(file_path) / 1024
        if (
            filter_rules.max_file_size_mb > 0
            and size_mb > filter_rules.max_file_size_mb
        ):
            return True
        if (
            filter_rules.min_file_size_kb > 0
            and size_kb < filter_rules.min_file_size_kb
        ):
            return True
    except OSError:
        return True

    # Glob exclusion patterns
    path = file_path.replace("\\", "/")
    for pattern in filter_rules.exclude_patterns:
        if fnmatch.fnmatch(path, pattern):
            return True

    return False


def count_pending_files(
    folder: str,
    since_utc: datetime,
    filter_rules,
) -> int:
    """Count how many files in a folder are newer than since_utc and pass filters."""
    count = 0
    if not os.path.isdir(folder):
        return 0

    exclude_dirs = {
        "@eadir",
        "@__thumb",
        ".spotlight-v100",
        ".photostructure",
        "thumbnails",
        "lightroom catalog",
        "recently deleted",
        "$recycle.bin",
        "system volume information",
    }

    for root, dirs, files in os.walk(folder):
        # Filter directories in-place
        dirs[:] = [
            d for d in dirs if d.lower() not in exclude_dirs and not d.startswith(".")
        ]
        for f in files:
            fpath = os.path.join(root, f)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=UTC)
                if mtime >= since_utc and not _should_skip_file(fpath, filter_rules):
                    count += 1
            except OSError:
                continue
    return count


def run_folder_upload(
    folder: str,
    config: MonitorConfig,
    server_url: str,
    api_key: str,
    since_utc: datetime,
    log_dir: str,
    state: RunnerState,
    on_log: Callable[[str, str], None] | None = None,
    advanced_state: dict | None = None,
) -> UploadResult:
    """Run immich-go upload for a single folder as a hidden subprocess.

    Args:
        folder: Source folder path.
        config: Monitor configuration.
        server_url: Immich server URL.
        api_key: Immich API key.
        since_utc: Only upload files modified since this timestamp.
        log_dir: Directory for log output.
        state: Shared runner state for pause/cancel coordination.
        on_log: Callback(folder_key, log_line) for live progress.

    Returns:
        UploadResult with success/failure details.
    """
    import time

    start_time = time.monotonic()
    folder_key = os.path.basename(folder) or "root"
    safe_folder_key = "".join(
        char if char.isalnum() or char in "-_" else "_" for char in folder_key
    )
    state.current_folder = folder_key

    log_file = os.path.join(
        log_dir,
        f"upload-{datetime.now(UTC).strftime('%Y-%m-%d-%H%M%S')}-{safe_folder_key}.log",
    )

    # Build command (uses build_plan_from_state when advanced_state is set)
    plan = _build_upload_plan(
        folder, config, server_url, api_key, since_utc, advanced_state
    )
    args = plan.argv

    result = UploadResult(folder=folder, success=False, log_file=log_file)

    if on_log:
        on_log(folder_key, f"Starting upload: {folder}")
        on_log(folder_key, f"  Since: {since_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    try:
        # Resolve immich-go binary
        binary = _resolve_binary_path()

        # Use plan.env (includes server/API key via env vars, not CLI args)
        env = os.environ.copy()
        env.update(plan.env)

        with subprocess.Popen(
            [binary] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            env=env,
        ) as proc:
            # ``select.select`` cannot be used with Windows pipe handles;
            # Windows raises WinError 10038 because only sockets are valid
            # there.  Use reader threads and a queue for both platforms.
            import queue

            lines: list[str] = []
            output_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()

            def _read_output(stream, name: str) -> None:
                try:
                    for output_line in iter(stream.readline, ""):
                        output_queue.put((name, output_line.rstrip("\n")))
                finally:
                    output_queue.put((name, None))

            readers = [
                threading.Thread(
                    target=_read_output,
                    args=(proc.stdout, "stdout"),
                    daemon=True,
                ),
                threading.Thread(
                    target=_read_output,
                    args=(proc.stderr, "stderr"),
                    daemon=True,
                ),
            ]
            for reader in readers:
                reader.start()

            try:
                closed_streams = 0
                while proc.poll() is None or closed_streams < len(readers):
                    # Check pause
                    if not state.pause_event.is_set():
                        state.pause_event.wait(timeout=0.5)
                        if state.cancel_event.is_set():
                            break

                    # Check cancel
                    if state.cancel_event.is_set():
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        result.success = False
                        result.message = "Cancelled"
                        if on_log:
                            on_log(folder_key, "[cancelled] Upload cancelled")
                        return result

                    try:
                        stream_name, line = output_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if line is None:
                        closed_streams += 1
                        continue
                    if line.strip():
                        lines.append(line)
                        if on_log:
                            on_log(
                                folder_key,
                                line if stream_name == "stdout" else f"[stderr] {line}",
                            )
                        if "Uploaded" in line or "uploading" in line.lower():
                            state.current_file = line.strip()

                for reader in readers:
                    reader.join(timeout=2)

            except Exception:
                proc.kill()
                raise

            result.exit_code = proc.returncode
            result.success = proc.returncode == 0

            # Parse stats from output
            result.files_uploaded = _count_in_lines(lines, "uploaded")
            result.files_skipped = _count_in_lines(lines, "already exists")
            result.files_errored = _count_in_lines(lines, "error")

            if result.success:
                result.message = f"Completed: {result.files_uploaded} uploaded, "
                result.message += f"{result.files_skipped} skipped"
            else:
                result.message = f"Exited with code {result.exit_code}"

    except FileNotFoundError:
        result.success = False
        result.message = "immich-go binary not found"
        if on_log:
            on_log(folder_key, f"[error] {result.message}")
    except Exception as exc:
        result.success = False
        result.message = str(exc)
        if on_log:
            on_log(folder_key, f"[error] {exc}")

    # Write log file
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Folder: {folder}\n")
            f.write(f"Since: {since_utc.isoformat()}\n")
            f.write(
                f"Result: {'success' if result.success else 'failed'} "
                f"(exit {result.exit_code})\n"
            )
            f.write(f"Message: {result.message}\n\n")
    except OSError:
        pass

    result.duration_seconds = time.monotonic() - start_time
    return result


def _build_upload_plan(
    folder: str,
    config: MonitorConfig,
    server_url: str,
    api_key: str,
    since_utc: datetime,
    advanced_state: dict | None = None,
):
    """Build the immich-go CommandPlan for an upload.

    Always uses build_plan_from_state() so that the same flag registry,
    validation system, and env-var secret delivery as the Upload tab applies.
    Advanced flags from the Monitor tab's Advanced Flags card are included
    when advanced_state is provided.

    Returns:
        CommandPlan with .argv, .env, .errors, .warnings
    """
    from .command_builder import build_plan_from_state

    date_range = (
        f"{since_utc.strftime('%Y-%m-%d')},{datetime.now(UTC).strftime('%Y-%m-%d')}"
    )

    config_state = {
        "server": server_url,
        "api_key": api_key,
        "skip-ssl": False,
        "client_timeout_minutes": 60,
    }
    tab_state = {
        "path": folder,
        "folder-album": "NONE",
        "into-album": "",
        "manage-burst": "Stack",
        "manage-raw-jpeg": "StackCoverRaw",
        "manage-heic-jpeg": "NoStack",
        "date-range": date_range,
    }

    plan = build_plan_from_state(
        tab_key="upload-folder",
        config_state=config_state,
        tab_state=tab_state,
        binary_path=_resolve_binary_path(),
        dry_run=False,
        advanced_state=advanced_state,
    )

    if plan.errors:
        _log.warning("Command plan errors: %s", plan.errors)
    if plan.warnings:
        _log.info("Command plan warnings: %s", plan.warnings)

    return plan


def _resolve_binary_path() -> str:
    """Find the immich-go binary."""
    # First check relative to this module
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "immich-go"),
        os.path.join(os.path.dirname(__file__), "..", "immich-go.exe"),
        "immich-go",
        "immich-go.exe",
    ]
    for candidate in candidates:
        expanded = os.path.expanduser(os.path.normpath(candidate))
        if os.path.isfile(expanded):
            return expanded
    return "immich-go"


def _count_in_lines(lines: list[str], keyword: str) -> int:
    """Count lines containing a keyword."""
    return sum(1 for line in lines if keyword.lower() in line.lower())
