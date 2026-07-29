"""Shared pytest fixtures for Immich-Go GUI test suite."""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from gui import ImmichGoGUI


def _norm_argv(argv):
    normed = []
    for arg in argv:
        clean = str(arg).replace("\\", "/")
        if "=" in clean:
            key, val = clean.split("=", 1)
            if len(val) >= 2 and val[1] == ":" and val[0].isalpha():
                val = val[2:]
            clean = f"{key}={val}"
        else:
            if len(clean) >= 2 and clean[1] == ":" and clean[0].isalpha():
                clean = clean[2:]
        normed.append(clean)
    return normed


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(scope="session")
def gui(qapp):
    """One shared window for the whole suite.

    Session teardown must not show Save/Discard dialogs: function-scoped
    monkeypatches are already gone when this fixture exits. Use _force_close.
    """
    with (
        patch.object(ImmichGoGUI, "check_binary_version"),
        patch.object(ImmichGoGUI, "_probe_keyring", return_value=True),
        patch("PySide6.QtWidgets.QMessageBox.warning"),
        patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Discard,
        ),
    ):
        # Only skip load during construction; other tests may instantiate ImmichGoGUI
        # and need the real load_configuration implementation.
        with patch.object(ImmichGoGUI, "load_configuration"):
            g = ImmichGoGUI()
        g.binary_path = "./immich-go"
        # Never fire silent connection tests during the suite — they hit the
        # network with a 4s timeout and dominate wall time when Qt processes events.
        if hasattr(g, "_conn_test_debounce"):
            g._conn_test_debounce.stop()
            g._conn_test_debounce.timeout.disconnect()
        g._auto_test_connection = lambda: None
        g._mark_configuration_clean()
        if hasattr(g, "_mark_server_details_clean"):
            g._mark_server_details_clean()
        yield g
        g._force_close = True
        g.close()


@pytest.fixture(autouse=True)
def _reset_client_timeout(gui):
    spin = gui.inputs.get("config", {}).get("client_timeout_minutes")
    if spin is not None:
        spin.setValue(60)
    yield


@pytest.fixture(autouse=True)
def suppress_qt_dialogs(monkeypatch):
    """Suppress modal QMessageBox dialogs during each test function."""
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", MagicMock())
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", MagicMock())
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", MagicMock())
    # Discard: close-without-save path. Lock-prompt tests that need Yes override this.
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.question",
        MagicMock(return_value=QMessageBox.StandardButton.Discard),
    )


@pytest.fixture(autouse=True)
def _isolate_user_config(tmp_path, monkeypatch):
    """Keep tests off the developer's real ~/.config/immich-go-gui directory."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.delenv("IMMICH_GO_GUI_CONFIG", raising=False)
    from core.profile_manager import clear_profiles_cache

    clear_profiles_cache()
    yield
    clear_profiles_cache()


@pytest.fixture(autouse=True)
def _clear_profiles_cache():
    from core.profile_manager import clear_profiles_cache

    clear_profiles_cache()
    yield
    clear_profiles_cache()


@pytest.fixture(autouse=True)
def _reset_shared_config(gui):
    cfg = gui.inputs["config"]
    cfg["skip-ssl"].setChecked(False)
    if cfg.get("server"):
        cfg["server"].clear()
    spin = cfg.get("client_timeout_minutes")
    if spin is not None:
        spin.setValue(60)
    gui._mark_configuration_clean()
    yield
    gui.toggle_advanced(False)
    if hasattr(gui, "reset_advanced_flags"):
        gui.reset_advanced_flags()
    picasa = gui.inputs.get("upload-picasa", {})
    if "folder-album" in picasa:
        picasa["folder-album"].setCurrentIndex(0)
    if "into-album" in picasa:
        picasa["into-album"].clear()
