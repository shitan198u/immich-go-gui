"""Pure command-building and state validation logic for Immich-Go.

This module contains pure command generation logic and MUST NOT import PySide6 or Qt.
It operates entirely on plain Python dictionaries and primitive types.
"""

import glob
import os
import re
from typing import Any

from .models import CommandPlan, ValidationResult
from .cli_schema import (
    ENV_KEY_MAP,
    ON_ERRORS_CUSTOM_LABEL,
    ON_ERRORS_CUSTOM_VALUE,
    SECRET_FLAGS,
    SERVER_REQUIRED_TABS,
    TAB_COMMANDS,
    UPLOAD_TABS,
    flag_allowed_for_tab,
)
from .validation import (
    clean_date_range,
    normalize_extensions_csv,
    normalize_list_csv,
    validate_date_range as validate_date_range_func,
    validate_server_url,
    expand_source_paths,
    validate_destination_folder,
)


class FlagEmitter:
    """Helper class that checks per-tab flag allowlists before emitting CLI options."""

    def __init__(self, tab_key: str, strict: bool = False):
        self.tab_key = tab_key
        self.strict = strict
        self.opts: list[str] = []
        self.errors: list[str] = []

    def add_option(self, flag_name: str, value: Any) -> bool:
        clean_name = str(flag_name).lstrip("-")
        if not flag_allowed_for_tab(self.tab_key, clean_name):
            err = f"Flag '--{clean_name}' is not allowed for tab '{self.tab_key}'"
            if self.strict:
                raise ValueError(err)
            self.errors.append(err)
            return False
        val_str = str(value)
        if val_str:
            self.opts.append(f"--{clean_name}={val_str}")
            return True
        return False

    def add_flag(self, flag_name: str, enabled: bool = True) -> bool:
        clean_name = str(flag_name).lstrip("-")
        if not flag_allowed_for_tab(self.tab_key, clean_name):
            err = f"Flag '--{clean_name}' is not allowed for tab '{self.tab_key}'"
            if self.strict:
                raise ValueError(err)
            self.errors.append(err)
            return False
        if enabled:
            self.opts.append(f"--{clean_name}")
            return True
        return False

    def add_bool_val(self, flag_name: str, value: bool) -> bool:
        clean_name = str(flag_name).lstrip("-")
        if not flag_allowed_for_tab(self.tab_key, clean_name):
            err = f"Flag '--{clean_name}' is not allowed for tab '{self.tab_key}'"
            if self.strict:
                raise ValueError(err)
            self.errors.append(err)
            return False
        val_str = "true" if value else "false"
        self.opts.append(f"--{clean_name}={val_str}")
        return True


def emit_bool_flag(emitter: FlagEmitter, flag_name: str, value: bool, default: bool = False) -> None:
    """Emits boolean CLI options respecting CLI default value.
    - Default True: emits --<flag>=false if value is False.
    - Default False: emits --<flag> if value is True.
    """
    if default:
        if not value:
            emitter.add_bool_val(flag_name, False)
    else:
        if value:
            emitter.add_flag(flag_name)


def emit_if_not_default(emitter: FlagEmitter, flag_name: str, value: Any, default: Any = "") -> None:
    """Emits CLI option if value is not equal to default and is non-empty."""
    if value != default and value not in ("", None):
        emitter.add_option(flag_name, value)


_DATE_RANGE_RE = re.compile(
    r"^\d{4}(-\d{2}(-\d{2})?)?"
    r"(,\d{4}(-\d{2}(-\d{2})?)?)?$"
)


def normalize_server_url(url: str) -> str:
    """Normalize a server URL for CLI consumption."""
    url = url.strip()
    if not url:
        return ""

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    return url.rstrip("/")


def collect_paths(raw_text: str) -> list[str]:
    """Expands glob patterns, expands user tildes (~), and converts relative paths to absolute paths."""
    paths = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        expanded_user = os.path.expanduser(line)
        expanded = glob.glob(expanded_user)
        if expanded:
            for p in expanded:
                paths.append(os.path.abspath(p))
        else:
            paths.append(os.path.abspath(expanded_user))
    return paths


