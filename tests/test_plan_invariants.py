"""CLI invariant guardrails: behavior that must *always* remain true regardless
of implementation changes an AI agent might make.

These verify structural properties of every ``CommandPlan`` produced by
``build_plan_from_state``: correct command prefix, single dry-run emission,
from-dry-run scoping, and absolute path positionals.
"""

import os

import pytest

from core.cli_schema import TAB_COMMANDS
from core.command_builder import build_plan_from_state, collect_paths
from core.flag_registry import REGISTRY

IMMICH_SOURCE_TABS = ("upload-immich", "archive-immich")


def _config_state():
    """Build the standard configuration state used by plan invariant tests.

    Returns:
        dict: Configuration values for the server, API keys, SSL handling, and client timeout.
    """
    return {
        "server": "http://localhost:2283",
        "api_key": "k",
        "admin_api_key": "a",
        "skip-ssl": False,
        "client_timeout_minutes": 60,
    }


def _tab_state(tab_key, tmp_path):
    """Build representative tab-specific state for plan invariant tests.

    Parameters:
        tab_key (str): The tab identifier used to determine which state fields to include.
        tmp_path (path-like): Temporary directory used to construct source and output paths.

    Returns:
        dict: State containing applicable source paths, output paths, and Immich source credentials.
    """
    state: dict = {}
    if tab_key != "stack" and tab_key != "archive-immich":
        state["path"] = str(tmp_path / "src")
    if tab_key in (
        "archive-folder",
        "archive-gp",
        "archive-icloud",
        "archive-picasa",
        "archive-immich",
    ):
        state["write-to"] = str(tmp_path / "out")
    if tab_key in IMMICH_SOURCE_TABS:
        state["from-server"] = "http://src:2283"
        state["from-api-key"] = "fk"
    return state


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.tabs))
def test_plan_starts_with_tab_command(tab_key, tmp_path):
    """Every plan must begin with the registered subcommand prefix."""
    plan = build_plan_from_state(
        tab_key=tab_key,
        config_state=_config_state(),
        tab_state=_tab_state(tab_key, tmp_path),
        binary_path="./immich-go",
        base_env={},
    )
    assert not plan.errors, plan.errors
    expected = TAB_COMMANDS[tab_key]
    assert plan.argv[: len(expected)] == expected, (
        f"{tab_key}: expected prefix {expected}, got {plan.argv}"
    )


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.tabs))
def test_plan_argv_excludes_binary_path(tab_key, tmp_path):
    """argv must contain only the subcommand + flags + positionals.

    The binary path is prepended only in display_argv, never in the argv that
    is passed to the terminal launcher (which receives the binary separately).
    """
    plan = build_plan_from_state(
        tab_key=tab_key,
        config_state=_config_state(),
        tab_state=_tab_state(tab_key, tmp_path),
        binary_path="./immich-go",
        base_env={},
    )
    assert plan.argv[0] != "./immich-go", (
        f"{tab_key}: binary path leaked into argv: {plan.argv}"
    )


def test_dry_run_emitted_once_when_enabled(tmp_path):
    plan = build_plan_from_state(
        tab_key="upload-folder",
        config_state=_config_state(),
        tab_state={"path": str(tmp_path / "src")},
        binary_path="./immich-go",
        dry_run=True,
        base_env={},
    )
    dry = [a for a in plan.argv if a == "--dry-run" or a.startswith("--dry-run=")]
    assert len(dry) == 1, f"Expected one --dry-run, got {dry}"


def test_dry_run_not_emitted_when_disabled(tmp_path):
    plan = build_plan_from_state(
        tab_key="upload-folder",
        config_state=_config_state(),
        tab_state={"path": str(tmp_path / "src")},
        binary_path="./immich-go",
        dry_run=False,
        base_env={},
    )
    assert not any(a == "--dry-run" or a.startswith("--dry-run=") for a in plan.argv)


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.tabs))
def test_from_dry_run_scoped_to_immich_source_tabs(tab_key, tmp_path):
    """--from-dry-run may only appear for upload-immich/archive-immich."""
    plan = build_plan_from_state(
        tab_key=tab_key,
        config_state=_config_state(),
        tab_state=_tab_state(tab_key, tmp_path),
        binary_path="./immich-go",
        dry_run=True,
        base_env={},
    )
    has = any(a == "--from-dry-run" for a in plan.argv)
    if tab_key in IMMICH_SOURCE_TABS:
        assert has, f"{tab_key} should emit --from-dry-run with dry_run"
    else:
        assert not has, f"{tab_key} must not emit --from-dry-run: {plan.argv}"


def test_unknown_tab_produces_error():
    plan = build_plan_from_state(
        tab_key="does-not-exist",
        config_state={},
        tab_state={},
        binary_path="./immich-go",
        base_env={},
    )
    assert plan.errors, "Unknown tab should produce a plan error"


def test_collect_paths_returns_absolute_paths():
    """Path positionals must always be absolute (glob-expanded + abspath)."""
    result = collect_paths("nonexistent_alpha\nnonexistent_beta")
    assert len(result) == 2
    assert all(os.path.isabs(p) for p in result)


def test_collect_paths_expands_tilde_to_absolute():
    result = collect_paths("~/nonexistent_home_path")
    assert len(result) == 1
    assert os.path.isabs(result[0])
    assert "~" not in result[0]
