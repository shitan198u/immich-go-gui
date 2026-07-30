"""Unit tests for GUI application update checks."""

from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QMessageBox

from core.app_update import (
    GuiReleaseInfo,
    clean_gui_release_version,
    get_latest_gui_release,
    is_parseable_semver,
    is_update_available,
)
from gui.mixins.app_update import AppUpdateMixin, clean_display_version


def _drain_update_check() -> None:
    """Wait for the off-thread update check to finish and deliver its result."""
    from PySide6.QtCore import QThreadPool
    from PySide6.QtWidgets import QApplication

    QThreadPool.globalInstance().waitForDone()
    QApplication.processEvents()


def test_is_update_available_compares_versions():
    assert is_update_available("1.0.0", "1.1.0") is True
    assert is_update_available("1.1.0", "1.1.0") is False
    assert is_update_available("v1.2.0", "1.1.9") is False


def test_clean_gui_release_version_strips_release_please_tag():
    assert clean_gui_release_version("immich-go-gui-v1.2.0") == "1.2.0"
    assert clean_gui_release_version("v1.2.1") == "1.2.1"


def test_is_update_available_dev_build_never_reports_update():
    assert is_parseable_semver("dev") is False
    assert is_update_available("dev", "1.2.0") is False
    assert is_update_available("dev", "immich-go-gui-v1.2.0") is False


@patch("core.app_update.requests.get")
def test_get_latest_gui_release_parses_release_please_tag(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "tag_name": "immich-go-gui-v1.2.0",
            "html_url": "https://github.com/shitan198u/immich-go-gui/releases/tag/immich-go-gui-v1.2.0",
        },
    )
    mock_get.return_value.raise_for_status = MagicMock()

    release = get_latest_gui_release()
    assert release is not None
    assert release.version == "1.2.0"


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
    monkeypatch.setattr("gui.mixins.app_update.QMessageBox", MagicMock())
    host.check_for_application_updates()
    _drain_update_check()
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
    _drain_update_check()
    assert host.app_update_status_state() == "warn"


def test_check_for_application_updates_dev_build(monkeypatch):
    host = _UpdateHost()
    monkeypatch.setattr(
        "gui.mixins.app_update._gui_version",
        lambda: "dev",
    )
    monkeypatch.setattr(
        "gui.mixins.app_update.get_latest_gui_release",
        lambda: GuiReleaseInfo(
            tag="immich-go-gui-v1.2.0",
            version="1.2.0",
            html_url="https://example.com/release",
        ),
    )
    monkeypatch.setattr("gui.mixins.app_update.QMessageBox", MagicMock())
    host.check_for_application_updates()
    _drain_update_check()
    assert host.lbl_app_update_status.text().startswith("Development build")
    assert "1.2.0" in host.lbl_app_update_status.text()
    assert host.app_update_status_state() == "default"


def test_check_for_application_updates_network_error(monkeypatch):
    host = _UpdateHost()
    monkeypatch.setattr(
        "gui.mixins.app_update._gui_version",
        lambda: "1.2.0",
    )
    monkeypatch.setattr(
        "gui.mixins.app_update.get_latest_gui_release",
        lambda: None,
    )
    monkeypatch.setattr("gui.mixins.app_update.QMessageBox", MagicMock())
    host.check_for_application_updates()
    _drain_update_check()
    assert host.lbl_app_update_status.text() == "Could not check for updates."
    assert host.app_update_status_state() == "err"


def test_check_for_application_updates_opens_download_page(monkeypatch):
    host = _UpdateHost()
    monkeypatch.setattr(
        "gui.mixins.app_update._gui_version",
        lambda: "1.1.0",
    )
    release_url = "https://example.com/release"
    monkeypatch.setattr(
        "gui.mixins.app_update.get_latest_gui_release",
        lambda: GuiReleaseInfo(
            tag="v1.2.0",
            version="1.2.0",
            html_url=release_url,
        ),
    )
    open_mock = MagicMock()
    monkeypatch.setattr("gui.mixins.app_update.webbrowser.open", open_mock)

    msgbox_mock = MagicMock()
    msgbox_mock.ButtonRole = QMessageBox.ButtonRole
    msgbox_mock.StandardButton = QMessageBox.StandardButton
    msg = MagicMock()
    open_btn = MagicMock()
    msg.addButton.return_value = open_btn
    msg.clickedButton.return_value = open_btn
    msgbox_mock.return_value = msg
    monkeypatch.setattr("gui.mixins.app_update.QMessageBox", msgbox_mock)

    host.check_for_application_updates()
    _drain_update_check()
    open_mock.assert_called_once_with(release_url)


def test_clean_display_version_strips_v_prefix():
    assert clean_display_version("v1.2.3") == "1.2.3"
    assert clean_display_version("immich-go-gui-v1.2.0") == "1.2.0"
