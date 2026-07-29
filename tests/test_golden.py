import json
from pathlib import Path

from core.command_builder import build_plan_from_state
from tests.conftest import _norm_argv


def test_golden_upload_folder(gui):
    """Golden: upload-folder simple mode minimal command."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["admin_api_key"].setText("admin-key")  # prevent auto-disable
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "upload",
            "from-folder",
            "--server=http://localhost:2283",
            "--client-timeout=60m",
            "/photos",
        ]
    )
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert not any("--api-key" in p for p in plan.argv)


def test_golden_upload_gp(gui):
    """Golden: upload from-google-photos simple mode minimal command."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["admin_api_key"].setText("admin-key")  # prevent auto-disable
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout-001.zip\n/takeout-002.zip")

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "upload",
            "from-google-photos",
            "--server=http://localhost:2283",
            "--client-timeout=60m",
            "/takeout-001.zip",
            "/takeout-002.zip",
        ]
    )


def test_golden_stack(gui):
    """Golden: stack simple mode command."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["admin_api_key"].setText("admin-key")  # prevent auto-disable
    gui.inputs["stack"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["stack"]["manage-raw-jpeg"].setCurrentText("NoStack")
    gui.inputs["stack"]["manage-heic-jpeg"].setCurrentText("NoStack")

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "stack",
            "--server=http://localhost:2283",
            "--client-timeout=60m",
            "--manage-burst=Stack",
        ]
    )


def test_golden_stack_advanced_with_date_range(gui):
    """Golden: stack advanced mode command with date-range flag."""
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["admin_api_key"].setText("admin-key")  # prevent auto-disable
    gui.inputs["stack"]["manage-burst"].setCurrentText("Stack")
    gui.adv_rows["stack"]["date-range"].set_state(
        {"enabled": True, "value": "2023-01-01,2023-12-31"}
    )

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "stack",
            "--server=http://localhost:2283",
            "--client-timeout=60m",
            "--manage-burst=Stack",
            "--date-range=2023-01-01,2023-12-31",
        ]
    )


def test_golden_archive_folder(gui):
    """Golden: archive from-folder simple mode."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["archive-folder"]["path"].setText("/messy/photos")
    gui.inputs["archive-folder"]["write-to"].setText("/organized")

    plan = gui.build_plan(dry_run=True)

    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "archive",
            "from-folder",
            "--write-to-folder=/organized",
            "--dry-run",
            "/messy/photos",
        ]
    )
    assert not any("--server" in p for p in plan.argv)


def test_golden_upload_immich(gui):
    """Golden: upload from-immich simple mode."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(4)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new-key")
    gui.inputs["config"]["admin_api_key"].setText("admin-key")  # prevent auto-disable
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    gui.inputs["upload-immich"]["from-date-range"].clear()
    gui.inputs["upload-immich"]["from-albums"].clear()

    plan = gui.build_plan(dry_run=False)

    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "upload",
            "from-immich",
            "--server=http://new:2283",
            "--from-client-timeout=60m",
            "--client-timeout=60m",
            "--from-server=http://old:2283",
        ]
    )
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

    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "archive",
            "from-immich",
            "--from-client-timeout=60m",
            "--from-server=http://localhost:2283",
            "--write-to-folder=/backup/photos",
        ]
    )
    assert plan.env.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_API_KEY") == "test-key"


def test_build_plan_from_state_upload_folder_golden():
    config_state = {
        "server": "http://localhost:2283",
        "api_key": "test-key",
        "admin_api_key": "admin-key",
        "skip-ssl": False,
        "client_timeout_minutes": 60,
    }

    tab_state = {
        "path": "/photos",
        "folder-album": "NONE",
        "into-album": "",
        "manage-burst": "Stack",
        "manage-raw-jpeg": "NoStack",
        "manage-heic-jpeg": "NoStack",
    }

    plan = build_plan_from_state(
        tab_key="upload-folder",
        config_state=config_state,
        tab_state=tab_state,
        binary_path="./immich-go",
        dry_run=False,
        base_env={},
    )

    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "upload",
            "from-folder",
            "--server=http://localhost:2283",
            "--client-timeout=60m",
            "--manage-burst=Stack",
            "/photos",
        ]
    )

    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert not any("--api-key" in part for part in plan.argv)


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
        assert _norm_argv(plan.argv) == _norm_argv(expected_argv), (
            f"Fixture {jf.name} produced unexpected argv: {plan.argv} != {expected_argv}"
        )


def test_golden_upload_icloud_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["admin_api_key"].setText("admin-key")  # prevent auto-disable
    gui.inputs["upload-icloud"]["path"].setText("/photos/icloud")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "upload",
            "from-icloud",
            "--server=http://localhost:2283",
            "--client-timeout=60m",
            "/photos/icloud",
        ]
    )
    assert plan.tab_key == "upload-icloud"


def test_golden_upload_picasa_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["admin_api_key"].setText("admin-key")  # prevent auto-disable
    gui.inputs["upload-picasa"]["path"].setText("/photos/picasa")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "upload",
            "from-picasa",
            "--server=http://localhost:2283",
            "--client-timeout=60m",
            "/photos/picasa",
        ]
    )
    assert plan.tab_key == "upload-picasa"


def test_golden_archive_gp_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(1)
    gui.inputs["archive-gp"]["path"].setPlainText("/takeout/photos")
    gui.inputs["archive-gp"]["write-to"].setText("/backup/takeout")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(
        [
            "archive",
            "from-google-photos",
            "--write-to-folder=/backup/takeout",
            "/takeout/photos",
        ]
    )
    assert "--server" not in " ".join(plan.argv)
    assert plan.tab_key == "archive-gp"


def test_golden_archive_icloud_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(2)
    gui.inputs["archive-icloud"]["path"].setText("/photos/icloud")
    gui.inputs["archive-icloud"]["write-to"].setText("/backup/icloud")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(
        ["archive", "from-icloud", "--write-to-folder=/backup/icloud", "/photos/icloud"]
    )
    assert "--server" not in " ".join(plan.argv)
    assert plan.tab_key == "archive-icloud"


def test_golden_archive_picasa_simple(gui):
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(3)
    gui.inputs["archive-picasa"]["path"].setText("/photos/picasa")
    gui.inputs["archive-picasa"]["write-to"].setText("/backup/picasa")

    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv(
        ["archive", "from-picasa", "--write-to-folder=/backup/picasa", "/photos/picasa"]
    )
    assert "--server" not in " ".join(plan.argv)
    assert plan.tab_key == "archive-picasa"
