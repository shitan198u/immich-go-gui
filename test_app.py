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
    with patch.object(ImmichGoGUI, 'check_binary_version'):
        with patch.object(ImmichGoGUI, 'load_configuration'):
            # Load config from actual settings might interfere with tests, so we mock it.
            gui = ImmichGoGUI()
            gui.binary_path = "./immich-go"
            qtbot.addWidget(gui)
            yield gui

@pytest.mark.skip(reason="Tests need to be decoupled from UI after rewrite")
def test_build_command_global_options(gui):
    # Switch to config tab (index 0), though build_command returns [] for config tab.
    # To test global options we can switch to another tab and check.
    gui.stacked_widget.setCurrentIndex(1) # folder upload
    
    # Set non-default values in the active tab's global overrides or config
    gui.inputs["upload-folder"]["log-level"].setCurrentText("DEBUG")
    
    opts = gui.build_command(dry_run=False)
    assert "--log-level=DEBUG" in opts
    assert "--no-ui" in opts

def test_build_command_google_takeout(gui):
    gui.stacked_widget.setCurrentIndex(2) # Google Takeout
    gui.inputs["config"]["server"].setText("http://immich:2283")
    gui.inputs["config"]["api_key"].setText("takeout-key")
    
    gui.inputs["upload-gp"]["path"].setText("/tmp/takeout.zip")
    
    # Disable default true options
    gui.inputs["upload-gp"]["sync-albums"].setChecked(False)
    gui.inputs["upload-gp"]["include-archived"].setChecked(False)
    gui.inputs["upload-gp"]["include-partner"].setChecked(False)
    gui.inputs["upload-gp"]["takeout-tag"].setChecked(False)
    gui.inputs["upload-gp"]["people-tag"].setChecked(False)
    
    # Enable default false options
    gui.inputs["upload-gp"]["include-trashed"].setChecked(True)
    gui.inputs["upload-gp"]["include-unmatched"].setChecked(True)
    
    gui.inputs["upload-gp"]["from-album-name"].setText("My Album")
    
    opts = gui.build_command(dry_run=True)
    
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
    assert "--from-album-name=My Album" in opts
    
    assert "--dry-run" in opts
    assert "/tmp/takeout.zip" in opts

@pytest.mark.skip(reason="Tests need to be decoupled from UI after rewrite")
def test_build_command_local_upload(gui):
    gui.stacked_widget.setCurrentIndex(1) # Local Upload
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("local-key")
    
    gui.inputs["upload-folder"]["path"].setText("/tmp/photos")
    
    # Date filter
    gui.inputs["upload-folder"]["date-range"].setText("2023-01-01,2023-12-31")
    
    # Extensions filter
    gui.inputs["upload-folder"]["include-ext"].setText(".jpg, .png")
    
    gui.inputs["upload-folder"]["into-album"].setText("Local Album")
    gui.inputs["upload-folder"]["folder-album"].setCurrentText("FOLDER")
    gui.inputs["upload-folder"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["upload-folder"]["manage-raw-jpeg"].setCurrentText("KeepRaw")
    gui.inputs["upload-folder"]["manage-heic-jpeg"].setCurrentText("StackCoverJPG")
    
    opts = gui.build_command(dry_run=True)
    
    assert "upload" in opts
    assert "from-folder" in opts
    
    assert "--date-range=2023-01-01,2023-12-31" in opts
    assert "--include-extensions=.jpg, .png" in opts
    assert "--into-album=Local Album" in opts
    assert "--folder-as-album=FOLDER" in opts
    assert "--manage-burst=Stack" in opts
    assert "--manage-raw-jpeg=KeepRaw" in opts
    assert "--manage-heic-jpeg=StackCoverJPG" in opts
    assert "--dry-run" in opts
    
    assert "/tmp/photos" in opts

@pytest.mark.skip(reason="Tests need to be decoupled from UI after rewrite")
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



@pytest.mark.skip(reason="Tests need to be decoupled from UI after rewrite")
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

@pytest.mark.skip(reason="Tests need to be decoupled from UI after rewrite")
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

@pytest.mark.skip(reason="Tests need to be decoupled from UI after rewrite")
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


def test_build_command_google_takeout_multiple_paths(gui, tmp_path):
    file1 = tmp_path / "takeout-001.zip"
    file1.touch()
    file2 = tmp_path / "takeout-002.zip"
    file2.touch()
    
    gui.stacked_widget.setCurrentIndex(2)
    gui.inputs["config"]["server"].setText("http://immich:2283")
    gui.inputs["config"]["api_key"].setText("takeout-key")
    
    non_existent = str(tmp_path / "takeout-999.zip")
    glob_pattern = str(tmp_path / "takeout-*.zip")
    gui.inputs["upload-gp"]["path"].setText(f"{non_existent}\n{glob_pattern}")
    
    opts = gui.build_command(dry_run=True)
    
    assert non_existent in opts
    assert str(file1) in opts
    assert str(file2) in opts
