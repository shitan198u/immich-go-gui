from unittest.mock import MagicMock

from core.binary_manager import TESTED_IMMICH_GO_VERSION
from gui import ImmichGoGUI


def test_keyring_probe_warning(monkeypatch):
    """Probe failure during init should surface a warning when keyring is selected."""

    warn = MagicMock()
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", warn)
    monkeypatch.setattr(ImmichGoGUI, "check_binary_version", lambda self: None)
    monkeypatch.setattr(ImmichGoGUI, "load_configuration", lambda self: None)
    monkeypatch.setattr(ImmichGoGUI, "_probe_keyring", lambda self: False)

    gui = ImmichGoGUI()
    gui._conn_test_debounce.stop()
    gui._force_close = True
    gui.close()
    assert warn.called
    assert "keyring" in warn.call_args[0][2].lower()


def test_about_dialog_version_dynamic(gui, monkeypatch):
    captured = {}

    def fake_about(parent, title, text):
        captured["text"] = text

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.about", fake_about)
    monkeypatch.setattr("gui.mixins.menu._gui_version", lambda: "9.9.9-test")
    gui.show_about_dialog()
    assert "9.9.9-test" in captured["text"]
    assert f"v{TESTED_IMMICH_GO_VERSION}" in captured["text"]
