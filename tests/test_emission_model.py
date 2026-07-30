"""Integration tests for the simplified emission model."""

from tests.conftest import _norm_argv


def test_simple_mode_no_optional_flags(gui):
    """Simple mode emits connection, global timeout, and positional path."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--server=http://local:2283" in opts
    assert "/photos" in _norm_argv(opts)
    assert "--client-timeout=60m" in opts
    assert not any("--log-level" in o for o in opts)
    assert not any("--on-errors" in o for o in opts)


def test_advanced_mode_enabled_row_emits(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["on-errors"].set_state(
        {"enabled": True, "value": "continue"}
    )
    opts = gui.build_command(dry_run=False)
    assert "--on-errors=continue" in opts


def test_advanced_mode_disabled_row_skips(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["on-errors"].set_state(
        {"enabled": False, "value": "continue"}
    )
    opts = gui.build_command(dry_run=False)
    assert not any("--on-errors" in o for o in opts)


def test_config_client_timeout_emits(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    from PySide6.QtWidgets import QSpinBox
    spin = QSpinBox()
    spin.setValue(90)
    gui.inputs["config"]["client_timeout_minutes"] = spin
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--client-timeout=90m" in opts


def test_advanced_mode_log_level_row_emits(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["log-level"].set_state(
        {"enabled": True, "value": "DEBUG"}
    )
    opts = gui.build_command(dry_run=False)
    assert "--log-level=DEBUG" in opts


def test_advanced_mode_pause_jobs_row_emits(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["admin_api_key"].setText("admin")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["pause-jobs"].set_state(
        {"enabled": True, "value": True}
    )
    opts = gui.build_command(dry_run=False)
    from core.command_builder import FlagEmitter

    emitter = FlagEmitter("upload-folder")
    assert any(emitter._flag_name_from_arg(o) == "pause-immich-jobs" for o in opts)


def test_advanced_mode_picasa_folder_album_emitted(gui):
    """Picasa folder-album stays on simple widget in advanced mode (no mode=both)."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(3)  # upload-picasa
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-picasa"]["path"].setText("/pics")
    gui.inputs["upload-picasa"]["folder-album"].setCurrentText("FOLDER")
    opts = gui.build_command(dry_run=False)
    assert "--folder-as-album=FOLDER" in opts
