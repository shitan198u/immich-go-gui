import pytest
from unittest.mock import patch
from app import ImmichGoGUI
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def gui(qapp, qtbot):
    with patch.object(ImmichGoGUI, 'update_binary'):
        with patch.object(ImmichGoGUI, 'load_configuration'):
            # Load config from actual settings might interfere with tests, so we mock it.
            gui = ImmichGoGUI()
            gui.binary_path = "./immich-go"
            qtbot.addWidget(gui)
            yield gui

def test_get_global_options(gui):
    # Set non-default values
    gui.log_level_combo.setCurrentText("DEBUG")
    gui.log_type_combo.setCurrentText("JSON")
    gui.no_ui_check.setChecked(True)
    
    opts = gui.get_global_options()
    assert "--log-level=DEBUG" in opts
    assert "--log-type=JSON" in opts
    assert "--no-ui" in opts
    
    # Set default values
    gui.log_level_combo.setCurrentText("INFO")
    gui.log_type_combo.setCurrentText("TEXT")
    gui.no_ui_check.setChecked(False)
    
    opts = gui.get_global_options()
    assert "--log-level=INFO" not in opts
    assert "--log-type=TEXT" not in opts
    assert "--no-ui" not in opts

def test_get_server_options(gui):
    gui.server_url_edit.setText("http://localhost:2283")
    gui.api_key_edit.setText("my-secret-key")
    gui.skip_ssl_checkbox.setChecked(True)
    gui.client_timeout_spin.setValue(40)
    gui.device_uuid_edit.setText("TEST-UUID")
    
    opts = gui.get_server_options()
    assert "--server=http://localhost:2283" in opts
    assert "--api-key=my-secret-key" in opts
    assert "--skip-verify-ssl" in opts
    assert "--client-timeout=40m" in opts
    assert "--device-uuid=TEST-UUID" in opts

def test_get_upload_behavior_options(gui):
    gui.concurrent_tasks_spin.setValue(5)
    gui.pause_immich_jobs_check.setChecked(False)
    gui.on_errors_combo.setCurrentText("continue")
    
    opts = gui.get_upload_behavior_options()
    assert "--concurrent-tasks=5" in opts
    assert "--pause-immich-jobs=false" in opts
    assert "--on-errors=continue" in opts

def test_command_builder_google_takeout(gui):
    gui.tab_widget.setCurrentIndex(1) # Google Takeout
    gui.server_url_edit.setText("http://immich:2283")
    gui.api_key_edit.setText("takeout-key")
    
    gui.source_path_edit.setText("/tmp/takeout.zip")
    gui.zip_radio.setChecked(True)
    
    # Disable default true options
    gui.sync_albums_check.setChecked(False)
    gui.include_archived_check.setChecked(False)
    gui.include_partner_check.setChecked(False)
    gui.takeout_tag_check.setChecked(False)
    gui.people_tag_check.setChecked(False)
    
    # Enable default false options
    gui.include_trashed_check.setChecked(True)
    gui.include_unmatched_check.setChecked(True)
    gui.include_untitled_albums_check.setChecked(True)
    gui.takeout_dry_run_check.setChecked(True)
    
    gui.from_album_name_edit.setText("My Album")
    
    opts = gui.get_command_and_tab_options()
    
    # Command and sub-command
    assert "upload" in opts
    assert "from-google-photos" in opts
    
    # Server options
    assert "--server=http://immich:2283" in opts
    assert "--api-key=takeout-key" in opts
    
    # Specific options
    assert "--sync-albums=false" in opts
    assert "--include-archived=false" in opts
    assert "--include-partner=false" in opts
    assert "--takeout-tag=false" in opts
    assert "--people-tag=false" in opts
    assert "--include-trashed=true" in opts
    assert "--include-unmatched=true" in opts
    assert "--include-untitled-albums=true" in opts
    assert "--dry-run" in opts
    assert "--from-album-name=My Album" in opts
    
    # Path
    assert "/tmp/takeout.zip" in opts

def test_command_builder_local_upload(gui):
    gui.tab_widget.setCurrentIndex(2) # Local Upload
    gui.server_url_edit.setText("http://local:2283")
    gui.api_key_edit.setText("local-key")
    
    gui.local_path_edit.setText("/tmp/photos")
    
    # Date filter
    gui.date_check.setChecked(True)
    # The date is tested assuming start and end format yyyy-MM-dd
    start_str = gui.start_date.date().toString("yyyy-MM-dd")
    end_str = gui.end_date.date().toString("yyyy-MM-dd")
    
    # Extensions filter
    gui.type_check.setChecked(True)
    gui.type_edit.setText(".jpg, .png")
    
    gui.album_name_edit.setText("Local Album")
    gui.folder_as_album_combo.setCurrentText("FOLDER")
    gui.folder_as_tags_check.setChecked(True)
    gui.manage_burst_combo.setCurrentText("Stack")
    gui.manage_raw_jpeg_combo.setCurrentText("KeepRaw")
    gui.manage_heic_jpeg_combo.setCurrentText("StackCoverJPG")
    gui.dry_run_check.setChecked(True)
    
    opts = gui.get_command_and_tab_options()
    
    assert "upload" in opts
    assert "from-folder" in opts
    
    assert f"--date-range={start_str},{end_str}" in opts
    assert "--include-extensions=.jpg,.png" in opts
    assert "--into-album=Local Album" in opts
    assert "--folder-as-album=FOLDER" in opts
    assert "--folder-as-tags=true" in opts
    assert "--manage-burst=Stack" in opts
    assert "--manage-raw-jpeg=KeepRaw" in opts
    assert "--manage-heic-jpeg=StackCoverJPG" in opts
    assert "--dry-run" in opts
    
    assert "/tmp/photos" in opts

def test_command_builder_stack(gui):
    gui.tab_widget.setCurrentIndex(3) # Stack
    gui.server_url_edit.setText("http://stack:2283")
    gui.api_key_edit.setText("stack-key")
    
    gui.stack_manage_burst_combo.setCurrentText("StackKeepRaw")
    gui.stack_manage_raw_jpeg_combo.setCurrentText("StackCoverRaw")
    gui.stack_manage_heic_jpeg_combo.setCurrentText("KeepHeic")
    gui.manage_epson_fastfoto_check.setChecked(True)
    gui.stack_time_zone_edit.setText("UTC")
    gui.stack_dry_run_check.setChecked(True)
    
    opts = gui.get_command_and_tab_options()
    
    assert "stack" in opts
    assert "--manage-burst=StackKeepRaw" in opts
    assert "--manage-raw-jpeg=StackCoverRaw" in opts
    assert "--manage-heic-jpeg=KeepHeic" in opts
    assert "--manage-epson-fastfoto=true" in opts
    assert "--time-zone=UTC" in opts
    assert "--dry-run" in opts

def test_update_command_preview(gui):
    # This tests the full assembly of the command
    gui.tab_widget.setCurrentIndex(3) # Stack
    gui.server_url_edit.setText("http://preview:2283")
    gui.api_key_edit.setText("preview-key")
    gui.stack_manage_burst_combo.setCurrentText("Stack")
    
    gui.update_command_preview()
    
    preview_text = gui.command_preview.toPlainText()
    assert "./immich-go" in preview_text
    assert "stack" in preview_text
    assert "--server=http://preview:2283" in preview_text
    assert "--api-key=preview-key" in preview_text
    assert "--manage-burst=Stack" in preview_text
