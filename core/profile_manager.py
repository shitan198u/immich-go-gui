"""Profile management logic for Immich-Go GUI.

Pure Python module, Qt-free.
"""

import logging
import os
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import tomli_w

from .config_manager import SecretStore, _atomic_write_text, default_config_dir

_log = logging.getLogger(__name__)


@dataclass
class ProfileInfo:
    name: str
    active: bool = False
    created_at: str = ""
    config_path: str = ""


_PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$")


def profiles_root() -> Path:
    """Returns the base directory for profile storage."""
    return default_config_dir() / "profiles"


def global_profiles_path() -> Path:
    """Returns the path to the global profiles.toml index file."""
    return default_config_dir() / "profiles.toml"


def profile_dir(name: str) -> Path:
    """Returns the directory path for a specific profile."""
    safe_name = sanitize_profile_name(name)
    return profiles_root() / safe_name


def profile_config_path(name: str) -> Path:
    """Returns the config.toml path for a specific profile."""
    return profile_dir(name) / "config.toml"


def profile_secrets_path(name: str) -> Path:
    """Returns the secrets.toml path for a specific profile."""
    return profile_dir(name) / "secrets.toml"


def sanitize_profile_name(name: str) -> str:
    """Strip whitespace from profile name."""
    return name.strip()


def validate_profile_name(
    name: str, existing_names: list[str] | None = None
) -> tuple[bool, str | None]:
    """Validate profile name format and uniqueness.

    Returns (is_valid, error_message).
    """
    clean_name = sanitize_profile_name(name)
    if not clean_name:
        return False, "Profile name cannot be empty."

    if clean_name in (".", "..") or "/" in clean_name or "\\" in clean_name:
        return False, "Profile name contains invalid characters or path specifiers."

    if not _PROFILE_NAME_RE.match(clean_name):
        return False, (
            "Profile name must start with an alphanumeric character and contain "
            "only letters, numbers, spaces, hyphens, or underscores (max 64 chars)."
        )

    if existing_names:
        norm_existing = [n.strip().lower() for n in existing_names]
        if clean_name.lower() in norm_existing:
            return False, f"A profile named '{clean_name}' already exists."

    return True, None


_profiles_cache: dict | None = None
_profiles_cache_path: Path | None = None


def _load_profiles_index() -> dict:
    global _profiles_cache, _profiles_cache_path
    idx_path = global_profiles_path()
    if _profiles_cache is not None and _profiles_cache_path == idx_path:
        return _profiles_cache
    if not idx_path.exists():
        _profiles_cache = {}
        _profiles_cache_path = idx_path
        return _profiles_cache
    try:
        content = idx_path.read_text(encoding="utf-8")
        _profiles_cache = tomllib.loads(content)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(
            "Failed to parse profiles index %s: %s",
            idx_path,
            exc,
        )
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        try:
            corrupt_path = idx_path.with_suffix(idx_path.suffix + f".corrupt-{stamp}")
            idx_path.rename(corrupt_path)
        except OSError:
            pass
        _profiles_cache = {}
    _profiles_cache_path = idx_path
    return _profiles_cache


def _save_profiles_index(data: dict) -> None:
    global _profiles_cache, _profiles_cache_path
    text = tomli_w.dumps(data)
    idx_path = global_profiles_path()
    _atomic_write_text(idx_path, text, mode=0o644)
    _profiles_cache = data
    _profiles_cache_path = idx_path


def clear_profiles_cache() -> None:
    """Test helper / forced reload."""
    global _profiles_cache, _profiles_cache_path
    _profiles_cache = None
    _profiles_cache_path = None


