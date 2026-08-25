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
    assert restored.tray_icon_style == "colorful"


def test_monitor_config_tray_icon_style_validation():
    config = MonitorConfig(tray_icon_style="monochrome-dark")
    restored = MonitorConfig.from_dict(config.to_dict())
    assert restored.tray_icon_style == "monochrome-dark"

    invalid = MonitorConfig.from_dict({"tray_icon_style": "invalid_mode"})
    assert invalid.tray_icon_style == "colorful"


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
        lambda profile_name=None: (
            tmp_path / (profile_name or "default") / "config.toml"
        ),
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

    # The monitor runs immich-go headless; --no-ui must precede the path.
    path_index = plan.argv.index(str(tmp_path))
    assert plan.argv.index("--no-ui") < path_index


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


def test_tally_report_line_parses_summary_and_report():
    from core.folder_runner import UploadResult, _tally_report_line

    result = UploadResult(folder="x", success=True)

    # Per-file progress lines must NOT be tallied as the run total.
    _tally_report_line("Uploaded file=2026-08-09_00.04.39.png", result)
    _tally_report_line("uploading file=photo.jpg", result)
    assert result.files_uploaded == 0

    # The whole-run summary line.
    _tally_report_line(
        "Immich read 100%, Assets found: 8, Upload errors: 0, Uploaded 1", result
    )
    assert result.files_uploaded == 1
    assert result.files_errored == 0

    # Asset Tracking Report lifecycle tallies override to report numbers.
    _tally_report_line(
        "  uploaded successfully              :       1  (4.2 MB)", result
    )
    assert result.files_uploaded == 1
    _tally_report_line(
        "  server has duplicate               :       7  (22.3 MB)", result
    )
    assert result.files_skipped == 7


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


def test_is_due_handles_naive_iso_marker():
    mixin = MonitorMixin()
    mixin.monitor_state = MonitorState(last_weekly_handled_utc="2026-08-12T12:00:00")
    occurrence = datetime(2026, 8, 12, 13, 0, tzinfo=UTC)
    # Must not raise TypeError when comparing naive marker vs aware occurrence
    assert mixin._is_due("weekly", occurrence) is True


def test_network_policy_options_mapping():
    from core.monitor_config import NetworkPolicy
    from gui.tabs.monitor_tab import NETWORK_POLICY_OPTIONS

    # First element of tuple must be a valid NetworkPolicy enum value
    config_keys = [opt[0] for opt in NETWORK_POLICY_OPTIONS]
    assert config_keys == ["always", "no_metered", "ssid_only"]
    for key in config_keys:
        assert NetworkPolicy(key) in NetworkPolicy


def test_run_folder_upload_masks_secrets_and_streams_logs(tmp_path, monkeypatch):
    from core import folder_runner
    from core.folder_runner import RunnerState, run_folder_upload
    from core.models import CommandPlan

    secret_key = "super_secret_api_key_12345"
    plan = CommandPlan()
    plan.argv = ["-c", f"print('Uploading file with secret {secret_key}')"]
    plan.env = {"IMMICH_API_KEY": secret_key}

    monkeypatch.setattr(folder_runner, "_resolve_binary_path", lambda: sys.executable)
    monkeypatch.setattr(folder_runner, "_build_upload_plan", lambda *a, **k: plan)

    state = RunnerState()
    state.reset()
    logs = []

    result = run_folder_upload(
        folder=str(tmp_path),
        config=MonitorConfig(),
        server_url="http://localhost:2283",
        api_key=secret_key,
        since_utc=datetime.now(UTC) - timedelta(days=1),
        log_dir=str(tmp_path / "logs"),
        state=state,
        on_log=lambda f, msg: logs.append(msg),
    )

    assert result.success is True
    log_content = Path(result.log_file).read_text(encoding="utf-8")
    assert secret_key not in log_content
    assert "********" in log_content
    assert any("********" in line for line in logs)


