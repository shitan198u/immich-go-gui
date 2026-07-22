"""Pure command-building and state validation logic for Immich-Go.

This module contains pure command generation logic and MUST NOT import PySide6 or Qt.
It operates entirely on plain Python dictionaries and primitive types.
"""

import glob
import os
import re

from .models import CommandPlan, ValidationResult
from .cli_schema import (
    ENV_KEY_MAP,
    SECRET_FLAGS,
    SERVER_REQUIRED_TABS,
    TAB_COMMANDS,
    UPLOAD_TABS,
)
from .validation import (
    clean_date_range,
    normalize_extensions_csv,
    normalize_list_csv,
    validate_date_range as validate_date_range_func,
    expand_source_paths,
    validate_destination_folder,
)


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

    global_opts: list[str] = []
    cmd = TAB_COMMANDS[tab_key]
    cmd_opts: list[str] = []
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

    # 6.1 Global options
    log_level = str(tab_state.get("log-level", "INFO"))
    if log_level and log_level != "INFO":
        global_opts.append(f"--log-level={log_level}")

    # 6.3 Server and SSL
    if tab_key != "archive-folder":
        if server:
            cmd_opts.append(f"--server={normalize_server_url(server)}")

        if config_state.get("skip-ssl"):
            cmd_opts.append("--skip-verify-ssl")
            plan.warnings.append(
                "SSL verification is disabled. "
                "Use only on trusted networks or self-hosted test servers."
            )

    # 6.4 API key handling for upload-immich source server
    if tab_key == "upload-immich" and from_server:
        cmd_opts.append(f"--from-server={normalize_server_url(from_server)}")

    # 6.5 Global advanced options
    client_timeout = config_state.get("client_timeout", 20)
    if client_timeout != 20:
        cmd_opts.append(f"--client-timeout={client_timeout}m")

    if tab_key in UPLOAD_TABS and config_state.get("device_uuid"):
        cmd_opts.append(f"--device-uuid={config_state['device_uuid']}")

    concurrent = config_state.get("concurrent", 0)
    concurrent_default = config_state.get("concurrent_default", 0)
    if concurrent != concurrent_default:
        cmd_opts.append(f"--concurrent-tasks={concurrent}")

    if tab_key in UPLOAD_TABS:
        if "pause-jobs" in tab_state:
            if not tab_state["pause-jobs"]:
                cmd_opts.append("--pause-immich-jobs=false")
        elif not config_state.get("pause_jobs", True):
            cmd_opts.append("--pause-immich-jobs=false")

    if tab_key in UPLOAD_TABS:
        if "on-errors" in tab_state:
            if tab_state["on-errors"] != "stop":
                cmd_opts.append(f"--on-errors={tab_state['on-errors']}")
        else:
            oe_config = config_state.get("on_errors", "stop")
            if oe_config == "custom…":
                tol = config_state.get("on_errors_tolerance", 10)
                cmd_opts.append(f"--on-errors={tol}")
            elif oe_config != "stop":
                cmd_opts.append(f"--on-errors={oe_config}")

    # 6.6 Tab-specific options in strict order
    if tab_key == "upload-folder":
        if tab_state.get("include-type", "all") != "all":
            cmd_opts.append(f"--include-type={tab_state['include-type']}")

        if tab_state.get("folder-album", "NONE") != "NONE":
            cmd_opts.append(f"--folder-as-album={tab_state['folder-album']}")

        if tab_state.get("into-album"):
            cmd_opts.append(f"--into-album={tab_state['into-album']}")

        if tab_state.get("overwrite"):
            cmd_opts.append("--overwrite")
            plan.warnings.append("Overwrite mode will replace existing files on the server.")

        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-burst={tab_state['manage-burst']}")

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-raw-jpeg={tab_state['manage-raw-jpeg']}")

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-heic-jpeg={tab_state['manage-heic-jpeg']}")

        dr = clean_date_range(str(tab_state.get("date-range", "")))
        if dr:
            cmd_opts.append(f"--date-range={dr}")

        inc_ext = normalize_extensions_csv(str(tab_state.get("include-ext", "")))
        if inc_ext:
            cmd_opts.append(f"--include-extensions={inc_ext}")

        exc_ext = normalize_extensions_csv(str(tab_state.get("exclude-ext", "")))
        if exc_ext:
            cmd_opts.append(f"--exclude-extensions={exc_ext}")

        if tab_state.get("ban-file"):
            for line in str(tab_state["ban-file"]).split("\n"):
                if line.strip():
                    cmd_opts.append(f"--ban-file={line.strip()}")

        if tab_state.get("ignore-sidecar"):
            cmd_opts.append("--ignore-sidecar-files")

        if "date-from-name" in tab_state and not tab_state["date-from-name"]:
            cmd_opts.append("--date-from-name=false")

        if tab_state.get("tag"):
            for t in str(tab_state["tag"]).split(","):
                if t.strip():
                    cmd_opts.append(f"--tag={t.strip()}")

        if tab_state.get("session-tag"):
            cmd_opts.append("--session-tag")

        if tab_state.get("folder-tags"):
            cmd_opts.append("--folder-as-tags")

        if tab_state.get("api-trace"):
            cmd_opts.append("--api-trace")

        if tab_state.get("path"):
            path_opt.append(tab_state["path"])

    elif tab_key == "upload-gp":
        if tab_state.get("include-type", "all") != "all":
            cmd_opts.append(f"--include-type={tab_state['include-type']}")

        if tab_state.get("into-album"):
            cmd_opts.append(f"--into-album={tab_state['into-album']}")

        if tab_state.get("include-unmatched"):
            cmd_opts.append("--include-unmatched=true")

        if "include-partner" in tab_state and not tab_state["include-partner"]:
            cmd_opts.append("--include-partner=false")

        if "sync-albums" in tab_state and not tab_state["sync-albums"]:
            cmd_opts.append("--sync-albums=false")

        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-burst={tab_state['manage-burst']}")

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-heic-jpeg={tab_state['manage-heic-jpeg']}")

        if tab_state.get("from-album-name"):
            cmd_opts.append(f"--from-album-name={tab_state['from-album-name']}")

        if "include-archived" in tab_state and not tab_state["include-archived"]:
            cmd_opts.append("--include-archived=false")

        if tab_state.get("include-trashed"):
            cmd_opts.append("--include-trashed=true")

        if tab_state.get("partner-album"):
            cmd_opts.append(f"--partner-shared-album={tab_state['partner-album']}")

        if "takeout-tag" in tab_state and not tab_state["takeout-tag"]:
            cmd_opts.append("--takeout-tag=false")

        if "people-tag" in tab_state and not tab_state["people-tag"]:
            cmd_opts.append("--people-tag=false")

        if tab_state.get("tag"):
            for t in str(tab_state["tag"]).split(","):
                if t.strip():
                    cmd_opts.append(f"--tag={t.strip()}")

        if tab_state.get("session-tag"):
            cmd_opts.append("--session-tag")

        if tab_state.get("api-trace"):
            cmd_opts.append("--api-trace")

        raw_paths = str(tab_state.get("path", "")).strip()
        if raw_paths:
            path_opt.extend(collect_paths(raw_paths))

    elif tab_key == "upload-immich":
        from_ct = tab_state.get("from-client-timeout")
        if from_ct is not None and int(from_ct) != 20 and int(from_ct) > 0:
            cmd_opts.append(f"--from-client-timeout={from_ct}m")

        if tab_state.get("from-favorite"):
            cmd_opts.append("--from-favorite=true")

        if tab_state.get("from-archived"):
            cmd_opts.append("--from-archived=true")

        if tab_state.get("from-trash"):
            cmd_opts.append("--from-trash=true")

        if tab_state.get("from-date-range"):
            cmd_opts.append(f"--from-date-range={tab_state['from-date-range']}")

        if tab_state.get("from-albums"):
            for a in str(tab_state["from-albums"]).split(","):
                if a.strip():
                    cmd_opts.append(f"--from-albums={a.strip()}")

        if tab_state.get("from-minimal-rating", 0) > 0:
            cmd_opts.append(f"--from-minimal-rating={tab_state['from-minimal-rating']}")

        if tab_state.get("from-people"):
            for p in str(tab_state["from-people"]).split(","):
                if p.strip():
                    cmd_opts.append(f"--from-people={p.strip()}")

        if tab_state.get("from-tags"):
            for t in str(tab_state["from-tags"]).split(","):
                if t.strip():
                    cmd_opts.append(f"--from-tags={t.strip()}")

        if tab_state.get("from-city"):
            cmd_opts.append(f"--from-city={tab_state['from-city']}")

        if tab_state.get("from-state"):
            cmd_opts.append(f"--from-state={tab_state['from-state']}")

        if tab_state.get("from-country"):
            cmd_opts.append(f"--from-country={tab_state['from-country']}")

        if tab_state.get("from-make"):
            cmd_opts.append(f"--from-make={tab_state['from-make']}")

        if tab_state.get("from-model"):
            cmd_opts.append(f"--from-model={tab_state['from-model']}")

        if tab_state.get("from-skip-ssl"):
            cmd_opts.append("--from-skip-verify-ssl")

        if tab_state.get("api-trace"):
            cmd_opts.append("--api-trace")

    elif tab_key == "archive-folder":
        if tab_state.get("write-to"):
            cmd_opts.append(f"--write-to-folder={tab_state['write-to']}")

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-raw-jpeg={tab_state['manage-raw-jpeg']}")

        if tab_state.get("date-range"):
            cmd_opts.append(f"--date-range={tab_state['date-range']}")

        if tab_state.get("path"):
            path_opt.append(tab_state["path"])

    elif tab_key == "archive-immich":
        if tab_state.get("write-to"):
            cmd_opts.append(f"--write-to-folder={tab_state['write-to']}")

        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-burst={tab_state['manage-burst']}")

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-raw-jpeg={tab_state['manage-raw-jpeg']}")

        if tab_state.get("from-date-range"):
            cmd_opts.append(f"--from-date-range={tab_state['from-date-range']}")

        if tab_state.get("from-albums"):
            for a in str(tab_state["from-albums"]).split(","):
                if a.strip():
                    cmd_opts.append(f"--from-albums={a.strip()}")

    elif tab_key == "stack":
        if tab_state.get("manage-burst", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-burst={tab_state['manage-burst']}")

        if tab_state.get("manage-raw-jpeg", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-raw-jpeg={tab_state['manage-raw-jpeg']}")

        if tab_state.get("manage-heic-jpeg", "NoStack") != "NoStack":
            cmd_opts.append(f"--manage-heic-jpeg={tab_state['manage-heic-jpeg']}")

        if tab_state.get("time-zone"):
            cmd_opts.append(f"--time-zone={tab_state['time-zone']}")

        if tab_state.get("manage-epson"):
            cmd_opts.append("--manage-epson-fastfoto=true")

        if tab_state.get("api-trace"):
            cmd_opts.append("--api-trace")

    # 6.7 Dry-run handling
    if dry_run:
        if "--dry-run" not in cmd_opts:
            cmd_opts.append("--dry-run")
    else:
        if "--dry-run" in cmd_opts:
            cmd_opts.remove("--dry-run")

    plan.argv = global_opts + cmd + cmd_opts + path_opt
    plan.env = env
    plan.display_argv = mask_command_for_display([binary_path] + plan.argv)
    return plan
