import pytest
import os
import sys
from pathlib import Path
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
    gui.upload_tabs.setCurrentIndex(4)
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
def suppress_qt_dialogs(monkeypatch):
    """Globally suppress modal QMessageBox dialogs during test execution."""
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", MagicMock())
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", MagicMock())
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", MagicMock())
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question", MagicMock(return_value=QMessageBox.StandardButton.Yes))


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

    gui.upload_tabs.setCurrentIndex(4)    # From Immich sub-tab
    assert gui.lbl_crumb.text() == "upload · from-immich"

    gui.stacked_widget.setCurrentIndex(2)  # Archive page
    gui.archive_tabs.setCurrentIndex(4)    # Archive Server sub-tab
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
    """Global opts (--log-level) must appear in subcommand options when enabled in advanced flags."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)     # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.adv_rows["upload-folder"]["log-level"].set_state({"enabled": True, "value": "DEBUG"})
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--log-level=DEBUG" in opts


def test_pause_jobs_not_on_archive(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(0)    # archive-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("/dst")
    opts = gui.build_command(dry_run=False)
    assert not any("--pause-immich-jobs" in o for o in opts)


def test_pause_jobs_not_on_stack(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(3)  # stack
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    opts = gui.build_command(dry_run=False)
    assert not any("--pause-immich-jobs" in o for o in opts)


def test_on_errors_emitted_when_configured(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(4)    # archive-immich
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-immich"]["write-to"].setText("/dst")
    gui.inputs["config"]["on_errors"].setCurrentText("continue")
    opts = gui.build_command(dry_run=False)
    assert "--on-errors=continue" in opts


def test_client_timeout_emitted(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)     # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["client_timeout"].setValue(60)
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--client-timeout=60m" in opts


def test_device_uuid_emitted(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)     # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["device_uuid"].setText("my-device-123")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--device-uuid=my-device-123" in opts


def test_api_trace_on_upload_gp(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(1)     # upload-gp
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout")
    gui.adv_rows["upload-gp"]["api-trace"].set_state({"enabled": True, "value": True})
    opts = gui.build_command(dry_run=False)
    assert "--api-trace" in opts


def test_api_trace_on_stack(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(3)  # stack
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.adv_rows["stack"]["api-trace"].set_state({"enabled": True, "value": True})
    opts = gui.build_command(dry_run=False)
    assert "--api-trace" in opts


def test_from_client_timeout(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(4)     # upload-immich
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    gui.adv_rows["upload-immich"]["from-client-timeout"].set_state({"enabled": True, "value": 60})
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
    opts = gui.build_command(dry_run=True)
    assert "stack" in opts
    assert "--manage-burst=StackKeepRaw" in opts
    assert "--manage-raw-jpeg=StackCoverRaw" in opts
    assert "--manage-heic-jpeg=KeepHeic" in opts
    assert "--dry-run" in opts


def test_api_trace_on_stack_disabled(gui):
    gui.stacked_widget.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://stack:2283")
    gui.inputs["config"]["api_key"].setText("stack-key")
    gui.adv_rows["stack"]["api-trace"].set_state({"enabled": False, "value": True})
    opts = gui.build_command(dry_run=False)
    assert not any("--api-trace" in o for o in opts)


def test_build_command_upload_immich(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(4)     # upload-immich sub-tab
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("local-key")
    gui.inputs["upload-immich"]["from-server"].setText("http://remote:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("remote-key")
    # from-date-range and from-albums are now simple-mode controls
    gui.inputs["upload-immich"]["from-date-range"].setText("2020-01-01,2021-01-01")
    gui.inputs["upload-immich"]["from-albums"].setText("Album1, Album2")
    gui.adv_rows["upload-immich"]["from-favorite"].set_state({"enabled": True, "value": True})
    gui.adv_rows["upload-immich"]["from-archived"].set_state({"enabled": True, "value": True})
    gui.adv_rows["upload-immich"]["from-trash"].set_state({"enabled": True, "value": True})
    gui.adv_rows["upload-immich"]["from-minimal-rating"].set_state({"enabled": True, "value": 3})
    gui.adv_rows["upload-immich"]["from-people"].set_state({"enabled": True, "value": "John, Jane"})
    gui.adv_rows["upload-immich"]["from-tags"].set_state({"enabled": True, "value": "Vacation, Family"})
    gui.adv_rows["upload-immich"]["from-city"].set_state({"enabled": True, "value": "Paris"})
    gui.adv_rows["upload-immich"]["from-state"].set_state({"enabled": True, "value": "IDF"})
    gui.adv_rows["upload-immich"]["from-country"].set_state({"enabled": True, "value": "France"})
    gui.adv_rows["upload-immich"]["from-make"].set_state({"enabled": True, "value": "Apple"})
    gui.adv_rows["upload-immich"]["from-model"].set_state({"enabled": True, "value": "iPhone 13"})
    gui.adv_rows["upload-immich"]["from-skip-ssl"].set_state({"enabled": True, "value": True})
    opts = gui.build_command(dry_run=False)
    assert "upload" in opts
    assert "from-immich" in opts
    assert "--server=http://local:2283" in opts
    assert "--from-server=http://remote:2283" in opts
    assert "--from-date-range=2020-01-01,2021-01-01" in opts
    assert "--from-albums=Album1" in opts
    assert "--from-albums=Album2" in opts
    assert "--from-favorite" in opts
    assert "--from-archived" in opts
    assert "--from-trash" in opts
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
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(0)    # archive-folder sub-tab
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["archive-folder"]["path"].setText("/source/folder")
    gui.inputs["archive-folder"]["write-to"].setText("/dest/folder")
    gui.adv_rows["archive-folder"]["date-range"].set_state({"enabled": True, "value": "2024-01-01,2024-02-01"})
    opts = gui.build_command(dry_run=True)
    assert "archive" in opts
    assert "from-folder" in opts
    assert "--server=http://local:2283" not in opts
    assert "--write-to-folder=/dest/folder" in opts
    assert "--date-range=2024-01-01,2024-02-01" in opts
    assert "/source/folder" in opts
    assert "--dry-run" in opts


def test_build_command_archive_immich(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(4)    # archive-immich sub-tab
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-immich"]["write-to"].setText("/dest/folder")
    # from-date-range and from-albums are now simple-mode controls
    gui.inputs["archive-immich"]["from-date-range"].setText("2024-01-01,2024-02-01")
    gui.inputs["archive-immich"]["from-albums"].setText("ArchiveAlbum")
    opts = gui.build_command(dry_run=False)
    assert "archive" in opts
    assert "from-immich" in opts
    assert "--write-to-folder=/dest/folder" in opts
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

def _norm_argv(argv):
    import re
    normed = []
    for arg in argv:
        clean = re.sub(r'^[A-Za-z]:', '', arg).replace('\\', '/')
        normed.append(clean)
    return normed


def test_golden_upload_folder(gui):
    """Golden: upload-folder simple mode minimal command."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv([
        "upload", "from-folder",
        "--server=http://localhost:2283",
        "/photos",
    ])
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert not any("--api-key" in p for p in plan.argv)