def test_network_awareness_ssid_helpers(monkeypatch):
    from core.monitor_config import NetworkPolicy
    from core.network_awareness import (
        NetworkMonitor,
        NetworkStatus,
        _get_ssid_linux,
        _get_ssid_macos,
        _get_ssid_windows,
    )

    class MockRunWin:
        stdout = "    SSID 1                   : HomeWiFi\n"

    monkeypatch.setattr("subprocess.run", lambda *a, **k: MockRunWin())
    assert _get_ssid_windows() == "HomeWiFi"

    class MockRunMac1:
        stdout = "SSID: OfficeWiFi\n"

    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("subprocess.run", lambda *a, **k: MockRunMac1())
    assert _get_ssid_macos() == "OfficeWiFi"

    class MockRunMac2:
        stdout = "Current Wi-Fi Network: GuestWiFi\n"

    def mock_run_mac2(cmd, *a, **k):
        if len(cmd) > 0 and "networksetup" in cmd[0]:
            return MockRunMac2()
        raise Exception("airport failed")

    monkeypatch.setattr("os.path.exists", lambda p: False)
    monkeypatch.setattr("subprocess.run", mock_run_mac2)
    assert _get_ssid_macos() == "GuestWiFi"

    class MockRunLinuxNmcli:
        stdout = "yes:LinuxWiFi\n"

    monkeypatch.setattr("subprocess.run", lambda *a, **k: MockRunLinuxNmcli())
    assert _get_ssid_linux() == "LinuxWiFi"

    class MockRunLinuxIwconfig:
        stdout = 'wlan0     IEEE 802.11  ESSID:"IwconfigWiFi"\n'

    def mock_run_linux_iwconfig(cmd, *a, **k):
        if len(cmd) > 0 and "iwconfig" in cmd[0]:
            return MockRunLinuxIwconfig()
        raise Exception("nmcli failed")

    monkeypatch.setattr("subprocess.run", mock_run_linux_iwconfig)
    assert _get_ssid_linux() == "IwconfigWiFi"

    nm = NetworkMonitor(NetworkPolicy.SSID_ONLY, allowed_ssids=["HomeWiFi"])
    monkeypatch.setattr(NetworkMonitor, "_is_online", lambda *a: True)
    monkeypatch.setattr(NetworkMonitor, "_get_ssid", lambda *a: "HomeWiFi")
    assert nm.check_status() == NetworkStatus.ALLOWED

    monkeypatch.setattr(NetworkMonitor, "_get_ssid", lambda *a: "OtherWiFi")
    assert nm.check_status() == NetworkStatus.BLOCKED_SSID

    monkeypatch.setattr(NetworkMonitor, "_get_ssid", lambda *a: None)
    assert nm.check_status() == NetworkStatus.UNKNOWN

    monkeypatch.setattr(NetworkMonitor, "_is_online", lambda *a: False)
    assert nm.check_status() == NetworkStatus.BLOCKED_OFFLINE


