"""Tests for unified flag registry (core/flags.toml and core/flag_registry.py)."""

import pytest

from core.flag_registry import REGISTRY


def test_registry_loads():
    assert len(REGISTRY.tabs) == 11
    assert REGISTRY.serverless_tabs == {
        "archive-folder",
        "archive-gp",
        "archive-icloud",
        "archive-picasa",
    }
    assert REGISTRY.server_required_tabs == {
        "upload-folder",
        "upload-gp",
        "upload-icloud",
        "upload-picasa",
        "upload-immich",
        "archive-immich",
        "stack",
    }


def test_registry_flag_counts_match_docs():
    """Counts must match docs/reference/cli-command-mapping.md."""
    expected = {
        "upload-folder": 31,
        "upload-gp": 33,
        "upload-icloud": 31,
        "upload-picasa": 31,
        "upload-immich": 45,
        "archive-folder": 17,
        "archive-gp": 20,
        "archive-icloud": 18,
        "archive-picasa": 18,
        "archive-immich": 31,
        "stack": 16,
    }
    for tab, count in expected.items():
        allowed = REGISTRY.allowed_flags(tab)
        assert len(allowed) == count, (
            f"Tab {tab}: expected {count}, got {len(allowed)}: {sorted(allowed)}"
        )


def test_upload_picasa_folder_album_not_stripped_in_simple_mode(gui):
    """folder-album and into-album are simple-mode widgets on upload-picasa."""
    gui.toggle_advanced(False)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(3)  # upload-picasa
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["config"]["admin_api_key"].setText("admin-key")
    gui.inputs["upload-picasa"]["path"].setText("/photos/picasa")
    gui.inputs["upload-picasa"]["folder-album"].setCurrentText("FOLDER")
    gui.inputs["upload-picasa"]["into-album"].setText("My Album")
    plan = gui.build_plan(dry_run=False)
    assert "--folder-as-album=FOLDER" in plan.argv
    assert "--into-album=My Album" in plan.argv


def test_log_level_emitted_once_from_advanced_row(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.adv_rows["upload-folder"]["log-level"].set_state(
        {"enabled": True, "value": "DEBUG"}
    )
    plan = gui.build_plan(dry_run=False)
    log_flags = [a for a in plan.argv if "log-level" in a]
    assert len(log_flags) == 1, f"Expected single log-level flag: {log_flags}"


def test_picasa_simple_keys_are_not_advanced_only():
    """folder-album and into-album are simple mode, not advanced-only."""
    assert "folder-album" in REGISTRY.simple_keys("upload-picasa")
    assert "into-album" in REGISTRY.simple_keys("upload-picasa")
    assert "folder-album" not in REGISTRY.advanced_keys("upload-picasa")
    assert "into-album" not in REGISTRY.advanced_keys("upload-picasa")
    assert "recursive" in REGISTRY.advanced_keys("upload-picasa")


@pytest.mark.live_cli
def test_bool_defaults_match_live_cli():
    """Bool flag defaults in flags.toml must match live immich-go --help output."""
    import subprocess
    from pathlib import Path

    from core.binary_manager import (
        TESTED_IMMICH_GO_VERSION,
        get_binary_path,
        load_binary_metadata,
        parse_version_output,
    )
    from core.cli_contract import collect_bool_defaults_from_binary

    meta = load_binary_metadata()
    binary_path = get_binary_path(meta)
    if not binary_path or not Path(binary_path).exists():
        pytest.skip("immich-go binary not installed")

    try:
        res = subprocess.run(
            [binary_path, "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version = parse_version_output(res.stdout or res.stderr)
    except Exception:
        pytest.skip("immich-go binary not runnable")

    if version != TESTED_IMMICH_GO_VERSION:
        pytest.skip(
            f"immich-go version {version} != tested version {TESTED_IMMICH_GO_VERSION}"
        )

    cli_defaults = collect_bool_defaults_from_binary(Path(binary_path))

    for tab_key, flag_defs in REGISTRY.flags.items():
        tab_defaults = cli_defaults.get(tab_key, {})
        for flag_def in flag_defs:
            if flag_def.kind != "bool" or not flag_def.flag:
                continue
            if flag_def.flag not in tab_defaults:
                continue
            assert flag_def.default == tab_defaults[flag_def.flag], (
                f"Tab {tab_key}: flag {flag_def.flag} default "
                f"{flag_def.default!r} != CLI {tab_defaults[flag_def.flag]!r}"
            )
