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


_DATE_RANGE_RE = re.compile(
    r"^\d{4}(-\d{2}(-\d{2})?)?"
    r"(,\d{4}(-\d{2}(-\d{2})?)?)?$"
)


def normalize_server_url(url: str) -> str:
    """Normalize a server URL for CLI consumption.

    - Strips leading/trailing whitespace
    - Adds http:// if no scheme is present
    - Strips trailing slashes
    - Returns empty string for empty input
    """
    url = url.strip()
    if not url:
        return ""

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    return url.rstrip("/")


def collect_paths(raw_text: str) -> list[str]:
    """Expands glob patterns and handles multi-line path inputs."""
    paths = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        expanded = glob.glob(line)
        if expanded:
            paths.extend(expanded)
        else:
            paths.append(line)
    return paths


def validate_date_range(text: str) -> bool:
    """Validate immich-go date range format.

    Accepts: 2023, 2023-07, 2023-07-15, 2023-01-01,2023-12-31
    """
    valid, _ = validate_date_range_func(text)
    return valid


def mask_command_for_display(command_parts: list[str]) -> list[str]:
    """Obfuscates secrets in command previews.

    Handles both forms:
      --api-key=secret   (single element)
      --api-key secret   (two elements)
    """
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

        hidden = False
        for flag in SECRET_FLAGS:
            if part.startswith(f"{flag}="):
                masked.append(f"{flag}=********")
                hidden = True
                break

        if not hidden:
            masked.append(part)

    return masked