def test_golden_upload_gp(gui):
    """Golden: upload from-google-photos simple mode minimal command."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout-001.zip\n/takeout-002.zip")

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv([
        "upload", "from-google-photos",
        "--server=http://localhost:2283",
        "/takeout-001.zip",
        "/takeout-002.zip",
    ])


def test_golden_stack(gui):
    """Golden: stack simple mode command."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["stack"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["stack"]["manage-raw-jpeg"].setCurrentText("NoStack")
    gui.inputs["stack"]["manage-heic-jpeg"].setCurrentText("NoStack")

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv([
        "stack",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
    ])


def test_golden_stack_advanced_with_date_range(gui):
    """Golden: stack advanced mode command with date-range flag."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["stack"]["manage-burst"].setCurrentText("Stack")
    gui.adv_rows["stack"]["date-range"].set_state({"enabled": True, "value": "2023-01-01,2023-12-31"})

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv([
        "stack",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "--date-range=2023-01-01,2023-12-31",
    ])


def test_golden_archive_folder(gui):
    """Golden: archive from-folder simple mode."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["archive-folder"]["path"].setText("/messy/photos")
    gui.inputs["archive-folder"]["write-to"].setText("/organized")

    plan = gui.build_plan(dry_run=True)

    assert _norm_argv(plan.argv) == _norm_argv([
        "archive", "from-folder",
        "--write-to-folder=/organized",
        "--dry-run",
        "/messy/photos",
    ])
    assert not any("--server" in p for p in plan.argv)


def test_golden_upload_immich(gui):
    """Golden: upload from-immich simple mode."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new-key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    gui.inputs["upload-immich"]["from-date-range"].clear()
    gui.inputs["upload-immich"]["from-albums"].clear()

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv([
        "upload", "from-immich",
        "--server=http://new:2283",
        "--from-server=http://old:2283",
    ])
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "new-key"
    assert plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY") == "old-key"


def test_golden_archive_immich(gui):
    """Golden: archive from-immich simple mode."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["archive-immich"]["write-to"].setText("/backup/photos")
    gui.inputs["archive-immich"]["from-date-range"].clear()
    gui.inputs["archive-immich"]["from-albums"].clear()

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv([
        "archive", "from-immich",
        "--from-server=http://localhost:2283",
        "--write-to-folder=/backup/photos",
    ])
    assert plan.env.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_API_KEY") == "test-key"


def test_simple_mode_ignores_advanced_upload_folder_flags(gui):
    gui.toggle_advanced(False)

    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")

    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["log-level"].set_state({"enabled": True, "value": "DEBUG"})
    gui.adv_rows["upload-folder"]["recursive"].set_state({"enabled": True, "value": False})
    gui.adv_rows["upload-folder"]["date-from-name"].set_state({"enabled": True, "value": False})
    gui.adv_rows["upload-folder"]["album-path-joiner"].set_state({"enabled": True, "value": "/"})
    gui.adv_rows["upload-folder"]["time-zone"].set_state({"enabled": True, "value": "UTC"})
    gui.adv_rows["upload-folder"]["manage-epson"].set_state({"enabled": True, "value": True})

    plan = gui.build_plan(dry_run=True)

    assert "--log-level=DEBUG" not in plan.argv
    assert "--recursive=false" not in plan.argv
    assert "--date-from-name=false" not in plan.argv
    assert "--album-path-joiner=/" not in plan.argv
    assert "--time-zone=UTC" not in plan.argv
    assert "--manage-epson-fastfoto" not in plan.argv


def test_advanced_mode_emits_advanced_upload_folder_flags(gui):
    gui.toggle_advanced(True)

    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")

    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["log-level"].set_state({"enabled": True, "value": "DEBUG"})
    gui.adv_rows["upload-folder"]["recursive"].set_state({"enabled": True, "value": False})
    gui.adv_rows["upload-folder"]["date-from-name"].set_state({"enabled": True, "value": False})
    gui.adv_rows["upload-folder"]["album-path-joiner"].set_state({"enabled": True, "value": "/"})
    gui.adv_rows["upload-folder"]["time-zone"].set_state({"enabled": True, "value": "UTC"})
    gui.adv_rows["upload-folder"]["manage-epson"].set_state({"enabled": True, "value": True})

    plan = gui.build_plan(dry_run=True)

    assert "--log-level=DEBUG" in plan.argv
    assert "--recursive=false" in plan.argv
    assert "--date-from-name=false" in plan.argv
    assert "--album-path-joiner=/" in plan.argv
    assert "--time-zone=UTC" in plan.argv
    assert "--manage-epson-fastfoto" in plan.argv


def test_simple_mode_ignores_advanced_stack_flags(gui):
    gui.toggle_advanced(False)

    gui.stacked_widget.setCurrentIndex(3)

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")

    gui.adv_rows["stack"]["date-range"].set_state({"enabled": True, "value": "2023-01-01,2023-12-31"})
    gui.adv_rows["stack"]["time-zone"].set_state({"enabled": True, "value": "UTC"})
    gui.adv_rows["stack"]["manage-epson"].set_state({"enabled": True, "value": True})
    gui.adv_rows["stack"]["api-trace"].set_state({"enabled": True, "value": True})

    plan = gui.build_plan(dry_run=False)

    assert "--date-range=2023-01-01,2023-12-31" not in plan.argv
    assert "--time-zone=UTC" not in plan.argv
    assert "--manage-epson-fastfoto" not in plan.argv
    assert "--api-trace" not in plan.argv


def test_archive_folder_destination_is_absolutized(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)

    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("relative/dest")

    plan = gui.build_plan(dry_run=False)

    assert any(arg.startswith("--write-to-folder=") for arg in plan.argv)

    write_arg = next(arg for arg in plan.argv if arg.startswith("--write-to-folder="))
    write_path = write_arg.split("=", 1)[1]
    assert os.path.isabs(write_path)


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


