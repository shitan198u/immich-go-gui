"""Unit tests for GUI application update checks."""

from unittest.mock import MagicMock, patch

from core.app_update import GuiReleaseInfo, get_latest_gui_release, is_update_available
from gui.mixins.app_update import AppUpdateMixin, clean_display_version


def test_is_update_available_compares_versions():
    assert is_update_available("1.0.0", "1.1.0") is True
    assert is_update_available("1.1.0", "1.1.0") is False
    assert is_update_available("v1.2.0", "1.1.9") is False


@patch("core.app_update.requests.get")
def test_get_latest_gui_release_parses_tag(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "tag_name": "v1.2.1",
            "html_url": "https://github.com/shitan198u/immich-go-gui/releases/tag/v1.2.1",
        },
    )
    mock_get.return_value.raise_for_status = MagicMock()

    release = get_latest_gui_release()
    assert release is not None
    assert release.version == "1.2.1"
    assert release.html_url.endswith("v1.2.1")


class _StatusLabel:
    def __init__(self):
        self._text = ""

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setStyleSheet(self, _style):
        pass


class _UpdateHost(AppUpdateMixin):
    def __init__(self):
        self.lbl_app_update_status = _StatusLabel()


def test_check_for_application_updates_up_to_date(monkeypatch):
    host = _UpdateHost()
    monkeypatch.setattr(
        "gui.mixins.app_update._gui_version",
        lambda: "1.2.0",
    )
    monkeypatch.setattr(
        "gui.mixins.app_update.get_latest_gui_release",
        lambda: GuiReleaseInfo(
            tag="v1.2.0",
            version="1.2.0",
            html_url="https://example.com/release",
        ),
    )
    host.check_for_application_updates()
    assert host.lbl_app_update_status.text().startswith("Up to date")
    assert host.app_update_status_state() == "ok"


def test_check_for_application_updates_available(monkeypatch):
    host = _UpdateHost()
    monkeypatch.setattr(
        "gui.mixins.app_update._gui_version",
        lambda: "1.1.0",
    )
    monkeypatch.setattr(
        "gui.mixins.app_update.get_latest_gui_release",
        lambda: GuiReleaseInfo(
            tag="v1.2.0",
            version="1.2.0",
            html_url="https://example.com/release",
        ),
    )
    monkeypatch.setattr("gui.mixins.app_update.QMessageBox", MagicMock())
    host.check_for_application_updates()
    assert host.app_update_status_state() == "warn"


def test_clean_display_version_strips_v_prefix():
    assert clean_display_version("v1.2.3") == "1.2.3"
