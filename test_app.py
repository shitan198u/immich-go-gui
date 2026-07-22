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
    CommandPlan,
    ValidationResult,
    normalize_server_url,
    validate_date_range,
    load_binary_metadata,
    save_binary_metadata,
    get_binary_path,
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


def test_normalize_server_url_adds_scheme():
    assert normalize_server_url("localhost:2283") == "http://localhost:2283"


def test_normalize_server_url_strips_trailing_slash():
    assert normalize_server_url("http://localhost:2283/") == "http://localhost:2283"


def test_normalize_server_url_preserves_https():
    assert normalize_server_url("https://photos.example.com/") == "https://photos.example.com"


def test_normalize_server_url_empty():
    assert normalize_server_url("") == ""
    assert normalize_server_url("   ") == ""


def test_mask_command_for_display():
    cmd = ["immich-go", "upload", "from-folder",
           "--server=http://local", "--api-key=super_secret_123", "/photos"]
    masked = mask_command_for_display(cmd)
    assert "--api-key=super_secret_123" not in masked
    assert "--api-key=********" in masked
    assert "--server=http://local" in masked


def test_mask_command_space_separated():
    cmd = ["immich-go", "upload", "from-folder", "--api-key", "super_secret", "/photos"]
    masked = mask_command_for_display(cmd)
    assert "super_secret" not in masked
    assert "********" in masked
    assert "--api-key" in masked


def test_mask_command_from_api_key():
    cmd = ["immich-go", "upload", "from-immich", "--from-api-key=old_secret"]
    masked = mask_command_for_display(cmd)
    assert "--from-api-key=********" in masked


def test_mask_command_admin_api_key():
    cmd = ["immich-go", "stack", "--admin-api-key=ADMIN_SECRET"]
    masked = mask_command_for_display(cmd)
    assert "ADMIN_SECRET" not in masked
    assert "--admin-api-key=********" in masked


def test_validate_date_range():
    assert validate_date_range("") is True
    assert validate_date_range("2023") is True
    assert validate_date_range("2023-07") is True
    assert validate_date_range("2023-07-15") is True
    assert validate_date_range("2023-01-01,2023-12-31") is True
    assert validate_date_range("invalid-date") is False


def test_build_environment_no_trailing_spaces():
    env = build_environment("upload-folder", "http://s", "key", "http://fs", "fkey")
    for k in env:
        if k.startswith("IMMICH_GO_"):
            assert k == k.strip(), f"Trailing space in env key: {k!r}"