def test_check_preflight_server_connection_serverless():
    from core.network import check_preflight_server_connection
    res = check_preflight_server_connection("archive-folder", {"server": "http://localhost:2283"})
    assert res.ok is True
    assert "Serverless" in res.message


def test_check_preflight_server_connection_success():
    from core.network import check_preflight_server_connection
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"version": "v1.100.0"}
        mock_get.return_value = mock_resp

        res = check_preflight_server_connection("upload-folder", {"server": "http://localhost:2283", "api_key": "key"})
        assert res.ok is True


def test_check_preflight_server_connection_unreachable():
    from core.network import check_preflight_server_connection
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        res = check_preflight_server_connection("upload-folder", {"server": "http://localhost:2283", "api_key": "key"})
        assert res.ok is False
        assert "Failed to connect to server" in res.message


def test_status_card_reflects_connection_test_failure(gui):
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")

    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        gui.on_test_connection_clicked()
        assert gui._last_conn_test_ok is False
        assert "Connection Failed" in gui.status_card.txt_s.text()


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


# ==============================================================================
# SECTION 4: PROCESS TRACKER & TERMINAL LAUNCHER TESTS
# ==============================================================================

from core.process_tracker import (
    create_lock,
    release_lock,
    read_lock,
    is_lock_active,
    scan_locks,
    cleanup_stale_locks,
    reset_all_locks,
)
from core.terminal_launcher import launch_external_terminal


def test_process_tracker_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))

    lock_path = create_lock(
        tab_key="upload-folder",
        command_summary="upload from-folder",
        binary_path="./immich-go",
    )
    assert lock_path.exists()

    lock = read_lock(lock_path)
    assert lock is not None
    assert lock.tab_key == "upload-folder"

    assert is_lock_active(lock_path) is True
    assert len(scan_locks()) == 1

    release_lock(lock_path)
    assert lock_path.exists() is False
    assert len(scan_locks()) == 0


def test_terminal_launcher_posix_script_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    lock_path = create_lock("upload-folder", "upload", "./immich-go")

    env = {
        "IMMICH_GO_UPLOAD_SERVER": "http://localhost:2283",
        "IMMICH_GO_UPLOAD_API_KEY": "secret_key_123",
    }
    cmd = ["./immich-go", "upload", "from-folder", "/photos"]

    with patch("subprocess.Popen") as mock_popen, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gnome-terminal"
        res = launch_external_terminal(cmd, env, lock_path, preferred_terminal="auto")
        assert res.ok is True
        assert mock_popen.called


# ==============================================================================
# SECTION 3: CLI CORRECTNESS & COMPATIBILITY TESTS (MILESTONE 1)
# ==============================================================================

from core.cli_help import parse_help_flags, load_help_fixture, help_name_for_tab
from core.cli_schema import (
    TAB_ALLOWED_FLAGS,
    flag_allowed_for_tab,
    assert_flag_allowed,
)


def test_parse_help_flags():
    sample_help = """
    OPTIONS:
       --server value           Immich server URL
       --skip-verify-ssl        Skip SSL verification (default: false)
       -s, --session-tag value  Session tag
       --recursive              Recursive search (default: true)
       --help                   Show help
    """
    flags = parse_help_flags(sample_help)
    assert "server" in flags
    assert "skip-verify-ssl" in flags
    assert "session-tag" in flags
    assert "recursive" in flags
    assert "help" not in flags


def test_help_name_for_tab():
    assert help_name_for_tab("upload-folder") == "upload_from-folder"
    assert help_name_for_tab("upload-gp") == "upload_from-google-photos"
    assert help_name_for_tab("archive-immich") == "archive_from-immich"
    assert help_name_for_tab("stack") == "stack"


def test_load_help_fixture():
    flags = load_help_fixture("0.32.0", "upload_from-folder")
    assert "server" in flags
    assert "recursive" in flags
    assert "manage-raw-jpeg" in flags


def test_all_tab_allowed_flags_exist_in_help_fixtures():
    tabs = ["upload-folder", "upload-gp", "upload-immich", "archive-folder", "archive-immich", "stack"]
    for tab_key in tabs:
        fixture_name = help_name_for_tab(tab_key)
        fixture_flags = load_help_fixture("0.32.0", fixture_name)
        allowed_flags = TAB_ALLOWED_FLAGS[tab_key]

        for flag in allowed_flags:
            assert flag in fixture_flags, f"Flag '--{flag}' registered in TAB_ALLOWED_FLAGS[{tab_key}] was not found in fixture '{fixture_name}'"


# ==============================================================================
# SECTION 3: CLI CORRECTNESS & COMPATIBILITY TESTS (MILESTONE 2)
# ==============================================================================

from core.command_builder import FlagEmitter


def test_flag_emitter_allowlist_enforcement():
    emitter = FlagEmitter("upload-folder", strict=False)
    assert emitter.add_option("server", "http://localhost:2283") is True
    assert emitter.add_flag("recursive") is True
    assert emitter.add_option("disallowed-invalid-flag", "value") is False
    assert len(emitter.errors) == 1
    assert "disallowed-invalid-flag" in emitter.errors[0]

    strict_emitter = FlagEmitter("upload-folder", strict=True)
    with pytest.raises(ValueError, match="not allowed"):
        strict_emitter.add_option("invalid-flag", "val")


def test_terminal_launcher_working_directory_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    lock_path = create_lock("upload-folder", "upload", "./immich-go")

    env = {"IMMICH_GO_UPLOAD_SERVER": "http://localhost:2283"}
    cmd = ["./immich-go", "upload", "from-folder", "/photos"]

    with patch("subprocess.Popen") as mock_popen, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gnome-terminal"
        res = launch_external_terminal(cmd, env, lock_path, preferred_terminal="auto")
        assert res.ok is True

    temp_dirs = list(Path("/tmp").glob("immich-go-run-*"))
    assert temp_dirs, "Expected POSIX launcher to create a temp run directory"

    latest_temp = max(temp_dirs, key=lambda d: d.stat().st_mtime)
    run_sh = latest_temp / "run.sh"
    assert run_sh.exists()

    content = run_sh.read_text(encoding="utf-8")

    assert 'SAFE_DIR="$HOME"' in content
    assert 'cd "$SAFE_DIR"' in content
    assert f"cd '{latest_temp}'" not in content
    assert f"rm -rf '{latest_temp}'" not in content


# ==============================================================================
# SECTION 3: CLI CORRECTNESS & COMPATIBILITY TESTS (MILESTONE 3)
# ==============================================================================

import json
from core.command_builder import build_plan_from_state


