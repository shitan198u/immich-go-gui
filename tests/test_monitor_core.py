from datetime import UTC, datetime

from core.folder_watcher import WatchedFolder
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

    assert restored.advanced_state == {
        "log-level": {"enabled": True, "value": "debug"}
    }


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
    monkeypatch.setattr(MonitorStateStore, "resolve_path", lambda: path)
    state = MonitorState()
    state.get_folder_state(".").last_success_utc = datetime.now(UTC).isoformat()

    MonitorStateStore.save(state)

    assert MonitorStateStore.load().folders


def test_watched_folder_filters_hidden_and_extensions(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"image")
    hidden = tmp_path / ".hidden.jpg"
    hidden.write_bytes(b"hidden")
    watched = WatchedFolder(
        str(tmp_path), FolderFilter(include_extensions=[".jpg"])
    )

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