def test_api_key_never_in_argv(gui):
    """Secrets must not appear in plan.argv for any tab."""
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("super_secret_key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(dry_run=False)

    for part in plan.argv:
        assert "super_secret_key" not in part
        assert "--api-key" not in part

    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "super_secret_key"


def test_from_api_key_never_in_argv(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new_key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old_secret")

    plan = gui.build_plan(dry_run=False)

    for part in plan.argv:
        assert "old_secret" not in part
        assert "--from-api-key" not in part

    assert plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY") == "old_secret"


def test_archive_folder_no_server_in_argv(gui):
    """archive-folder should not have --server or --api-key."""
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("/dst")

    plan = gui.build_plan(dry_run=False)

    assert not any("--server" in p for p in plan.argv)
    assert not any("--api-key" in p for p in plan.argv)


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
    with patch("core.config_manager.keyring") as mock_kr:
        mock_kr.get_password.return_value = "STORED"
        SecretStore.set_api_key("STORED")
        mock_kr.set_password.assert_called_once_with(
            "immich-go-gui", "default:api_key", "STORED"
        )
        assert SecretStore.get_api_key() == "STORED"


def test_secret_store_migration():
    with patch("core.config_manager.keyring") as mock_kr:
        mock_kr.get_password.return_value = "OLD_KEY"
        mock_settings = MagicMock()
        mock_settings.value.return_value = "OLD_KEY"
        SecretStore.migrate_from_qsettings(mock_settings)
        mock_kr.set_password.assert_called_once_with(
            "immich-go-gui", "default:api_key", "OLD_KEY"
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


# ==============================================================================
# GOLDEN COMMAND TESTS (§4.2)
# ==============================================================================

def test_golden_upload_folder(gui):
    """Golden: upload-folder with typical options."""
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["skip-ssl"].setChecked(False)
    gui.inputs["config"]["client_timeout"].setValue(20)
    cpu_default = min(max(os.cpu_count() or 2, 1), 20)
    gui.inputs["config"]["concurrent"].setValue(cpu_default)
    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.inputs["upload-folder"]["include-type"].setCurrentText("all")
    gui.inputs["upload-folder"]["folder-album"].setCurrentText("NONE")
    gui.inputs["upload-folder"]["into-album"].setText("")
    gui.inputs["upload-folder"]["overwrite"].setChecked(False)
    gui.inputs["upload-folder"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["upload-folder"]["manage-raw-jpeg"].setCurrentText("NoStack")
    gui.inputs["upload-folder"]["manage-heic-jpeg"].setCurrentText("NoStack")
    gui.inputs["upload-folder"]["date-range"].setText("")
    gui.inputs["upload-folder"]["include-ext"].setText("")
    gui.inputs["upload-folder"]["exclude-ext"].setText("")
    gui.inputs["upload-folder"]["ban-file"].setPlainText("")
    gui.inputs["upload-folder"]["ignore-sidecar"].setChecked(False)
    gui.inputs["upload-folder"]["date-from-name"].setChecked(True)
    gui.inputs["upload-folder"]["tag"].setText("")
    gui.inputs["upload-folder"]["session-tag"].setChecked(False)
    gui.inputs["upload-folder"]["folder-tags"].setChecked(False)
    gui.inputs["upload-folder"]["api-trace"].setChecked(False)
    gui.inputs["upload-folder"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "upload", "from-folder",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "/photos",
    ]
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert not any("--api-key" in p for p in plan.argv)


def test_golden_upload_gp(gui):
    """Golden: upload from-google-photos with partner + sync."""
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["skip-ssl"].setChecked(False)
    gui.inputs["config"]["client_timeout"].setValue(20)
    cpu_default = min(max(os.cpu_count() or 2, 1), 20)
    gui.inputs["config"]["concurrent"].setValue(cpu_default)
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout-001.zip\n/takeout-002.zip")
    gui.inputs["upload-gp"]["include-type"].setCurrentText("all")
    gui.inputs["upload-gp"]["into-album"].setText("")
    gui.inputs["upload-gp"]["include-unmatched"].setChecked(False)
    gui.inputs["upload-gp"]["include-partner"].setChecked(True)
    gui.inputs["upload-gp"]["sync-albums"].setChecked(True)
    gui.inputs["upload-gp"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["upload-gp"]["manage-heic-jpeg"].setCurrentText("NoStack")
    gui.inputs["upload-gp"]["from-album-name"].setText("")
    gui.inputs["upload-gp"]["include-archived"].setChecked(True)
    gui.inputs["upload-gp"]["include-trashed"].setChecked(False)
    gui.inputs["upload-gp"]["partner-album"].setText("")
    gui.inputs["upload-gp"]["takeout-tag"].setChecked(True)
    gui.inputs["upload-gp"]["people-tag"].setChecked(True)
    gui.inputs["upload-gp"]["tag"].setText("")
    gui.inputs["upload-gp"]["session-tag"].setChecked(False)
    if "api-trace" in gui.inputs["upload-gp"]:
        gui.inputs["upload-gp"]["api-trace"].setChecked(False)
    gui.inputs["upload-gp"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "upload", "from-google-photos",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "/takeout-001.zip",
        "/takeout-002.zip",
    ]


def test_golden_stack(gui):
    """Golden: stack with options."""
    gui.stacked_widget.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["skip-ssl"].setChecked(False)
    gui.inputs["config"]["client_timeout"].setValue(20)
    cpu_default = min(max(os.cpu_count() or 2, 1), 20)
    gui.inputs["config"]["concurrent"].setValue(cpu_default)
    gui.inputs["stack"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["stack"]["manage-raw-jpeg"].setCurrentText("StackCoverRaw")
    gui.inputs["stack"]["manage-heic-jpeg"].setCurrentText("StackCoverJPG")
    gui.inputs["stack"]["time-zone"].setText("UTC")
    gui.inputs["stack"]["manage-epson"].setChecked(True)
    if "api-trace" in gui.inputs["stack"]:
        gui.inputs["stack"]["api-trace"].setChecked(False)
    gui.inputs["stack"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "stack",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "--manage-raw-jpeg=StackCoverRaw",
        "--manage-heic-jpeg=StackCoverJPG",
        "--time-zone=UTC",
        "--manage-epson-fastfoto=true",
    ]


def test_golden_archive_folder(gui):
    """Golden: archive from-folder (no server)."""
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["archive-folder"]["path"].setText("/messy/photos")
    gui.inputs["archive-folder"]["write-to"].setText("/organized")
    gui.inputs["archive-folder"]["manage-raw-jpeg"].setCurrentText("KeepRaw")
    gui.inputs["archive-folder"]["date-range"].setText("2024")
    gui.inputs["archive-folder"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=True)

    assert plan.argv == [
        "archive", "from-folder",
        "--write-to-folder=/organized",
        "--manage-raw-jpeg=KeepRaw",
        "--date-range=2024",
        "--dry-run",
        "/messy/photos",
    ]
    assert not any("--server" in p for p in plan.argv)


def test_golden_upload_immich(gui):
    """Golden: upload from-immich with filters."""
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new-key")
    gui.inputs["config"]["skip-ssl"].setChecked(False)
    gui.inputs["config"]["client_timeout"].setValue(20)
    cpu_default = min(max(os.cpu_count() or 2, 1), 20)
    gui.inputs["config"]["concurrent"].setValue(cpu_default)
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    if "from-client-timeout" in gui.inputs["upload-immich"]:
        gui.inputs["upload-immich"]["from-client-timeout"].setValue(20)
    gui.inputs["upload-immich"]["from-favorite"].setChecked(True)
    gui.inputs["upload-immich"]["from-archived"].setChecked(False)
    gui.inputs["upload-immich"]["from-trash"].setChecked(False)
    gui.inputs["upload-immich"]["from-date-range"].setText("2023")
    gui.inputs["upload-immich"]["from-albums"].setText("Family, Travel")
    gui.inputs["upload-immich"]["from-minimal-rating"].setValue(0)
    gui.inputs["upload-immich"]["from-people"].setText("")
    gui.inputs["upload-immich"]["from-tags"].setText("")
    gui.inputs["upload-immich"]["from-city"].setText("")
    gui.inputs["upload-immich"]["from-state"].setText("")
    gui.inputs["upload-immich"]["from-country"].setText("")
    gui.inputs["upload-immich"]["from-make"].setText("")
    gui.inputs["upload-immich"]["from-model"].setText("")
    gui.inputs["upload-immich"]["from-skip-ssl"].setChecked(False)
    if "api-trace" in gui.inputs["upload-immich"]:
        gui.inputs["upload-immich"]["api-trace"].setChecked(False)
    gui.inputs["upload-immich"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "upload", "from-immich",
        "--server=http://new:2283",
        "--from-server=http://old:2283",
        "--from-favorite=true",
        "--from-date-range=2023",
        "--from-albums=Family",
        "--from-albums=Travel",
    ]
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "new-key"
    assert plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY") == "old-key"
    assert not any("--api-key" in p for p in plan.argv)
    assert not any("--from-api-key" in p for p in plan.argv)


def test_golden_archive_immich(gui):
    """Golden: archive from-immich with options."""
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["skip-ssl"].setChecked(False)
    gui.inputs["config"]["client_timeout"].setValue(20)
    cpu_default = min(max(os.cpu_count() or 2, 1), 20)
    gui.inputs["config"]["concurrent"].setValue(cpu_default)
    gui.inputs["archive-immich"]["write-to"].setText("/backup/photos")
    gui.inputs["archive-immich"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["archive-immich"]["manage-raw-jpeg"].setCurrentText("KeepRaw")
    gui.inputs["archive-immich"]["from-date-range"].setText("2024")
    gui.inputs["archive-immich"]["from-albums"].setText("Family")
    gui.inputs["archive-immich"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "archive", "from-immich",
        "--server=http://localhost:2283",
        "--write-to-folder=/backup/photos",
        "--manage-burst=Stack",
        "--manage-raw-jpeg=KeepRaw",
        "--from-date-range=2024",
        "--from-albums=Family",
    ]
    assert plan.env.get("IMMICH_GO_ARCHIVE_API_KEY") == "test-key"
    assert not any("--api-key" in p for p in plan.argv)


# ==========================================================
# PURE CORE MODULE UNIT TESTS (NO QT REQUIRED)
# ==========================================================

from core.binary_manager import BinaryManager, get_version_support
from core.command_builder import build_plan_from_state
from core.config_manager import load_config, save_config
from core.models import AppConfig, VersionSupport


def test_build_plan_from_state_upload_folder_golden():
    config_state = {
        "server": "http://localhost:2283",
        "api_key": "test-key",
        "skip-ssl": False,
        "client_timeout": 20,
        "concurrent": 8,
        "concurrent_default": 8,
        "device_uuid": "",
        "on_errors": "stop",
        "on_errors_tolerance": 10,
        "pause_jobs": True,
    }

    tab_state = {
        "path": "/photos",
        "include-type": "all",
        "folder-album": "NONE",
        "into-album": "",
        "manage-burst": "Stack",
        "manage-raw-jpeg": "NoStack",
        "manage-heic-jpeg": "NoStack",
        "date-range": "",
        "include-ext": "",
        "exclude-ext": "",
        "ban-file": "",
        "ignore-sidecar": False,
        "date-from-name": True,
        "tag": "",
        "session-tag": False,
        "folder-tags": False,
        "on-errors": "stop",
        "overwrite": False,
        "pause-jobs": True,
        "log-level": "INFO",
        "api-trace": False,
    }

    plan = build_plan_from_state(
        tab_key="upload-folder",
        config_state=config_state,
        tab_state=tab_state,
        binary_path="./immich-go",
        dry_run=False,
        base_env={},
    )

    assert plan.argv == [
        "upload",
        "from-folder",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "/photos",
    ]

    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert not any("--api-key" in part for part in plan.argv)


def test_version_support_tested():
    assert get_version_support("0.32.0") == VersionSupport.TESTED
    assert get_version_support("v0.32.0") == VersionSupport.TESTED


def test_version_support_unsupported_old():
    assert get_version_support("0.31.0") == VersionSupport.UNSUPPORTED_OLD


def test_version_support_untested_new():
    assert get_version_support("0.33.0") == VersionSupport.UNTESTED_NEW


def test_update_decision_allows_tested_version():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.31.0",
        latest_version="0.32.0",
        allow_untested=False,
        release_notes="",
    )

    assert decision.allowed is True
    assert decision.requires_confirmation is True


def test_update_decision_blocks_untested_by_default():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.32.0",
        latest_version="0.33.0",
        allow_untested=False,
        release_notes="",
    )

    assert decision.allowed is False


def test_update_decision_allows_untested_when_enabled():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.32.0",
        latest_version="0.33.0",
        allow_untested=True,
        release_notes="",
    )

    assert decision.allowed is True
    assert decision.requires_confirmation is True


def test_config_roundtrip(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(cfg_file))

    cfg = AppConfig()
    cfg.server_url = "http://localhost:2283"
    cfg.skip_ssl = True
    cfg.client_timeout_minutes = 60

    save_config(cfg)
    loaded = load_config()

    assert loaded.server_url == "http://localhost:2283"
    assert loaded.skip_ssl is True
    assert loaded.client_timeout_minutes == 60


# ==============================================================================
# SECTION 8: VALIDATION & NETWORK TESTS
# ==============================================================================

import requests
from core.validation import (
    clean_date_range,
    validate_date_range as validate_date_range_core,
    normalize_extensions_csv,
    normalize_list_csv,
    has_glob_pattern,
    expand_source_paths,
    validate_destination_folder,
)
from core.network import test_immich_connection as run_test_immich_connection


def test_clean_date_range():
    assert clean_date_range("  2023-01-01 , 2023-12-31  ") == "2023-01-01,2023-12-31"
    assert clean_date_range("2023") == "2023"
    assert clean_date_range("") == ""


def test_validate_date_range_extended():
    ok, err = validate_date_range_core("2023")
    assert ok is True and err is None

    ok, err = validate_date_range_core("2023-07")
    assert ok is True and err is None

    ok, err = validate_date_range_core("2023-07-15")
    assert ok is True and err is None

    ok, err = validate_date_range_core("2023-01-01, 2023-12-31")
    assert ok is True and err is None

    # Invalid month
    ok, err = validate_date_range_core("2023-13")
    assert ok is False and "month" in err.lower()

    # Invalid day
    ok, err = validate_date_range_core("2023-02-30")
    assert ok is False and "day" in err.lower()

    # Start date after end date
    ok, err = validate_date_range_core("2023-12-31,2023-01-01")
    assert ok is False and "cannot be after" in err.lower()


def test_normalize_extensions_csv():
    assert normalize_extensions_csv(".JPG, png , .heic, jpg") == ".jpg,.png,.heic"
    assert normalize_extensions_csv("  RAW, .CR2, raw ") == ".raw,.cr2"
    assert normalize_extensions_csv("") == ""


def test_normalize_list_csv():
    assert normalize_list_csv(" vacation, family/reunion , ") == ["vacation", "family/reunion"]
    assert normalize_list_csv("") == []


def test_glob_and_path_validation(tmp_path):
    f1 = tmp_path / "photo1.jpg"
    f1.touch()
    
    assert has_glob_pattern("*.jpg") is True
    assert has_glob_pattern("/path/to/file") is False

    expanded, warnings = expand_source_paths(f"{tmp_path}/*.jpg")
    assert len(expanded) == 1
    assert len(warnings) == 0

    non_existent = str(tmp_path / "non_existent_folder")
    expanded, warnings = expand_source_paths(non_existent)
    assert len(warnings) == 1
    assert "does not exist" in warnings[0]


def test_destination_validation(tmp_path):
    src_dir = tmp_path / "photos"
    src_dir.mkdir()
    dest_dir = src_dir / "archive"
    dest_dir.mkdir()

    warnings = validate_destination_folder(str(dest_dir), [str(src_dir)])
    assert len(warnings) == 1
    assert "inside the source path" in warnings[0]


def test_network_connection_success():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"version": "v1.100.0"}
        mock_get.return_value = mock_resp

        res = run_test_immich_connection("http://localhost:2283", "secret_key")
        assert res.ok is True
        assert res.status_code == 200
        assert "v1.100.0" in res.message
        assert res.server_version == "v1.100.0"


def test_network_connection_auth_failure():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        res = run_test_immich_connection("http://localhost:2283", "bad_key")
        assert res.ok is False
        assert res.status_code == 401
        assert "Authentication failed" in res.message


def test_network_connection_ssl_error():
    with patch("requests.get", side_effect=requests.exceptions.SSLError):
        res = run_test_immich_connection("https://localhost:2283", "secret_key")
        assert res.ok is False
        assert "SSL certificate verification failed" in res.message


def test_network_connection_timeout():
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        res = run_test_immich_connection("http://localhost:2283", "secret_key")
        assert res.ok is False
        assert "timed out" in res.message


def test_command_builder_destructive_warnings():
    from core.command_builder import build_plan_from_state

    config_state = {"server": "http://localhost:2283", "api_key": "test_key"}
    tab_state = {
        "path": "/photos",
        "manage-raw-jpeg": "KeepJPG",
        "manage-burst": "StackKeepJPEG",
    }

    plan = build_plan_from_state(
        tab_key="upload-folder",
        config_state=config_state,
        tab_state=tab_state,
        binary_path="./immich-go",
        dry_run=False,
    )

    warn_text = " ".join(plan.warnings)
    assert "KeepJPG may delete the RAW file" in warn_text
    assert "StackKeepJPEG may discard non-cover burst frames" in warn_text


# ==============================================================================
# SECTION 6: SECURITY & SECRET MANAGEMENT TESTS
# ==============================================================================

from core.config_manager import (
    SecretStore,
    get_secret_with_fallback,
    save_secret_with_fallback,
    load_secrets,
    save_secrets,
)


def test_secret_store_profile_scoped(monkeypatch):
    store = {}

    def mock_set(service, username, password):
        store[username] = password

    def mock_get(service, username):
        return store.get(username, None)

    def mock_delete(service, username):
        store.pop(username, None)

    monkeypatch.setattr("core.config_manager.keyring.set_password", mock_set)
    monkeypatch.setattr("core.config_manager.keyring.get_password", mock_get)
    monkeypatch.setattr("core.config_manager.keyring.delete_password", mock_delete)

    assert SecretStore.set_secret("default", "api_key", "key_default") is True
    assert SecretStore.set_secret("work", "api_key", "key_work") is True
    assert SecretStore.set_secret("work", "admin_api_key", "admin_work") is True

    assert SecretStore.get_secret("default", "api_key") == "key_default"
    assert SecretStore.get_secret("work", "api_key") == "key_work"
    assert SecretStore.get_secret("work", "admin_api_key") == "admin_work"

    SecretStore.clear_secret("work", "api_key")
    assert SecretStore.get_secret("work", "api_key") == ""
    assert SecretStore.get_secret("default", "api_key") == "key_default"


def test_secret_keyring_failure_fallback(tmp_path, monkeypatch):
    secrets_file = tmp_path / "secrets.toml"

    def mock_failing_set(service, username, password):
        raise RuntimeError("Keyring unavailable")

    def mock_failing_get(service, username):
        return ""

    monkeypatch.setattr("core.config_manager.keyring.set_password", mock_failing_set)
    monkeypatch.setattr("core.config_manager.keyring.get_password", mock_failing_get)

    res = save_secret_with_fallback(
        profile_name="default",
        key="api_key",
        value="fallback_secret",
        provider="keyring",
        secrets_path=secrets_file,
    )

    assert res.ok is True
    assert res.provider_used == "config"
    assert "keyring is unavailable" in res.message.lower()

    val = get_secret_with_fallback(
        profile_name="default",
        key="api_key",
        provider="keyring",
        secrets_path=secrets_file,
    )
    assert val == "fallback_secret"


def test_admin_api_key_environment_passing():
    from core.command_builder import build_plan_from_state

    config_state = {
        "server": "http://localhost:2283",
        "api_key": "user_key",
        "admin_api_key": "super_admin_key",
    }
    tab_state = {"path": "/photos"}

    plan = build_plan_from_state(
        tab_key="upload-folder",
        config_state=config_state,
        tab_state=tab_state,
        binary_path="./immich-go",
        dry_run=False,
    )

    assert "super_admin_key" not in plan.argv
    assert plan.env.get("IMMICH_GO_UPLOAD_ADMIN_API_KEY") == "super_admin_key"


# ==============================================================================
# SECTION 5: USER PROFILES & FORM-STATE TESTS
# ==============================================================================

from core.profile_manager import (
    list_profiles,
    active_profile_name,
    set_active_profile_name,
    create_profile,
    rename_profile,
    duplicate_profile,
    delete_profile,
    validate_profile_name,
)


def test_profile_manager_lifecycle(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config_dir"
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(cfg_dir / "config.toml"))

    profiles = list_profiles()
    assert len(profiles) >= 1
    assert active_profile_name() == "default"

    # Create new profile
    pinfo = create_profile("work")
    assert pinfo.name == "work"

    all_p = [p.name for p in list_profiles()]
    assert "work" in all_p

    # Set active
    set_active_profile_name("work")
    assert active_profile_name() == "work"

    # Duplicate
    dup = duplicate_profile("work", "work_copy")
    assert dup.name == "work_copy"
    assert "work_copy" in [p.name for p in list_profiles()]

    # Rename
    rename_profile("work_copy", "work_renamed")
    assert "work_renamed" in [p.name for p in list_profiles()]
    assert "work_copy" not in [p.name for p in list_profiles()]

    # Delete
    delete_profile("work_renamed")
    assert "work_renamed" not in [p.name for p in list_profiles()]


def test_profile_name_validation():
    valid, err = validate_profile_name("work_profile-1")
    assert valid is True

    valid, err = validate_profile_name("../bad_path")
    assert valid is False

    valid, err = validate_profile_name("")
    assert valid is False


def test_collect_form_state_excludes_secrets(gui):
    state = gui.collect_form_state()
    for tab_name, tab_dict in state.items():
        for secret_key in ("api_key", "from-api-key", "admin_api_key"):
            assert secret_key not in tab_dict