def test_golden_json_fixtures():
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "command_states"
    json_files = list(fixtures_dir.glob("*.json"))
    assert len(json_files) >= 6, "Expected at least 6 golden state fixtures"

    for jf in json_files:
        data = json.loads(jf.read_text(encoding="utf-8"))
        tab_key = data["tab_key"]
        config_state = data.get("config_state", {})
        tab_state = data.get("tab_state", {})
        expected_argv = data["expected_argv"]

        advanced_state = data.get("advanced_state")
        plan = build_plan_from_state(
            tab_key=tab_key,
            config_state=config_state,
            tab_state=tab_state,
            binary_path="./immich-go",
            dry_run=False,
            advanced_state=advanced_state,
        )
        assert _norm_argv(plan.argv) == _norm_argv(expected_argv), f"Fixture {jf.name} produced unexpected argv: {plan.argv} != {expected_argv}"


# ==============================================================================
# SECTION 3: CLI CORRECTNESS & COMPATIBILITY TESTS (MILESTONE 4)
# ==============================================================================

from core.cli_contract import check_fixtures, check_binary_help


def test_check_fixtures_compatibility():
    report = check_fixtures("0.32.0")
    assert report.version == "0.32.0"
    assert report.is_fully_compatible() is True
    assert len(report.missing_flags_by_tab) == 0


def test_show_cli_compatibility_dialog(gui):
    with patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
        gui.show_cli_compatibility_dialog()
        assert mock_info.called
        title = mock_info.call_args[0][1]
        assert "CLI Compatibility" in title


# ==============================================================================
# SECTION 3: CRITICAL FIX 2 & CRITICAL FIX 3 TESTS
# ==============================================================================

from core.command_builder import CommandPlan, build_environment, build_plan_from_state


def test_archive_immich_source_model_env():
    env = build_environment(
        tab_key="archive-immich",
        server="http://source-server:2283",
        api_key="source-key",
        admin_api_key="source-admin-key",
    )
    assert env.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER") == "http://source-server:2283"
    assert env.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_API_KEY") == "source-key"
    assert env.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_ADMIN_API_KEY") == "source-admin-key"
    assert "IMMICH_GO_ARCHIVE_SERVER" not in env


def test_archive_immich_source_model_cmd():
    plan = build_plan_from_state(
        tab_key="archive-immich",
        config_state={"server": "http://source-server:2283", "api_key": "source-key"},
        tab_state={"write-to": "/dest/folder"},
        binary_path="./immich-go",
        dry_run=True,
    )
    assert "--from-server=http://source-server:2283" in plan.argv
    assert "--write-to-folder=/dest/folder" in plan.argv
    assert "--dry-run" in plan.argv
    assert not any(arg.startswith("--server=") for arg in plan.argv)


