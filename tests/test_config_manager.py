"""Unit tests for configuration loading and quarantine behavior."""

import tomllib

from core.config_manager import get_config_load_warning, load_config, save_config
from core.models import AppConfig


def test_corrupt_config_quarantined_and_defaults_loaded(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("not valid {{{{ toml", encoding="utf-8")

    cfg = load_config()
    warning = get_config_load_warning()

    assert cfg.server_url == ""
    assert cfg.theme_mode == "system"
    assert warning is not None
    assert "could not be parsed" in warning.lower()

    corrupt_files = list(tmp_path.glob("config.toml.corrupt-*"))
    assert len(corrupt_files) == 1
    assert not cfg_path.exists()


def test_schema_v2_migrates_client_timeout_from_form_state(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        """
schema_version = 2

[general]
theme = "system"

[server]
url = "http://localhost:2283"

[secrets]
provider = "keyring"

[form_state.advanced."upload-folder"]
[form_state.advanced."upload-folder"."client-timeout"]
enabled = true
value = 45
""".strip(),
        encoding="utf-8",
    )

    cfg = load_config()
    assert cfg.schema_version == 3
    assert cfg.client_timeout_minutes == 45

    data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 3
    assert data["server"]["client_timeout_minutes"] == 45
    assert "form_state" not in data


def test_save_config_schema_v3_without_form_state(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    cfg = AppConfig()
    cfg.client_timeout_minutes = 90
    save_config(cfg)

    data = tomllib.loads((tmp_path / "config.toml").read_text(encoding="utf-8"))
    assert data["schema_version"] == 3
    assert data["server"]["client_timeout_minutes"] == 90
    assert "form_state" not in data


def test_default_config_dir_respects_xdg_cross_platform(tmp_path, monkeypatch):
    """Verify default_config_dir prefers XDG_CONFIG_HOME over platform defaults."""
    from core.config_manager import default_config_dir

    monkeypatch.delenv("IMMICH_GO_GUI_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "custom_xdg"))
    assert default_config_dir() == tmp_path / "custom_xdg" / "immich-go-gui"


def test_keyring_isolation_in_pytest():
    """Verify SecretStore operations in test suite use in-memory mock keyring."""
    from core.config_manager import SecretStore

    assert SecretStore.set_secret("test_prof", "api_key", "mock_key_value") is True
    assert SecretStore.get_secret("test_prof", "api_key") == "mock_key_value"
    SecretStore.clear_secret("test_prof", "api_key")
    assert SecretStore.get_secret("test_prof", "api_key") == ""
