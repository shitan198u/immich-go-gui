import pytest
import os
import sys
from unittest.mock import patch, MagicMock

from app import (
    ImmichGoGUI,
    collect_paths,
    mask_command_for_display,
    build_environment,
    SecretStore,
    DroppablePlainTextEdit,
)
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit
from PySide6.QtCore import QUrl, Qt, QMimeData, QPointF
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
    (tmp_path / "takeout-001.zip").touch()
    (tmp_path / "takeout-002.zip").touch()
    pattern = str(tmp_path / "takeout-*.zip")
    result = collect_paths(pattern)
    assert len(result) == 2
    assert all("takeout-" in p for p in result)


def test_mask_command_for_display():
    cmd = ["immich-go", "upload", "from-folder",
           "--server=http://local", "--api-key=super_secret_123", "/photos"]
    masked = mask_command_for_display(cmd)
    assert "--api-key=super_secret_123" not in masked
    assert "--api-key=********" in masked
    assert "--server=http://local" in masked


def test_mask_command_from_api_key():
    cmd = ["immich-go", "upload", "from-immich", "--from-api-key=old_secret"]
    masked = mask_command_for_display(cmd)
    assert "--from-api-key=********" in masked


def test_mask_command_admin_api_key():
    cmd = ["immich-go", "stack", "--admin-api-key=ADMIN_SECRET"]
    masked = mask_command_for_display(cmd)
    assert "ADMIN_SECRET" not in masked
    assert "--admin-api-key=********" in masked


def test_build_environment_no_trailing_spaces():
    env = build_environment("upload-folder", "http://s", "key", "http://fs", "fkey")
    for k in env:
        if k.startswith("IMMICH_GO_"):
            assert k == k.strip(), f"Trailing space in env key: {k!r}"


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


@pytest.fixture(scope="session")
def gui(qapp):
    with patch.object(ImmichGoGUI, "check_binary_version"), \
         patch.object(ImmichGoGUI, "load_configuration"):
        g = ImmichGoGUI()
        g.binary_path = "./immich-go"
        yield g
        g.close()


@pytest.fixture(autouse=True)
def _reset_shared_config(gui):
    cfg = gui.inputs["config"]
    cfg["skip-ssl"].setChecked(False)
    cfg["client_timeout"].setValue(20)
    cfg["device_uuid"].setText("")
    cfg["on_errors"].setCurrentText("stop")
    cfg["concurrent"].setValue(min(max(os.cpu_count() or 2, 1), 20))
    yield


def test_tab_switching_updates_crumb(gui):
    gui.stacked_widget.setCurrentIndex(1)  # Upload page
    gui.upload_tabs.setCurrentIndex(1)    # Google Takeout sub-tab
    assert gui.lbl_crumb.text() == "upload · from-google-photos"

    gui.upload_tabs.setCurrentIndex(2)    # From Immich sub-tab
    assert gui.lbl_crumb.text() == "upload · from-immich"

    gui.stacked_widget.setCurrentIndex(2)  # Archive page
    gui.archive_tabs.setCurrentIndex(1)    # Archive Server sub-tab
    assert gui.lbl_crumb.text() == "archive · from-immich"


def test_droppable_plain_text_edit_drop(qapp, qtbot):
    edit = DroppablePlainTextEdit()
    qtbot.addWidget(edit)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile("/path/a.zip"), QUrl.fromLocalFile("/path/b.zip")])
    event = QDropEvent(
        QPointF(0, 0), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    )
    edit.dropEvent(event)
    assert edit.toPlainText() == "/path/a.zip\n/path/b.zip"


def test_global_flag_ordering(gui):
    """Global opts (--log-level) must appear BEFORE the command (upload)."""
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)     # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["log-level"].setCurrentText("DEBUG")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    log_idx = next(i for i, o in enumerate(opts) if o.startswith("--log-level"))
    upload_idx = opts.index("upload")
    assert log_idx < upload_idx, "--log-level must come before 'upload'"


def test_pause_jobs_not_on_archive(gui):
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(0)    # archive-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("/dst")
    opts = gui.build_command(dry_run=False)
    assert not any("--pause-immich-jobs" in o for o in opts)