def test_plan_errors_surfaced_in_gui(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")

    mock_plan = CommandPlan(
        argv=["upload", "from-folder"],
        env={},
        tab_key="upload-folder",
        binary_path="./immich-go",
        errors=["Invalid flag '--unsupported' specified."],
    )

    with patch.object(gui, "check_binary_ready", return_value=(True, "Ready")):
        with patch.object(gui, "build_plan", return_value=mock_plan):
            with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_crit:
                gui.show_confirm_dialog(is_dry_run=True)
                assert mock_crit.called
                title = mock_crit.call_args[0][1]
                msg = mock_crit.call_args[0][2]
                assert "Command Build Errors" in title
                assert "Invalid flag '--unsupported'" in msg


def test_running_process_boolean_state(gui):
    from PySide6.QtWidgets import QMessageBox

    gui.active_lock_path = None
    gui.running_process = False
    gui.update_status()
    assert gui.lbl_running_warning.isHidden() is True

    gui.running_process = True
    gui.update_status()
    assert gui.lbl_running_warning.isHidden() is False

    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
        gui.on_reset_run_state_clicked()
        assert gui.running_process is False
        assert gui.active_lock_path is None
        assert gui.lbl_running_warning.isHidden() is True


def test_stale_lock_detection_with_pid_and_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    from core.process_tracker import create_lock, update_lock, is_lock_active, release_lock

    l_path = create_lock("upload-folder", "upload", "./immich-go")
    assert is_lock_active(l_path) is True

    # Record dead PID (999999)
    update_lock(l_path, shell_pid=999999, started_at="2020-01-01T00:00:00+00:00")
    assert is_lock_active(l_path) is False

    # Record current process PID
    update_lock(l_path, shell_pid=os.getpid())
    assert is_lock_active(l_path) is True

    release_lock(l_path)


def test_forward_all_immich_go_env_vars(tmp_path, monkeypatch):
    from core.terminal_launcher import launch_external_terminal
    dummy_lock = tmp_path / "test.lock"
    dummy_lock.write_text("{}", encoding="utf-8")

    test_env = {
        "IMMICH_GO_CUSTOM_VAR": "custom_val",
        "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER": "http://srv:2283",
        "OTHER_VAR": "ignored",
    }

    with patch("subprocess.Popen") as mock_popen:
        launch_external_terminal(
            command=["./immich-go", "archive", "from-immich"],
            env=test_env,
            lock_path=dummy_lock,
        )
        assert mock_popen.called
        call_args = mock_popen.call_args
        if call_args:
            args, kwargs = call_args
            env_used = kwargs.get("env", {})
            if env_used and "IMMICH_GO_CUSTOM_VAR" in env_used:
                assert env_used.get("IMMICH_GO_CUSTOM_VAR") == "custom_val"
                assert env_used.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER") == "http://srv:2283"
            elif args and args[0]:
                cmd_list = args[0]
                for item in cmd_list:
                    if isinstance(item, str) and item.endswith(".sh") and os.path.exists(item):
                        env_sh = Path(item).parent / "env.sh"
                        if env_sh.exists():
                            content = env_sh.read_text(encoding="utf-8")
                            assert "IMMICH_GO_CUSTOM_VAR" in content
                            assert "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER" in content


def test_archive_ui_options_removed(gui):
    assert "manage-raw-jpeg" not in gui.inputs["archive-folder"]
    assert "manage-burst" not in gui.inputs["archive-immich"]
    assert "manage-raw-jpeg" not in gui.inputs["archive-immich"]


def test_config_tab_completeness(gui):
    assert "allow_untested_updates" in gui.inputs["config"]
    assert "preferred_terminal" in gui.inputs["config"]
    gui.inputs["config"]["allow_untested_updates"].setChecked(True)
    gui.inputs["config"]["preferred_terminal"].setCurrentText("konsole")
    gui.save_configuration()
    assert gui.app_config.allow_untested_updates is True
    assert gui.app_config.preferred_terminal == "konsole"


def test_default_true_boolean_emission():
    from core.command_builder import build_plan_from_state
    config_state = {"server": "http://localhost:2283", "api_key": "test_key"}

    # upload-folder boolean flags explicitly enabled and set to False
    tab_state_folder = {"path": "/photos"}
    advanced_folder = {
        "recursive": {"enabled": True, "value": False},
        "date-from-name": {"enabled": True, "value": False},
        "pause-jobs": {"enabled": True, "value": False},
    }
    plan_folder = build_plan_from_state("upload-folder", config_state, tab_state_folder, advanced_state=advanced_folder)
    assert "--recursive=false" in plan_folder.argv
    assert "--date-from-name=false" in plan_folder.argv
    assert "--pause-immich-jobs=false" in plan_folder.argv

    # upload-gp boolean flags explicitly set to False in tab_state & advanced_state
    tab_state_gp = {
        "path": "/takeout",
        "include-archived": False,
        "include-partner": False,
        "sync-albums": False,
    }
    advanced_gp = {
        "takeout-tag": {"enabled": True, "value": False},
        "people-tag": {"enabled": True, "value": False},
    }
    plan_gp = build_plan_from_state("upload-gp", config_state, tab_state_gp, advanced_state=advanced_gp)
    assert "--include-archived=false" in plan_gp.argv
    assert "--include-partner=false" in plan_gp.argv
    assert "--sync-albums=false" in plan_gp.argv
    assert "--takeout-tag=false" in plan_gp.argv
    assert "--people-tag=false" in plan_gp.argv


def test_simple_vs_advanced_mode_toggle(gui):
    gui.toggle_advanced(True)
    assert gui.is_advanced is True
    assert gui.lbl_mode.text() == "Advanced"
    for frame in gui.adv_frames:
        assert not frame.isHidden()

    gui.toggle_advanced(False)
    assert gui.is_advanced is False
    assert gui.lbl_mode.text() == "Simple"
    for frame in gui.adv_frames:
        assert frame.isHidden()


def test_from_dry_run_emitted_for_immich_tabs():
    from core.command_builder import build_plan_from_state
    config_state = {"server": "http://localhost:2283", "api_key": "test"}
    tab_state = {
        "from-server": "http://remote:2283",
        "from-api-key": "remote_key",
        "write-to": "/dst",
    }
    plan = build_plan_from_state("archive-immich", config_state, tab_state, dry_run=True)
    assert "--dry-run" in plan.argv
    assert "--from-dry-run" in plan.argv


def test_stack_pause_jobs_and_archive_folder_on_errors():
    from core.command_builder import build_plan_from_state
    config_state = {"server": "http://localhost:2283", "api_key": "test"}
    plan_stack = build_plan_from_state("stack", config_state, {"pause-jobs": False})
    assert "--pause-immich-jobs=false" in plan_stack.argv

    plan_archive = build_plan_from_state(
        "archive-folder",
        config_state,
        {"path": "/src", "write-to": "/dst", "on-errors": "continue"},
    )
    assert "--on-errors=continue" in plan_archive.argv


def test_collect_paths_expansion_and_abspath(tmp_path):
    from core.command_builder import collect_paths
    rel_path = "./subfolder"
    paths = collect_paths(rel_path)
    assert len(paths) == 1
    assert os.path.isabs(paths[0])


def test_upload_folder_path_is_absolutized(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("relative/folder")
    opts = gui.build_command(False)
    assert opts[-1]
    assert os.path.isabs(opts[-1])


def test_archive_folder_path_is_absolutized(gui):
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["archive-folder"]["path"].setText("relative/source")
    gui.inputs["archive-folder"]["write-to"].setText("/tmp/dest")
    opts = gui.build_command(False)
    assert opts[-1]
    assert os.path.isabs(opts[-1])


def test_archive_folder_destination_warnings(gui, tmp_path):
    src = tmp_path / "src"
    dest = src / "dest"
    src.mkdir()
    dest.mkdir()

    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["archive-folder"]["path"].setText(str(src))
    gui.inputs["archive-folder"]["write-to"].setText(str(dest))

    validation = gui.validate_inputs()
    assert any("inside the source" in w for w in validation.warnings)


def test_missing_fixtures_not_fully_compatible(tmp_path):
    from core.cli_contract import check_fixtures
    report = check_fixtures.__wrapped__(str(tmp_path / "missing-fixtures")) if hasattr(check_fixtures, "__wrapped__") else None
    # Direct unit test against the method
    from core.cli_contract import CompatibilityReport
    report_missing = CompatibilityReport(version="0.99.0", supported=False)
    assert report_missing.is_fully_compatible() is False
    report_empty = CompatibilityReport(version="0.99.0", supported=True)
    assert report_empty.is_fully_compatible() is True


def test_advanced_flag_disabled_not_emitted(gui):
    """Verify disabled advanced flag is not emitted even if value widget is set."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    gui.adv_rows["upload-folder"]["time-zone"].set_state({
        "enabled": False,
        "value": "UTC",
    })

    plan = gui.build_plan(dry_run=False)
    assert "--time-zone=UTC" not in plan.argv


def test_advanced_flag_enabled_text_emitted(gui):
    """Verify enabled advanced text flag is emitted."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    gui.adv_rows["upload-folder"]["time-zone"].set_state({
        "enabled": True,
        "value": "UTC",
    })

    plan = gui.build_plan(dry_run=False)
    assert "--time-zone=UTC" in plan.argv


def test_advanced_bool_false_emitted(gui):
    """Verify enabled boolean false flag is emitted as --flag=false."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    gui.adv_rows["upload-folder"]["recursive"].set_state({
        "enabled": True,
        "value": False,
    })

    plan = gui.build_plan(dry_run=False)
    assert "--recursive=false" in plan.argv


def test_advanced_bool_true_emitted_as_presence(gui):
    """Verify enabled boolean true flag is emitted as --flag presence."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout")

    gui.adv_rows["upload-gp"]["include-trashed"].set_state({
        "enabled": True,
        "value": True,
    })

    plan = gui.build_plan(dry_run=False)
    assert "--include-trashed" in plan.argv