def build_environment(
    tab_key: str,
    server: str,
    api_key: str,
    from_server: str = "",
    from_api_key: str = "",
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

    api_key_name = mapping.get("api_key")
    if api_key_name and api_key:
        env[api_key_name] = api_key

    if tab_key == "upload-immich":
        if from_server:
            env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER"] = from_server
        if from_api_key:
            env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY"] = from_api_key

    if admin_api_key:
        if tab_key in UPLOAD_TABS:
            env["IMMICH_GO_UPLOAD_ADMIN_API_KEY"] = admin_api_key
        elif tab_key == "stack":
            env["IMMICH_GO_STACK_ADMIN_API_KEY"] = admin_api_key

    return env


def validate_state(
    tab_key: str,
    config_state: dict,
    tab_state: dict,
) -> ValidationResult:
    """Validates global and tab-specific input states returning a ValidationResult."""
    result = ValidationResult()

    if tab_key != "config":
        server = config_state.get("server", "").strip()
        api_key = config_state.get("api_key", "").strip()
        normalized_server = normalize_server_url(server)

        if tab_key in SERVER_REQUIRED_TABS:
            if not server:
                result.errors.append("Server URL is required.")
            elif not re.match(r"^https?://.+", normalized_server):
                result.errors.append("Server URL must start with http:// or https://.")

            if not api_key:
                result.errors.append("API key is required.")

        if config_state.get("skip-ssl"):
            result.warnings.append(
                "SSL verification is disabled. Use only on trusted networks."
            )

    src_paths: list[str] = []
    if tab_key == "upload-folder":
        raw_path = str(tab_state.get("path", "")).strip()
        if not raw_path:
            result.errors.append("Source folder or ZIP path is required.")
        else:
            expanded, path_warns = expand_source_paths(raw_path)
            src_paths = expanded
            result.warnings.extend(path_warns)

    elif tab_key == "upload-gp":
        raw_path = str(tab_state.get("path", "")).strip()
        if not raw_path:
            result.errors.append("Google Takeout source is required.")
        else:
            expanded, path_warns = expand_source_paths(raw_path)
            src_paths = expanded
            result.warnings.extend(path_warns)

    elif tab_key == "upload-immich":
        if not str(tab_state.get("from-server", "")).strip():
            result.errors.append("Source server URL is required.")
        if not str(tab_state.get("from-api-key", "")).strip():
            result.errors.append("Source API key is required.")

    elif tab_key == "archive-folder":
        raw_path = str(tab_state.get("path", "")).strip()
        if not raw_path:
            result.errors.append("Source path is required.")
        else:
            expanded, path_warns = expand_source_paths(raw_path)
            src_paths = expanded
            result.warnings.extend(path_warns)
        
        write_to = str(tab_state.get("write-to", "")).strip()
        if not write_to:
            result.errors.append("Destination folder is required.")
        else:
            dest_warns = validate_destination_folder(write_to, src_paths)
            result.warnings.extend(dest_warns)

    elif tab_key == "archive-immich":
        write_to = str(tab_state.get("write-to", "")).strip()
        if not write_to:
            result.errors.append("Destination folder is required.")
        else:
            dest_warns = validate_destination_folder(write_to, [])
            result.warnings.extend(dest_warns)

    # Validate date range format if provided
    dr = str(tab_state.get("date-range", "")).strip()
    if dr:
        valid, err = validate_date_range_func(dr)
        if not valid:
            result.errors.append(err or "Date range must be YYYY, YYYY-MM, YYYY-MM-DD, or start,end.")

    fdr = str(tab_state.get("from-date-range", "")).strip()
    if fdr:
        valid, err = validate_date_range_func(fdr)
        if not valid:
            result.errors.append(err or "Date range must be YYYY, YYYY-MM, YYYY-MM-DD, or start,end.")

    return result


def _add_destructive_warnings(tab_state: dict, plan: CommandPlan) -> None:
    raw_jpeg = tab_state.get("manage-raw-jpeg", "NoStack")
    if raw_jpeg == "KeepRaw":
        plan.warnings.append("RAW+JPEG mode KeepRaw may delete the JPEG file from paired assets.")
    elif raw_jpeg == "KeepJPG":
        plan.warnings.append("RAW+JPEG mode KeepJPG may delete the RAW file from paired assets.")

    heic_jpeg = tab_state.get("manage-heic-jpeg", "NoStack")
    if heic_jpeg == "KeepHeic":
        plan.warnings.append("HEIC+JPEG mode KeepHeic may delete the JPEG file from paired assets.")
    elif heic_jpeg == "KeepJPG":
        plan.warnings.append("HEIC+JPEG mode KeepJPG may delete the HEIC file from paired assets.")

    burst = tab_state.get("manage-burst", "NoStack")
    if burst == "StackKeepJPEG":
        plan.warnings.append("Burst mode StackKeepJPEG may discard non-cover burst frames.")
    elif burst == "StackKeepRaw":
        plan.warnings.append("Burst mode StackKeepRaw may discard non-cover burst frames.")


def build_plan_from_state(
    tab_key: str,
    config_state: dict,
    tab_state: dict,
    binary_path: str,
    dry_run: bool,
    base_env: dict[str, str] | None = None,
) -> CommandPlan:
    """Builds a CommandPlan from pure state dictionaries without UI dependencies."""
    if tab_key == "config" or tab_key not in TAB_COMMANDS:
        return CommandPlan(
            errors=["No executable tab selected."],
            tab_key=tab_key,
        )

    plan = CommandPlan(
        tab_key=tab_key,
        dry_run=dry_run,
        binary_path=binary_path,
    )

    _add_destructive_warnings(tab_state, plan)

    emitter = FlagEmitter(tab_key)
    cmd = TAB_COMMANDS[tab_key]
    path_opt: list[str] = []

    server = str(config_state.get("server", ""))
    api_key = str(config_state.get("api_key", ""))
    admin_api_key = str(config_state.get("admin_api_key", ""))
    from_server = str(tab_state.get("from-server", ""))
    from_api_key = str(tab_state.get("from-api-key", ""))

    env = build_environment(
        tab_key=tab_key,
        server=normalize_server_url(server) if server else "",
        api_key=api_key,
        from_server=normalize_server_url(from_server) if from_server else "",
        from_api_key=from_api_key,
        admin_api_key=admin_api_key,
        base_env=base_env,
    )

    # Global options
    log_level = str(tab_state.get("log-level", "INFO"))
    if log_level and log_level != "INFO":
        emitter.add_option("log-level", log_level)

    # Server and SSL
    if tab_key != "archive-folder":
        if server:
            emitter.add_option("server", normalize_server_url(server))

        if config_state.get("skip-ssl"):
            emitter.add_flag("skip-verify-ssl")
            plan.warnings.append(
                "SSL verification is disabled. "
                "Use only on trusted networks or self-hosted test servers."
            )

    # API key handling for upload-immich source server
    if tab_key == "upload-immich" and from_server:
        emitter.add_option("from-server", normalize_server_url(from_server))

    # Global advanced options
    client_timeout = config_state.get("client_timeout", 20)
    if client_timeout != 20:
        emitter.add_option("client-timeout", f"{client_timeout}m")

    if tab_key in UPLOAD_TABS and config_state.get("device_uuid"):
        emitter.add_option("device-uuid", config_state["device_uuid"])

    concurrent = config_state.get("concurrent", 0)
    concurrent_default = config_state.get("concurrent_default", 0)
    if concurrent != concurrent_default:
        emitter.add_option("concurrent-tasks", concurrent)

    if tab_key in UPLOAD_TABS:
        if "pause-jobs" in tab_state:
            if not tab_state["pause-jobs"]:
                emitter.add_bool_val("pause-immich-jobs", False)
        elif not config_state.get("pause_jobs", True):
            emitter.add_bool_val("pause-immich-jobs", False)

    if tab_key in UPLOAD_TABS:
        if "on-errors" in tab_state:
            if tab_state["on-errors"] != "stop":
                emitter.add_option("on-errors", tab_state["on-errors"])
        else:
            oe_config = config_state.get("on_errors", "stop")
            if oe_config == "custom…":
                tol = config_state.get("on_errors_tolerance", 10)
                emitter.add_option("on-errors", tol)
            elif oe_config != "stop":
                emitter.add_option("on-errors", oe_config)

    # Tab-specific options
    if tab_key == "upload-folder":
        if tab_state.get("include-type", "all") != "all":
            emitter.add_option("include-type", tab_state["include-type"])

        if tab_state.get("folder-album", "NONE") != "NONE":
            emitter.add_option("folder-as-album", tab_state["folder-album"])

        if tab_state.get("into-album"):
            emitter.add_option("into-album", tab_state["into-album"])

        if tab_state.get("overwrite"):
            emitter.add_flag("overwrite")
            plan.warnings.append("Overwrite mode will replace existing files on the server.")

        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            emitter.add_option("manage-burst", tab_state["manage-burst"])

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-raw-jpeg", tab_state["manage-raw-jpeg"])

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-heic-jpeg", tab_state["manage-heic-jpeg"])

        dr = clean_date_range(str(tab_state.get("date-range", "")))
        if dr:
            emitter.add_option("date-range", dr)

        inc_ext = normalize_extensions_csv(str(tab_state.get("include-ext", "")))
        if inc_ext:
            emitter.add_option("include-extensions", inc_ext)

        exc_ext = normalize_extensions_csv(str(tab_state.get("exclude-ext", "")))
        if exc_ext:
            emitter.add_option("exclude-extensions", exc_ext)

        if tab_state.get("ban-file"):
            for line in str(tab_state["ban-file"]).split("\n"):
                if line.strip():
                    emitter.add_option("ban-file", line.strip())

        if tab_state.get("ignore-sidecar"):
            emitter.add_flag("ignore-sidecar-files")

        if "date-from-name" in tab_state and not tab_state["date-from-name"]:
            emitter.add_bool_val("date-from-name", False)

        if tab_state.get("tag"):
            for t in str(tab_state["tag"]).split(","):
                if t.strip():
                    emitter.add_option("tag", t.strip())

        if tab_state.get("session-tag"):
            emitter.add_flag("session-tag")

        if tab_state.get("folder-tags"):
            emitter.add_flag("folder-as-tags")

        if tab_state.get("api-trace"):
            emitter.add_flag("api-trace")

        if tab_state.get("album-path-joiner"):
            emitter.add_option("album-path-joiner", tab_state["album-path-joiner"])

        if tab_state.get("album-picasa"):
            emitter.add_flag("album-picasa")

        if tab_state.get("manage-epson-fastfoto"):
            emitter.add_flag("manage-epson-fastfoto")

        if tab_state.get("path"):
            path_opt.append(tab_state["path"])

    elif tab_key == "upload-gp":
        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            emitter.add_option("manage-burst", tab_state["manage-burst"])

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-raw-jpeg", tab_state["manage-raw-jpeg"])

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-heic-jpeg", tab_state["manage-heic-jpeg"])

        if tab_state.get("include-untitled-albums"):
            emitter.add_flag("include-untitled-albums")

        dr = clean_date_range(str(tab_state.get("date-range", "")))
        if dr:
            emitter.add_option("date-range", dr)

        inc_ext = normalize_extensions_csv(str(tab_state.get("include-ext", "")))
        if inc_ext:
            emitter.add_option("include-extensions", inc_ext)

        exc_ext = normalize_extensions_csv(str(tab_state.get("exclude-ext", "")))
        if exc_ext:
            emitter.add_option("exclude-extensions", exc_ext)

        if tab_state.get("ban-file"):
            for line in str(tab_state["ban-file"]).split("\n"):
                if line.strip():
                    emitter.add_option("ban-file", line.strip())

        if tab_state.get("tag"):
            for t in str(tab_state["tag"]).split(","):
                if t.strip():
                    emitter.add_option("tag", t.strip())

        if tab_state.get("session-tag"):
            emitter.add_flag("session-tag")

        if tab_state.get("api-trace"):
            emitter.add_flag("api-trace")

        raw_paths = str(tab_state.get("path", "")).strip()
        if raw_paths:
            path_opt.extend(collect_paths(raw_paths))

    elif tab_key == "upload-immich":
        from_ct = tab_state.get("from-client-timeout")
        if from_ct is not None and int(from_ct) != 20 and int(from_ct) > 0:
            emitter.add_option("from-client-timeout", f"{from_ct}m")

        if tab_state.get("from-favorite"):
            emitter.add_flag("from-favorite")

        if tab_state.get("from-archived"):
            emitter.add_flag("from-archived")

        if tab_state.get("from-trash"):
            emitter.add_flag("from-trash")

        if tab_state.get("from-date-range"):
            emitter.add_option("from-date-range", tab_state["from-date-range"])

        if tab_state.get("from-albums"):
            for a in str(tab_state["from-albums"]).split(","):
                if a.strip():
                    emitter.add_option("from-albums", a.strip())

        if tab_state.get("from-minimal-rating", 0) > 0:
            emitter.add_option("from-minimal-rating", tab_state["from-minimal-rating"])

        if tab_state.get("from-people"):
            for p in str(tab_state["from-people"]).split(","):
                if p.strip():
                    emitter.add_option("from-people", p.strip())

        if tab_state.get("from-tags"):
            for t in str(tab_state["from-tags"]).split(","):
                if t.strip():
                    emitter.add_option("from-tags", t.strip())

        if tab_state.get("from-city"):
            emitter.add_option("from-city", tab_state["from-city"])

        if tab_state.get("from-state"):
            emitter.add_option("from-state", tab_state["from-state"])

        if tab_state.get("from-country"):
            emitter.add_option("from-country", tab_state["from-country"])

        if tab_state.get("from-make"):
            emitter.add_option("from-make", tab_state["from-make"])

        if tab_state.get("from-model"):
            emitter.add_option("from-model", tab_state["from-model"])

        if tab_state.get("from-skip-ssl"):
            emitter.add_flag("from-skip-verify-ssl")

        if tab_state.get("from-include-type", "all") != "all":
            emitter.add_option("from-include-type", tab_state["from-include-type"])

        inc_ext = normalize_extensions_csv(str(tab_state.get("from-include-ext", "")))
        if inc_ext:
            emitter.add_option("from-include-extensions", inc_ext)

        exc_ext = normalize_extensions_csv(str(tab_state.get("from-exclude-ext", "")))
        if exc_ext:
            emitter.add_option("from-exclude-extensions", exc_ext)

        if tab_state.get("from-partners"):
            emitter.add_flag("from-partners")

        if tab_state.get("from-time-zone"):
            emitter.add_option("from-time-zone", tab_state["from-time-zone"])

        if tab_state.get("from-no-album"):
            emitter.add_flag("from-no-album")

        if tab_state.get("from-device-uuid"):
            emitter.add_option("from-device-uuid", tab_state["from-device-uuid"])

        if tab_state.get("api-trace"):
            emitter.add_flag("api-trace")

    elif tab_key == "archive-folder":
        if tab_state.get("write-to"):
            emitter.add_option("write-to", tab_state["write-to"])

        dr = clean_date_range(str(tab_state.get("date-range", "")))
        if dr:
            emitter.add_option("date-range", dr)

        if tab_state.get("include-type", "all") != "all":
            emitter.add_option("include-type", tab_state["include-type"])

        inc_ext = normalize_extensions_csv(str(tab_state.get("include-ext", "")))
        if inc_ext:
            emitter.add_option("include-extensions", inc_ext)

        exc_ext = normalize_extensions_csv(str(tab_state.get("exclude-ext", "")))
        if exc_ext:
            emitter.add_option("exclude-extensions", exc_ext)

        if tab_state.get("ban-file"):
            for line in str(tab_state["ban-file"]).split("\n"):
                if line.strip():
                    emitter.add_option("ban-file", line.strip())

        if tab_state.get("ignore-sidecar"):
            emitter.add_flag("ignore-sidecar-files")

        if tab_state.get("date-from-name"):
            emitter.add_flag("date-from-name")

        if tab_state.get("path"):
            path_opt.append(tab_state["path"])

    elif tab_key == "archive-immich":
        if tab_state.get("write-to"):
            emitter.add_option("write-to", tab_state["write-to"])

        if tab_state.get("from-date-range"):
            emitter.add_option("from-date-range", tab_state["from-date-range"])

        if tab_state.get("from-albums"):
            for a in str(tab_state["from-albums"]).split(","):
                if a.strip():
                    emitter.add_option("from-albums", a.strip())

        if tab_state.get("from-favorite"):
            emitter.add_flag("from-favorite")

        if tab_state.get("from-archived"):
            emitter.add_flag("from-archived")

        if tab_state.get("from-trash"):
            emitter.add_flag("from-trash")

        if tab_state.get("from-minimal-rating", 0) > 0:
            emitter.add_option("from-minimal-rating", tab_state["from-minimal-rating"])

        if tab_state.get("from-people"):
            for p in str(tab_state["from-people"]).split(","):
                if p.strip():
                    emitter.add_option("from-people", p.strip())

        if tab_state.get("from-tags"):
            for t in str(tab_state["from-tags"]).split(","):
                if t.strip():
                    emitter.add_option("from-tags", t.strip())

        if tab_state.get("from-city"):
            emitter.add_option("from-city", tab_state["from-city"])

        if tab_state.get("from-state"):
            emitter.add_option("from-state", tab_state["from-state"])

        if tab_state.get("from-country"):
            emitter.add_option("from-country", tab_state["from-country"])

        if tab_state.get("from-make"):
            emitter.add_option("from-make", tab_state["from-make"])

        if tab_state.get("from-model"):
            emitter.add_option("from-model", tab_state["from-model"])

        if tab_state.get("from-include-type", "all") != "all":
            emitter.add_option("from-include-type", tab_state["from-include-type"])

        inc_ext = normalize_extensions_csv(str(tab_state.get("from-include-ext", "")))
        if inc_ext:
            emitter.add_option("from-include-extensions", inc_ext)

        exc_ext = normalize_extensions_csv(str(tab_state.get("from-exclude-ext", "")))
        if exc_ext:
            emitter.add_option("from-exclude-extensions", exc_ext)

        if tab_state.get("from-partners"):
            emitter.add_flag("from-partners")

        if tab_state.get("from-time-zone"):
            emitter.add_option("from-time-zone", tab_state["from-time-zone"])

        if tab_state.get("from-no-album"):
            emitter.add_flag("from-no-album")

    elif tab_key == "stack":
        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            emitter.add_option("manage-burst", tab_state["manage-burst"])

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-raw-jpeg", tab_state["manage-raw-jpeg"])

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            emitter.add_option("manage-heic-jpeg", tab_state["manage-heic-jpeg"])

        if tab_state.get("api-trace"):
            emitter.add_flag("api-trace")

    # Dry-run handling
    if dry_run:
        emitter.add_flag("dry-run")

    if emitter.errors:
        plan.errors.extend(emitter.errors)

    plan.argv = cmd + emitter.opts + path_opt
    plan.env = env
    plan.display_argv = mask_command_for_display([binary_path] + plan.argv)
    return plan
