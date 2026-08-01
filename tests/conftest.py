"""Shared pytest fixtures for Immich-Go GUI test suite."""

import os
from unittest.mock import MagicMock, patch

import pytest


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
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(scope="session")
def _session_config_root(tmp_path_factory):
    """Redirect config to a session tmp dir BEFORE any ImmichGoGUI is built.

    The function-scoped ``_isolate_user_config`` runs too late for the
    session-scoped ``gui`` fixture (session scope is set up before function
    scope). Without this, the shared window's ``__init__`` calls
    ``active_profile_name()`` (which writes the real ``profiles.toml``) and
    ``load_config()`` (which loads the developer's real config into
    ``app_config``) against the real ``~/.config/immich-go-gui``. This closes
    that leak by redirecting XDG for the whole session.
    """
    session_dir = tmp_path_factory.mktemp("session-config")
    prev_xdg = os.environ.get("XDG_CONFIG_HOME")
    os.environ["XDG_CONFIG_HOME"] = str(session_dir / "xdg-config")
    os.environ.pop("IMMICH_GO_GUI_CONFIG", None)
    from core.profile_manager import clear_profiles_cache

    clear_profiles_cache()
    yield session_dir
    if prev_xdg is None:
        os.environ.pop("XDG_CONFIG_HOME", None)
    else:
        os.environ["XDG_CONFIG_HOME"] = prev_xdg
    clear_profiles_cache()


@pytest.fixture(scope="session")
def gui(qapp, _session_config_root):
    """Create and yield a shared GUI window for the test session.

    The window is force-closed during session teardown to avoid modal save or discard dialogs.

    Yields:
        ImmichGoGUI: The shared application window.
    """
    from PySide6.QtWidgets import QMessageBox

    from gui import ImmichGoGUI

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
        # Stop ALL background timers so tests never pay for deferred work that
        # fires when Qt processes events. `_conn_test_debounce` is the obvious
        # one; `_status_debounce` (150ms) and `_cleanup_timer` (6h) also do
        # widget work and can fire mid-test.
        for _timer_name in (
            "_conn_test_debounce",
            "_status_debounce",
            "_cleanup_timer",
            "binary_debounce",
        ):
            _timer = getattr(g, _timer_name, None)
            if _timer is not None:
                try:
                    _timer.stop()
                except Exception:
                    pass
        g._auto_test_connection = lambda: None
        g._mark_configuration_clean()
        if hasattr(g, "_mark_server_details_clean"):
            g._mark_server_details_clean()
        yield g
        g._force_close = True
        g.close()


@pytest.fixture(autouse=True)
def _reset_client_timeout(request):
    # Pure-core tests (unit marker, no `gui` fixture) must not pay the full
    # ImmichGoGUI construction cost. Only run the reset when the test actually
    # requests the shared `gui` fixture (or the gui marker is applied).
    """
    Reset the GUI client timeout control before tests that request the shared GUI fixture.

    Parameters:
        request: Pytest fixture request used to determine whether the test requests the GUI.

    Yields:
        None
    """
    if "gui" in request.fixturenames:
        gui = request.getfixturevalue("gui")
        spin = gui.inputs.get("config", {}).get("client_timeout_minutes")
        if spin is not None:
            spin.setValue(60)
    yield


@pytest.fixture(autouse=True)
def suppress_qt_dialogs(monkeypatch):
    """Suppress modal QMessageBox dialogs during each test function."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", MagicMock())
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", MagicMock())
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", MagicMock())
    # Discard: close-without-save path. Lock-prompt tests that need Yes override this.
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.question",
        MagicMock(return_value=QMessageBox.StandardButton.Discard),
    )


@pytest.fixture(autouse=True)
def _isolate_keyring(monkeypatch):
    """Prevent tests from reading, writing, or deleting real OS keyring secrets."""
    store = {}

    def mock_get_password(service, username):
        return store.get((service, username))

    def mock_set_password(service, username, password):
        store[(service, username)] = password

    def mock_delete_password(service, username):
        store.pop((service, username), None)

    monkeypatch.setattr("keyring.get_password", mock_get_password)
    monkeypatch.setattr("keyring.set_password", mock_set_password)
    monkeypatch.setattr("keyring.delete_password", mock_delete_password)
    monkeypatch.setattr("core.config_manager.keyring.get_password", mock_get_password)
    monkeypatch.setattr("core.config_manager.keyring.set_password", mock_set_password)
    monkeypatch.setattr(
        "core.config_manager.keyring.delete_password", mock_delete_password
    )
    yield store


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
def _reset_shared_config(request):
    """
    Reset shared GUI configuration before and after each test that uses the ``gui`` fixture.

    Parameters:
        request: Pytest fixture request used to determine whether the test requests ``gui``.
    """
    if "gui" not in request.fixturenames:
        yield
        return
    gui = request.getfixturevalue("gui")
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


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    """
    Prevent tests from making real HTTP requests.

    Requests that reach the patched methods raise ``RuntimeError`` immediately.
    """
    import requests

    def _deny(*args, **kwargs):
        """
        Raise an error when a test attempts an unmocked network request.

        Raises:
            RuntimeError: Always, indicating that the request must be explicitly patched.
        """
        raise RuntimeError(
            "Tests must not make real network calls. Patch requests explicitly."
        )

    for _name in ("get", "post", "put", "delete", "head", "patch"):
        monkeypatch.setattr(requests, _name, _deny)
    monkeypatch.setattr(requests.Session, "request", _deny)


@pytest.fixture(autouse=True)
def _disable_gui_auto_conn_test(monkeypatch):
    """Prevent ImmichGoGUI background connection timers from making live network requests in tests."""
    from gui.mixins.connection import ConnectionMixin

    monkeypatch.setattr(ConnectionMixin, "_auto_test_connection", lambda self: None)
