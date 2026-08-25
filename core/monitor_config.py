"""Monitoring configuration model and persistence.

Defines the schema for watched folders, scheduling, exclusions, filters,
network policy, and activity detection settings. Persisted as a section
inside the main TOML config via the existing config_manager.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .config_manager import _atomic_write_text, default_config_path


class NetworkPolicy(str, Enum):
    """Network policy for upload allowedness."""

    ALWAYS = "always"  # Upload on any network
    NO_METERED = "no_metered"  # Pause on metered connections
    SSID_ONLY = "ssid_only"  # Only upload on specific SSIDs


class ActivityPauseMethod(str, Enum):
    """Methods for detecting high-activity states."""

    PROCESS_LIST = "process_list"  # Named process detection
    CPU_THRESHOLD = "cpu_threshold"  # Sustained CPU load
    GPU_THRESHOLD = "gpu_threshold"  # GPU 3D usage
    FULLSCREEN = "fullscreen"  # Fullscreen/DirectX app active


@dataclass
class FolderFilter:
    """Per-folder filtering rules."""

    folder_path: str = ""
    exclude_patterns: list[str] = field(default_factory=list)  # glob patterns
    include_extensions: list[str] = field(default_factory=list)  # e.g. [".jpg", ".png"]
    exclude_extensions: list[str] = field(default_factory=list)
    max_file_size_mb: int = 0  # 0 = no limit
    min_file_size_kb: int = 0  # 0 = no limit
    skip_hidden: bool = True
    skip_system_files: bool = True

    @staticmethod
    def defaults() -> "FolderFilter":
        return FolderFilter(
            exclude_patterns=[
                "**/@eaDir/**",
                "**/@__thumb/**",
                "**/.Spotlight-V100/**",
                "**/.photostructure/**",
                "**/thumbnails/**",
                "**/Lightroom Catalog/**",
                "**/Recently Deleted/**",
                "**/$RECYCLE.BIN/**",
                "**/System Volume Information/**",
            ]
        )


@dataclass
class ActivityConfig:
    """Activity-based auto-pause settings."""

    enabled: bool = True
    detection_methods: list[ActivityPauseMethod] = field(
        default_factory=lambda: [
            ActivityPauseMethod.PROCESS_LIST,
        ]
    )
    monitored_processes: list[str] = field(
        default_factory=lambda: [
            "gamingservices.exe",
            "obs64.exe",
            "obs.exe",
            "premiere.exe",
            "afterfx.exe",
            "resolve.exe",
            "blender.exe",
            "photoshop.exe",
        ]
    )
    cpu_threshold_percent: int = 70  # % utilization
    gpu_threshold_percent: int = 60  # % utilization
    activity_grace_seconds: int = 30  # sustained activity before pause
    resume_grace_seconds: int = 60  # quiet period before auto-resume


@dataclass
class MonitorConfig:
    """Complete monitoring configuration."""

    # Master switch for scheduled/background monitoring
    monitor_enabled: bool = False

    # Watched folders (paths)
    folders: list[str] = field(default_factory=list)

    # Per-folder filters
    folder_filters: dict[str, FolderFilter] = field(default_factory=dict)

    # Concurrency
    concurrency: int = 4  # immich-go --concurrent-tasks
    max_parallel_folders: int = 3  # how many folders process at once

    # Time window for incremental scans (days back when no prior timestamp)
    days_back: int = 7

    # Scheduling
    weekly_day: int = 6  # 0=Monday, 6=Sunday
    weekly_hour: int = 3
    weekly_minute: int = 0

    monthly_rescan_day: int = 1  # 1-28
    monthly_rescan_hour: int = 4
    monthly_rescan_minute: int = 0

    # Scheduling toggle
    scheduled_weekly_enabled: bool = True
    scheduled_monthly_enabled: bool = True

    # File watcher
    file_watcher_enabled: bool = True
    watcher_debounce_seconds: int = 30  # batch changes within this window

    # Network
    network_policy: NetworkPolicy = NetworkPolicy.ALWAYS
    allowed_ssids: list[str] = field(default_factory=list)

    # Activity pause
    activity: ActivityConfig = field(default_factory=ActivityConfig)

    # Retry
    max_retries: int = 4
    retry_delays_minutes: list[int] = field(
        default_factory=lambda: [1, 5, 15, 30]
    )  # backoff schedule

    # GUI
    start_minimized: bool = False
    minimize_to_tray: bool = True
    launch_on_startup: bool = False
    tray_icon_style: str = "colorful"

    # Logging
    log_dir: str = ""

    # Advanced upload-folder options used by monitor runs
    advanced_state: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_folder_filter(self, folder: str) -> FolderFilter:
        return self.folder_filters.get(folder, FolderFilter.defaults())

    def to_dict(self) -> dict[str, Any]:
        return {
            "monitor_enabled": self.monitor_enabled,
            "folders": self.folders,
            "concurrency": self.concurrency,
            "max_parallel_folders": self.max_parallel_folders,
            "days_back": self.days_back,
            "weekly_day": self.weekly_day,
            "weekly_hour": self.weekly_hour,
            "weekly_minute": self.weekly_minute,
            "monthly_rescan_day": self.monthly_rescan_day,
            "monthly_rescan_hour": self.monthly_rescan_hour,
            "monthly_rescan_minute": self.monthly_rescan_minute,
            "scheduled_weekly_enabled": self.scheduled_weekly_enabled,
            "scheduled_monthly_enabled": self.scheduled_monthly_enabled,
            "file_watcher_enabled": self.file_watcher_enabled,
            "watcher_debounce_seconds": self.watcher_debounce_seconds,
            "network_policy": self.network_policy.value,
            "allowed_ssids": self.allowed_ssids,
            "folder_filters": {
                path: {
                    "folder_path": filt.folder_path,
                    "exclude_patterns": filt.exclude_patterns,
                    "include_extensions": filt.include_extensions,
                    "exclude_extensions": filt.exclude_extensions,
                    "max_file_size_mb": filt.max_file_size_mb,
                    "min_file_size_kb": filt.min_file_size_kb,
                    "skip_hidden": filt.skip_hidden,
                    "skip_system_files": filt.skip_system_files,
                }
                for path, filt in self.folder_filters.items()
            },
            "activity": {
                "enabled": self.activity.enabled,
                "detection_methods": [m.value for m in self.activity.detection_methods],
                "monitored_processes": self.activity.monitored_processes,
                "cpu_threshold_percent": self.activity.cpu_threshold_percent,
                "gpu_threshold_percent": self.activity.gpu_threshold_percent,
                "activity_grace_seconds": self.activity.activity_grace_seconds,
                "resume_grace_seconds": self.activity.resume_grace_seconds,
            },
            "max_retries": self.max_retries,
            "retry_delays_minutes": self.retry_delays_minutes,
            "start_minimized": self.start_minimized,
            "minimize_to_tray": self.minimize_to_tray,
            "launch_on_startup": self.launch_on_startup,
            "tray_icon_style": self.tray_icon_style,
            "log_dir": self.log_dir,
            "advanced_state": self.advanced_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MonitorConfig":
        if not isinstance(data, dict):
            return cls()
        cfg = cls()
        schedule = data.get("schedule", {})
        if isinstance(schedule, dict):
            data = {**data, **schedule}
        cfg.monitor_enabled = data.get("monitor_enabled", False)
        folders = data.get("folders", [])
        cfg.folders = (
            [str(v) for v in folders if isinstance(v, str)]
            if isinstance(folders, list)
            else []
        )
        cfg.concurrency = data.get("concurrency", 4)
        cfg.max_parallel_folders = data.get("max_parallel_folders", 3)
        cfg.days_back = data.get("days_back", 7)
        cfg.weekly_day = data.get("weekly_day", 6)
        cfg.weekly_hour = data.get("weekly_hour", 3)
        cfg.weekly_minute = data.get("weekly_minute", 0)
        cfg.monthly_rescan_day = data.get("monthly_rescan_day", 1)
        cfg.monthly_rescan_hour = data.get("monthly_rescan_hour", 4)
        cfg.monthly_rescan_minute = data.get("monthly_rescan_minute", 0)
        cfg.scheduled_weekly_enabled = data.get(
            "scheduled_weekly_enabled",
            data.get("weekly_enabled", True),
        )
        cfg.scheduled_monthly_enabled = data.get(
            "scheduled_monthly_enabled",
            data.get("monthly_enabled", True),
        )
        cfg.file_watcher_enabled = data.get("file_watcher_enabled", True)
        cfg.watcher_debounce_seconds = data.get("watcher_debounce_seconds", 30)
        raw_policy = data.get("network_policy", "always")
        if raw_policy == "ssids_only":
            raw_policy = "ssid_only"
        if raw_policy == "wifi_only":
            # Legacy wifi_only value: map to no_metered for restricted but not
            # SSID-locked policy. Users who need SSID-specific control must
            # explicitly configure ssid_only.
            raw_policy = "no_metered"
        try:
            cfg.network_policy = NetworkPolicy(raw_policy)
        except (TypeError, ValueError):
            cfg.network_policy = NetworkPolicy.ALWAYS
        ssids = data.get("allowed_ssids", [])
        cfg.allowed_ssids = (
            [str(v) for v in ssids if isinstance(v, str)]
            if isinstance(ssids, list)
            else []
        )
        filters = data.get("folder_filters", {})
        cfg.folder_filters = (
            {
                path: _folder_filter_from_dict(value)
                for path, value in filters.items()
                if isinstance(path, str) and isinstance(value, dict)
            }
            if isinstance(filters, dict)
            else {}
        )
        activity = data.get("activity")
        if isinstance(activity, dict):
            raw_methods = activity.get("detection_methods")
            if not isinstance(raw_methods, list):
                raw_methods = [ActivityPauseMethod.PROCESS_LIST.value]
            valid_method_values = {m.value for m in ActivityPauseMethod}
            cfg.activity = ActivityConfig(
                enabled=activity.get("enabled", True),
                detection_methods=[
                    ActivityPauseMethod(v)
                    for v in raw_methods
                    if v in valid_method_values
                ],
                monitored_processes=activity.get(
                    "monitored_processes", ActivityConfig().monitored_processes
                ),
                cpu_threshold_percent=activity.get("cpu_threshold_percent", 70),
                gpu_threshold_percent=activity.get("gpu_threshold_percent", 60),
                activity_grace_seconds=activity.get("activity_grace_seconds", 30),
                resume_grace_seconds=activity.get("resume_grace_seconds", 60),
            )
        cfg.max_retries = data.get("max_retries", 4)
        cfg.retry_delays_minutes = data.get("retry_delays_minutes", [1, 5, 15, 30])
        cfg.start_minimized = data.get("start_minimized", False)
        cfg.minimize_to_tray = data.get("minimize_to_tray", True)
        cfg.launch_on_startup = data.get("launch_on_startup", False)
        style = data.get("tray_icon_style", "colorful")
        if style not in (
            "colorful",
            "monochrome-system",
            "monochrome-light",
            "monochrome-dark",
        ):
            style = "colorful"
        cfg.tray_icon_style = style
        cfg.log_dir = data.get("log_dir", "")
        advanced_state = data.get("advanced_state", {})
        if isinstance(advanced_state, dict):
            from .advanced_flags import ADVANCED_FLAGS

            valid_keys = {
                definition.key for definition in ADVANCED_FLAGS.get("upload-folder", ())
            }
            valid_state: dict[str, dict[str, Any]] = {}
            for key, entry in advanced_state.items():
                if key not in valid_keys or not isinstance(entry, dict):
                    continue
                if "enabled" not in entry or not isinstance(entry["enabled"], bool):
                    continue
                value = entry.get("value")
                try:
                    json.dumps(value)
                except (TypeError, ValueError):
                    continue
                valid_state[key] = {"enabled": entry["enabled"], "value": value}
            cfg.advanced_state = valid_state
        return cfg


def _coerce_int(value: Any, default: int = 0) -> int:
    """Coerce a persisted value to int so strings never raise TypeError later."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _folder_filter_from_dict(value: dict[str, Any]) -> FolderFilter:
    fields = {k: v for k, v in value.items() if k in FolderFilter.__dataclass_fields__}
    fields["max_file_size_mb"] = _coerce_int(fields.get("max_file_size_mb", 0))
    fields["min_file_size_kb"] = _coerce_int(fields.get("min_file_size_kb", 0))
    return FolderFilter(**fields)


class MonitorConfigStore:
    """Persist monitor settings beside the active profile configuration."""

    @staticmethod
    def resolve_path(profile_name: str | None = None) -> Path:
        return default_config_path(profile_name).parent / "monitor_config.json"

    @classmethod
    def load(cls, profile_name: str | None = None) -> MonitorConfig:
        path = cls.resolve_path(profile_name)
        if not path.exists():
            return MonitorConfig()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return MonitorConfig()
            return MonitorConfig.from_dict(data)
        except (AttributeError, OSError, TypeError, ValueError):
            return MonitorConfig()

    @classmethod
    def save(cls, config: MonitorConfig, profile_name: str | None = None) -> None:
        path = cls.resolve_path(profile_name)
        _atomic_write_text(path, json.dumps(config.to_dict(), indent=2), mode=0o600)
