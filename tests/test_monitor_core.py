import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from core.folder_filters import is_within_folder
from core.folder_watcher import DebounceFileQueue, WatchedFolder
from core.monitor_config import (
    ActivityPauseMethod,
    FolderFilter,
    MonitorConfig,
    MonitorConfigStore,
    NetworkPolicy,
)
from core.monitor_state import MonitorState, MonitorStateStore
from core.network_awareness import NetworkMonitor, NetworkStatus
from gui.mixins.monitor_mixin import MonitorMixin


def test_monitor_config_round_trip_preserves_nested_values():
    config = MonitorConfig(
        folders=["C:/Photos"],
        network_policy=NetworkPolicy.SSID_ONLY,
        allowed_ssids=["Home"],
    )
    config.activity.detection_methods = [ActivityPauseMethod.CPU_THRESHOLD]

    restored = MonitorConfig.from_dict(config.to_dict())

    assert restored.folders == config.folders
    assert restored.network_policy == NetworkPolicy.SSID_ONLY
    assert restored.activity.detection_methods == [ActivityPauseMethod.CPU_THRESHOLD]


def test_monitor_config_round_trip_preserves_valid_advanced_state():
    config = MonitorConfig(
        advanced_state={
            "log-level": {"enabled": True, "value": "debug"},
            "unknown": {"enabled": True, "value": "discard"},
        }
    )

    restored = MonitorConfig.from_dict(config.to_dict())

    assert restored.advanced_state == {"log-level": {"enabled": True, "value": "debug"}}


def test_monitor_config_ignores_malformed_advanced_state():
    restored = MonitorConfig.from_dict(
        {
            "advanced_state": {
                "log-level": {"enabled": "yes", "value": "debug"},
                "on-errors": {"enabled": True, "value": object()},
                "not-a-flag": {"enabled": True, "value": "x"},
            }
        }
    )

    assert restored.advanced_state == {}


def test_monitor_config_store_uses_atomic_profile_file(tmp_path, monkeypatch):
    path = tmp_path / "monitor_config.json"
    monkeypatch.setattr(MonitorConfigStore, "resolve_path", lambda *_: path)
    config = MonitorConfig(monitor_enabled=True)

    MonitorConfigStore.save(config)

    assert MonitorConfigStore.load().monitor_enabled is True
    assert not path.with_suffix(".tmp").exists()


def test_monitor_state_store_round_trip(tmp_path, monkeypatch):
    path = tmp_path / "monitor_state.json"
    monkeypatch.setattr(MonitorStateStore, "resolve_path", lambda *_: path)
    state = MonitorState()
    state.get_folder_state(".").last_success_utc = datetime.now(UTC).isoformat()

    MonitorStateStore.save(state)

    assert MonitorStateStore.load().folders


def test_monitor_state_store_is_profile_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.config_manager.default_config_path",
        lambda profile_name=None: tmp_path
        / (profile_name or "default")
        / "config.toml",
    )
    state = MonitorState()
    state.last_weekly_handled_utc = "2026-08-03T03:00:00+00:00"

    MonitorStateStore.save(state, "alpha")

    assert (tmp_path / "alpha" / "monitor_state.json").exists()
    loaded = MonitorStateStore.load("alpha")
    assert loaded.last_weekly_handled_utc == "2026-08-03T03:00:00+00:00"
    assert MonitorStateStore.load("beta").last_weekly_handled_utc is None


def test_watched_folder_filters_hidden_and_extensions(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"image")
    hidden = tmp_path / ".hidden.jpg"
    hidden.write_bytes(b"hidden")
    watched = WatchedFolder(str(tmp_path), FolderFilter(include_extensions=[".jpg"]))

    assert watched.should_accept_event(str(image)) is True
    assert watched.should_accept_event(str(hidden)) is False


def test_network_unknown_ssid_is_not_allowed(monkeypatch):
    monitor = NetworkMonitor(NetworkPolicy.SSID_ONLY, ["Home"])
    monkeypatch.setattr(NetworkMonitor, "_is_online", staticmethod(lambda: True))
    monkeypatch.setattr(NetworkMonitor, "_get_ssid", staticmethod(lambda: None))

    assert monitor.check_status() == NetworkStatus.UNKNOWN


