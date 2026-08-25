import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.cli_contract import check_fixtures
from core.cli_help import help_name_for_tab, load_help_fixture, parse_help_flags
from core.cli_schema import TAB_ALLOWED_FLAGS
from core.command_builder import (
    FlagEmitter,
    build_environment,
    build_plan_from_state,
    collect_paths,
    mask_command_for_display,
    validate_date_range,
)
from core.flag_registry import REGISTRY
from core.network import normalize_server_url
from core.process_tracker import create_lock, is_lock_active
from core.validation import (
    clean_date_range,
    expand_source_paths,
    has_glob_pattern,
    normalize_extensions_csv,
    normalize_list_csv,
    validate_destination_folder,
)
from core.validation import validate_date_range as validate_date_range_core
from tests.conftest import _norm_argv


def test_collect_paths_single_file():
    assert _norm_argv(collect_paths("/path/to/file.zip")) == _norm_argv(
        ["/path/to/file.zip"]
    )


def test_collect_paths_multiline():
    text = "/path/one.zip\n\n/path/two.zip\n"
    assert _norm_argv(collect_paths(text)) == _norm_argv(
        ["/path/one.zip", "/path/two.zip"]
    )


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
    assert (
        normalize_server_url("https://photos.example.com/")
        == "https://photos.example.com"
    )


def test_normalize_server_url_empty():
    assert normalize_server_url("") == ""
    assert normalize_server_url("   ") == ""


def test_mask_command_for_display():
    cmd = [
        "immich-go",
        "upload",
        "from-folder",
        "--server=http://local",
        "--api-key=super_secret_123",
        "/photos",
    ]
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
    assert normalize_list_csv(" vacation, family/reunion , ") == [
        "vacation",
        "family/reunion",
    ]
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


def test_command_builder_destructive_warnings():
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


def test_admin_api_key_environment_passing():
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
    tabs = list(REGISTRY.tabs.keys())
    for tab_key in tabs:
        fixture_name = help_name_for_tab(tab_key)
        fixture_flags = load_help_fixture("0.32.0", fixture_name)
        allowed_flags = TAB_ALLOWED_FLAGS[tab_key]

        for flag in allowed_flags:
            assert flag in fixture_flags, (
                f"Flag '--{flag}' registered in TAB_ALLOWED_FLAGS[{tab_key}] was not found in fixture '{fixture_name}'"
            )


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


def test_check_fixtures_compatibility():
    report = check_fixtures("0.32.0")
    assert report.version == "0.32.0"
    assert report.is_fully_compatible() is True
    assert len(report.missing_flags_by_tab) == 0


def test_compat_ignore_list_excludes_api_key_flags():
    report = check_fixtures("0.32.0")
    for flags in report.unknown_flags_by_tab.values():
        assert "api-key" not in flags
        assert "from-api-key" not in flags


def test_show_cli_compatibility_dialog(gui):
    with patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
        gui.show_cli_compatibility_dialog()
        assert mock_info.called
        title = mock_info.call_args[0][1]
        assert "CLI Compatibility" in title


def test_stale_lock_detection_with_pid_and_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    from core.process_tracker import (
        release_lock,
        update_lock,
    )

    l_path = create_lock("upload-folder", "upload", "./immich-go")
    assert is_lock_active(l_path) is True

    # Record dead PID (999999)
    update_lock(l_path, shell_pid=999999, started_at="2020-01-01T00:00:00+00:00")
    assert is_lock_active(l_path) is False

    # Record current process PID
    update_lock(l_path, shell_pid=os.getpid())
    assert is_lock_active(l_path) is True

    release_lock(l_path)


