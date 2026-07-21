import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Ensure the app module can be imported
from app import (
    ImmichGoGUI, 
    collect_paths, 
    mask_command_for_display, 
    build_environment,
    SecretStore
)
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit
from PySide6.QtCore import QUrl, Qt, QMimeData
from PySide6.QtGui import QDropEvent

# ==============================================================================
# 1. PURE LOGIC TESTS (Decoupled from GUI - Fast & Reliable)
# ==============================================================================

def test_collect_paths_single_file():
    assert collect_paths("/path/to/file.zip") == ["/path/to/file.zip"]

def test_collect_paths_multiline():
    text = "/path/one.zip\n\n/path/two.zip\n"
    assert collect_paths(text) == ["/path/one.zip", "/path/two.zip"]

def test_collect_paths_glob_expansion(tmp_path):
    # Create dummy files
    (tmp_path / "takeout-001.zip").touch()
    (tmp_path / "takeout-002.zip").touch()
    
    pattern = str(tmp_path / "takeout-*.zip")
    result = collect_paths(pattern)
    
    assert len(result) == 2
    assert all("takeout-" in p for p in result)

def test_mask_command_for_display():
    cmd = ["immich-go", "upload", "from-folder", "--server=http://local", "--api-key=super_secret_123", "/photos"]
    masked = mask_command_for_display(cmd)
    
    assert "--api-key=super_secret_123" not in masked
    assert "--api-key=********" in masked
    assert "--server=http://local" in masked  # Ensure non-secrets are untouched

def test_mask_command_from_api_key():
    cmd = ["immich-go", "upload", "from-immich", "--from-api-key=old_secret"]
    masked = mask_command_for_display(cmd)
    assert "--from-api-key=********" in masked

def test_build_environment_upload(gui):
    gui.inputs["config"]["server"].setText("http://test:2283")
    gui.inputs["config"]["api_key"].setText("my_key")
    env = gui.build_environment("upload-folder")
    assert env["IMMICH_GO_UPLOAD_SERVER"] == "http://test:2283"
    assert env["IMMICH_GO_UPLOAD_API_KEY"] == "my_key"

def test_build_environment_upload_immich(gui):
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new_key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old_key")
    env = gui.build_environment("upload-immich")
    assert env["IMMICH_GO_UPLOAD_SERVER"] == "http://new:2283"
    assert env["IMMICH_GO_UPLOAD_API_KEY"] == "new_key"
    assert env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER"] == "http://old:2283"
    assert env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY"] == "old_key"

# ==============================================================================
# 2. GUI SMOKE TESTS (Using qtbot, decoupled from internal dict structure)
# ==============================================================================

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def gui(qapp, qtbot):
    # Mock heavy startup tasks to speed up tests
    with patch.object(ImmichGoGUI, 'check_binary_version'), \
         patch.object(ImmichGoGUI, 'load_configuration'):
        gui = ImmichGoGUI()
        gui.binary_path = "./immich-go"
        qtbot.addWidget(gui)
        yield gui

def test_build_command_stack(gui):
    gui.stacked_widget.setCurrentIndex(6) # Stack
    gui.inputs["config"]["server"].setText("http://stack:2283")
    gui.inputs["config"]["api_key"].setText("stack-key")
    
    gui.inputs["stack"]["manage-burst"].setCurrentText("StackKeepRaw")
    gui.inputs["stack"]["manage-raw-jpeg"].setCurrentText("StackCoverRaw")
    gui.inputs["stack"]["manage-heic-jpeg"].setCurrentText("KeepHeic")
    gui.inputs["stack"]["manage-epson"].setChecked(True)
    gui.inputs["stack"]["time-zone"].setText("UTC")
    
    opts = gui.build_command(dry_run=True)
    
    assert "stack" in opts
    assert "--manage-burst=StackKeepRaw" in opts
    assert "--manage-raw-jpeg=StackCoverRaw" in opts
    assert "--manage-heic-jpeg=KeepHeic" in opts
    assert "--manage-epson-fastfoto=true" in opts
    assert "--time-zone=UTC" in opts
    assert "--dry-run" in opts