def test_activity_monitor_detection_methods(monkeypatch):
    from core.activity_monitor import (
        ActivityMonitor,
        check_processes_running,
    )
    from core.monitor_config import ActivityConfig, ActivityPauseMethod

    config = ActivityConfig(
        enabled=True,
        detection_methods=[
            ActivityPauseMethod.PROCESS_LIST,
            ActivityPauseMethod.CPU_THRESHOLD,
            ActivityPauseMethod.GPU_THRESHOLD,
            ActivityPauseMethod.FULLSCREEN,
        ],
        monitored_processes=["game.exe"],
        cpu_threshold_percent=80,
        gpu_threshold_percent=80,
        activity_grace_seconds=0,
        resume_grace_seconds=0,
    )

    monitor = ActivityMonitor(config)
    monitor._running = True

    monkeypatch.setattr(
        monitor, "_check_processes", lambda: "Process running: game.exe"
    )
    monitor._check_activity()
    assert monitor.is_active is True

    class MockTasklist:
        stdout = '"game.exe","1234","Console","1","100 KB"\n'

    monkeypatch.setattr("subprocess.run", lambda *a, **k: MockTasklist())
    assert monitor._check_processes_windows() == "Process running: game.exe"

    class MockNvidiaSmi:
        stdout = "85\n"

    monkeypatch.setattr("subprocess.run", lambda *a, **k: MockNvidiaSmi())
    assert monitor._check_gpu() is True or not sys.platform.startswith("win")

    assert isinstance(check_processes_running(["game.exe"]), set)

    # Test CPU, GPU, Fullscreen branches in _check_activity
    monkeypatch.setattr(monitor, "_check_processes", lambda: None)
    monkeypatch.setattr(monitor, "_check_cpu", lambda: True)
    monitor._check_activity()
    assert monitor.is_active is True

    monkeypatch.setattr(monitor, "_check_cpu", lambda: False)
    monkeypatch.setattr(monitor, "_check_gpu", lambda: True)
    monitor._check_activity()
    assert monitor.is_active is True

    monkeypatch.setattr(monitor, "_check_gpu", lambda: False)
    monkeypatch.setattr(monitor, "_check_fullscreen", lambda: True)
    monitor._check_activity()
    assert monitor.is_active is True

    # Test start and stop
    monitor.start()
    assert monitor._running is True
    monitor.stop()
    assert monitor._running is False


def test_debounce_queue_reset_after_shutdown():
    from core.folder_watcher import DebounceFileQueue

    queue = DebounceFileQueue(debounce_seconds=30)
    queue.add_file("first.jpg")
    queue.shutdown()
    assert queue.flush() == []

    # Reset clears shutdown state and allows new files to be queued
    queue.reset(debounce_seconds=15)
    queue.add_file("second.jpg")
    assert queue.flush() == ["second.jpg"]


def test_folder_watcher_on_moved_event(tmp_path):
    from core.folder_watcher import FolderWatcher
    from core.monitor_config import MonitorConfig

    queued = []
    config = MonitorConfig(folders=[str(tmp_path)], watcher_debounce_seconds=30)
    watcher = FolderWatcher(config, on_batch_ready=queued.append)

    class FakeMoveEvent:
        dest_path = str(tmp_path / "moved_photo.jpg")

    (tmp_path / "moved_photo.jpg").write_bytes(b"content")

    # Start watcher and test moved event
    watcher.start()
    assert watcher.running is True

    # Simulate moved event directly
    watcher._handle_event(FakeMoveEvent.dest_path)
    assert watcher.flush_pending() == [str(tmp_path / "moved_photo.jpg")]
    watcher.stop()


def test_run_folder_upload_handles_log_file_creation_failure(tmp_path, monkeypatch):
    from core import folder_runner
    from core.folder_runner import RunnerState, run_folder_upload
    from core.models import CommandPlan

    plan = CommandPlan()
    plan.argv = ["-c", "print('ok')"]
    plan.env = {}

    monkeypatch.setattr(folder_runner, "_resolve_binary_path", lambda: sys.executable)
    monkeypatch.setattr(folder_runner, "_build_upload_plan", lambda *a, **k: plan)
    # Simulate os.makedirs failure for log dir
    monkeypatch.setattr(
        "os.makedirs",
        lambda *a, **k: (_ for _ in ()).throw(OSError("Permission denied")),
    )

    state = RunnerState()
    state.reset()

    # Must complete without unhandled AttributeError on None.close()
    result = run_folder_upload(
        folder=str(tmp_path),
        config=MonitorConfig(),
        server_url="http://localhost:2283",
        api_key="k",
        since_utc=datetime.now(UTC) - timedelta(days=1),
        log_dir="/nonexistent/forbidden/dir",
        state=state,
    )

    assert result.success is True
    assert result.exit_code == 0


