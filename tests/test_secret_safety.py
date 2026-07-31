"""Security guardrails: secrets must never leak into argv, display previews,
or anywhere a shell/process could expose them.

API keys are delivered exclusively via ``IMMICH_GO_*`` environment variables
(see ``build_environment``). These tests lock that invariant in so an AI agent
cannot regress it by accidentally emitting ``--api-key=<value>``.
"""

import pytest

from core.command_builder import build_plan_from_state
from core.flag_registry import REGISTRY

SECRET_API_KEY = "super-secret-api-key-12345"
SECRET_ADMIN_KEY = "admin-secret-key-67890"
SECRET_FROM_KEY = "from-source-secret-key-abcde"
ALL_SECRETS = (SECRET_API_KEY, SECRET_ADMIN_KEY, SECRET_FROM_KEY)

IMMICH_SOURCE_TABS = ("upload-immich", "archive-immich")


def _config_state():
    """
    Build representative server configuration containing API credentials and client settings.
    
    Returns:
    	dict: Configuration values for the server URL, API keys, SSL verification, and client timeout.
    """
    return {
        "server": "http://localhost:2283",
        "api_key": SECRET_API_KEY,
        "admin_api_key": SECRET_ADMIN_KEY,
        "skip-ssl": False,
        "client_timeout_minutes": 60,
    }


def _tab_state(tab_key, tmp_path):
    """
    Build representative tab state for security-related command plan tests.
    
    Parameters:
    	tab_key: The tab identifier whose state should be constructed.
    	tmp_path: Temporary directory used to create input and output paths.
    
    Returns:
    	dict: Tab state containing applicable paths and Immich source server credentials.
    """
    path = str(tmp_path / "src")
    out = str(tmp_path / "out")
    state: dict = {}
    if tab_key in (
        "archive-folder",
        "archive-gp",
        "archive-icloud",
        "archive-picasa",
        "archive-immich",
    ):
        state["write-to"] = out
    if tab_key != "archive-immich":
        state["path"] = path
    if tab_key in IMMICH_SOURCE_TABS:
        state["from-server"] = "http://source:2283"
        state["from-api-key"] = SECRET_FROM_KEY
        state["from-admin-api-key"] = SECRET_ADMIN_KEY
    return state


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.server_required_tabs))
def test_secrets_never_in_argv(tab_key, tmp_path):
    """No secret value may appear in the executable argv list."""
    plan = build_plan_from_state(
        tab_key=tab_key,
        config_state=_config_state(),
        tab_state=_tab_state(tab_key, tmp_path),
        binary_path="./immich-go",
        base_env={},
    )
    assert not plan.errors, plan.errors
    joined = " ".join(plan.argv)
    for secret in ALL_SECRETS:
        assert secret not in joined, (
            f"Secret leaked into argv for {tab_key}: {secret!r}\nargv={plan.argv}"
        )


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.server_required_tabs))
def test_secrets_never_in_display_argv(tab_key, tmp_path):
    """No secret value may appear in the display/preview argv list."""
    plan = build_plan_from_state(
        tab_key=tab_key,
        config_state=_config_state(),
        tab_state=_tab_state(tab_key, tmp_path),
        binary_path="./immich-go",
        base_env={},
    )
    assert not plan.errors, plan.errors
    joined = " ".join(plan.display_argv)
    for secret in ALL_SECRETS:
        assert secret not in joined, (
            f"Secret leaked into display_argv for {tab_key}: {secret!r}\n"
            f"display_argv={plan.display_argv}"
        )


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.server_required_tabs))
def test_secrets_delivered_via_env(tab_key, tmp_path):
    """Secrets must be present in the env dict (delivered to the process)."""
    plan = build_plan_from_state(
        tab_key=tab_key,
        config_state=_config_state(),
        tab_state=_tab_state(tab_key, tmp_path),
        binary_path="./immich-go",
        base_env={},
    )
    assert not plan.errors, plan.errors
    env_values = set(plan.env.values())
    assert any(s in env_values for s in ALL_SECRETS), (
        f"No secret delivered via env for {tab_key}: {plan.env}"
    )


@pytest.mark.parametrize("tab_key", sorted(REGISTRY.serverless_tabs))
def test_serverless_tabs_never_receive_api_key_env(tab_key, tmp_path):
    """Verify that serverless tabs exclude API keys from the process environment."""
    plan = build_plan_from_state(
        tab_key=tab_key,
        config_state=_config_state(),
        tab_state={"path": str(tmp_path / "src"), "write-to": str(tmp_path / "out")},
        binary_path="./immich-go",
        base_env={},
    )
    assert not plan.errors, plan.errors
    for secret in ALL_SECRETS:
        assert secret not in plan.env.values(), (
            f"Serverless tab {tab_key} received a secret in env: {plan.env}"
        )
