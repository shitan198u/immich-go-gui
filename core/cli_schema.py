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
}

# Environment variables used to pass secrets safely.
ENV_KEY_MAP = {
    "upload-folder": {
        "server": "IMMICH_GO_UPLOAD_SERVER",
        "api_key": "IMMICH_GO_UPLOAD_API_KEY",
    },
    "upload-gp": {
        "server": "IMMICH_GO_UPLOAD_SERVER",
        "api_key": "IMMICH_GO_UPLOAD_API_KEY",
    },
    "upload-immich": {
        "server": "IMMICH_GO_UPLOAD_SERVER",
        "api_key": "IMMICH_GO_UPLOAD_API_KEY",
    },
    "archive-immich": {
        "server": "IMMICH_GO_ARCHIVE_SERVER",
        "api_key": "IMMICH_GO_ARCHIVE_API_KEY",
    },
    "stack": {
        "server": "IMMICH_GO_STACK_SERVER",
        "api_key": "IMMICH_GO_STACK_API_KEY",
    },
}

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