def test_build_command_upload_immich(gui):
    gui.stacked_widget.setCurrentIndex(3) # Upload Immich
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("local-key")
    
    gui.inputs["upload-immich"]["from-server"].setText("http://remote:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("remote-key")
    gui.inputs["upload-immich"]["from-favorite"].setChecked(True)
    gui.inputs["upload-immich"]["from-archived"].setChecked(True)
    gui.inputs["upload-immich"]["from-trash"].setChecked(True)
    gui.inputs["upload-immich"]["from-date-range"].setText("2020-01-01,2021-01-01")
    gui.inputs["upload-immich"]["from-albums"].setText("Album1, Album2")
    gui.inputs["upload-immich"]["from-minimal-rating"].setValue(3)
    gui.inputs["upload-immich"]["from-people"].setText("John, Jane")
    gui.inputs["upload-immich"]["from-tags"].setText("Vacation, Family")
    gui.inputs["upload-immich"]["from-city"].setText("Paris")
    gui.inputs["upload-immich"]["from-state"].setText("IDF")
    gui.inputs["upload-immich"]["from-country"].setText("France")
    gui.inputs["upload-immich"]["from-make"].setText("Apple")
    gui.inputs["upload-immich"]["from-model"].setText("iPhone 13")
    gui.inputs["upload-immich"]["from-skip-ssl"].setChecked(True)
    
    opts = gui.build_command(dry_run=False)
    
    assert "upload" in opts
    assert "from-immich" in opts
    assert "--server=http://local:2283" in opts
    assert "--from-server=http://remote:2283" in opts
    assert "--from-favorite=true" in opts
    assert "--from-archived=true" in opts
    assert "--from-trash=true" in opts
    assert "--from-date-range=2020-01-01,2021-01-01" in opts
    assert "--from-albums=Album1" in opts
    assert "--from-albums=Album2" in opts
    assert "--from-minimal-rating=3" in opts
    assert "--from-people=John" in opts
    assert "--from-people=Jane" in opts
    assert "--from-tags=Vacation" in opts
    assert "--from-tags=Family" in opts
    assert "--from-city=Paris" in opts
    assert "--from-state=IDF" in opts
    assert "--from-country=France" in opts
    assert "--from-make=Apple" in opts
    assert "--from-model=iPhone 13" in opts
    assert "--from-skip-verify-ssl" in opts
    assert "--dry-run" not in opts

def test_build_command_archive_folder(gui):
    gui.stacked_widget.setCurrentIndex(4) # Archive folder
    # config server/api key shouldn't be added for archive-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    
    gui.inputs["archive-folder"]["path"].setText("/source/folder")
    gui.inputs["archive-folder"]["write-to"].setText("/dest/folder")
    gui.inputs["archive-folder"]["manage-raw-jpeg"].setCurrentText("KeepRaw")
    gui.inputs["archive-folder"]["date-range"].setText("2024-01-01,2024-02-01")
    
    opts = gui.build_command(dry_run=True)
    
    assert "archive" in opts
    assert "from-folder" in opts
    assert "--server=http://local:2283" not in opts
    assert "--write-to-folder=/dest/folder" in opts
    assert "--manage-raw-jpeg=KeepRaw" in opts
    assert "--date-range=2024-01-01,2024-02-01" in opts
    assert "/source/folder" in opts
    assert "--dry-run" in opts

def test_build_command_archive_immich(gui):
    gui.stacked_widget.setCurrentIndex(5) # Archive immich
    gui.inputs["config"]["server"].setText("http://local:2283")
    
    gui.inputs["archive-immich"]["write-to"].setText("/dest/folder")
    gui.inputs["archive-immich"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["archive-immich"]["manage-raw-jpeg"].setCurrentText("KeepRaw")
    gui.inputs["archive-immich"]["from-date-range"].setText("2024-01-01,2024-02-01")
    gui.inputs["archive-immich"]["from-albums"].setText("ArchiveAlbum")
    
    opts = gui.build_command(dry_run=False)
    
    assert "archive" in opts
    assert "from-immich" in opts
    assert "--write-to-folder=/dest/folder" in opts
    assert "--manage-burst=Stack" in opts
    assert "--manage-raw-jpeg=KeepRaw" in opts
    assert "--from-date-range=2024-01-01,2024-02-01" in opts
    assert "--from-albums=ArchiveAlbum" in opts
    assert "--dry-run" not in opts


def test_global_skip_ssl_option(gui):
    gui.inputs["config"]["skip-ssl"].setChecked(True)
    gui.stacked_widget.setCurrentIndex(1)
    opts = gui.build_command(dry_run=True)
    assert "--skip-verify-ssl" in opts
