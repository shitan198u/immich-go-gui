"""Per-folder upload state tracking for the Monitor subsystem.

Persists per-folder last-success timestamps, retry state, and upload queue
to a JSON file. No PySide6/Qt dependencies — pure Python.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock


@dataclass
class FolderUploadState:
    """Runtime state for a single watched folder."""

    last_success_utc: str | None = None  # ISO timestamp
    last_attempt_utc: str | None = None
    retry_count: int = 0
    last_error: str | None = None
    pending_files: list[str] = field(default_factory=list)  # queued file paths


@dataclass
class MonitorState:
    """Persistent state for the entire monitoring subsystem."""

    folders: dict[str, FolderUploadState] = field(
        default_factory=dict
    )  # keyed by folder path
    last_full_rescan_utc: str | None = None
    last_run_started_utc: str | None = None
    last_run_finished_utc: str | None = None
    last_run_result: str | None = None  # "success", "partial", "failure"

    def get_folder_state(self, folder: str) -> FolderUploadState:
        """Get or create state for a folder path."""
        key = str(Path(folder).resolve())
        if key not in self.folders:
            self.folders[key] = FolderUploadState()
        return self.folders[key]

    def clean_stale_folders(self, active_folders: set[str]) -> None:
        """Remove folder state entries for paths no longer in use."""
        active_keys = {str(Path(f).resolve()) for f in active_folders}
        stale = [k for k in self.folders if k not in active_keys]
        for k in stale:
            del self.folders[k]


class MonitorStateStore:
    """Load/save MonitorState to a JSON file."""

    @staticmethod
    def resolve_path() -> Path:
        from .config_manager import default_config_path

        return default_config_path().parent / "monitor_state.json"

    _write_lock = Lock()

    @staticmethod
    def load() -> MonitorState:
        path = MonitorStateStore.resolve_path()
        if not path.exists():
            return MonitorState()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = MonitorState()
            for folder_key, folder_data in data.get("folders", {}).items():
                fs = FolderUploadState(
                    last_success_utc=folder_data.get("last_success_utc"),
                    last_attempt_utc=folder_data.get("last_attempt_utc"),
                    retry_count=folder_data.get("retry_count", 0),
                    last_error=folder_data.get("last_error"),
                    pending_files=folder_data.get("pending_files", []),
                )
                state.folders[folder_key] = fs
            state.last_full_rescan_utc = data.get("last_full_rescan_utc")
            state.last_run_started_utc = data.get("last_run_started_utc")
            state.last_run_finished_utc = data.get("last_run_finished_utc")
            state.last_run_result = data.get("last_run_result")
            return state
        except (AttributeError, OSError, TypeError, ValueError):
            return MonitorState()

    @staticmethod
    def save(state: MonitorState) -> None:
        path = MonitorStateStore.resolve_path()
        data = {
            "folders": {
                k: {
                    "last_success_utc": v.last_success_utc,
                    "last_attempt_utc": v.last_attempt_utc,
                    "retry_count": v.retry_count,
                    "last_error": v.last_error,
                    "pending_files": v.pending_files,
                }
                for k, v in state.folders.items()
            },
            "last_full_rescan_utc": state.last_full_rescan_utc,
            "last_run_started_utc": state.last_run_started_utc,
            "last_run_finished_utc": state.last_run_finished_utc,
            "last_run_result": state.last_run_result,
        }
        with MonitorStateStore._write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            if os.name == "posix":
                try:
                    os.chmod(tmp, 0o600)
                except OSError:
                    pass
            os.replace(tmp, path)