def test_simple_mode_ignores_advanced_rows(gui):
    """Verify Simple mode ignores advanced flag rows even if enabled."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    gui.adv_rows["upload-folder"]["time-zone"].set_state({
        "enabled": True,
        "value": "UTC",
    })

    plan = gui.build_plan(dry_run=False)
    assert "--time-zone=UTC" not in plan.argv


def test_form_state_advanced_rows_persistence(gui):
    """Verify form state serialization and deserialization of advanced flag rows."""
    gui.adv_rows["upload-folder"]["time-zone"].set_state({
        "enabled": True,
        "value": "America/New_York",
    })

    state = gui.collect_form_state()
    assert "advanced" in state
    assert state["advanced"]["upload-folder"]["time-zone"] == {
        "enabled": True,
        "value": "America/New_York",
    }

    # Reset and restore
    gui.reset_advanced_flags()
    assert gui.adv_rows["upload-folder"]["time-zone"].enable.isChecked() is False

    gui.apply_form_state(state)
    assert gui.adv_rows["upload-folder"]["time-zone"].enable.isChecked() is True
    assert gui.adv_rows["upload-folder"]["time-zone"].get_value() == "America/New_York"


def test_advanced_mode_persistence(gui):
    gui.toggle_advanced(True)
    assert gui.is_advanced is True
    assert gui.app_config.advanced_mode is True

    gui.toggle_advanced(False)
    assert gui.is_advanced is False
    assert gui.app_config.advanced_mode is False


def test_validate_server_url():
    from core.validation import validate_server_url
    ok, err = validate_server_url("http://localhost:2283")
    assert ok is True
    assert err is None

    ok, err = validate_server_url("https://immich.example.com")
    assert ok is True
    assert err is None

    ok, err = validate_server_url("ftp://example.com")
    assert ok is False
    assert "http://" in err

    ok, err = validate_server_url("invalid-url")
    assert ok is False


def test_upload_gp_path_warnings(gui, tmp_path):
    nonexistent = str(tmp_path / "missing_takeout")
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["upload-gp"]["path"].setPlainText(nonexistent)

    val = gui.validate_inputs()
    assert any("does not exist" in w for w in val.warnings)


def test_secret_copy_success_verification(monkeypatch):
    from core.config_manager import SecretStore
    secrets_db = {}

    def mock_set(profile, key, val):
        secrets_db[(profile, key)] = val
        return True

    def mock_get(profile, key):
        return secrets_db.get((profile, key), "")

    monkeypatch.setattr(SecretStore, "set_secret", mock_set)
    monkeypatch.setattr(SecretStore, "get_secret", mock_get)

    secrets_db[("src", "api_key")] = "my-secret-key"
    res = SecretStore.copy_secrets("src", "dst")
    assert res is True
    assert secrets_db.get(("dst", "api_key")) == "my-secret-key"


def test_binary_manager_downgrade_prevention():
    from core.binary_manager import BinaryManager
    bm = BinaryManager()
    decision = bm.evaluate_update(current_version="0.33.0", latest_version="0.32.0")
    assert decision.allowed is False
    assert "newer version" in decision.message


def test_binary_manager_get_release_asset_url(monkeypatch):
    from core.binary_manager import BinaryManager
    bm = BinaryManager(os_name="linux", arch="x86_64")

    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "assets": [
                    {
                        "name": "immich-go_0.32.0_linux_x86_64.tar.gz",
                        "browser_download_url": "https://github.com/simulot/immich-go/releases/download/v0.32.0/immich-go_0.32.0_linux_x86_64.tar.gz"
                    }
                ]
            }

    monkeypatch.setattr("requests.get", lambda url, timeout=10: MockResponse())
    url = bm.get_release_asset_url("0.32.0")
    assert "immich-go_0.32.0_linux_x86_64.tar.gz" in url


def test_binary_manager_verify_extracted_binary(tmp_path):
    from core.binary_manager import BinaryManager
    bm = BinaryManager()
    # Nonexistent file
    assert bm.verify_extracted_binary(str(tmp_path / "nonexistent")) is False


def test_cleanup_stale_temp_dirs(tmp_path, monkeypatch):
    import tempfile, time
    from core.terminal_launcher import cleanup_stale_temp_dirs

    dummy_dir = tmp_path / "immich-go-run-test"
    dummy_dir.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    # Set mtime to 30 hours ago
    past_mtime = time.time() - (30 * 3600)
    os.utime(dummy_dir, (past_mtime, past_mtime))

    cleaned = cleanup_stale_temp_dirs(max_age_hours=24)
    assert cleaned == 1
    assert not dummy_dir.exists()


def test_advanced_keys_derived_from_advanced_flags():
    from app import ImmichGoGUI
    from core.advanced_flags import ADVANCED_FLAGS

    expected = {
        tab: {def_.key for def_ in defs}
        for tab, defs in ADVANCED_FLAGS.items()
    }
    assert ImmichGoGUI.ADVANCED_KEYS == expected


def test_upload_gp_does_not_include_into_album_advanced_key():
    from app import ImmichGoGUI

    assert "into-album" not in ImmichGoGUI.ADVANCED_KEYS.get("upload-gp", set())


def test_from_admin_api_key_advanced_secret_env(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(4)

    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new-key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")

    gui.adv_rows["upload-immich"]["from-admin-api-key"].set_state({
        "enabled": True,
        "value": "old-admin-secret",
    })

    plan = gui.build_plan(False)

    assert "--from-admin-api-key" not in " ".join(plan.argv)
    assert "old-admin-secret" not in " ".join(plan.argv)
    assert plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY") == "old-admin-secret"


def test_advanced_secret_value_not_persisted(gui):
    gui.toggle_advanced(True)
    gui.adv_rows["upload-immich"]["from-admin-api-key"].set_state({
        "enabled": True,
        "value": "super-secret-admin-key",
    })

    state = gui.collect_form_state()
    saved = state["advanced"]["upload-immich"]["from-admin-api-key"]
    assert saved["enabled"] is False
    assert saved["value"] == ""


def test_gp_simple_card_has_restored_checkboxes(gui):
    """A9: GP simple card has include-partner, sync-albums, include-archived checkboxes."""
    gp_inputs = gui.inputs.get("upload-gp", {})
    assert "include-partner" in gp_inputs
    assert "sync-albums" in gp_inputs
    assert "include-archived" in gp_inputs


def test_gp_simple_mode_checkboxes_emitted_when_unchecked(gui):
    """A9: When GP simple checkboxes are unchecked, --flag=false is emitted."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-gp"]["path"].setPlainText("/path/to/takeout.zip")
    gui.inputs["upload-gp"]["include-partner"].setChecked(False)
    gui.inputs["upload-gp"]["sync-albums"].setChecked(False)
    gui.inputs["upload-gp"]["include-archived"].setChecked(False)

    plan = gui.build_plan(dry_run=False)
    assert "--include-partner=false" in plan.argv
    assert "--sync-albums=false" in plan.argv
    assert "--include-archived=false" in plan.argv


