from tests.conftest import _norm_argv


def test_tab_switching_updates_crumb(gui):
    gui.stacked_widget.setCurrentIndex(1)  # Upload page
    gui.upload_tabs.setCurrentIndex(1)  # Google Takeout sub-tab
    assert gui.lbl_crumb.text() == "upload · from-google-photos"

    gui.upload_tabs.setCurrentIndex(4)  # From Immich sub-tab
    assert gui.lbl_crumb.text() == "upload · from-immich"

    gui.stacked_widget.setCurrentIndex(2)  # Archive page
    gui.archive_tabs.setCurrentIndex(4)  # Archive Server sub-tab
    assert gui.lbl_crumb.text() == "archive · from-immich"


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
    gui.upload_tabs.setCurrentIndex(4)  # upload-immich sub-tab
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("local-key")
    gui.inputs["upload-immich"]["from-server"].setText("http://remote:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("remote-key")
    # from-date-range and from-albums are now simple-mode controls
    gui.inputs["upload-immich"]["from-date-range"].setText("2020-01-01,2021-01-01")
    gui.inputs["upload-immich"]["from-albums"].setText("Album1, Album2")
    gui.adv_rows["upload-immich"]["from-favorite"].set_state(
        {"enabled": True, "value": True}
    )
    gui.adv_rows["upload-immich"]["from-archived"].set_state(
        {"enabled": True, "value": True}
    )
    gui.adv_rows["upload-immich"]["from-trash"].set_state(
        {"enabled": True, "value": True}
    )
    gui.adv_rows["upload-immich"]["from-minimal-rating"].set_state(
        {"enabled": True, "value": 3}
    )
    gui.adv_rows["upload-immich"]["from-people"].set_state(
        {"enabled": True, "value": "John, Jane"}
    )
    gui.adv_rows["upload-immich"]["from-tags"].set_state(
        {"enabled": True, "value": "Vacation, Family"}
    )
    gui.adv_rows["upload-immich"]["from-city"].set_state(
        {"enabled": True, "value": "Paris"}
    )
    gui.adv_rows["upload-immich"]["from-state"].set_state(
        {"enabled": True, "value": "IDF"}
    )
    gui.adv_rows["upload-immich"]["from-country"].set_state(
        {"enabled": True, "value": "France"}
    )
    gui.adv_rows["upload-immich"]["from-make"].set_state(
        {"enabled": True, "value": "Apple"}
    )
    gui.adv_rows["upload-immich"]["from-model"].set_state(
        {"enabled": True, "value": "iPhone 13"}
    )
    gui.adv_rows["upload-immich"]["from-skip-ssl"].set_state(
        {"enabled": True, "value": True}
    )
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
    gui.archive_tabs.setCurrentIndex(0)  # archive-folder sub-tab
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["archive-folder"]["path"].setText("/source/folder")
    gui.inputs["archive-folder"]["write-to"].setText("/dest/folder")
    gui.adv_rows["archive-folder"]["date-range"].set_state(
        {"enabled": True, "value": "2024-01-01,2024-02-01"}
    )
    opts = _norm_argv(gui.build_command(dry_run=True))
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
    gui.archive_tabs.setCurrentIndex(4)  # archive-immich sub-tab
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-immich"]["write-to"].setText("/dest/folder")
    # from-date-range and from-albums are now simple-mode controls
    gui.inputs["archive-immich"]["from-date-range"].setText("2024-01-01,2024-02-01")
    gui.inputs["archive-immich"]["from-albums"].setText("ArchiveAlbum")
    opts = _norm_argv(gui.build_command(dry_run=False))
    assert "archive" in opts
    assert "from-immich" in opts
    assert "--write-to-folder=/dest/folder" in opts
    assert "--from-date-range=2024-01-01,2024-02-01" in opts
    assert "--from-albums=ArchiveAlbum" in opts
    assert "--dry-run" not in opts


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


def test_gp_simple_card_has_restored_checkboxes(gui):
    """A9: GP simple card has include-partner, sync-albums, include-archived checkboxes."""
    gp_inputs = gui.inputs.get("upload-gp", {})
    assert "include-partner" in gp_inputs
    assert "sync-albums" in gp_inputs
    assert "include-archived" in gp_inputs


def test_upload_immich_simple_mode_has_no_from_favorite_widget(gui):
    """A1: from-favorite must NOT be a simple-mode widget (it's advanced-only)."""
    assert "from-favorite" not in gui.inputs.get("upload-immich", {})
