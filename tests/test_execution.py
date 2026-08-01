import os
from unittest.mock import patch

from core.command_builder import build_environment, build_plan_from_state
from core.flag_registry import REGISTRY
from core.models import CommandPlan
from tests.conftest import _norm_argv


def test_global_flag_ordering(gui):
    """Global opts (--log-level) must appear in subcommand options when enabled in advanced flags."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)  # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.adv_rows["upload-folder"]["log-level"].set_state(
        {"enabled": True, "value": "DEBUG"}
    )
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--log-level=DEBUG" in opts


def test_on_errors_emitted_when_configured(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(4)  # archive-immich
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-immich"]["write-to"].setText("/dst")
    gui.adv_rows["archive-immich"]["on-errors"].set_state(
        {"enabled": True, "value": "continue"}
    )
    opts = gui.build_command(dry_run=False)
    assert "--on-errors=continue" in opts


def test_client_timeout_emitted(gui):
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)  # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["client_timeout_minutes"].setValue(60)
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--client-timeout=60m" in opts


def test_device_uuid_emitted(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)  # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.adv_rows["upload-folder"]["device-uuid"].set_state(
        {"enabled": True, "value": "my-device-123"}
    )
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=False)
    assert "--device-uuid=my-device-123" in opts


def test_api_trace_on_upload_gp(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(1)  # upload-gp
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
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(4)  # upload-immich
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["client_timeout_minutes"].setValue(60)
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    opts = gui.build_command(dry_run=False)
    assert "--from-client-timeout=60m" in opts
    assert "--client-timeout=60m" in opts


def test_gp_multi_path(gui):
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(1)  # upload-gp
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout-001.zip\n/takeout-002.zip")
    opts = _norm_argv(gui.build_command(dry_run=False))
    assert "/takeout-001.zip" in opts
    assert "/takeout-002.zip" in opts


def test_archive_immich_global_skip_ssl(gui):
    gui.inputs["config"]["skip-ssl"].setChecked(True)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-immich"]["write-to"].setText("/backup")
    opts = gui.build_command(dry_run=True)
    assert "--from-skip-verify-ssl" in opts


def test_upload_immich_global_skip_ssl(gui):
    gui.inputs["config"]["skip-ssl"].setChecked(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    opts = gui.build_command(dry_run=True)
    assert "--from-skip-verify-ssl" in opts
    assert "--skip-verify-ssl" in opts


def test_global_skip_ssl_option(gui):
    gui.inputs["config"]["skip-ssl"].setChecked(True)
    gui.stacked_widget.setCurrentIndex(1)  # upload page
    gui.upload_tabs.setCurrentIndex(0)  # upload-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    opts = gui.build_command(dry_run=True)
    assert "--skip-verify-ssl" in opts


def test_simple_mode_ignores_advanced_upload_folder_flags(gui):
    gui.toggle_advanced(False)

    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")

    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["log-level"].set_state(
        {"enabled": True, "value": "DEBUG"}
    )
    gui.adv_rows["upload-folder"]["recursive"].set_state(
        {"enabled": True, "value": False}
    )
    gui.adv_rows["upload-folder"]["date-from-name"].set_state(
        {"enabled": True, "value": False}
    )
    gui.adv_rows["upload-folder"]["album-path-joiner"].set_state(
        {"enabled": True, "value": "/"}
    )
    gui.adv_rows["upload-folder"]["time-zone"].set_state(
        {"enabled": True, "value": "UTC"}
    )
    gui.adv_rows["upload-folder"]["manage-epson"].set_state(
        {"enabled": True, "value": True}
    )

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
    gui.adv_rows["upload-folder"]["log-level"].set_state(
        {"enabled": True, "value": "DEBUG"}
    )
    gui.adv_rows["upload-folder"]["recursive"].set_state(
        {"enabled": True, "value": False}
    )
    gui.adv_rows["upload-folder"]["date-from-name"].set_state(
        {"enabled": True, "value": False}
    )
    gui.adv_rows["upload-folder"]["album-path-joiner"].set_state(
        {"enabled": True, "value": "/"}
    )
    gui.adv_rows["upload-folder"]["time-zone"].set_state(
        {"enabled": True, "value": "UTC"}
    )
    gui.adv_rows["upload-folder"]["manage-epson"].set_state(
        {"enabled": True, "value": True}
    )

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

    gui.adv_rows["stack"]["date-range"].set_state(
        {"enabled": True, "value": "2023-01-01,2023-12-31"}
    )
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


def test_archive_immich_source_model_env():
    env = build_environment(
        tab_key="archive-immich",
        server="http://source-server:2283",
        api_key="source-key",
        admin_api_key="source-admin-key",
    )
    assert (
        env.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER")
        == "http://source-server:2283"
    )
    assert env.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_API_KEY") == "source-key"
    assert (
        env.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_ADMIN_API_KEY")
        == "source-admin-key"
    )
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
    assert "--write-to-folder=/dest/folder" in _norm_argv(plan.argv)
    assert "--dry-run" in plan.argv
    assert not any(arg.startswith("--server=") for arg in plan.argv)


def test_plan_errors_surfaced_in_gui(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

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
    plan = build_plan_from_state(
        "archive-immich", config_state, tab_state, dry_run=True
    )
    assert "--dry-run" in plan.argv
    assert "--from-dry-run" in plan.argv


def test_stack_pause_jobs_and_archive_folder_on_errors():
    from core.command_builder import build_plan_from_state

    config_state = {"server": "http://localhost:2283", "api_key": "test"}
    plan_stack = build_plan_from_state(
        "stack",
        config_state,
        {},
        advanced_state={"pause-jobs": {"enabled": True, "value": False}},
    )
    assert "--pause-immich-jobs=false" in plan_stack.argv

    plan_archive = build_plan_from_state(
        "archive-folder",
        config_state,
        {"path": "/src", "write-to": "/dst"},
        advanced_state={"on-errors": {"enabled": True, "value": "continue"}},
    )
    assert "--on-errors=continue" in plan_archive.argv


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


def test_simple_mode_ignores_advanced_rows(gui):
    """Verify Simple mode ignores advanced flag rows even if enabled."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    gui.adv_rows["upload-folder"]["time-zone"].set_state(
        {
            "enabled": True,
            "value": "UTC",
        }
    )

    plan = gui.build_plan(dry_run=False)
    assert "--time-zone=UTC" not in plan.argv