def migrate_single_config_to_default() -> None:
    """One-time migration helper converting legacy single-config to default profile."""
    env_override = os.environ.get("IMMICH_GO_GUI_CONFIG", "").strip()
    if env_override:
        return

    base_dir = default_config_dir()
    old_config = base_dir / "config.toml"
    old_secrets = base_dir / "secrets.toml"
    default_p_dir = profiles_root() / "default"
    default_cfg = default_p_dir / "config.toml"
    default_sec = default_p_dir / "secrets.toml"

    # Migrate when legacy root files exist but the default profile copy is missing.
    # profiles/ may already exist from ensure_default_profile() without a prior copy.
    if not old_config.exists() and not old_secrets.exists():
        return
    if default_cfg.exists() and (not old_secrets.exists() or default_sec.exists()):
        return

    default_p_dir.mkdir(parents=True, exist_ok=True)

    if old_config.exists() and not default_cfg.exists():
        try:
            shutil.copy2(old_config, default_cfg)
            if not default_cfg.exists():
                _log.error(
                    "Profile migration failed: copy of %s did not create %s",
                    old_config,
                    default_cfg,
                )
                return
            if default_cfg.read_text(encoding="utf-8") != old_config.read_text(
                encoding="utf-8"
            ):
                _log.error(
                    "Profile migration failed: copied config at %s does not match source",
                    default_cfg,
                )
                default_cfg.unlink(missing_ok=True)
                return
            bak = base_dir / "config.toml.pre-profile.bak"
            old_config.rename(bak)
            _log.info(
                "Migrated legacy config %s -> %s",
                old_config,
                default_cfg,
            )
        except Exception as exc:
            _log.error(
                "Profile migration failed copying %s to %s: %s",
                old_config,
                default_cfg,
                exc,
            )
            return

    if old_secrets.exists() and not default_sec.exists():
        try:
            shutil.copy2(old_secrets, default_sec)
            if not default_sec.exists():
                _log.error(
                    "Profile migration failed: copy of %s did not create %s",
                    old_secrets,
                    default_sec,
                )
                return
            sbak = base_dir / "secrets.toml.pre-profile.bak"
            old_secrets.rename(sbak)
            _log.info(
                "Migrated legacy secrets %s -> %s",
                old_secrets,
                default_sec,
            )
        except Exception as exc:
            _log.error(
                "Profile migration failed copying %s to %s: %s",
                old_secrets,
                default_sec,
                exc,
            )

    if default_cfg.exists() or default_sec.exists():
        now_iso = datetime.now(UTC).isoformat()
        idx_data = _load_profiles_index()
        p_list = idx_data.get("profiles", [])
        if not any(p.get("name") == "default" for p in p_list if isinstance(p, dict)):
            p_list.append({"name": "default", "created_at": now_iso})
            idx_data["profiles"] = p_list
        if not idx_data.get("active_profile"):
            idx_data["active_profile"] = "default"
        if "schema_version" not in idx_data:
            idx_data["schema_version"] = 1
        _save_profiles_index(idx_data)


def ensure_default_profile() -> None:
    """Ensures at least the default profile directory and profiles.toml index exist."""
    migrate_single_config_to_default()

    idx_data = _load_profiles_index()
    p_list = idx_data.get("profiles", [])

    has_default = any(p.get("name") == "default" for p in p_list if isinstance(p, dict))
    if not has_default:
        now_iso = datetime.now(UTC).isoformat()
        p_list.append({"name": "default", "created_at": now_iso})
        idx_data["profiles"] = p_list

    if not idx_data.get("active_profile"):
        idx_data["active_profile"] = "default"
    if "schema_version" not in idx_data:
        idx_data["schema_version"] = 1

    _save_profiles_index(idx_data)

    def_dir = profile_dir("default")
    def_dir.mkdir(parents=True, exist_ok=True)


def active_profile_name() -> str:
    """Returns the currently active profile name."""
    ensure_default_profile()
    idx_data = _load_profiles_index()
    return idx_data.get("active_profile", "default")


def set_active_profile_name(name: str) -> None:
    """Sets the active profile name in profiles.toml."""
    ensure_default_profile()
    clean_name = sanitize_profile_name(name)
    idx_data = _load_profiles_index()
    p_list = idx_data.get("profiles", [])

    if not any(p.get("name") == clean_name for p in p_list if isinstance(p, dict)):
        raise ValueError(f"Profile '{clean_name}' does not exist.")

    idx_data["active_profile"] = clean_name
    _save_profiles_index(idx_data)


def list_profiles() -> list[ProfileInfo]:
    """Lists all available profiles."""
    ensure_default_profile()
    idx_data = _load_profiles_index()
    active_name = idx_data.get("active_profile", "default")
    p_list = idx_data.get("profiles", [])

    results = []
    for item in p_list:
        if isinstance(item, dict):
            pname = item.get("name", "")
            if pname:
                results.append(
                    ProfileInfo(
                        name=pname,
                        active=(pname == active_name),
                        created_at=item.get("created_at", ""),
                        config_path=str(profile_config_path(pname)),
                    )
                )

    return results