def test_default_true_boolean_emission():
    config_state = {
        "server": "http://localhost:2283",
        "api_key": "test_key",
        "admin_api_key": "admin_key",
    }

    # upload-folder boolean flags explicitly enabled and set to False
    tab_state_folder = {"path": "/photos"}
    advanced_folder = {
        "recursive": {"enabled": True, "value": False},
        "date-from-name": {"enabled": True, "value": False},
        "pause-jobs": {"enabled": True, "value": False},
    }
    plan_folder = build_plan_from_state(
        "upload-folder", config_state, tab_state_folder, advanced_state=advanced_folder
    )
    assert "--recursive=false" in plan_folder.argv
    assert "--date-from-name=false" in plan_folder.argv
    assert "--pause-immich-jobs=false" in plan_folder.argv
    pause_sources = [
        e for e in plan_folder.emission_log if e["key"] == "pause-immich-jobs"
    ]
    assert pause_sources and pause_sources[0]["source"] == "advanced"

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
    plan_gp = build_plan_from_state(
        "upload-gp", config_state, tab_state_gp, advanced_state=advanced_gp
    )
    assert "--include-archived=false" in plan_gp.argv
    assert "--include-partner=false" in plan_gp.argv
    assert "--sync-albums=false" in plan_gp.argv
    assert "--takeout-tag=false" in plan_gp.argv
    assert "--people-tag=false" in plan_gp.argv


def test_collect_paths_expansion_and_abspath(tmp_path):
    from core.command_builder import collect_paths

    rel_path = "./subfolder"
    paths = collect_paths(rel_path)
    assert len(paths) == 1
    assert os.path.isabs(paths[0])


def test_missing_fixtures_not_fully_compatible(tmp_path):
    from core.cli_contract import check_fixtures

    _ = (
        check_fixtures.__wrapped__(str(tmp_path / "missing-fixtures"))
        if hasattr(check_fixtures, "__wrapped__")
        else None
    )
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

    gui.adv_rows["upload-folder"]["time-zone"].set_state(
        {
            "enabled": False,
            "value": "UTC",
        }
    )

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

    gui.adv_rows["upload-folder"]["time-zone"].set_state(
        {
            "enabled": True,
            "value": "UTC",
        }
    )

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

    gui.adv_rows["upload-folder"]["recursive"].set_state(
        {
            "enabled": True,
            "value": False,
        }
    )

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

    gui.adv_rows["upload-gp"]["include-trashed"].set_state(
        {
            "enabled": True,
            "value": True,
        }
    )

    plan = gui.build_plan(dry_run=False)
    assert "--include-trashed" in plan.argv


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

    ok, err = validate_server_url("http://")
    assert ok is False

    ok, err = validate_server_url("http://localhost:999999")
    assert ok is False
    assert "port" in err.lower()


def test_cleanup_stale_temp_dirs(tmp_path, monkeypatch):
    import time

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


def test_advanced_keys_match_registry():
    from core.advanced_flags import ADVANCED_FLAGS

    for tab, defs in ADVANCED_FLAGS.items():
        expected = {def_.key for def_ in defs}
        assert REGISTRY.advanced_keys(tab) == expected


