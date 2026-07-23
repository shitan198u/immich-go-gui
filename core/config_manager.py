"""TOML configuration loading, saving, and secret management logic.

This module handles user-level TOML configuration files and secret providers (OS keyring
and plaintext secrets.toml) without PySide6 or Qt dependencies.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import keyring
import tomli_w

from .models import AppConfig


def _get_keyring():
    return keyring


@dataclass
class SecretSaveResult:
    ok: bool
    provider_used: str
    message: str = ""


class SecretStore:
    """Manages profile-scoped API keys via OS-native keyring with safe migration."""

    SERVICE_NAME = "immich-go-gui"

    @staticmethod
    def _make_keyring_user(profile_name: str, key: str) -> str:
        return f"{profile_name}:{key}"

    @staticmethod
    def set_secret(profile_name: str, key: str, value: str) -> bool:
        user = SecretStore._make_keyring_user(profile_name, key)
        try:
            _get_keyring().set_password(SecretStore.SERVICE_NAME, user, value)
            return True
        except Exception:
            return False

    @staticmethod
    def get_secret(profile_name: str, key: str) -> str:
        user = SecretStore._make_keyring_user(profile_name, key)
        try:
            val = _get_keyring().get_password(SecretStore.SERVICE_NAME, user)
            if val:
                return val
        except Exception:
            pass

        # Legacy compatibility for default profile api_key
        if profile_name == "default" and key == "api_key":
            try:
                legacy_val = _get_keyring().get_password(SecretStore.SERVICE_NAME, "immich_api_key")
                if legacy_val:
                    # Non-destructive migration
                    if SecretStore.set_secret("default", "api_key", legacy_val):
                        # Verify read back before deleting old key
                        verified = _get_keyring().get_password(SecretStore.SERVICE_NAME, user)
                        if verified == legacy_val:
                            try:
                                _get_keyring().delete_password(SecretStore.SERVICE_NAME, "immich_api_key")
                            except Exception:
                                pass
                    return legacy_val
            except Exception:
                pass

        return ""

    @staticmethod
    def clear_secret(profile_name: str, key: str) -> None:
        user = SecretStore._make_keyring_user(profile_name, key)
        try:
            _get_keyring().delete_password(SecretStore.SERVICE_NAME, user)
        except Exception:
            pass

    @staticmethod
    def copy_secrets(src_profile: str, dst_profile: str) -> bool:
        ok = True
        for k in ("api_key", "admin_api_key"):
            val = SecretStore.get_secret(src_profile, k)
            if not val:
                continue
            if not SecretStore.set_secret(dst_profile, k, val):
                ok = False
                continue
            if SecretStore.get_secret(dst_profile, k) != val:
                ok = False
        return ok

    @staticmethod
    def migrate_from_qsettings(settings) -> None:
        """One-time migration helper for QSettings objects."""
        try:
            old_key = settings.value("api_key", "")
            if old_key:
                if SecretStore.set_secret("default", "api_key", old_key):
                    read_back = SecretStore.get_secret("default", "api_key")
                    if read_back == old_key:
                        settings.remove("api_key")
                        settings.sync()
        except Exception:
            pass

    # Legacy static helpers for backwards compatibility
    @staticmethod
    def set_api_key(api_key: str) -> None:
        SecretStore.set_secret("default", "api_key", api_key)

    @staticmethod
    def get_api_key() -> str:
        return SecretStore.get_secret("default", "api_key")

    @staticmethod
    def clear_api_key() -> None:
        SecretStore.clear_secret("default", "api_key")


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


def default_config_path(profile_name: str | None = None) -> Path:
    """Returns the path to the config TOML file for the given or active profile."""
    env_override = os.environ.get("IMMICH_GO_GUI_CONFIG", "").strip()
    if env_override:
        return Path(env_override)

    from .profile_manager import active_profile_name, profile_config_path
    target_profile = profile_name or active_profile_name()
    return profile_config_path(target_profile)


def default_secrets_path(profile_name: str | None = None) -> Path:
    """Returns the path to secrets.toml file for the given or active profile."""
    from .profile_manager import active_profile_name, profile_secrets_path
    target_profile = profile_name or active_profile_name()
    return profile_secrets_path(target_profile)


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


def load_config(path: Path | None = None, profile_name: str | None = None) -> AppConfig:
    """Loads configuration from user-level TOML file."""
    if path is None:
        path = default_config_path(profile_name)

    cfg = AppConfig()
    from .profile_manager import active_profile_name
    cfg.profile_name = profile_name or active_profile_name()

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
    cfg.preferred_terminal = gen.get("preferred_terminal", "auto")

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


def save_config(config: AppConfig, path: Path | None = None, profile_name: str | None = None) -> None:
    """Saves AppConfig to user-level TOML file."""
    target_prof = profile_name or config.profile_name
    if path is None:
        path = default_config_path(target_prof)

    on_errors_val = "custom" if config.on_errors in ("custom", "custom…") else config.on_errors

    data = {
        "schema_version": 2,
        "general": {
            "theme": config.theme_mode,
            "advanced_mode": config.advanced_mode,
            "allow_untested_updates": config.allow_untested_updates,
            "preferred_terminal": config.preferred_terminal,
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


def get_secret_with_fallback(
    profile_name: str = "default",
    key: str = "api_key",
    provider: str = "keyring",
    secrets_path: Path | None = None,
) -> str:
    """Resolves secret using environment overrides and provider settings."""
    env_var = "IMMICH_GO_GUI_API_KEY" if key == "api_key" else "IMMICH_GO_GUI_ADMIN_API_KEY"
    env_val = os.environ.get(env_var, "").strip()
    if env_val:
        return env_val

    if provider == "config":
        secrets = load_secrets(secrets_path)
        val = str(secrets.get(key, "")).strip()
        if val:
            return val
        return SecretStore.get_secret(profile_name, key)
    else: # keyring provider
        val = SecretStore.get_secret(profile_name, key)
        if val:
            return val
        secrets = load_secrets(secrets_path)
        return str(secrets.get(key, "")).strip()


def save_secret_with_fallback(
    profile_name: str = "default",
    key: str = "api_key",
    value: str = "",
    provider: str = "keyring",
    secrets_path: Path | None = None,
) -> SecretSaveResult:
    """Saves secret according to provider preference with keyring write failure fallback."""
    value = value.strip()

    if provider == "keyring":
        if SecretStore.set_secret(profile_name, key, value):
            # Verify read back
            read_back = SecretStore.get_secret(profile_name, key)
            if read_back == value:
                # Clear local file secret if present
                secrets = load_secrets(secrets_path)
                if key in secrets:
                    secrets.pop(key, None)
                    save_secrets(secrets, secrets_path)
                return SecretSaveResult(ok=True, provider_used="keyring")

        # Keyring write failed or failed verification -> Fallback to file
        secrets = load_secrets(secrets_path)
        secrets[key] = value
        save_secrets(secrets, secrets_path)
        return SecretSaveResult(
            ok=True,
            provider_used="config",
            message="OS keyring is unavailable. Secret was saved to local secrets file instead.",
        )
    else: # provider == "config"
        secrets = load_secrets(secrets_path)
        secrets[key] = value
        save_secrets(secrets, secrets_path)
        SecretStore.clear_secret(profile_name, key)
        return SecretSaveResult(ok=True, provider_used="config")


def get_api_key(config: AppConfig | None = None) -> str:
    """Resolves API key according to secret policy (backwards-compatible wrapper)."""
    provider = config.secrets_provider if config else "keyring"
    return get_secret_with_fallback(profile_name="default", key="api_key", provider=provider)


def clear_api_key(config: AppConfig | None = None) -> None:
    """Clears API key (backwards-compatible wrapper)."""
    SecretStore.clear_secret("default", "api_key")
    secrets = load_secrets()
    if "api_key" in secrets:
        secrets.pop("api_key", None)
        save_secrets(secrets)


def set_api_key(value: str, config: AppConfig) -> SecretSaveResult:
    """Saves API key using configured secret provider (backwards-compatible wrapper)."""
    return save_secret_with_fallback(
        profile_name="default",
        key="api_key",
        value=value,
        provider=config.secrets_provider,
    )
