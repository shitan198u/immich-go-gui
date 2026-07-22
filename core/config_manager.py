"""TOML configuration loading, saving, and secret management logic.

This module handles user-level TOML configuration files and secret providers (OS keyring
and plaintext secrets.toml) without PySide6 or Qt dependencies.
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import keyring
import tomli_w

from .models import AppConfig


def _get_keyring():
    app_mod = sys.modules.get("app")
    if app_mod and hasattr(app_mod, "keyring"):
        return app_mod.keyring
    return keyring


class SecretStore:
    """Manages API keys via OS-native keyring."""

    SERVICE_NAME = "immich-go-gui"

    @staticmethod
    def set_api_key(api_key: str) -> None:
        try:
            _get_keyring().set_password(SecretStore.SERVICE_NAME, "immich_api_key", api_key)
        except Exception:
            pass

    @staticmethod
    def get_api_key() -> str:
        try:
            return _get_keyring().get_password(SecretStore.SERVICE_NAME, "immich_api_key") or ""
        except Exception:
            return ""

    @staticmethod
    def clear_api_key() -> None:
        try:
            _get_keyring().delete_password(SecretStore.SERVICE_NAME, "immich_api_key")
        except Exception:
            pass

    @staticmethod
    def migrate_from_qsettings(settings) -> None:
        """One-time migration helper for settings objects."""
        try:
            old_key = settings.value("api_key", "")
            if old_key:
                SecretStore.set_api_key(old_key)
                settings.remove("api_key")
                settings.sync()
        except Exception:
            pass


def default_config_dir() -> Path:
    """Returns the user-level configuration directory."""
    env_override = os.environ.get("IMMICH_GO_GUI_CONFIG", "").strip()
    if env_override:
        return Path(env_override).parent

    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(base) / "immich-go-gui"
    elif sys.platform.startswith("darwin"):
        return Path.home() / "Library" / "Application Support" / "immich-go-gui"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg) / "immich-go-gui"
        return Path.home() / ".config" / "immich-go-gui"


def default_config_path() -> Path:
    """Returns the path to the primary config TOML file."""
    env_override = os.environ.get("IMMICH_GO_GUI_CONFIG", "").strip()
    if env_override:
        return Path(env_override)
    return default_config_dir() / "config.toml"


def default_secrets_path() -> Path:
    """Returns the path to secrets.toml file."""
    return default_config_path().parent / "secrets.toml"


def _atomic_write_text(path: Path, text: str, mode: int | None = None) -> None:
    """Atomically writes text to path and optionally sets POSIX permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")

    if mode is not None and os.name == "posix":
        try:
            os.chmod(tmp, mode)
        except OSError:
            pass

    os.replace(tmp, path)


def load_config(path: Path | None = None) -> AppConfig:
    """Loads configuration from user-level TOML file."""
    if path is None:
        path = default_config_path()

    cfg = AppConfig()
    if not path.exists():
        return cfg

    try:
        content = path.read_text(encoding="utf-8")
        data = tomllib.loads(content)
    except Exception:
        return cfg

    cfg.schema_version = data.get("schema_version", 2)

    gen = data.get("general", {})
    cfg.theme_mode = gen.get("theme", "system")
    cfg.advanced_mode = gen.get("advanced_mode", False)
    cfg.allow_untested_updates = gen.get("allow_untested_updates", False)

    srv = data.get("server", {})
    cfg.server_url = srv.get("url", "")
    cfg.skip_ssl = srv.get("skip_ssl", False)

    sec = data.get("secrets", {})
    cfg.secrets_provider = sec.get("provider", "keyring")

    adv = data.get("advanced", {})
    cfg.client_timeout_minutes = adv.get("client_timeout_minutes", 20)
    cfg.concurrent_tasks = adv.get("concurrent_tasks", 0)
    cfg.device_uuid = adv.get("device_uuid", "")

    oe = adv.get("on_errors", "stop")
    cfg.on_errors = "custom" if oe in ("custom", "custom…") else oe
    cfg.on_errors_tolerance = adv.get("on_errors_tolerance", 10)
    cfg.pause_immich_jobs = adv.get("pause_immich_jobs", True)

    cfg.form_state = data.get("form_state", {})

    return cfg


def save_config(config: AppConfig, path: Path | None = None) -> None:
    """Saves AppConfig to user-level TOML file."""
    if path is None:
        path = default_config_path()

    on_errors_val = "custom" if config.on_errors in ("custom", "custom…") else config.on_errors

    data = {
        "schema_version": 2,
        "general": {
            "theme": config.theme_mode,
            "advanced_mode": config.advanced_mode,
            "allow_untested_updates": config.allow_untested_updates,
        },
        "server": {
            "url": config.server_url,
            "skip_ssl": config.skip_ssl,
        },
        "secrets": {
            "provider": config.secrets_provider,
        },
        "advanced": {
            "client_timeout_minutes": config.client_timeout_minutes,
            "concurrent_tasks": config.concurrent_tasks,
            "device_uuid": config.device_uuid,
            "on_errors": on_errors_val,
            "on_errors_tolerance": config.on_errors_tolerance,
            "pause_immich_jobs": config.pause_immich_jobs,
        },
        "form_state": config.form_state or {},
    }

    text = tomli_w.dumps(data)
    _atomic_write_text(path, text, mode=0o644)


def load_secrets(path: Path | None = None) -> dict:
    """Loads plaintext secrets from secrets.toml."""
    if path is None:
        path = default_secrets_path()

    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
        return tomllib.loads(content)
    except Exception:
        return {}


def save_secrets(secrets: dict, path: Path | None = None) -> None:
    """Saves plaintext secrets to secrets.toml with 0600 permissions."""
    if path is None:
        path = default_secrets_path()

    text = tomli_w.dumps(secrets)
    _atomic_write_text(path, text, mode=0o600)


def get_api_key(config: AppConfig | None = None) -> str:
    """Resolves API key according to secret policy."""
    env_val = os.environ.get("IMMICH_GO_GUI_API_KEY", "").strip()
    if env_val:
        return env_val

    if config and config.secrets_provider == "config":
        secrets = load_secrets()
        val = str(secrets.get("api_key", "")).strip()
        if val:
            return val

    return SecretStore.get_api_key()


def set_api_key(value: str, config: AppConfig) -> None:
    """Saves API key using the configured secret provider."""
    value = value.strip()

    if config.secrets_provider == "config":
        secrets = load_secrets()
        secrets["api_key"] = value
        save_secrets(secrets)
        SecretStore.clear_api_key()
    else:
        SecretStore.set_api_key(value)
        secrets = load_secrets()
        if "api_key" in secrets:
            secrets.pop("api_key", None)
            save_secrets(secrets)


def clear_api_key(config: AppConfig | None = None) -> None:
    """Cleans up API key from all secret stores."""
    SecretStore.clear_api_key()
    secrets = load_secrets()
    if "api_key" in secrets:
        secrets.pop("api_key", None)
        save_secrets(secrets)