def validate_date_range(text: str) -> bool:
    """Validate immich-go date range format."""
    valid, _ = validate_date_range_func(text)
    return valid


def mask_command_for_display(command_parts: list[str]) -> list[str]:
    """Obfuscates secrets in command previews."""
    masked = []
    skip_next = False
    for part in command_parts:
        if skip_next:
            masked.append("********")
            skip_next = False
            continue

        if part in SECRET_FLAGS:
            masked.append(part)
            skip_next = True
            continue

        if "=" in part:
            flag, val = part.split("=", 1)
            if flag in SECRET_FLAGS:
                masked.append(f"{flag}=********")
                continue

        masked.append(part)

    return masked


def build_environment(
    tab_key: str,
    server: str,
    api_key: str,
    from_server: str = "",
    from_api_key: str = "",
    from_admin_api_key: str = "",
    admin_api_key: str = "",
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Builds a secure environment dict to pass secrets without CLI exposure."""
    if base_env is not None:
        env = base_env.copy()
    else:
        env = os.environ.copy()

    mapping = ENV_KEY_MAP.get(tab_key, {})

    srv_key = mapping.get("server")
    if srv_key and server:
        env[srv_key] = server

    from_srv_key = mapping.get("from_server")
    target_srv = from_server or server
    if from_srv_key and target_srv:
        env[from_srv_key] = target_srv

    api_key_name = mapping.get("api_key")
    if api_key_name and api_key:
        env[api_key_name] = api_key

    from_api_key_name = mapping.get("from_api_key")
    target_api_key = from_api_key or api_key
    if from_api_key_name and target_api_key:
        env[from_api_key_name] = target_api_key

    if tab_key == "upload-immich":
        if from_server:
            env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER"] = from_server
        if from_api_key:
            env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY"] = from_api_key
        if from_admin_api_key:
            env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY"] = from_admin_api_key

    if admin_api_key:
        if tab_key in UPLOAD_TABS:
            env["IMMICH_GO_UPLOAD_ADMIN_API_KEY"] = admin_api_key
        elif tab_key == "stack":
            env["IMMICH_GO_STACK_ADMIN_API_KEY"] = admin_api_key
        elif tab_key == "archive-immich":
            env["IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_ADMIN_API_KEY"] = admin_api_key

    return env


def validate_state(
    tab_key: str,
    config_state: dict,
    tab_state: dict,
) -> ValidationResult:
    """Validates full input state for a tab."""
    res = ValidationResult()

    if tab_key in SERVER_REQUIRED_TABS:
        srv = config_state.get("server", "").strip()
        key = config_state.get("api_key", "").strip()
        if not srv:
            if tab_key == "archive-immich":
                res.errors.append("Source server URL is required. Configure it in the Configuration tab.")
            elif tab_key == "stack":
                res.errors.append("Immich server URL is required. Configure it in the Configuration tab.")
            else:
                res.errors.append("Server URL is required. Configure it in the Configuration tab.")
        else:
            ok, err = validate_server_url(srv)
            if not ok and err:
                res.errors.append(err)

        if not key:
            res.errors.append("API Key is required. Configure it in the Configuration tab.")

    if tab_key == "upload-folder":
        p = tab_state.get("path", "").strip()
        if not p:
            res.errors.append("Source folder path is required.")
        else:
            _, path_warns = expand_source_paths(p)
            res.warnings.extend(path_warns)

    elif tab_key == "upload-gp":
        p = tab_state.get("path", "").strip()
        if not p:
            res.errors.append("Google Photos takeout source path is required.")
        else:
            _, path_warns = expand_source_paths(p)
            res.warnings.extend(path_warns)

    elif tab_key == "upload-immich":
        fs = tab_state.get("from-server", "").strip()
        fk = tab_state.get("from-api-key", "").strip()
        if not fs:
            res.errors.append("Source Immich Server URL is required.")
        else:
            ok, err = validate_server_url(fs)
            if not ok and err:
                res.errors.append(f"Source {err}")
        if not fk:
            res.errors.append("Source Immich API Key is required.")

    elif tab_key == "archive-folder":
        p = tab_state.get("path", "").strip()
        w = tab_state.get("write-to", "").strip()
        if not p:
            res.errors.append("Source folder path is required.")
        if not w:
            res.errors.append("Destination folder is required.")
        if p and w:
            expanded_sources, path_warns = expand_source_paths(p)
            res.warnings.extend(path_warns)
            res.warnings.extend(validate_destination_folder(w, expanded_sources))

    elif tab_key == "archive-immich":
        w = tab_state.get("write-to", "").strip()
        if not w:
            res.errors.append("Destination folder is required.")
        else:
            res.warnings.extend(validate_destination_folder(w, []))

    # Date range validation across tabs
    for key in ("date-range", "from-date-range"):
        if key in tab_state and tab_state[key].strip():
            valid, err = validate_date_range_func(tab_state[key])
            if not valid:
                res.errors.append(f"Invalid date range format: {err}")

    return res


def build_plan_from_state(
    tab_key: str,
    config_state: dict,
    tab_state: dict,
    binary_path: str = "./immich-go",
    dry_run: bool = False,
    base_env: dict[str, str] | None = None,
    strict_schema: bool = False,
    advanced_state: dict | None = None,
) -> CommandPlan:
    """Converts configuration state, tab input state, and opt-in advanced state into a CommandPlan."""
    plan = CommandPlan()
    plan.tab_key = tab_key
    plan.dry_run = dry_run
    plan.binary_path = binary_path

    cmd_parts = TAB_COMMANDS.get(tab_key, [])
    if not cmd_parts:
        plan.errors.append(f"Unknown tab key: '{tab_key}'")
        return plan

    emitter = FlagEmitter(tab_key, strict=strict_schema)

    server = config_state.get("server", "")
    api_key = config_state.get("api_key", "")
    admin_api_key = config_state.get("admin_api_key", "")
    from_server = tab_state.get("from-server", "")
    from_api_key = tab_state.get("from-api-key", "")
    from_admin_api_key = tab_state.get("from-admin-api-key", "")

    plan.env = build_environment(
        tab_key=tab_key,
        server=normalize_server_url(server) if server else "",
        api_key=api_key,
        from_server=normalize_server_url(from_server) if from_server else "",
        from_api_key=from_api_key,
        from_admin_api_key=from_admin_api_key,
        admin_api_key=admin_api_key,
        base_env=base_env,
    )

    # Global options
    log_level = str(tab_state.get("log-level", "INFO"))
    if log_level and log_level != "INFO":
        emitter.add_option("log-level", log_level)

    # Server and SSL (exclude serverless archive-folder & source-only archive-immich)
    if tab_key not in ("archive-folder", "archive-immich"):
        if server:
            emitter.add_option("server", normalize_server_url(server))

        if config_state.get("skip-ssl"):
            emitter.add_flag("skip-verify-ssl")
            plan.warnings.append(
                "SSL verification is disabled. "
                "Use only on trusted networks or self-hosted test servers."
            )

    # Global advanced options
    if tab_key not in ("archive-folder", "archive-immich"):
        client_timeout = config_state.get("client_timeout", 20)
        if client_timeout != 20:
            emitter.add_option("client-timeout", f"{client_timeout}m")

    if (tab_key in UPLOAD_TABS or tab_key == "stack") and config_state.get("device_uuid"):
        emitter.add_option("device-uuid", config_state["device_uuid"])

    concurrent = config_state.get("concurrent", 0)
    concurrent_default = config_state.get("concurrent_default", 0)
    if concurrent != concurrent_default:
        emitter.add_option("concurrent-tasks", concurrent)

    if tab_key in UPLOAD_TABS or tab_key == "stack":
        if "pause-jobs" in tab_state:
            if not tab_state["pause-jobs"]:
                emitter.add_bool_val("pause-immich-jobs", False)
        elif not config_state.get("pause_jobs", True):
            emitter.add_bool_val("pause-immich-jobs", False)

    if flag_allowed_for_tab(tab_key, "on-errors"):
        if "on-errors" in tab_state:
            if tab_state["on-errors"] != "stop":
                emitter.add_option("on-errors", tab_state["on-errors"])
        else:
            oe_config = config_state.get("on_errors", "stop")
            if oe_config in (ON_ERRORS_CUSTOM_LABEL, ON_ERRORS_CUSTOM_VALUE):
                tol = config_state.get("on_errors_tolerance", 10)
                emitter.add_option("on-errors", tol)
            elif oe_config != "stop":
                emitter.add_option("on-errors", oe_config)

    path_opt: list[str] = []

    # Tab-specific options
    if tab_key == "upload-folder":
        if tab_state.get("folder-album", "NONE") != "NONE":
            emitter.add_option("folder-as-album", tab_state["folder-album"])

        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            emitter.add_option("manage-burst", tab_state["manage-burst"])
            mb = tab_state["manage-burst"]
            plan.warnings.append(f"{mb} may discard non-cover burst frames when stacking.")

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-raw-jpeg", tab_state["manage-raw-jpeg"])
            if tab_state["manage-raw-jpeg"] == "KeepJPG":
                plan.warnings.append("KeepJPG may delete the RAW file when stacking pairs.")
            elif tab_state["manage-raw-jpeg"] == "KeepRaw":
                plan.warnings.append("KeepRaw may delete the JPEG file when stacking pairs.")

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-heic-jpeg", tab_state["manage-heic-jpeg"])

        raw_path = str(tab_state.get("path", "")).strip()
        if raw_path:
            path_opt.extend(collect_paths(raw_path))

    elif tab_key == "upload-gp":
        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            emitter.add_option("manage-burst", tab_state["manage-burst"])

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-raw-jpeg", tab_state["manage-raw-jpeg"])
            if tab_state["manage-raw-jpeg"] == "KeepJPG":
                plan.warnings.append("KeepJPG may delete the RAW file when stacking pairs.")
            elif tab_state["manage-raw-jpeg"] == "KeepRaw":
                plan.warnings.append("KeepRaw may delete the JPEG file when stacking pairs.")

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-heic-jpeg", tab_state["manage-heic-jpeg"])

        raw_paths = str(tab_state.get("path", "")).strip()
        if raw_paths:
            path_opt.extend(collect_paths(raw_paths))

    elif tab_key == "upload-immich":
        if from_server:
            emitter.add_option("from-server", normalize_server_url(from_server))

    elif tab_key == "archive-folder":
        if tab_state.get("write-to"):
            write_to = os.path.abspath(
                os.path.expanduser(str(tab_state["write-to"]).strip())
            )
            emitter.add_option("write-to-folder", write_to)

        raw_path = str(tab_state.get("path", "")).strip()
        if raw_path:
            path_opt.extend(collect_paths(raw_path))

    elif tab_key == "archive-immich":
        from_srv = tab_state.get("from-server", "") or config_state.get("server", "")
        if from_srv:
            emitter.add_option("from-server", normalize_server_url(from_srv))

        if tab_state.get("write-to"):
            write_to = os.path.abspath(
                os.path.expanduser(str(tab_state["write-to"]).strip())
            )
            emitter.add_option("write-to-folder", write_to)

    elif tab_key == "stack":
        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            emitter.add_option("manage-burst", tab_state["manage-burst"])

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-raw-jpeg", tab_state["manage-raw-jpeg"])
            if tab_state["manage-raw-jpeg"] == "KeepJPG":
                plan.warnings.append("KeepJPG may delete the RAW file when stacking pairs.")
            elif tab_state["manage-raw-jpeg"] == "KeepRaw":
                plan.warnings.append("KeepRaw may delete the JPEG file when stacking pairs.")

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-heic-jpeg", tab_state["manage-heic-jpeg"])

    # Opt-in Advanced Flags
    if advanced_state:
        from .advanced_flags import apply_advanced_flags_to_plan
        apply_advanced_flags_to_plan(
            plan=plan,
            emitter=emitter,
            tab_key=tab_key,
            advanced_state=advanced_state,
        )

    # Dry-run handling
    if dry_run:
        emitter.add_flag("dry-run")
        if tab_key in ("upload-immich", "archive-immich"):
            emitter.add_flag("from-dry-run")

    if emitter.errors:
        plan.errors.extend(emitter.errors)

    plan.argv = cmd_parts + emitter.opts + path_opt
    plan.display_argv = mask_command_for_display([binary_path] + plan.argv)
    return plan
