"""Advanced flag emission guardrails.

Verifies that the schema-driven advanced-flag mechanism behaves correctly for
every flag in every tab:

* disabled advanced rows are never emitted to argv,
* enabled advanced rows (with a non-default value) are emitted to argv,
* secret advanced flags are routed to env vars, never argv,
* hidden flags are never exposed as advanced definitions.
"""

from typing import Any

import pytest

from core.command_builder import build_plan_from_state
from core.flag_registry import REGISTRY, FlagDef

IMMICH_SOURCE_TABS = ("upload-immich", "archive-immich")


def _trigger_value(def_: FlagDef) -> Any:
    """
    Provide a representative non-default value for a flag definition.

    Parameters:
        def_ (FlagDef): Flag definition whose kind determines the value.

    Returns:
        Any: A value suitable for exercising the flag.
    """
    if def_.kind == "bool":
        return True
    if def_.kind == "enum":
        return def_.options[0] if def_.options else "x"
    if def_.kind == "int":
        return 1
    if def_.kind == "duration_minutes":
        return 5
    if def_.kind == "date_range":
        return "2023-01-01,2023-12-31"
    if def_.kind == "extensions":
        return ".jpg"
    if def_.kind in ("csv_repeat", "lines_repeat"):
        return "alpha"
    if def_.kind in ("text", "path", "paths"):
        return "/tmp/x"
    return "x"


def _config_state():
    # admin_api_key present so the pause-jobs safety override is skipped.
    """
    Return the baseline server, authentication, SSL, and timeout configuration used by the tests.
    """
    return {
        "server": "http://localhost:2283",
        "api_key": "k",
        "admin_api_key": "a",
        "skip-ssl": False,
        "client_timeout_minutes": 60,
    }


def _tab_state(tab_key, tmp_path):
    """
    Build tab-specific test state using paths and source server credentials where applicable.

    Parameters:
        tab_key: The registered tab identifier.
        tmp_path: Temporary directory used to construct source and output paths.

    Returns:
        A dictionary containing the state required for the specified tab.
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


def _build(tab_key, advanced_state, tmp_path):
    """Build a plan for a tab using baseline configuration and the provided advanced state.

    Parameters:
        tab_key: The registry key of the tab to build.
        advanced_state: The advanced flag state to apply.
        tmp_path: Temporary directory used for tab-specific paths.

    Returns:
        The generated execution plan.
    """
    return build_plan_from_state(
        tab_key=tab_key,
        config_state=_config_state(),
        tab_state=_tab_state(tab_key, tmp_path),
        binary_path="./immich-go",
        base_env={},
        advanced_state=advanced_state,
    )


def _has_flag(argv, flag_name):
    """Determine whether command-line arguments contain a specified flag.

    Parameters:
        argv (iterable): Command-line arguments to inspect.
        flag_name (str): Flag name without the leading ``--``.

    Returns:
        bool: ``True`` if the flag appears alone or with an assigned value, ``False`` otherwise.
    """
    prefix = f"--{flag_name}"
    return any(a == prefix or a.startswith(f"{prefix}=") for a in argv)


def _emittable_defs(tab_key):
    """
    Select advanced flag definitions that are emitted as command-line arguments.

    Parameters:
        tab_key: The registry tab whose advanced definitions are selected.

    Returns:
        A list of definitions with CLI flags that are neither secret environment variables nor dry-run options.
    """
    return [
        d
        for d in REGISTRY.advanced_defs(tab_key)
        if d.flag and not d.secret_env and "dry-run" not in d.key
    ]


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.tabs))
def test_disabled_advanced_flags_not_emitted(tab_key, tmp_path):
    defs = _emittable_defs(tab_key)
    if not defs:
        pytest.skip(f"No emittable advanced flags for {tab_key}")
    advanced_state = {
        d.key: {"enabled": False, "value": _trigger_value(d)} for d in defs
    }
    plan = _build(tab_key, advanced_state, tmp_path)
    leaked = [d.flag for d in defs if _has_flag(plan.argv, d.flag)]
    assert not leaked, (
        f"{tab_key}: disabled advanced flags leaked into argv: {leaked}\n"
        f"argv={plan.argv}"
    )


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.tabs))
def test_enabled_advanced_flags_are_emitted(tab_key, tmp_path):
    defs = _emittable_defs(tab_key)
    if not defs:
        pytest.skip(f"No emittable advanced flags for {tab_key}")
    missing = []
    for d in defs:
        advanced_state = {d.key: {"enabled": True, "value": _trigger_value(d)}}
        plan = _build(tab_key, advanced_state, tmp_path)
        if not _has_flag(plan.argv, d.flag):
            missing.append(d.flag)
    assert not missing, f"{tab_key}: enabled advanced flags not emitted: {missing}"


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.tabs))
def test_secret_advanced_flags_routed_to_env(tab_key, tmp_path):
    secret_defs = [d for d in REGISTRY.advanced_defs(tab_key) if d.secret_env]
    if not secret_defs:
        pytest.skip(f"No secret advanced flags for {tab_key}")
    token = "secret-value-via-env-only"
    advanced_state = {d.key: {"enabled": True, "value": token} for d in secret_defs}
    plan = _build(tab_key, advanced_state, tmp_path)
    joined = " ".join(plan.argv)
    for d in secret_defs:
        assert token not in joined, (
            f"{tab_key}: secret flag {d.key} leaked to argv: {plan.argv}"
        )
        assert plan.env.get(d.secret_env) == token, (
            f"{tab_key}: secret flag {d.key} not in env[{d.secret_env}]: {plan.env}"
        )


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.tabs))
def test_hidden_flags_not_exposed_as_advanced_defs(tab_key):
    """REGISTRY.advanced_defs must never include hidden flags."""
    for d in REGISTRY.advanced_defs(tab_key):
        assert not d.hidden, f"{tab_key}: hidden flag {d.key} exposed in advanced_defs"