def test_refresh_watcher_status_is_safe_before_monitor_initialization():
    class Host(MonitorMixin):
        def __init__(self):
            pass

    host = Host()
    host._refresh_watcher_status()


def test_debounce_window_is_fixed_not_sliding(monkeypatch):
    timers = []

    class FakeTimer:
        def __init__(self, interval, function):
            self.interval = interval
            self.function = function
            timers.append(self)

        def start(self):
            pass

        def cancel(self):
            pass

    monkeypatch.setattr(threading, "Timer", FakeTimer)

    queue = DebounceFileQueue(debounce_seconds=30)
    queue.add_file("a.jpg")
    queue.add_file("b.jpg")
    queue.add_files(["c.jpg"])
    # The window starts on the first file and is NOT reset by later files.
    assert len(timers) == 1

    fired = []
    queue.set_callback(fired.append)
    queue._on_timeout()
    assert fired == [["a.jpg", "b.jpg", "c.jpg"]]

    # A new window starts for files added after the flush.
    queue.add_file("d.jpg")
    assert len(timers) == 2

    # After shutdown nothing is queued and no timer is started.
    queue.shutdown()
    queue.add_file("e.jpg")
    assert len(timers) == 2
    assert queue.flush() == []


def test_watched_folder_rejects_sibling_folder_with_shared_prefix(tmp_path):
    photos = tmp_path / "photos"
    photos.mkdir()
    backup = tmp_path / "photos_backup"
    backup.mkdir()
    inside = photos / "a.jpg"
    inside.write_bytes(b"x")
    outside = backup / "b.jpg"
    outside.write_bytes(b"x")

    watched = WatchedFolder(str(photos), FolderFilter())

    assert watched.should_accept_event(str(inside)) is True
    assert watched.should_accept_event(str(outside)) is False


def test_is_within_folder_boundary_safe(tmp_path):
    base = tmp_path / "photos"
    base.mkdir()

    assert is_within_folder(str(base), str(base / "sub" / "x.jpg")) is True
    assert (
        is_within_folder(str(base), str(tmp_path / "photos_backup" / "x.jpg")) is False
    )


def test_activity_monitor_resets_idle_since_on_activity(monkeypatch):
    from core.activity_monitor import ActivityMonitor
    from core.monitor_config import ActivityConfig

    monitor = ActivityMonitor(
        ActivityConfig(activity_grace_seconds=0, resume_grace_seconds=60)
    )
    monitor._running = True
    monitor._idle_since = 123.0
    monkeypatch.setattr(monitor, "_check_processes", lambda: "Process running: obs.exe")
    monkeypatch.setattr(monitor, "_schedule_next_check", lambda: None)

    monitor._check_activity()

    assert monitor._idle_since is None
    assert monitor.is_active


def test_no_metered_policy_allows_when_detection_unavailable(monkeypatch):
    monitor = NetworkMonitor(NetworkPolicy.NO_METERED)
    monkeypatch.setattr(NetworkMonitor, "_is_online", staticmethod(lambda: True))

    assert monitor.check_status() == NetworkStatus.ALLOWED


class _SchedulerHost(MonitorMixin):
    def __init__(self):
        pass


def _make_scheduler_host(tmp_path, monkeypatch) -> MonitorMixin:
    monkeypatch.setattr(
        MonitorStateStore, "resolve_path", lambda *_: tmp_path / "s.json"
    )
    host = _SchedulerHost()
    host.monitor_config = MonitorConfig()
    host.monitor_state = MonitorState()
    host._state_lock = threading.Lock()
    return host


def test_previous_weekly_time_is_most_recent_past_occurrence():
    host = _SchedulerHost()
    host.monitor_config = MonitorConfig(weekly_day=0, weekly_hour=3, weekly_minute=0)
    local_tz = datetime.now().astimezone().tzinfo

    # Wednesday 10:00 -> previous Monday 03:00
    now = datetime(2026, 8, 5, 10, 0, tzinfo=local_tz)
    assert host._previous_weekly_time(now) == datetime(
        2026, 8, 3, 3, 0, tzinfo=local_tz
    )

    # Monday 02:00 (before today's 03:00) -> previous week's Monday
    now = datetime(2026, 8, 3, 2, 0, tzinfo=local_tz)
    assert host._previous_weekly_time(now) == datetime(
        2026, 7, 27, 3, 0, tzinfo=local_tz
    )