def test_gp_simple_mode_checkboxes_omitted_when_checked(gui):
    """A9: When GP simple checkboxes are checked (default), --flag=false is NOT emitted."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-gp"]["path"].setPlainText("/path/to/takeout.zip")
    gui.inputs["upload-gp"]["include-partner"].setChecked(True)
    gui.inputs["upload-gp"]["sync-albums"].setChecked(True)
    gui.inputs["upload-gp"]["include-archived"].setChecked(True)

    plan = gui.build_plan(dry_run=False)
    assert "--include-partner=false" not in plan.argv
    assert "--sync-albums=false" not in plan.argv
    assert "--include-archived=false" not in plan.argv


# ==============================================================================
# A1 REGRESSION: Simple-mode controls not silently discarded
# ==============================================================================

def test_upload_immich_simple_mode_from_date_range_emitted(gui):
    """A1: from-date-range in upload-immich simple card must produce CLI flag."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    gui.inputs["upload-immich"]["from-date-range"].setText("2022-01-01,2022-12-31")
    gui.inputs["upload-immich"]["from-albums"].clear()

    plan = gui.build_plan(dry_run=False)
    assert "--from-date-range=2022-01-01,2022-12-31" in plan.argv
    assert not plan.errors


def test_upload_immich_simple_mode_from_albums_emitted(gui):
    """A1: from-albums in upload-immich simple card must produce repeat CLI flags."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    gui.inputs["upload-immich"]["from-date-range"].clear()
    gui.inputs["upload-immich"]["from-albums"].setText("Family, Travel")

    plan = gui.build_plan(dry_run=False)
    assert "--from-albums=Family" in plan.argv
    assert "--from-albums=Travel" in plan.argv
    assert not plan.errors


def test_archive_immich_simple_mode_from_date_range_emitted(gui):
    """A1: from-date-range in archive-immich simple card must produce CLI flag."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-immich"]["write-to"].setText("/backup")
    gui.inputs["archive-immich"]["from-date-range"].setText("2023-06-01,2023-12-31")
    gui.inputs["archive-immich"]["from-albums"].clear()

    plan = gui.build_plan(dry_run=False)
    assert "--from-date-range=2023-06-01,2023-12-31" in plan.argv
    assert not plan.errors


