"""Schema guardrails for core/flags.toml — the single source of truth.

Validates that the parsed ``REGISTRY`` satisfies structural invariants so a
malformed ``flags.toml`` is caught immediately rather than silently producing
wrong command plans. These tests protect the SSOT from AI-agent edits that
introduce invalid kinds, duplicate keys, or broken secret routing.
"""

import pytest

from core.flag_registry import REGISTRY

VALID_KINDS = {
    "bool",
    "text",
    "enum",
    "int",
    "duration_minutes",
    "extensions",
    "csv_repeat",
    "lines_repeat",
    "date_range",
    "path",
    "paths",
}
VALID_SECTIONS = {"upload", "archive", "stack"}


def test_registry_has_eleven_tabs():
    """The GUI defines exactly 11 workflow tabs."""
    assert len(REGISTRY.tabs) == 11


def test_all_tabs_have_known_sections():
    for key, tab in REGISTRY.tabs.items():
        assert tab.section in VALID_SECTIONS, (
            f"Tab {key} has unknown section {tab.section!r}"
        )


def test_all_tabs_have_nonempty_command():
    for key, tab in REGISTRY.tabs.items():
        assert tab.command, f"Tab {key} has empty command"


def test_server_required_and_serverless_are_mutually_exclusive():
    """Ensure no registry tab is marked as both server-required and serverless."""
    for key, tab in REGISTRY.tabs.items():
        assert not (tab.server_required and tab.serverless), (
            f"Tab {key} is both server_required and serverless"
        )


def test_all_flag_kinds_are_valid():
    for tab_key, defs in REGISTRY.flags.items():
        for d in defs:
            assert d.kind in VALID_KINDS, (
                f"Tab {tab_key} flag {d.key} has invalid kind {d.kind!r}"
            )


def test_enum_flags_have_options():
    for tab_key, defs in REGISTRY.flags.items():
        for d in defs:
            if d.kind == "enum":
                assert d.options, f"Tab {tab_key} enum flag {d.key} has no options"


def test_no_duplicate_flag_keys_within_tab():
    for tab_key, defs in REGISTRY.flags.items():
        keys = [d.key for d in defs]
        dupes = {k for k in keys if keys.count(k) > 1}
        assert not dupes, f"Tab {tab_key} has duplicate flag keys: {dupes}"


def test_no_duplicate_cli_flag_names_within_tab():
    for tab_key, defs in REGISTRY.flags.items():
        names = [d.flag for d in defs if d.flag]
        dupes = {n for n in names if names.count(n) > 1}
        assert not dupes, f"Tab {tab_key} has duplicate CLI flag names: {dupes}"


def test_secret_env_flags_use_immich_go_prefix():
    for tab_key, defs in REGISTRY.flags.items():
        for d in defs:
            if d.secret_env:
                assert d.secret_env.startswith("IMMICH_GO_"), (
                    f"Tab {tab_key} flag {d.key} secret_env "
                    f"{d.secret_env!r} lacks IMMICH_GO_ prefix"
                )


def test_flags_reference_existing_tabs():
    tab_keys = set(REGISTRY.tabs)
    for flag_tab in REGISTRY.flags:
        assert flag_tab in tab_keys, f"flags reference unknown tab {flag_tab!r}"


def test_secrets_reference_existing_tabs():
    tab_keys = set(REGISTRY.tabs)
    for sec_tab in REGISTRY.secrets:
        assert sec_tab in tab_keys, f"secrets reference unknown tab {sec_tab!r}"


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.server_required_tabs))
def test_server_required_tab_has_secret_mapping(tab_key):
    """Every server-required tab must route at least one secret via env."""
    mapping = REGISTRY.env_key_map.get(tab_key, {})
    assert mapping, f"Server-required tab {tab_key} has no secret mapping"
    assert mapping.get("api_key") or mapping.get("from_api_key"), (
        f"Server-required tab {tab_key} has no api_key/from_api_key route"
    )
