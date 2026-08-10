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

from .folder_filters import should_skip_file
from .monitor_config import FolderFilter, MonitorConfig

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
    total_uploaded: int = 0
    total_skipped: int = 0
    total_errored: int = 0
    failed_folders: int = 0

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
        self.total_uploaded = 0
        self.total_skipped = 0
        self.total_errored = 0
        self.failed_folders = 0


def count_pending_files(
    folder: str,
    since_utc: datetime,
    filter_rules: FolderFilter,
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
                if mtime >= since_utc and not should_skip_file(fpath, filter_rules):
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
    skip_ssl: bool = False,
    client_timeout_minutes: int = 60,
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
        advanced_state: Advanced upload-folder flag state.
        skip_ssl: Skip SSL verification (from application configuration).
        client_timeout_minutes: immich-go client timeout (from app config).

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

    result = UploadResult(folder=folder, success=False, log_file=log_file)

    if on_log:
        on_log(folder_key, f"Starting upload: {folder}")
        on_log(folder_key, f"  Since: {since_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    try:
        # Resolve immich-go binary via the binary manager (the installed
        # build keeps it in BinaryManager's versioned directory).
        binary = _resolve_binary_path()

        # Build command (uses build_plan_from_state when advanced_state is set)
        plan = _build_upload_plan(
            folder,
            config,
            server_url,
            api_key,
            since_utc,
            advanced_state,
            binary_path=binary,
            skip_ssl=skip_ssl,
            client_timeout_minutes=client_timeout_minutes,
        )
        if plan.errors:
            raise ValueError("Invalid upload command: " + "; ".join(plan.errors))
        args = plan.argv

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
                cancelled = False
                child_suspended = False
                while proc.poll() is None or closed_streams < len(readers):
                    # Check cancel
                    if state.cancel_event.is_set():
                        if child_suspended:
                            _resume_process(proc.pid)
                            child_suspended = False
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        result.success = False
                        result.message = "Cancelled"
                        if on_log:
                            on_log(folder_key, "[cancelled] Upload cancelled")
                        cancelled = True
                        break

                    # Check pause: actually suspend the child so no upload
                    # work happens while paused.
                    if not state.pause_event.is_set():
                        if not child_suspended:
                            _suspend_process(proc.pid)
                            child_suspended = True
                        state.pause_event.wait(timeout=0.5)
                        continue
                    if child_suspended:
                        _resume_process(proc.pid)
                        child_suspended = False

                    try:
                        stream_name, line = output_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if line is None:
                        closed_streams += 1
                        continue
                    if line.strip():
                        if on_log:
                            on_log(
                                folder_key,
                                line if stream_name == "stdout" else f"[stderr] {line}",
                            )
                        if "Uploaded" in line or "uploading" in line.lower():
                            state.current_file = line.strip()
                        _tally_report_line(line, result)

                for reader in readers:
                    reader.join(timeout=2)

            except Exception:
                proc.kill()
                raise

            if not cancelled:
                result.exit_code = (
                    proc.returncode if proc.returncode is not None else -1
                )
                result.success = result.exit_code == 0

                # File counts are only reported when an explicit immich-go
                # summary parse is available; otherwise they stay 0 so the
                # GUI never shows wrong numbers.

                if result.success:
                    result.message = "Completed"
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
    binary_path: str = "",
    skip_ssl: bool = False,
    client_timeout_minutes: int = 60,
):
    """Build the immich-go CommandPlan for an upload.

    Always uses build_plan_from_state() so that the same flag registry,
    validation system, and env-var secret delivery as the Upload tab applies.
    Advanced flags from the Monitor tab's Advanced Flags card are included
    when advanced_state is provided.

    Album/stacking choices are intentionally fixed: monitor runs are
    independent of the Upload tab's UI selections.

    Raises:
        ValueError: when the plan contains validation errors, so no
            malformed command is ever launched.

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
        "skip-ssl": skip_ssl,
        "client_timeout_minutes": client_timeout_minutes,
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
        binary_path=binary_path or "./immich-go",
        dry_run=False,
        advanced_state=advanced_state,
    )

    if plan.errors:
        _log.warning("Command plan errors: %s", plan.errors)
        raise ValueError("; ".join(plan.errors))
    if plan.warnings:
        _log.info("Command plan warnings: %s", plan.warnings)

    # The monitor runs immich-go as a hidden subprocess with piped stdout.
    # Without --no-ui the interactive TUI starts up and, because stdout is
    # not a terminal, never exits after the upload completes — leaving the
    # run stuck in "running" and the process lingering.  Force headless mode.
    # plan.argv is "cmd_parts + options + positional path"; Go's flag parser
    # stops at the first positional argument, so --no-ui must precede it.
    from .cli_schema import TAB_COMMANDS
    from .command_builder import mask_command_for_display

    cmd_count = len(TAB_COMMANDS.get("upload-folder", ()))
    plan.argv.insert(cmd_count, "--no-ui")
    plan.display_argv = mask_command_for_display(
        [binary_path or "./immich-go"] + plan.argv
    )

    return plan


def _resolve_binary_path() -> str:
    """Find the immich-go binary via the binary manager.

    Raises:
        FileNotFoundError: when no managed binary exists, so callers report
            a clear error instead of launching a bogus command.
    """
    from .binary_manager import get_binary_path

    path = get_binary_path()
    if not path:
        raise FileNotFoundError("immich-go binary not found")
    return path


def _tally_report_line(line: str, result: UploadResult) -> None:
    """Update UploadResult file counts from immich-go report output lines.

    immich-go emits a running summary line such as::

        Immich read 100%, Assets found: 8, Upload errors: 0, Uploaded 1

    and an Asset Tracking Report whose lifecycle lines look like::

        uploaded successfully              :       1  (4.2 MB)
        server has duplicate               :       7  (22.3 MB)

    These are parsed so the GUI can report accurate totals instead of 0.
    Regexes are anchored to the report fields so unrelated lines are ignored.
    """
    import re

    try:
        # The whole-run summary line can carry several fields at once, e.g.
        #   "Immich read 100%, Assets found: 8, Upload errors: 0, Uploaded 1"
        # so parse every field on the line rather than returning on the first.
        m = re.search(r"[Uu]pload errors?:\s*(\d+)", line)
        if m:
            result.files_errored = int(m.group(1))
        m = re.search(r"\bUploaded\s+(\d+)\s*$", line)
        if m:
            result.files_uploaded = int(m.group(1))
        # Asset Tracking Report lifecycle lines (count then size in parens).
        m = re.search(r"uploaded successfully\s*:?\s*(\d+)", line)
        if m:
            result.files_uploaded = int(m.group(1))
        m = re.search(r"server has duplicate\s*:?\s*(\d+)", line)
        if m:
            result.files_skipped = int(m.group(1))
        # Regular per-file progress like "Uploading file=..." is ignored;
        # only the whole-run summary and report tallies are captured.
    except (ValueError, TypeError):
        pass


def _suspend_process(pid: int) -> None:
    """Suspend a child process; best-effort, never raises."""
    try:
        import psutil
    except ImportError:
        return
    try:
        psutil.Process(pid).suspend()
    except psutil.Error:
        pass


def _resume_process(pid: int) -> None:
    """Resume a suspended child process; best-effort, never raises."""
    try:
        import psutil
    except ImportError:
        return
    try:
        psutil.Process(pid).resume()
    except psutil.Error:
        pass
