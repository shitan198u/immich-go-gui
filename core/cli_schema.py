"""Stable metadata constants, mappings, and compatibility matrices.

This module defines tab keys, immich-go CLI token mappings, secret flag definitions,
environment variable mappings, and version compatibility metadata.
MUST NOT import PySide6 or Qt.
"""

from .models import VersionSupport


# Stable internal tab keys used by the GUI.
TAB_KEYS = [
    "config",
    "upload-folder",
    "upload-gp",
    "upload-immich",
    "archive-folder",
    "archive-immich",
    "stack",
]

UPLOAD_TABS = {
    "upload-folder",
    "upload-gp",
    "upload-immich",
}

ARCHIVE_TABS = {
    "archive-folder",
    "archive-immich",
}

# Tabs that require the main Immich server and API key.
SERVER_REQUIRED_TABS = {
    "upload-folder",
    "upload-gp",
    "upload-immich",
    "archive-immich",
    "stack",
}

# Tabs that do not require the main Immich server.
SERVERLESS_TABS = {
    "archive-folder",
}

# Mapping from internal tab key to immich-go command tokens.
TAB_COMMANDS = {
    "upload-folder": ["upload", "from-folder"],
    "upload-gp": ["upload", "from-google-photos"],
    "upload-immich": ["upload", "from-immich"],
    "archive-folder": ["archive", "from-folder"],
    "archive-immich": ["archive", "from-immich"],
    "stack": ["stack"],
}

# Flags that must always be masked in previews.
SECRET_FLAGS = {
    "--api-key",
    "--from-api-key",
    "--admin-api-key",
    "--from-admin-api-key",
}

# Constants for error handling UI and schema strings.
ON_ERRORS_CUSTOM_LABEL = "Custom…"
ON_ERRORS_CUSTOM_VALUE = "custom"

# Environment variables used to pass secrets safely.
ENV_KEY_MAP = {
    "upload-folder": {
        "server": "IMMICH_GO_UPLOAD_SERVER",
        "api_key": "IMMICH_GO_UPLOAD_API_KEY",
        "admin_api_key": "IMMICH_GO_UPLOAD_ADMIN_API_KEY",
    },
    "upload-gp": {
        "server": "IMMICH_GO_UPLOAD_SERVER",
        "api_key": "IMMICH_GO_UPLOAD_API_KEY",
        "admin_api_key": "IMMICH_GO_UPLOAD_ADMIN_API_KEY",
    },
    "upload-immich": {
        "server": "IMMICH_GO_UPLOAD_SERVER",
        "api_key": "IMMICH_GO_UPLOAD_API_KEY",
        "admin_api_key": "IMMICH_GO_UPLOAD_ADMIN_API_KEY",
        "from_server": "IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER",
        "from_api_key": "IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY",
        "from_admin_api_key": "IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY",
    },
    "archive-immich": {
        "from_server": "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER",
        "from_api_key": "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_API_KEY",
        "from_admin_api_key": "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_ADMIN_API_KEY",
    },
    "stack": {
        "server": "IMMICH_GO_STACK_SERVER",
        "api_key": "IMMICH_GO_STACK_API_KEY",
        "admin_api_key": "IMMICH_GO_STACK_ADMIN_API_KEY",
    },
}

from dataclasses import dataclass
from typing import Any, Literal

FlagKind = Literal[
    "bool",
    "str",
    "int",
    "duration",
    "enum",
    "csv",
    "repeat",
    "date_range",
    "path",
    "paths",
]


@dataclass(frozen=True)
class FlagDef:
    name: str
    kind: FlagKind
    scope: Literal["global", "command", "subcommand"]
    default: Any = None
    secret: bool = False
    emit_in_argv: bool = True
    env_name: str | None = None
    notes: str = ""