def test_from_admin_api_key_advanced_secret_env(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(4)

    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new-key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")

    gui.adv_rows["upload-immich"]["from-admin-api-key"].set_state(
        {
            "enabled": True,
            "value": "old-admin-secret",
        }
    )

    plan = gui.build_plan(False)

    assert "--from-admin-api-key" not in " ".join(plan.argv)
    assert "old-admin-secret" not in " ".join(plan.argv)
    assert (
        plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY")
        == "old-admin-secret"
    )


def test_no_duplicate_test_names():
    """A2: Ensure no duplicate test function names exist in test_app.py."""
    import ast
    import collections

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    names = [
        n.name
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    ]
    dupes = [n for n, c in collections.Counter(names).items() if c > 1]
    assert not dupes, f"Duplicate test names found in test_app.py: {dupes}"


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
                missing.append(
                    f"'{d.flag}' in ADVANCED_FLAGS['{tab}'] missing from TAB_ALLOWED_FLAGS"
                )

    assert not missing, "\n".join(missing)


def test_validate_advanced_state_rejects_invalid_month():
    """A3: validate_advanced_state must reject semantically invalid dates."""
    from core.advanced_flags import validate_advanced_state

    # Month 13 is invalid
    result = validate_advanced_state(
        "upload-folder",
        {"date-range": {"enabled": True, "value": "2023-13-01,2023-12-31"}},
    )
    assert not result.is_valid
    assert any("date" in e.lower() or "invalid" in e.lower() for e in result.errors)


def test_validate_advanced_state_rejects_reversed_range():
    """A3: validate_advanced_state must reject start > end date ranges."""
    from core.advanced_flags import validate_advanced_state

    result = validate_advanced_state(
        "upload-folder",
        {"date-range": {"enabled": True, "value": "2023-12-31,2023-01-01"}},
    )
    assert not result.is_valid
    assert result.errors


def test_validate_advanced_state_accepts_valid_date_range():
    """A3: validate_advanced_state must accept well-formed date ranges."""
    from core.advanced_flags import validate_advanced_state

    result = validate_advanced_state(
        "upload-folder",
        {"date-range": {"enabled": True, "value": "2023-01-01,2023-12-31"}},
    )
    assert result.is_valid
    assert not result.errors


def test_env_var_secret_contract_with_stub(gui):
    """Fix 1.2: Verify subprocess receives secrets via env vars and never in argv."""
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
    gui.adv_rows["upload-immich"]["from-admin-api-key"].set_state(
        {
            "enabled": True,
            "value": "source-admin-secret-789",
        }
    )

    plan = gui.build_plan(dry_run=False)

    # 1. Assert secret values NEVER appear in plan.argv
    for secret in (
        "target-secret-key-123",
        "source-secret-key-456",
        "source-admin-secret-789",
    ):
        assert not any(secret in arg for arg in plan.argv), (
            f"Secret '{secret}' leaked into argv!"
        )

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
    assert (
        received_env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER")
        == "http://source:2283"
    )
    assert (
        received_env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY")
        == "source-secret-key-456"
    )
    assert (
        received_env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY")
        == "source-admin-secret-789"
    )

    # 4. Assert secrets are not in received argv
    for secret in (
        "target-secret-key-123",
        "source-secret-key-456",
        "source-admin-secret-789",
    ):
        assert not any(secret in arg for arg in received_argv)


def test_flag_emitter_allows_repeat_options():
    from core.command_builder import FlagEmitter

    emitter = FlagEmitter("upload-folder", strict=False)
    assert emitter.add_option("tag", "a") is True
    assert emitter.add_option("tag", "b") is True
    assert emitter.opts == ["--tag=a", "--tag=b"]


def test_emission_log_populated():
    config_state = {
        "server": "http://localhost:2283",
        "api_key": "key",
    }
    plan = build_plan_from_state(
        "upload-folder",
        config_state,
        {"path": "/photos"},
        advanced_state={"on-errors": {"enabled": True, "value": "continue"}},
    )
    assert plan.emission_log
    sources = {e["source"] for e in plan.emission_log}
    assert "always" in sources
    assert "advanced" in sources
    assert any(e["flag"] == "--on-errors=continue" for e in plan.emission_log)


def test_overwrite_warn_values(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["overwrite"].set_state(
        {"enabled": True, "value": True}
    )
    plan = gui.build_plan(dry_run=False)
    assert "--overwrite" in plan.argv
    assert any("Overwrite mode" in w for w in plan.warnings)


def test_log_file_created_and_masked(tmp_path, monkeypatch):
    import logging

    from core.logging_config import setup_logging
    from core.models import CommandPlan

    monkeypatch.setattr(
        "core.logging_config.default_config_dir",
        lambda: tmp_path,
    )
    # Reset logger handlers between runs
    logger = logging.getLogger("immich_go_gui")
    logger.handlers.clear()
    log = setup_logging()
    plan = CommandPlan(
        tab_key="upload-folder",
        argv=["upload", "from-folder", "--server=http://x"],
        env={"IMMICH_GO_UPLOAD_API_KEY": "super-secret"},
        display_argv=["immich-go", "upload", "from-folder", "--server=http://x"],
    )
    log.info(
        "Launching: tab=%s argv=%s env_keys=%s",
        plan.tab_key,
        plan.display_argv,
        sorted(plan.env.keys()),
    )
    for h in log.handlers:
        h.flush()
    text = (tmp_path / "logs" / "immich-go-gui.log").read_text(encoding="utf-8")
    assert "upload-folder" in text
    assert "super-secret" not in text
    assert "IMMICH_GO_UPLOAD_API_KEY" in text