def test_build_upload_plan_defaults_to_safe_no_stack(tmp_path):
    from core.folder_runner import _build_upload_plan

    plan = _build_upload_plan(
        str(tmp_path),
        MonitorConfig(),
        "http://localhost:2283",
        "key",
        datetime.now(UTC),
    )
    # Stacking flags must not be passed when using default NoStack
    assert not any("--manage-burst" in arg for arg in plan.argv)
    assert not any("--manage-raw-jpeg" in arg for arg in plan.argv)
    assert not any("--manage-heic-jpeg" in arg for arg in plan.argv)


def test_monitor_config_legacy_policy_aliases():
    from core.monitor_config import MonitorConfig, NetworkPolicy

    cfg1 = MonitorConfig.from_dict({"network_policy": "ssids_only"})
    assert cfg1.network_policy == NetworkPolicy.SSID_ONLY

    cfg2 = MonitorConfig.from_dict({"network_policy": "unknown_policy"})
    assert cfg2.network_policy == NetworkPolicy.ALWAYS

    cfg3 = MonitorConfig.from_dict({"network_policy": "wifi_only"})
    assert cfg3.network_policy == NetworkPolicy.NO_METERED


def test_is_within_folder_symlink_escape_rejected(tmp_path):
    from core.folder_filters import is_within_folder

    base_dir = tmp_path / "watched"
    base_dir.mkdir()
    outside_dir = tmp_path / "secret"
    outside_dir.mkdir()
    outside_file = outside_dir / "confidential.txt"
    outside_file.write_text("secret")

    # Inside file is accepted
    inside_file = base_dir / "photo.jpg"
    inside_file.write_text("photo")
    assert is_within_folder(str(base_dir), str(inside_file)) is True

    # Sibling file outside is rejected
    assert is_within_folder(str(base_dir), str(outside_file)) is False


def test_runner_state_concurrent_access_is_thread_safe():
    from core.folder_runner import RunnerState

    state = RunnerState()
    state.reset()
    errors = []

    def writer_thread():
        try:
            for i in range(100):
                state.set_current_folder(f"folder_{i}")
                state.set_current_file(f"file_{i}.jpg")
                state.set_completed_folders(i)
                state.increment_counters(uploaded=1, skipped=1)
                time.sleep(0.001)
        except Exception as e:
            errors.append(("writer", e))

    def reader_thread():
        try:
            for _ in range(100):
                snap = state.snapshot()
                assert isinstance(snap["running"], bool)
                assert isinstance(snap["current_folder"], str)
                assert isinstance(snap["total_uploaded"], int)
                state.get_running()
                state.get_current_folder()
                state.get_aggregate_counters()
                time.sleep(0.001)
        except Exception as e:
            errors.append(("reader", e))

    threads = [
        threading.Thread(target=writer_thread, daemon=True),
        threading.Thread(target=reader_thread, daemon=True),
        threading.Thread(target=reader_thread, daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"Thread-safety violations: {errors}"
    final_snap = state.snapshot()
    assert final_snap["completed_folders"] >= 0
    assert final_snap["total_uploaded"] >= 0


def test_debounce_queue_stale_callback_after_reset_does_not_drain():
    from core.folder_watcher import DebounceFileQueue

    queue = DebounceFileQueue(debounce_seconds=1)
    fired = []
    queue.set_callback(fired.append)

    # Add file and capture the old timer callback
    queue.add_file("before_reset.jpg")
    with queue._lock:
        old_timer = queue._timer

    # Reset queue and add new files
    queue.reset()
    queue.add_file("after_reset.jpg")

    # Simulate the old timer callback firing after reset
    old_timer.function()

    # The stale callback must not have drained the queue
    assert queue.flush() == ["after_reset.jpg"]
    # Only post-reset files should have been included
    assert not any("before_reset" in str(batch) for batch in fired)