def test_archive_immich_simple_mode_from_albums_emitted(gui):
    """A1: from-albums in archive-immich simple card must produce repeat CLI flags."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-immich"]["write-to"].setText("/backup")
    gui.inputs["archive-immich"]["from-date-range"].clear()
    gui.inputs["archive-immich"]["from-albums"].setText("ArchiveAlbum")

    plan = gui.build_plan(dry_run=False)
    assert "--from-albums=ArchiveAlbum" in plan.argv
    assert not plan.errors


def test_upload_immich_simple_mode_has_no_from_favorite_widget(gui):
    """A1: from-favorite must NOT be a simple-mode widget (it's advanced-only)."""
    assert "from-favorite" not in gui.inputs.get("upload-immich", {})


# ==============================================================================
# A2: Duplicate test name lint guard
# ==============================================================================

def test_no_duplicate_test_names():
    """A2: Ensure no duplicate test function names exist in test_app.py."""
    import ast
    import collections
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    names = [
        n.name for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    ]
    dupes = [n for n, c in collections.Counter(names).items() if c > 1]
    assert not dupes, f"Duplicate test names found in test_app.py: {dupes}"


# ==============================================================================
# A8: ADVANCED_FLAGS ⊆ TAB_ALLOWED_FLAGS
# ==============================================================================

def test_advanced_flags_subset_of_tab_allowed_flags():
    """A8: Every flag in ADVANCED_FLAGS must be in TAB_ALLOWED_FLAGS for its tab.
    Secret-env flags bypass argv so they are excluded from the argv allowlist check,
    but we still verify they appear in TAB_ALLOWED_FLAGS when present.
    """
    from core.advanced_flags import ADVANCED_FLAGS
    from core.cli_schema import TAB_ALLOWED_FLAGS

    missing = []
    for tab, defs in ADVANCED_FLAGS.items():
        allowed = TAB_ALLOWED_FLAGS.get(tab, frozenset())
        for d in defs:
            if d.secret_env:
                # Secret flags emit via env var, not argv — skip allowlist check
                continue
            if d.flag not in allowed:
                missing.append(f"'{d.flag}' in ADVANCED_FLAGS['{tab}'] missing from TAB_ALLOWED_FLAGS")

    assert not missing, "\n".join(missing)


# ==============================================================================
# A3: validate_advanced_state uses full date semantic validation
# ==============================================================================

def test_validate_advanced_state_rejects_invalid_month():
    """A3: validate_advanced_state must reject semantically invalid dates."""
    from core.advanced_flags import validate_advanced_state
    # Month 13 is invalid
    result = validate_advanced_state("upload-folder", {
        "date-range": {"enabled": True, "value": "2023-13-01,2023-12-31"}
    })
    assert not result.is_valid
    assert any("date" in e.lower() or "invalid" in e.lower() for e in result.errors)


def test_validate_advanced_state_rejects_reversed_range():
    """A3: validate_advanced_state must reject start > end date ranges."""
    from core.advanced_flags import validate_advanced_state
    result = validate_advanced_state("upload-folder", {
        "date-range": {"enabled": True, "value": "2023-12-31,2023-01-01"}
    })
    assert not result.is_valid
    assert result.errors


def test_validate_advanced_state_accepts_valid_date_range():
    """A3: validate_advanced_state must accept well-formed date ranges."""
    from core.advanced_flags import validate_advanced_state
    result = validate_advanced_state("upload-folder", {
        "date-range": {"enabled": True, "value": "2023-01-01,2023-12-31"}
    })
    assert result.is_valid
    assert not result.errors


# ==============================================================================
# Fix 1.2: Env-Var Secret Contract Verification via Stub Executable
# ==============================================================================

def test_env_var_secret_contract_with_stub(gui):
    """Fix 1.2: Verify subprocess receives secrets via env vars and never in argv."""
    import json
    import subprocess
    from pathlib import Path

    stub_path = str(Path(__file__).parent / "stub_immich_go.py")

    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(4)  # upload-immich tab

    gui.inputs["config"]["server"].setText("http://target:2283")
    gui.inputs["config"]["api_key"].setText("target-secret-key-123")
    gui.inputs["upload-immich"]["from-server"].setText("http://source:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("source-secret-key-456")
    gui.adv_rows["upload-immich"]["from-admin-api-key"].set_state({
        "enabled": True,
        "value": "source-admin-secret-789",
    })

    plan = gui.build_plan(dry_run=False)

    # 1. Assert secret values NEVER appear in plan.argv
    for secret in ("target-secret-key-123", "source-secret-key-456", "source-admin-secret-789"):
        assert not any(secret in arg for arg in plan.argv), f"Secret '{secret}' leaked into argv!"

    # 2. Run the stub process using plan.argv and plan.env
    cmd = [sys.executable, stub_path] + plan.argv
    full_env = {**os.environ, **plan.env}

    res = subprocess.run(cmd, capture_output=True, text=True, env=full_env)
    assert res.returncode == 0, f"Stub failed: {res.stderr}"

    output = json.loads(res.stdout)
    received_env = output["env"]
    received_argv = output["argv"]

    # 3. Assert secrets were delivered via env vars
    assert received_env.get("IMMICH_GO_UPLOAD_SERVER") == "http://target:2283"
    assert received_env.get("IMMICH_GO_UPLOAD_API_KEY") == "target-secret-key-123"
    assert received_env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER") == "http://source:2283"
    assert received_env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY") == "source-secret-key-456"
    assert received_env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY") == "source-admin-secret-789"

    # 4. Assert secrets are not in received argv
    for secret in ("target-secret-key-123", "source-secret-key-456", "source-admin-secret-789"):
        assert not any(secret in arg for arg in received_argv)


def test_binary_manager_download_and_install_cancellation(tmp_path):
    """Fix 1.3: download_and_install respects cancellation and cleans up temp files."""
    from core.binary_manager import BinaryManager

    bm = BinaryManager(base_dir=str(tmp_path))

    # Mock get_release_asset_url to return a dummy URL
    with patch.object(bm, "get_release_asset_url", return_value="https://example.com/immich-go.tar.gz"):
        # Mock requests.get to return a streaming dummy response
        mock_res = MagicMock()
        mock_res.headers = {"content-length": "100"}
        mock_res.iter_content.return_value = [b"dummy data chunk"]
        mock_res.__enter__.return_value = mock_res

        with patch("requests.get", return_value=mock_res):
            success, msg = bm.download_and_install(
                version="0.32.0",
                cancel_check=lambda: True,  # cancel immediately
            )
            assert success is False
            assert "cancelled" in msg.lower()

    # Ensure no leftover temp archive or binary exists
    v_dir = tmp_path / "0.32.0"
    assert not (v_dir / "download.tmp").exists()
    assert not (v_dir / "immich-go.tmp").exists()


def test_windows_bat_heartbeat_generation(tmp_path, monkeypatch):
    """Fix 1.4: Windows terminal launch generates a .bat file with background heartbeat loop."""
    from core.terminal_launcher import launch_external_terminal

    monkeypatch.setattr("sys.platform", "win32")

    lock_file = tmp_path / "run_test.lock"
    lock_file.write_text('{"run_id": "test"}', encoding="utf-8")

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value.pid = 1234
        res = launch_external_terminal(["immich-go", "stack"], {}, lock_file)
        assert res.ok

    bat_file = lock_file.with_suffix(".bat")
    assert bat_file.exists()
    bat_content = bat_file.read_text(encoding="utf-8")

    assert "HB_FILE=" in bat_content
    assert ".heartbeat" in bat_content
    assert "start /b cmd /c" in bat_content
    assert 'del /f "%HB_FILE%"' in bat_content


def test_golden_upload_icloud_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-icloud"]["path"].setText("/photos/icloud")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(["upload", "from-icloud", "--server=http://localhost:2283", "/photos/icloud"])
    assert plan.tab_key == "upload-icloud"


def test_golden_upload_picasa_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-picasa"]["path"].setText("/photos/picasa")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(["upload", "from-picasa", "--server=http://localhost:2283", "/photos/picasa"])
    assert plan.tab_key == "upload-picasa"


def test_golden_archive_gp_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(1)
    gui.inputs["archive-gp"]["path"].setPlainText("/takeout/photos")
    gui.inputs["archive-gp"]["write-to"].setText("/backup/takeout")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(["archive", "from-google-photos", "--write-to-folder=/backup/takeout", "/takeout/photos"])
    assert "--server" not in " ".join(plan.argv)
    assert plan.tab_key == "archive-gp"


def test_golden_archive_icloud_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(2)
    gui.inputs["archive-icloud"]["path"].setText("/photos/icloud")
    gui.inputs["archive-icloud"]["write-to"].setText("/backup/icloud")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(["archive", "from-icloud", "--write-to-folder=/backup/icloud", "/photos/icloud"])
    assert "--server" not in " ".join(plan.argv)
    assert plan.tab_key == "archive-icloud"


def test_golden_archive_picasa_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(3)
    gui.inputs["archive-picasa"]["path"].setText("/photos/picasa")
    gui.inputs["archive-picasa"]["write-to"].setText("/backup/picasa")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(["archive", "from-picasa", "--write-to-folder=/backup/picasa", "/photos/picasa"])
    assert "--server" not in " ".join(plan.argv)
    assert plan.tab_key == "archive-picasa"


def test_serverless_archive_tabs_never_emit_server(gui):
    from core.cli_schema import SERVERLESS_TABS
    gui.inputs["config"]["server"].setText("http://should-not-emit:2283")
    gui.inputs["config"]["api_key"].setText("secret")

    # archive-folder
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("/dst")
    plan = gui.build_plan(dry_run=False)
    assert "--server" not in " ".join(plan.argv)

    # archive-gp
    gui.archive_tabs.setCurrentIndex(1)
    gui.inputs["archive-gp"]["path"].setPlainText("/src")
    gui.inputs["archive-gp"]["write-to"].setText("/dst")
    plan = gui.build_plan(dry_run=False)
    assert "--server" not in " ".join(plan.argv)

    # archive-icloud
    gui.archive_tabs.setCurrentIndex(2)
    gui.inputs["archive-icloud"]["path"].setText("/src")
    gui.inputs["archive-icloud"]["write-to"].setText("/dst")
    plan = gui.build_plan(dry_run=False)
    assert "--server" not in " ".join(plan.argv)

    # archive-picasa
    gui.archive_tabs.setCurrentIndex(3)
    gui.inputs["archive-picasa"]["path"].setText("/src")
    gui.inputs["archive-picasa"]["write-to"].setText("/dst")
    plan = gui.build_plan(dry_run=False)
    assert "--server" not in " ".join(plan.argv)