def test_pause_jobs_not_on_stack(gui):
    gui.stacked_widget.setCurrentIndex(3)  # stack
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    opts = gui.build_command(dry_run=False)
    assert not any("--pause-immich-jobs" in o for o in opts)


def test_on_errors_not_on_archive(gui):
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(0)    # archive-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("/dst")
    gui.inputs["config"]["on_errors"].setCurrentText("continue")
    opts = gui.build_command(dry_run=False)
    assert not any("--on-errors" in o for o in opts)


def test_client_timeout_emitted(gui):
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)     # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["client_timeout"].setValue(60)
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--client-timeout=60m" in opts


def test_device_uuid_emitted(gui):
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)     # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["device_uuid"].setText("my-device-123")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--device-uuid=my-device-123" in opts


def test_api_trace_on_upload_gp(gui):
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(1)     # upload-gp
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout")
    gui.inputs["upload-gp"]["api-trace"].setChecked(True)
    opts = gui.build_command(dry_run=False)
    assert "--api-trace" in opts


def test_api_trace_on_stack(gui):
    gui.stacked_widget.setCurrentIndex(3)  # stack
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["stack"]["api-trace"].setChecked(True)
    opts = gui.build_command(dry_run=False)
    assert "--api-trace" in opts


def test_from_client_timeout(gui):
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(2)     # upload-immich
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    gui.inputs["upload-immich"]["from-client-timeout"].setValue(60)
    opts = gui.build_command(dry_run=False)
    assert "--from-client-timeout=60m" in opts


def test_gp_multi_path(gui):
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(1)     # upload-gp
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout-001.zip\n/takeout-002.zip")
    opts = gui.build_command(dry_run=False)
    assert "/takeout-001.zip" in opts
    assert "/takeout-002.zip" in opts


def test_global_skip_ssl_option(gui):
    gui.inputs["config"]["skip-ssl"].setChecked(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)     # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=True)
    assert "--skip-verify-ssl" in opts


def test_secret_store_save_load():
    with patch("app.keyring") as mock_kr:
        mock_kr.get_password.return_value = "STORED"
        SecretStore.set_api_key("STORED")
        mock_kr.set_password.assert_called_once_with(
            "immich-go-gui", "immich_api_key", "STORED"
        )
        assert SecretStore.get_api_key() == "STORED"


def test_secret_store_migration():
    with patch("app.keyring") as mock_kr:
        mock_settings = MagicMock()
        mock_settings.value.return_value = "OLD_KEY"
        SecretStore.migrate_from_qsettings(mock_settings)
        mock_kr.set_password.assert_called_once_with(
            "immich-go-gui", "immich_api_key", "OLD_KEY"
        )
        mock_settings.remove.assert_called_once_with("api_key")


# ==============================================================================
# 3. EXISTING TESTS (adapted for 4-page navigation structure)
# ==============================================================================

def test_build_command_stack(gui):
    gui.stacked_widget.setCurrentIndex(3)  # stack
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
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(2)     # upload-immich sub-tab
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
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(0)    # archive-folder sub-tab
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
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(1)    # archive-immich sub-tab
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
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


def test_browse_takeout_zips(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    with patch("PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=(["/path/a.zip", "/path/b.zip"], "")):
        gui.browse_takeout_zips()
        assert gui.inputs["upload-gp"]["path"].toPlainText() == "/path/a.zip\n/path/b.zip"


def test_browse_folder_upload(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value="/selected/folder"):
        gui.browse_folder_upload()
        assert gui.inputs["upload-folder"]["path"].text() == "/selected/folder"


def test_native_dialog_options_passed(gui):
    with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value="/test/path") as mock_get_dir:
        gui._browse_into(MagicMock(), "Test Caption")
        mock_get_dir.assert_called_once()
        from PySide6.QtWidgets import QFileDialog
        args, kwargs = mock_get_dir.call_args
        assert args[3] == QFileDialog.Option.ShowDirsOnly or kwargs.get("options") == QFileDialog.Option.ShowDirsOnly