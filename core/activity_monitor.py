"""Activity-based auto-pause detection for the Monitor subsystem.

Detects high-activity states (gaming, video editing, fullscreen apps)
using process name matching, CPU/GPU thresholds, and fullscreen detection.
"""

import logging
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from .monitor_config import ActivityConfig, ActivityPauseMethod

_log = logging.getLogger(__name__)


class ActivityState(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"


@dataclass
class ActivitySnapshot:
    state: ActivityState = ActivityState.IDLE
    reason: str = ""
    trigger: ActivityPauseMethod | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ActivityMonitor:
    """Monitors system activity and signals when to auto-pause uploads."""

    def __init__(
        self,
        config: ActivityConfig,
        on_activity_start: Callable[[str], None] | None = None,
        on_activity_end: Callable[[], None] | None = None,
    ):
        self._config = config
        self._on_activity_start = on_activity_start
        self._on_activity_end = on_activity_end
        self._current_state = ActivityState.IDLE
        self._active_since: float | None = None
        self._idle_since: float | None = None
        self._running = False
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._check_interval = 5  # seconds

    @property
    def is_active(self) -> bool:
        return self._current_state == ActivityState.ACTIVE

    def start(self) -> None:
        """Start periodic activity monitoring."""
        if self._running:
            return
        if not self._config.enabled:
            _log.info("Activity monitor disabled by config")
            return

        self._running = True
        self._schedule_next_check()
        _log.info(
            "Activity monitor started (methods: %s)",
            [m.value for m in self._config.detection_methods],
        )

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        _log.info("Activity monitor stopped")

    def _schedule_next_check(self) -> None:
        """Schedule the next activity check."""
        if not self._running:
            return
        self._timer = threading.Timer(self._check_interval, self._check_activity)
        self._timer.daemon = True
        self._timer.start()

    def _check_activity(self) -> None:
        """Run all enabled detection methods and update state."""
        if not self._running:
            return

        try:
            active = False
            reason = ""

            for method in self._config.detection_methods:
                if method == ActivityPauseMethod.PROCESS_LIST:
                    proc_result = self._check_processes()
                    if proc_result:
                        active = True
                        reason = proc_result
                        break

                elif method == ActivityPauseMethod.CPU_THRESHOLD:
                    if self._check_cpu():
                        active = True
                        reason = f"CPU above {self._config.cpu_threshold_percent}%"
                        break

                elif method == ActivityPauseMethod.GPU_THRESHOLD:
                    if self._check_gpu():
                        active = True
                        reason = f"GPU above {self._config.gpu_threshold_percent}%"
                        break

                elif method == ActivityPauseMethod.FULLSCREEN:
                    if self._check_fullscreen():
                        active = True
                        reason = "Fullscreen application detected"
                        break

            now = datetime.now(UTC).timestamp()
            with self._lock:
                if active:
                    if self._active_since is None:
                        self._active_since = now
                    elapsed = now - self._active_since
                    if elapsed >= self._config.activity_grace_seconds:
                        if self._current_state != ActivityState.ACTIVE:
                            self._current_state = ActivityState.ACTIVE
                            _log.info("Activity detected: %s", reason)
                            if self._on_activity_start:
                                self._on_activity_start(reason)
                else:
                    self._active_since = None
                    if self._idle_since is None:
                        self._idle_since = now
                    elapsed_idle = now - self._idle_since
                    if elapsed_idle >= self._config.resume_grace_seconds:
                        if self._current_state == ActivityState.ACTIVE:
                            self._current_state = ActivityState.IDLE
                            _log.info("Activity ended — resuming uploads")
                            if self._on_activity_end:
                                self._on_activity_end()

        except Exception:
            _log.debug("Activity check error", exc_info=True)
        finally:
            self._schedule_next_check()

    def _check_processes(self) -> str | None:
        """Check if any monitored processes are running."""
        try:
            import psutil

            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info["name"] or ""
                    if name.lower() in [
                        p.lower() for p in self._config.monitored_processes
                    ]:
                        return f"Process running: {name}"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            # Fallback: use tasklist on Windows
            if sys.platform.startswith("win"):
                return self._check_processes_windows()
        return None

    def _check_processes_windows(self) -> str | None:
        """Fallback process check using tasklist on Windows."""
        try:
            import subprocess

            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            running = set()
            for line in result.stdout.lower().splitlines():
                parts = line.replace('"', "").split(",")
                if parts:
                    running.add(parts[0].strip())
            for proc_name in self._config.monitored_processes:
                if proc_name.lower() in running:
                    return f"Process running: {proc_name}"
        except Exception:
            pass
        return None

    def _check_cpu(self) -> bool:
        """Check if CPU usage exceeds threshold."""
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=1)
            return cpu >= self._config.cpu_threshold_percent
        except ImportError:
            return False

    def _check_gpu(self) -> bool:
        """Check GPU usage (platform-specific)."""
        if not sys.platform.startswith("win"):
            return False

        # Try nvidia-smi
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            for line in result.stdout.strip().splitlines():
                try:
                    gpu_pct = int(line.strip())
                    if gpu_pct >= self._config.gpu_threshold_percent:
                        return True
                except ValueError:
                    continue
        except Exception:
            pass

        return False

    def _check_fullscreen(self) -> bool:
        """Detect if a fullscreen application is active."""
        if sys.platform.startswith("win"):
            try:
                import ctypes

                user32 = ctypes.windll.user32

                # Get foreground window
                hwnd = user32.GetForegroundWindow()
                if not hwnd:
                    return False

                # Check if the window covers the full screen
                screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN

                # Get window rect
                class RECT(ctypes.Structure):
                    _fields_ = [
                        ("left", ctypes.c_long),
                        ("top", ctypes.c_long),
                        ("right", ctypes.c_long),
                        ("bottom", ctypes.c_long),
                    ]

                rect = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width = rect.right - rect.left
                height = rect.bottom - rect.top

                if width >= screen_width and height >= screen_height:
                    return True

            except Exception:
                pass

        return False


def check_processes_running(process_names: list[str]) -> set[str]:
    """Quick one-shot check: which processes from the list are running.

    Args:
        process_names: List of process names (e.g., ['obs64.exe', 'blender.exe']).

    Returns:
        Set of process names that are currently running.
    """
    running = set()
    names_lower = {p.lower() for p in process_names}
    try:
        import psutil

        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info["name"] or ""
                if name.lower() in names_lower:
                    running.add(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        pass
    return running
