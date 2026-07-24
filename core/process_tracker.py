"""Process lock tracking logic for Immich-Go GUI.

Pure Python module, Qt-free.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid

from .config_manager import default_config_dir


@dataclass
class RunLock:
    run_id: str
    lock_path: Path
    gui_pid: int
    started_at: str
    tab_key: str
    command_summary: str
    binary_path: str
    shell_pid: int | None = None
    terminal_pid: int | None = None
    last_seen: str | None = None


def lock_dir() -> Path:
    """Returns the directory used for run lock files."""
    d = default_config_dir() / "locks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_lock(
    tab_key: str,
    command_summary: str,
    binary_path: str,
) -> Path:
    """Creates a run lock JSON file and returns its path."""
    run_id = uuid.uuid4().hex[:8]
    l_path = lock_dir() / f"run_{run_id}.lock"

    now_iso = datetime.now(timezone.utc).isoformat()
    data = {
        "run_id": run_id,
        "gui_pid": os.getpid(),
        "started_at": now_iso,
        "tab_key": tab_key,
        "command_summary": command_summary,
        "binary_path": binary_path,
        "shell_pid": None,
        "terminal_pid": None,
        "last_seen": now_iso,
    }

    text = json.dumps(data, indent=2)
    l_path.write_text(text, encoding="utf-8")
    return l_path


def update_lock(lock_path: Path, **fields) -> None:
    """Updates specific fields in a lock JSON file."""
    p = Path(lock_path)
    if not p.exists():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        for k, v in fields.items():
            data[k] = v
        data["last_seen"] = datetime.now(timezone.utc).isoformat()
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def release_lock(lock_path: Path) -> None:
    """Safely removes a lock file and its sidecars (.pid, .bat, .heartbeat)."""
    try:
        p = Path(lock_path)
        if p.exists():
            p.unlink()
        for ext in [".pid", ".bat", ".heartbeat"]:
            s = p.with_suffix(ext)
            if s.exists():
                s.unlink()
    except Exception:
        pass


def read_lock(lock_path: Path) -> RunLock | None:
    """Reads and parses a lock file."""
    p = Path(lock_path)
    if not p.exists():
        return None

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return RunLock(
            run_id=data.get("run_id", ""),
            lock_path=p,
            gui_pid=data.get("gui_pid", 0),
            started_at=data.get("started_at", ""),
            tab_key=data.get("tab_key", ""),
            command_summary=data.get("command_summary", ""),
            binary_path=data.get("binary_path", ""),
            shell_pid=data.get("shell_pid"),
            terminal_pid=data.get("terminal_pid"),
            last_seen=data.get("last_seen"),
        )
    except Exception:
        return None


def _is_process_alive(pid: int | None) -> bool:
    """Checks if a given process ID is active on current OS."""
    if not pid or pid <= 0:
        return False
    if sys.platform.startswith("win"):
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                kernel32.CloseHandle(handle)
                STILL_ACTIVE = 259
                return exit_code.value == STILL_ACTIVE
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def is_lock_active(lock_path: Path) -> bool:
    """Checks whether a lock is active or stale using PID, heartbeat, or timestamp grace."""
    p = Path(lock_path)
    lock = read_lock(p)
    if lock is None:
        return False

    # 1. Check sidecar .pid file or lock.shell_pid
    pid_file = p.with_suffix(".pid")
    shell_pid = lock.shell_pid
    if pid_file.exists():
        try:
            pid_val = int(pid_file.read_text(encoding="utf-8").strip())
            if pid_val > 0:
                shell_pid = pid_val
        except (ValueError, OSError):
            pass

    if shell_pid and _is_process_alive(shell_pid):
        return True

    # 2. Check terminal_pid
    if lock.terminal_pid and _is_process_alive(lock.terminal_pid):
        return True

    # 3. Check sidecar .heartbeat file
    hb_file = p.with_suffix(".heartbeat")
    if hb_file.exists():
        try:
            mtime = hb_file.stat().st_mtime
            age = (datetime.now().timestamp() - mtime)
            if age < 60:
                return True
        except OSError:
            pass

    # 4. Grace period for freshly created lock (< 60 seconds)
    if lock.started_at:
        try:
            start_dt = datetime.fromisoformat(lock.started_at)
            now = datetime.now(timezone.utc)
            if (now - start_dt).total_seconds() < 60:
                return True
        except ValueError:
            pass

    return False


def scan_locks() -> list[RunLock]:
    """Scans and returns all active locks."""
    d = lock_dir()
    if not d.exists():
        return []

    active_locks = []
    for p in d.glob("run_*.lock"):
        if is_lock_active(p):
            lock = read_lock(p)
            if lock:
                active_locks.append(lock)
        else:
            release_lock(p)

    return active_locks


def cleanup_stale_locks() -> int:
    """Scans lock directory and removes stale locks. Returns count of cleaned locks."""
    d = lock_dir()
    if not d.exists():
        return 0

    cleaned = 0
    for p in d.glob("run_*.lock"):
        if not is_lock_active(p):
            release_lock(p)
            cleaned += 1

    return cleaned


def reset_all_locks() -> int:
    """Force-deletes all locks in lock directory. Returns count of removed locks."""
    d = lock_dir()
    if not d.exists():
        return 0

    count = 0
    for p in d.glob("run_*.lock"):
        release_lock(p)
        count += 1

    return count