def test_scheduler_occurrence_fires_exactly_once(tmp_path, monkeypatch):
    host = _make_scheduler_host(tmp_path, monkeypatch)
    occurrence = datetime(2026, 8, 3, 3, 0, tzinfo=UTC)

    assert host._is_due("weekly", occurrence) is True
    host._mark_triggered("weekly", occurrence)
    assert host._is_due("weekly", occurrence) is False
    # Next week's occurrence is due again.
    assert host._is_due("weekly", occurrence + timedelta(days=7)) is True
    # The marker survived persistence.
    assert MonitorStateStore.load().last_weekly_handled_utc == occurrence.isoformat()


def test_monitor_schedule_round_trips_through_persistence(gui):
    gui.schedule_group.set_values(
        {
            "weekly_enabled": True,
            "weekly_day": 2,
            "weekly_hour": 5,
            "weekly_minute": 15,
            "monthly_enabled": True,
            "monthly_day": 14,
            "monthly_hour": 6,
            "monthly_minute": 30,
        }
    )
    gui._save_monitor_state()

    # Reset widgets to different values, then reload from disk.
    gui.schedule_group.set_values(
        {
            "weekly_enabled": False,
            "weekly_day": 0,
            "weekly_hour": 0,
            "weekly_minute": 0,
            "monthly_enabled": False,
            "monthly_day": 1,
            "monthly_hour": 0,
            "monthly_minute": 0,
        }
    )
    gui._load_monitor_state()

    values = gui.schedule_group.get_values()
    assert values["weekly_enabled"] is True
    assert values["weekly_day"] == 2
    assert values["weekly_hour"] == 5
    assert values["weekly_minute"] == 15
    assert values["monthly_enabled"] is True
    assert values["monthly_day"] == 14
    assert values["monthly_hour"] == 6
    assert values["monthly_minute"] == 30


def test_tray_manager_missing_icon_does_not_crash_and_close_falls_through(
    qapp, qtbot, tmp_path
):
    """Bug A: a missing .ico must not leave the app invisible and uncloseable."""
    from PySide6.QtWidgets import QMainWindow

    from gui.tray import TrayManager

    window = QMainWindow()
    qtbot.addWidget(window)

    tray = TrayManager(
        window,
        str(tmp_path / "missing.ico"),
        str(tmp_path / "missing.png"),
    )
    assert isinstance(tray.tray_available, bool)

    class FakeEvent:
        def __init__(self):
            self.ignored = False

        def ignore(self):
            self.ignored = True

    # Minimize-to-tray disabled -> close is NOT swallowed by the tray.
    tray.set_minimize_to_tray(False)
    event = FakeEvent()
    assert tray.handle_close(event) is False
    assert event.ignored is False

    # The stored preference is gated on tray availability.
    tray.set_minimize_to_tray(True)
    assert tray._minimize_to_tray == tray.tray_available

    tray.shutdown()


def test_resolve_binary_path_raises_when_missing(monkeypatch):
    from core import folder_runner

    monkeypatch.setattr("core.binary_manager.get_binary_path", lambda *a, **k: "")

    with pytest.raises(FileNotFoundError):
        folder_runner._resolve_binary_path()


def test_resolve_binary_path_uses_binary_manager(monkeypatch):
    from core import folder_runner

    monkeypatch.setattr(
        "core.binary_manager.get_binary_path", lambda *a, **k: "/managed/immich-go"
    )

    assert folder_runner._resolve_binary_path() == "/managed/immich-go"


def test_run_folder_upload_reports_missing_binary(tmp_path, monkeypatch):
    from core.folder_runner import RunnerState, run_folder_upload

    monkeypatch.setattr("core.binary_manager.get_binary_path", lambda *a, **k: "")
    state = RunnerState()
    state.reset()

    result = run_folder_upload(
        folder=str(tmp_path),
        config=MonitorConfig(),
        server_url="http://localhost:2283",
        api_key="k",
        since_utc=datetime.now(UTC) - timedelta(days=1),
        log_dir=str(tmp_path / "logs"),
        state=state,
    )

    assert result.success is False
    assert result.message == "immich-go binary not found"
    assert result.duration_seconds > 0
    assert Path(result.log_file).exists()


