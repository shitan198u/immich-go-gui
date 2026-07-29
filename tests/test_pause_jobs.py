from core.command_builder import FlagEmitter
from core.command_builder import build_plan_from_state as _build_plan


def test_pause_jobs_not_on_archive(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(2)  # archive page
    gui.archive_tabs.setCurrentIndex(0)  # archive-folder
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("/dst")
    opts = gui.build_command(dry_run=False)
    assert not any("--pause-immich-jobs" in o for o in opts)


def test_pause_jobs_auto_disables_on_stack_without_admin_key(gui):
    """Without an admin key, --pause-immich-jobs=false is emitted on stack tab
    to prevent 403 Forbidden from the server. See issue #64."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(3)  # stack
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    # Explicitly confirm no admin key is set
    gui.inputs["config"]["admin_api_key"].setText("")
    opts = gui.build_command(dry_run=False)
    assert "--pause-immich-jobs=false" in opts


def _pause_flag_args(argv):
    emitter = FlagEmitter("upload-folder")
    return [a for a in argv if emitter._flag_name_from_arg(a) == "pause-immich-jobs"]


class TestPauseJobsAutoDisable:
    """Regression tests for Bug #64: --pause-immich-jobs + no admin key = 403."""

    _BASE_CONFIG = {
        "server": "http://localhost:2283",
        "api_key": "user-key",
    }

    def test_pause_disabled_when_no_admin_key(self):
        """Default pause=True + no admin key: auto-emit --pause-immich-jobs=false + warning."""
        plan = _build_plan(
            tab_key="upload-folder",
            config_state={**self._BASE_CONFIG, "admin_api_key": ""},
            tab_state={"path": "/photos"},
            binary_path="./immich-go",
        )
        assert "--pause-immich-jobs=false" in plan.argv, (
            "Expected --pause-immich-jobs=false when no admin key is set"
        )
        assert any("Admin API Key" in w for w in plan.warnings), (
            f"Expected a warning about Admin API Key; got: {plan.warnings}"
        )

    def test_pause_not_disabled_when_admin_key_present(self):
        """When admin key is set, do not auto-disable pausing."""
        plan = _build_plan(
            tab_key="upload-folder",
            config_state={**self._BASE_CONFIG, "admin_api_key": "admin-secret"},
            tab_state={"path": "/photos"},
            binary_path="./immich-go",
        )
        assert "--pause-immich-jobs=false" not in plan.argv, (
            "Should not auto-disable when admin key is provided"
        )
        assert not any("Admin API Key" in w for w in plan.warnings)

    def test_explicit_pause_false_no_admin_key(self):
        """Explicit pause=False via advanced row + no admin key: flag appears once, no warning."""
        plan = _build_plan(
            tab_key="upload-folder",
            config_state={**self._BASE_CONFIG, "admin_api_key": ""},
            tab_state={"path": "/photos"},
            advanced_state={"pause-jobs": {"enabled": True, "value": False}},
            binary_path="./immich-go",
        )
        pause_flags = _pause_flag_args(plan.argv)
        assert len(pause_flags) == 1, (
            f"Expected exactly one pause flag; got: {pause_flags}"
        )
        assert pause_flags[0] == "--pause-immich-jobs=false"
        assert not any("Admin API Key" in w for w in plan.warnings)

    def test_pause_auto_disable_on_stack_tab(self):
        """Auto-disable also applies to the 'stack' tab (not just upload tabs)."""
        plan = _build_plan(
            tab_key="stack",
            config_state={**self._BASE_CONFIG, "admin_api_key": ""},
            tab_state={},
            binary_path="./immich-go",
        )
        assert "--pause-immich-jobs=false" in plan.argv
        assert any("Admin API Key" in w for w in plan.warnings)

    def test_pause_auto_disable_on_all_upload_tabs(self):
        """Auto-disable applies to all upload tabs."""
        from core.cli_schema import UPLOAD_TABS

        tab_paths = {
            "upload-folder": {"path": "/photos"},
            "upload-gp": {"path": "/takeout.zip"},
            "upload-icloud": {"path": "/icloud"},
            "upload-picasa": {"path": "/picasa"},
        }
        for tab_key in UPLOAD_TABS:
            if tab_key == "upload-immich":
                tab_state = {
                    "from-server": "http://old:2283",
                    "from-api-key": "old-key",
                }
            else:
                tab_state = tab_paths.get(tab_key, {"path": "/photos"})

            plan = _build_plan(
                tab_key=tab_key,
                config_state={**self._BASE_CONFIG, "admin_api_key": ""},
                tab_state=tab_state,
                binary_path="./immich-go",
            )
            assert "--pause-immich-jobs=false" in plan.argv, (
                f"Expected auto-disable on tab '{tab_key}'; argv={plan.argv}"
            )

    def test_from_pause_does_not_suppress_dest_pause_safety(self):
        """from-pause-immich-jobs must not block destination pause safety injection."""
        plan = _build_plan(
            tab_key="upload-immich",
            config_state={**self._BASE_CONFIG, "admin_api_key": ""},
            tab_state={"from-server": "http://old:2283", "from-api-key": "old-key"},
            advanced_state={"from-pause-jobs": {"enabled": True, "value": True}},
            binary_path="./immich-go",
        )
        assert "--pause-immich-jobs=false" in plan.argv

    def test_no_double_pause_flag_injection(self):
        """When admin key is absent AND pause=False via advanced row, only one flag is emitted."""
        plan = _build_plan(
            tab_key="upload-gp",
            config_state={**self._BASE_CONFIG, "admin_api_key": ""},
            tab_state={"path": "/takeout.zip"},
            advanced_state={"pause-jobs": {"enabled": True, "value": False}},
            binary_path="./immich-go",
        )
        pause_flags = _pause_flag_args(plan.argv)
        assert len(pause_flags) == 1, (
            f"Expected exactly one pause flag; got: {pause_flags}"
        )


def test_from_pause_jobs_warning_without_from_admin_key():
    plan = _build_plan(
        tab_key="upload-immich",
        config_state={"server": "http://localhost:2283", "api_key": "k"},
        tab_state={"from-server": "http://source:2283", "from-api-key": "sk"},
        advanced_state={"from-pause-jobs": {"enabled": True, "value": True}},
        binary_path="./immich-go",
    )
    assert any("Source job pausing enabled" in w for w in plan.warnings)


def test_from_pause_jobs_no_warning_with_from_admin_key():
    plan = _build_plan(
        tab_key="upload-immich",
        config_state={"server": "http://localhost:2283", "api_key": "k"},
        tab_state={
            "from-server": "http://source:2283",
            "from-api-key": "sk",
            "from-admin-api-key": "admin-sk",
        },
        advanced_state={"from-pause-jobs": {"enabled": True, "value": True}},
        binary_path="./immich-go",
    )
    assert not any("Source job pausing enabled" in w for w in plan.warnings)