def create_profile(name: str, copy_from: str | None = None) -> ProfileInfo:
    """Creates a new profile, optionally copying configuration and secrets from copy_from."""
    ensure_default_profile()
    clean_name = sanitize_profile_name(name)

    existing = [p.name for p in list_profiles()]
    valid, err = validate_profile_name(clean_name, existing)
    if not valid:
        raise ValueError(err or "Invalid profile name.")

    p_dir = profile_dir(clean_name)
    p_dir.mkdir(parents=True, exist_ok=True)

    if copy_from:
        src_dir = profile_dir(copy_from)
        if src_dir.exists():
            src_cfg = profile_config_path(copy_from)
            if src_cfg.exists():
                shutil.copy2(src_cfg, profile_config_path(clean_name))
            src_sec = profile_secrets_path(copy_from)
            if src_sec.exists():
                shutil.copy2(src_sec, profile_secrets_path(clean_name))
            SecretStore.copy_secrets(copy_from, clean_name)

    now_iso = datetime.now(UTC).isoformat()
    idx_data = _load_profiles_index()
    p_list = idx_data.get("profiles", [])
    p_list.append({"name": clean_name, "created_at": now_iso})
    idx_data["profiles"] = p_list
    _save_profiles_index(idx_data)

    return ProfileInfo(
        name=clean_name,
        active=False,
        created_at=now_iso,
        config_path=str(profile_config_path(clean_name)),
    )


def duplicate_profile(source_name: str, new_name: str) -> ProfileInfo:
    """Duplicates an existing profile into a new profile."""
    return create_profile(new_name, copy_from=source_name)


def rename_profile(old_name: str, new_name: str) -> None:
    """Renames an existing profile and updates directory & secret keys."""
    ensure_default_profile()
    clean_old = sanitize_profile_name(old_name)
    clean_new = sanitize_profile_name(new_name)

    if clean_old == "default":
        raise ValueError("The 'default' profile cannot be renamed.")

    if clean_old == clean_new:
        return

    existing = [p.name for p in list_profiles()]
    if clean_old not in existing:
        raise ValueError(f"Profile '{clean_old}' does not exist.")

    other_existing = [e for e in existing if e != clean_old]
    valid, err = validate_profile_name(clean_new, other_existing)
    if not valid:
        raise ValueError(err or "Invalid new profile name.")

    old_p_dir = profile_dir(clean_old)
    new_p_dir = profile_dir(clean_new)
    renamed_dir = False
    secrets_copied = False
    index_updated = False

    try:
        if not SecretStore.copy_secrets(clean_old, clean_new):
            raise RuntimeError("Failed to copy secrets to renamed profile.")
        secrets_copied = True

        if old_p_dir.exists():
            if new_p_dir.exists():
                raise RuntimeError(f"Profile directory '{clean_new}' already exists.")
            old_p_dir.rename(new_p_dir)
            renamed_dir = True

        idx_data = _load_profiles_index()
        if idx_data.get("active_profile") == clean_old:
            idx_data["active_profile"] = clean_new

        p_list = idx_data.get("profiles", [])
        for item in p_list:
            if isinstance(item, dict) and item.get("name") == clean_old:
                item["name"] = clean_new

        idx_data["profiles"] = p_list
        _save_profiles_index(idx_data)
        index_updated = True

        SecretStore.clear_secret(clean_old, "api_key")
        SecretStore.clear_secret(clean_old, "admin_api_key")
    except Exception:
        if index_updated:
            try:
                idx_data = _load_profiles_index()
                for item in idx_data.get("profiles", []):
                    if isinstance(item, dict) and item.get("name") == clean_new:
                        item["name"] = clean_old
                if idx_data.get("active_profile") == clean_new:
                    idx_data["active_profile"] = clean_old
                _save_profiles_index(idx_data)
            except Exception:
                pass
        if renamed_dir and new_p_dir.exists() and not old_p_dir.exists():
            try:
                new_p_dir.rename(old_p_dir)
            except OSError:
                pass
        if secrets_copied:
            SecretStore.clear_secret(clean_new, "api_key")
            SecretStore.clear_secret(clean_new, "admin_api_key")
        raise


def delete_profile(name: str) -> None:
    """Deletes a profile directory and its associated secrets."""
    ensure_default_profile()
    clean_name = sanitize_profile_name(name)

    if clean_name == "default":
        raise ValueError("The 'default' profile cannot be deleted.")

    existing = [p.name for p in list_profiles()]
    if clean_name not in existing:
        return

    active = active_profile_name()
    if active == clean_name:
        set_active_profile_name("default")

    p_dir = profile_dir(clean_name)
    if p_dir.exists():
        shutil.rmtree(p_dir, ignore_errors=True)

    SecretStore.clear_secret(clean_name, "api_key")
    SecretStore.clear_secret(clean_name, "admin_api_key")

    idx_data = _load_profiles_index()
    p_list = idx_data.get("profiles", [])
    idx_data["profiles"] = [
        p for p in p_list if isinstance(p, dict) and p.get("name") != clean_name
    ]
    _save_profiles_index(idx_data)