def test_build_upload_plan_raises_on_validation_errors(tmp_path, monkeypatch):
    from core import folder_runner
    from core.models import CommandPlan

    def fake_build(**_kwargs):
        plan = CommandPlan()
        plan.errors.append("boom")
        return plan

    monkeypatch.setattr("core.command_builder.build_plan_from_state", fake_build)

    with pytest.raises(ValueError, match="boom"):
        folder_runner._build_upload_plan(
            str(tmp_path), MonitorConfig(), "http://s", "k", datetime.now(UTC)
        )


def test_build_upload_plan_propagates_config_flags(tmp_path):
    from core import folder_runner

    plan = folder_runner._build_upload_plan(
        str(tmp_path),
        MonitorConfig(),
        "http://localhost:2283",
        "test-key",
        datetime.now(UTC) - timedelta(days=7),
        binary_path="./immich-go",
        skip_ssl=True,
        client_timeout_minutes=20,
    )

    assert plan.errors == []
    assert "--skip-verify-ssl" in plan.argv
    assert "--client-timeout=20m" in plan.argv
    assert plan.env.get("IMMICH_GO_UPLOAD_SERVER") == "http://localhost:2283"
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert "test-key" not in " ".join(plan.argv)


def test_run_folder_upload_end_to_end_with_stub(tmp_path, monkeypatch):
    from core import folder_runner
    from core.folder_runner import RunnerState, run_folder_upload
    from core.models import CommandPlan

    stub = str(Path(__file__).parent / "stub_immich_go.py")
    plan = CommandPlan()
    plan.argv = [stub]
    plan.env = {}

    monkeypatch.setattr(folder_runner, "_resolve_binary_path", lambda: sys.executable)
    monkeypatch.setattr(folder_runner, "_build_upload_plan", lambda *a, **k: plan)

    state = RunnerState()
    state.reset()
    logs: list[tuple[str, str]] = []

    result = run_folder_upload(
        folder=str(tmp_path),
        config=MonitorConfig(),
        server_url="http://localhost:2283",
        api_key="k",
        since_utc=datetime.now(UTC) - timedelta(days=1),
        log_dir=str(tmp_path / "logs"),
        state=state,
        on_log=lambda fk, msg: logs.append((fk, msg)),
    )

    assert result.success is True
    assert result.exit_code == 0
    assert result.message == "Completed"
    assert result.duration_seconds > 0
    assert Path(result.log_file).exists()
    # Counts are no longer line-estimated; they stay 0 without a summary parse.
    assert result.files_uploaded == 0
    assert result.files_skipped == 0
    assert result.files_errored == 0
    assert logs


def test_run_folder_upload_cancel_writes_log_and_duration(tmp_path, monkeypatch):
    from core import folder_runner
    from core.folder_runner import RunnerState, run_folder_upload
    from core.models import CommandPlan

    plan = CommandPlan()
    plan.argv = ["-c", "import time; time.sleep(30)"]
    plan.env = {}

    monkeypatch.setattr(folder_runner, "_resolve_binary_path", lambda: sys.executable)
    monkeypatch.setattr(folder_runner, "_build_upload_plan", lambda *a, **k: plan)

    state = RunnerState()
    state.reset()

    def cancel_soon():
        time.sleep(0.5)
        state.cancel_event.set()
        state.pause_event.set()

    canceller = threading.Thread(target=cancel_soon, daemon=True)
    canceller.start()

    result = run_folder_upload(
        folder=str(tmp_path),
        config=MonitorConfig(),
        server_url="http://localhost:2283",
        api_key="k",
        since_utc=datetime.now(UTC) - timedelta(days=1),
        log_dir=str(tmp_path / "logs"),
        state=state,
    )

    canceller.join(timeout=5)

    assert result.success is False
    assert result.message == "Cancelled"
    assert result.duration_seconds > 0
    log_path = Path(result.log_file)
    assert log_path.exists()
    assert "Cancelled" in log_path.read_text(encoding="utf-8")
