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

    data = {
        "run_id": run_id,
        "gui_pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "tab_key": tab_key,
        "command_summary": command_summary,
        "binary_path": binary_path,
        "shell_pid": None,
    }

    text = json.dumps(data, indent=2)
    l_path.write_text(text, encoding="utf-8")
    return l_path


def release_lock(lock_path: Path) -> None:
    """Safely removes a lock file."""
    try:
        p = Path(lock_path)
        if p.exists():
            p.unlink()
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
        )
    except Exception:
        return None


def is_lock_active(lock_path: Path) -> bool:
    """Checks whether a lock is active or stale."""
    lock = read_lock(lock_path)
    if lock is None:
        return False

    # Check if shell_pid is recorded and check process status on POSIX
    if lock.shell_pid and os.name == "posix":
        try:
            os.kill(lock.shell_pid, 0)
            return True
        except OSError:
            return False

    # If lock file exists and is readable, treat as active
    return True


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