def test_form_state_advanced_rows_persistence(gui):
    """Verify form state serialization and deserialization of advanced flag rows."""
    gui.adv_rows["upload-folder"]["time-zone"].set_state(
        {
            "enabled": True,
            "value": "America/New_York",
        }
    )

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


def test_upload_gp_path_warnings(gui, tmp_path):
    nonexistent = str(tmp_path / "missing_takeout")
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["upload-gp"]["path"].setPlainText(nonexistent)

    val = gui.validate_inputs()
    assert any("does not exist" in w for w in val.warnings)


def test_upload_gp_has_no_into_album_advanced_key():
    assert "into-album" not in REGISTRY.advanced_keys("upload-gp")


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


def test_serverless_archive_tabs_never_emit_server(gui):
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


def test_from_dry_run_button_only_one_flag(gui):
    """Dry Run button on archive-immich emits a single --from-dry-run."""
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-immich"]["write-to"].setText("/backup")
    plan = gui.build_plan(dry_run=True)
    count = sum(1 for a in plan.argv if a == "--from-dry-run")
    assert count == 1


def test_upload_icloud_advanced_flag_emission(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)  # upload-icloud
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-icloud"]["path"].setText("/icloud")
    gui.adv_rows["upload-icloud"]["recursive"].set_state(
        {"enabled": True, "value": False}
    )
    gui.adv_rows["upload-icloud"]["api-trace"].set_state(
        {"enabled": True, "value": True}
    )
    plan = gui.build_plan(dry_run=False)
    assert "--recursive=false" in plan.argv
    assert "--api-trace" in plan.argv


def test_upload_picasa_advanced_flag_emission(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(3)  # upload-picasa
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-picasa"]["path"].setText("/picasa")
    gui.adv_rows["upload-picasa"]["recursive"].set_state(
        {"enabled": True, "value": False}
    )
    gui.adv_rows["upload-picasa"]["album-picasa"].set_state(
        {"enabled": True, "value": True}
    )
    plan = gui.build_plan(dry_run=False)
    assert "--recursive=false" in plan.argv
    assert "--album-picasa" in plan.argv


def test_upload_folder_log_level_is_advanced_mode():
    defs = {d.key: d for d in REGISTRY.flags["upload-folder"]}
    assert defs["log-level"].mode == "advanced"