# Per-tab allowed flags registry based on captured immich-go CLI help.
TAB_ALLOWED_FLAGS: dict[str, frozenset[str]] = {
    "upload-folder": frozenset({
        "server", "skip-verify-ssl", "client-timeout", "dry-run", "concurrent-tasks",
        "overwrite", "pause-immich-jobs", "on-errors", "session-tag", "tag",
        "device-uuid", "api-trace", "log-level", "time-zone",

        "recursive", "date-from-name", "ignore-sidecar-files",
        "include-extensions", "exclude-extensions", "include-type",
        "ban-file", "date-range", "folder-as-album", "folder-as-tags",
        "album-path-joiner", "into-album",

        "manage-burst", "manage-raw-jpeg", "manage-heic-jpeg",
        "manage-epson-fastfoto",
    }),

    "upload-gp": frozenset({
        "server", "skip-verify-ssl", "client-timeout", "dry-run", "concurrent-tasks",
        "overwrite", "pause-immich-jobs", "on-errors", "session-tag", "tag",
        "device-uuid", "api-trace", "log-level", "time-zone",

        "ban-file", "date-range", "exclude-extensions", "include-extensions",
        "from-album-name", "include-archived", "include-partner",
        "include-trashed", "include-type", "include-unmatched",
        "include-untitled-albums", "partner-shared-album", "people-tag",
        "sync-albums", "takeout-tag",

        "manage-burst", "manage-raw-jpeg", "manage-heic-jpeg",
        "manage-epson-fastfoto",
    }),

    "upload-immich": frozenset({
        "server", "skip-verify-ssl", "client-timeout", "dry-run", "concurrent-tasks",
        "overwrite", "pause-immich-jobs", "on-errors", "session-tag", "tag",
        "device-uuid", "api-trace", "log-level", "time-zone",

        "manage-burst", "manage-raw-jpeg", "manage-heic-jpeg",
        "manage-epson-fastfoto",

        "from-server", "from-skip-verify-ssl", "from-client-timeout",
        "from-include-type", "from-include-extensions", "from-exclude-extensions",
        "from-partners", "from-time-zone", "from-no-album", "from-albums",
        "from-date-range", "from-device-uuid", "from-api-trace",
        "from-dry-run", "from-pause-immich-jobs",

        "from-favorite", "from-archived", "from-trash",
        "from-minimal-rating", "from-people", "from-tags",
        "from-city", "from-state", "from-country",
        "from-make", "from-model",
    }),

    "archive-folder": frozenset({
        "write-to-folder", "dry-run", "log-level", "concurrent-tasks", "on-errors",

        "album-path-joiner", "ban-file", "date-from-name", "date-range",
        "exclude-extensions", "folder-as-album", "folder-as-tags",
        "ignore-sidecar-files", "include-extensions", "include-type",
        "into-album", "recursive",
    }),

    "archive-immich": frozenset({
        "write-to-folder", "dry-run", "log-level", "concurrent-tasks", "on-errors",

        "from-server", "from-skip-verify-ssl", "from-client-timeout",
        "from-api-trace", "from-dry-run", "from-pause-immich-jobs",

        "from-albums", "from-archived", "from-city", "from-country",
        "from-date-range", "from-device-uuid", "from-exclude-extensions",
        "from-favorite", "from-include-extensions", "from-include-type",
        "from-make", "from-minimal-rating", "from-model", "from-no-album",
        "from-partners", "from-people", "from-state", "from-tags",
        "from-time-zone", "from-trash",
    }),

    "stack": frozenset({
        "server", "skip-verify-ssl", "client-timeout", "dry-run", "log-level",
        "concurrent-tasks", "on-errors",

        "api-trace", "date-range", "device-uuid",
        "manage-burst", "manage-epson-fastfoto", "manage-heic-jpeg",
        "manage-raw-jpeg", "pause-immich-jobs", "time-zone",
    }),
}


def flag_allowed_for_tab(tab_key: str, flag_name: str) -> bool:
    """Checks whether a given flag name (without --) is allowed for a tab."""
    allowed = TAB_ALLOWED_FLAGS.get(tab_key)
    if allowed is None:
        return False
    clean_flag = flag_name.lstrip("-")
    return clean_flag in allowed


def assert_flag_allowed(tab_key: str, flag_name: str) -> None:
    """Raises ValueError if flag_name is not allowed for tab_key."""
    clean_flag = flag_name.lstrip("-")
    if not flag_allowed_for_tab(tab_key, clean_flag):
        raise ValueError(f"Flag '--{clean_flag}' is not allowed for tab '{tab_key}'.")


# Future compatibility metadata.
COMPATIBILITY_MATRIX = {
    "0.32.0": {
        "tested": True,
        "notes": (
            "GUI-tested version. Upstream removed the ReplaceAsset API. "
            "The asset.replace API-key permission is no longer required. "
            "No known immich-go CLI flag breakage for this GUI."
        ),
        "renamed_flags": {},
        "removed_flags": [],
    },
}
