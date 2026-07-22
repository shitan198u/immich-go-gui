Below is a detailed, safe refactor specification you can give directly to an AI agent.

It is written to avoid common mistakes:

- no big rewrite
- no UI behavior change unless explicitly stated
- no Qt imports in core logic
- existing golden tests must keep passing
- clear file boundaries
- explicit handling of `immich-go` v0.32 as the tested version
- explicit TOML config and secret-handling policy

---

# Refactor Specification: Decouple Immich-Go GUI Core Logic

## Goal

Refactor the current monolithic `app.py` into a small number of clearly separated core modules.

The GUI must remain working as before, but the core logic must become independent of PySide6 so that future `immich-go` CLI changes can be handled without touching UI code.

This refactor should create **5 core files**:

```text
app.py
theme.py

immichgo_models.py
immichgo_schema.py
immichgo_commands.py
immichgo_binary.py
immichgo_config.py
```

If you want only 4 files, merge `immichgo_schema.py` into `immichgo_commands.py`.

But for long-term maintainability, keeping `immichgo_schema.py` separate is better.

---

# 1. Non-Negotiable Rules for the AI Agent

The AI agent must follow these rules:

1. **Do not rewrite the UI.**
   - Keep the current pages, tabs, widgets, sidebar, footer, dialogs, and theme behavior.

2. **Do not change command output behavior unless explicitly specified.**
   - Existing golden tests in `test_app.py` must continue to pass.
   - Command argument order must remain the same.

3. **No PySide6 imports in core modules.**
   These files must not import PySide6:

   ```text
   immichgo_models.py
   immichgo_schema.py
   immichgo_commands.py
   immichgo_binary.py
   immichgo_config.py
   ```

4. **No Qt widgets in core modules.**
   Core modules must not use:

   ```python
   QWidget
   QLineEdit
   QComboBox
   QCheckBox
   QMessageBox
   QSettings
   QApplication
   ```

5. **Core modules must not show dialogs.**
   No `QMessageBox`, no dialogs, no UI warnings.

   Core modules return data structures such as:

   ```python
   ValidationResult
   CommandPlan
   BinaryStatus
   UpdateDecision
   ```

6. **Keep secrets out of argv.**
   API keys must never appear in:

   ```python
   CommandPlan.argv
   CommandPlan.display_argv
   ```

   API keys may appear only in:

   ```python
   CommandPlan.env
   ```

   and must be masked in previews.

7. **Do not use the legacy `immich_go_gui_config.toml`.**
   The existing `immich_go_gui_config.toml` is legacy and should not be parsed or maintained.

   A new user-level TOML config file will be introduced.

8. **No network calls on import.**
   Modules may define functions and classes, but must not call GitHub, download binaries, or load config files at import time.

9. **No side effects on import.**
   Do not create directories, write files, or migrate settings when a module is imported.

10. **Preserve backward-compatible imports temporarily.**
   `app.py` should re-export existing symbols so current tests continue to work:

   ```python
   from immichgo_models import CommandPlan, ValidationResult
   from immichgo_commands import (
       collect_paths,
       mask_command_for_display,
       normalize_server_url,
       validate_date_range,
       build_environment,
   )
   from immichgo_config import SecretStore
   from immichgo_binary import (
       load_binary_metadata,
       save_binary_metadata,
       get_binary_path,
       TESTED_IMMICH_GO_VERSION,
   )
   ```

---

# 2. Target File Structure

After this refactor, the project should look like this:

```text
app.py
theme.py

immichgo_models.py
immichgo_schema.py
immichgo_commands.py
immichgo_binary.py
immichgo_config.py

test_app.py
```

Optional later:

```text
tests/
    test_app.py
    test_commands.py
    test_binary.py
    test_config.py
```

But for now, keeping `test_app.py` is enough.

---

# 3. Dependency Rules Between Core Files

The dependency direction must be:

```text
immichgo_models.py
        ^
        |
immichgo_schema.py
        ^
        |
immichgo_commands.py


immichgo_binary.py
        ^
        |
      app.py
        |
        v
immichgo_config.py
```

More precisely:

```text
immichgo_models.py
    imports only Python standard library

immichgo_schema.py
    may import immichgo_models.py

immichgo_commands.py
    may import immichgo_models.py
    may import immichgo_schema.py

immichgo_binary.py
    may import immichgo_models.py
    may import immichgo_schema.py if needed

immichgo_config.py
    may import immichgo_models.py

app.py
    may import all core modules
    may import PySide6
```

No core module may import `app.py`.

---

# 4. File Responsibilities

---

## File 1: `immichgo_models.py`

### Purpose

Contain pure data structures only.

This file must not contain UI logic, IO, network, or Qt.

### Required contents

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VersionSupport(str, Enum):
    UNKNOWN = "unknown"
    UNSUPPORTED_OLD = "unsupported_old"
    TESTED = "tested"
    UNTESTED_BUT_MAY_WORK = "untested_but_may_work"
    UNTESTED_NEW = "untested_new"


class UpdateSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class CommandPlan:
    argv: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    display_argv: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tab_key: str = ""
    dry_run: bool = False
    binary_path: str = ""


@dataclass
class BinaryStatus:
    state: str  # "ok" | "warn" | "err"
    card_text: str
    version_text: str
    support: VersionSupport = VersionSupport.UNKNOWN
    message: str = ""


@dataclass
class UpdateDecision:
    allowed: bool
    requires_confirmation: bool
    severity: UpdateSeverity
    message: str
    latest_version: str = ""
    current_version: str = ""
```

### Optional but recommended

You may also add future intent dataclasses later, but do not make the first refactor depend on them.

For now, keep the refactor simple by using plain state dictionaries.

---

## File 2: `immichgo_schema.py`

### Purpose

Contain stable metadata about tabs, commands, environment variables, secret flags, and future compatibility information.

This file should not contain widget logic.

### Required contents

```python
from immichgo_models import VersionSupport


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
#
# This is intentionally simple for now.
# Do not build a full dynamic flag engine in this refactor.
#
# When a future immich-go version changes CLI flags, update this table
# and the command builder accordingly.
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
```

### Important instruction

Do **not** attempt to make the entire command builder fully schema-driven in this refactor.

For now, `immichgo_schema.py` is a stable place for constants and future compatibility metadata.

---

## File 3: `immichgo_commands.py`

### Purpose

Contain all pure command-building logic.

This is the most important file for decoupling the GUI from `immich-go`.

It must not import PySide6.

It should accept plain Python dictionaries collected from the UI, not Qt widgets.

### Required public functions

```python
def normalize_server_url(url: str) -> str:
    ...


def collect_paths(raw_text: str) -> list[str]:
    ...


def validate_date_range(text: str) -> bool:
    ...


def mask_command_for_display(command_parts: list[str]) -> list[str]:
    ...


def build_environment(
    tab_key: str,
    server: str,
    api_key: str,
    from_server: str = "",
    from_api_key: str = "",
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    ...


def validate_state(
    tab_key: str,
    config_state: dict,
    tab_state: dict,
) -> ValidationResult:
    ...


def build_plan_from_state(
    tab_key: str,
    config_state: dict,
    tab_state: dict,
    binary_path: str,
    dry_run: bool,
    base_env: dict[str, str] | None = None,
) -> CommandPlan:
    ...
```

---

# 5. State Dictionary Contracts

The GUI will collect widget values into plain dictionaries.

The core command builder must only use these dictionaries.

---

## 5.1 `config_state`

This represents global configuration values.

```python
config_state = {
    "server": str,
    "api_key": str,
    "skip-ssl": bool,
    "client_timeout": int,
    "concurrent": int,
    "concurrent_default": int,
    "device_uuid": str,
    "on_errors": str,              # "stop" | "continue" | "custom…"
    "on_errors_tolerance": int,
    "pause_jobs": bool,
}
```

Example:

```python
{
    "server": "http://localhost:2283",
    "api_key": "secret",
    "skip-ssl": False,
    "client_timeout": 20,
    "concurrent": 8,
    "concurrent_default": 8,
    "device_uuid": "",
    "on_errors": "stop",
    "on_errors_tolerance": 10,
    "pause_jobs": True,
}
```

---

## 5.2 `upload-folder` tab state

```python
tab_state = {
    "path": str,
    "include-type": str,              # "all" | "IMAGE" | "VIDEO"
    "folder-album": str,              # "NONE" | "FOLDER" | "PATH"
    "into-album": str,
    "manage-burst": str,
    "manage-raw-jpeg": str,
    "manage-heic-jpeg": str,
    "date-range": str,
    "include-ext": str,
    "exclude-ext": str,
    "ban-file": str,                  # multi-line string
    "ignore-sidecar": bool,
    "date-from-name": bool,
    "tag": str,                       # comma-separated
    "session-tag": bool,
    "folder-tags": bool,
    "on-errors": str,                 # "stop" | "continue"
    "overwrite": bool,
    "pause-jobs": bool,
    "log-level": str,                 # "INFO" | "DEBUG" | "WARN" | "ERROR"
    "api-trace": bool,
}
```

---

## 5.3 `upload-gp` tab state

```python
tab_state = {
    "path": str,                      # multi-line string
    "include-type": str,
    "into-album": str,
    "include-unmatched": bool,
    "include-partner": bool,
    "sync-albums": bool,
    "manage-burst": str,
    "manage-heic-jpeg": str,
    "from-album-name": str,
    "include-archived": bool,
    "include-trashed": bool,
    "partner-album": str,
    "takeout-tag": bool,
    "people-tag": bool,
    "tag": str,
    "session-tag": bool,
    "on-errors": str,
    "pause-jobs": bool,
    "log-level": str,
    "api-trace": bool,
}
```

---

## 5.4 `upload-immich` tab state

```python
tab_state = {
    "from-server": str,
    "from-api-key": str,
    "from-client-timeout": int,
    "from-favorite": bool,
    "from-archived": bool,
    "from-trash": bool,
    "from-date-range": str,
    "from-albums": str,               # comma-separated
    "from-minimal-rating": int,
    "from-people": str,               # comma-separated
    "from-tags": str,                 # comma-separated
    "from-city": str,
    "from-state": str,
    "from-country": str,
    "from-make": str,
    "from-model": str,
    "from-skip-ssl": bool,
    "on-errors": str,
    "log-level": str,
    "api-trace": bool,
}
```

---

## 5.5 `archive-folder` tab state

```python
tab_state = {
    "path": str,
    "write-to": str,
    "manage-raw-jpeg": str,
    "date-range": str,
    "log-level": str,
}
```

---

## 5.6 `archive-immich` tab state

```python
tab_state = {
    "write-to": str,
    "manage-burst": str,
    "manage-raw-jpeg": str,
    "from-date-range": str,
    "from-albums": str,
    "log-level": str,
}
```

---

## 5.7 `stack` tab state

```python
tab_state = {
    "manage-burst": str,
    "manage-raw-jpeg": str,
    "manage-heic-jpeg": str,
    "time-zone": str,
    "manage-epson": bool,
    "log-level": str,
    "api-trace": bool,
}
```

---

# 6. Required Behavior of `build_plan_from_state()`

The AI agent must preserve the current command construction behavior exactly.

The resulting `CommandPlan.argv` must have this general shape:

```text
[global options] + [command tokens] + [command options] + [paths]
```

Example:

```python
[
    "--log-level=DEBUG",
    "upload",
    "from-folder",
    "--server=http://localhost:2283",
    "--manage-burst=Stack",
    "/photos",
]
```

---

## 6.1 Global options

If `tab_state["log-level"]` exists and is not `"INFO"`:

```python
global_opts.append(f"--log-level={tab_state['log-level']}")
```

This must appear **before** the command token.

Example:

```python
["--log-level=DEBUG", "upload", "from-folder", ...]
```

---

## 6.2 Command tokens

Use:

```python
cmd = TAB_COMMANDS[tab_key]
```

Examples:

```python
"upload-folder"    -> ["upload", "from-folder"]
"upload-gp"        -> ["upload", "from-google-photos"]
"upload-immich"    -> ["upload", "from-immich"]
"archive-folder"   -> ["archive", "from-folder"]
"archive-immich"   -> ["archive", "from-immich"]
"stack"            -> ["stack"]
```

---

## 6.3 Server and SSL

For all tabs except `archive-folder`:

```python
if config_state["server"]:
    cmd_opts.append(f"--server={normalize_server_url(config_state['server'])}")

if config_state["skip-ssl"]:
    cmd_opts.append("--skip-verify-ssl")
    plan.warnings.append(
        "SSL verification is disabled. "
        "Use only on trusted networks or self-hosted test servers."
    )
```

For `archive-folder`, do not add:

```text
--server
--skip-verify-ssl
```

---

## 6.4 API key handling

Do not add API keys to `argv`.

Use environment variables.

For main server API key:

```python
env_key = ENV_KEY_MAP[tab_key]["api_key"]
env[env_key] = config_state["api_key"]
```

For `upload-immich`, also set:

```python
env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER"] = from_server
env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY"] = from_api_key
```

And add source server to argv:

```python
cmd_opts.append(f"--from-server={normalize_server_url(from_server)}")
```

But never add:

```text
--from-api-key=...
```

---

## 6.5 Global advanced options

Preserve current behavior:

### Client timeout

```python
if config_state["client_timeout"] != 20:
    cmd_opts.append(f"--client-timeout={config_state['client_timeout']}m")
```

### Device UUID

Only for upload tabs:

```python
if tab_key in UPLOAD_TABS and config_state["device_uuid"]:
    cmd_opts.append(f"--device-uuid={config_state['device_uuid']}")
```

### Concurrent tasks

```python
if config_state["concurrent"] != config_state["concurrent_default"]:
    cmd_opts.append(f"--concurrent-tasks={config_state['concurrent']}")
```

### Pause Immich jobs

Only for upload tabs:

```python
if tab_key in UPLOAD_TABS:
    if "pause-jobs" in tab_state:
        if not tab_state["pause-jobs"]:
            cmd_opts.append("--pause-immich-jobs=false")
    elif not config_state["pause_jobs"]:
        cmd_opts.append("--pause-immich-jobs=false")
```

### On errors

Only for upload tabs:

```python
if tab_key in UPLOAD_TABS:
    if "on-errors" in tab_state:
        if tab_state["on-errors"] != "stop":
            cmd_opts.append(f"--on-errors={tab_state['on-errors']}")
    else:
        if config_state["on_errors"] == "custom…":
            cmd_opts.append(f"--on-errors={config_state['on_errors_tolerance']}")
        elif config_state["on_errors"] != "stop":
            cmd_opts.append(f"--on-errors={config_state['on_errors']}")
```

---

## 6.6 Tab-specific options

The AI agent must reproduce the existing option order from `app.py`.

Do not reorder flags.

Do not add new flags unless required by this specification.

### `upload-folder`

Emit in this order:

```text
--include-type
--folder-as-album
--into-album
--overwrite
--manage-burst
--manage-raw-jpeg
--manage-heic-jpeg
--date-range
--include-extensions
--exclude-extensions
--ban-file
--ignore-sidecar-files
--date-from-name=false
--tag
--session-tag
--folder-as-tags
--api-trace
```

Path goes last.

Example:

```python
path_opt.append(tab_state["path"])
```

---

### `upload-gp`

Emit in this order:

```text
--include-type
--into-album
--include-unmatched=true
--include-partner=false
--sync-albums=false
--manage-burst
--manage-heic-jpeg
--from-album-name
--include-archived=false
--include-trashed=true
--partner-shared-album
--takeout-tag=false
--people-tag=false
--tag
--session-tag
--api-trace
```

Paths are collected from multi-line input:

```python
path_opt.extend(collect_paths(tab_state["path"]))
```

---

### `upload-immich`

Emit in this order:

```text
--from-client-timeout
--from-favorite=true
--from-archived=true
--from-trash=true
--from-date-range
--from-albums
--from-minimal-rating
--from-people
--from-tags
--from-city
--from-state
--from-country
--from-make
--from-model
--from-skip-verify-ssl
--api-trace
```

Repeatable comma-separated fields:

```text
--from-albums
--from-people
--from-tags
```

Example:

```python
for album in tab_state["from-albums"].split(","):
    album = album.strip()
    if album:
        cmd_opts.append(f"--from-albums={album}")
```

---

### `archive-folder`

Emit in this order:

```text
--write-to-folder
--manage-raw-jpeg
--date-range
```

Path goes last.

Do not emit server flags.

---

### `archive-immich`

Emit in this order:

```text
--write-to-folder
--manage-burst
--manage-raw-jpeg
--from-date-range
--from-albums
```

Repeatable:

```text
--from-albums
```

---

### `stack`

Emit in this order:

```text
--manage-burst
--manage-raw-jpeg
--manage-heic-jpeg
--time-zone
--manage-epson-fastfoto=true
--api-trace
```

---

## 6.7 Dry-run handling

After all command options are built:

```python
if dry_run:
    if "--dry-run" not in cmd_opts:
        cmd_opts.append("--dry-run")
else:
    if "--dry-run" in cmd_opts:
        cmd_opts.remove("--dry-run")
```

Then:

```python
plan.argv = global_opts + cmd + cmd_opts + path_opt
plan.env = env
plan.display_argv = mask_command_for_display([binary_path] + plan.argv)
```

---

# 7. Required Behavior of `validate_state()`

This function replaces widget-based validation logic.

It must return:

```python
ValidationResult
```

It must not raise exceptions for normal validation failures.

---

## 7.1 Global validation

For all executable tabs:

```python
if tab_key != "config":
    if tab_key in SERVER_REQUIRED_TABS:
        if not server:
            errors.append("Server URL is required.")
        elif not re.match(r"^https?://.+", normalized_server):
            errors.append("Server URL must start with http:// or https://.")

        if not api_key:
            errors.append("API key is required.")

    if skip_ssl:
        warnings.append(
            "SSL verification is disabled. Use only on trusted networks."
        )
```

---

## 7.2 Tab validation

### `upload-folder`

```python
if not tab_state.get("path", "").strip():
    errors.append("Source folder or ZIP path is required.")
```

### `upload-gp`

```python
if not tab_state.get("path", "").strip():
    errors.append("Google Takeout source is required.")
```

### `upload-immich`

```python
if not tab_state.get("from-server", "").strip():
    errors.append("Source server URL is required.")

if not tab_state.get("from-api-key", "").strip():
    errors.append("Source API key is required.")
```

### `archive-folder`

```python
if not tab_state.get("path", "").strip():
    errors.append("Source path is required.")

if not tab_state.get("write-to", "").strip():
    errors.append("Destination folder is required.")
```

### `archive-immich`

```python
if not tab_state.get("write-to", "").strip():
    errors.append("Destination folder is required.")
```

---

## 7.3 Date-range validation

Add validation for these fields when non-empty:

```text
date-range
from-date-range
```

Use:

```python
validate_date_range()
```

If invalid:

```python
errors.append("Date range must be YYYY, YYYY-MM, YYYY-MM-DD, or start,end.")
```

This is a safe improvement and should not break valid commands.

---

# 8. File 4: `immichgo_binary.py`

## Purpose

Contain binary management, version detection, tested-version policy, update decisions, download URL resolution, and extraction logic.

This file must not import PySide6.

It must not show dialogs.

---

## 8.1 Required constants

```python
import re
import os
import sys
import json
import hashlib
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import requests
from packaging.version import Version, InvalidVersion

from immichgo_models import (
    BinaryStatus,
    UpdateDecision,
    UpdateSeverity,
    VersionSupport,
)


BINARY_BASE_DIR = os.path.join(os.path.expanduser("~"), ".immich-go-gui", "bin")
METADATA_PATH = os.path.join(BINARY_BASE_DIR, "metadata.json")

# The GUI is built/tested against immich-go v0.32.0.
RECOMMENDED_IMMICH_GO_VERSION = "0.32.0"

# Keep this for backward compatibility with existing code/tests.
TESTED_IMMICH_GO_VERSION = RECOMMENDED_IMMICH_GO_VERSION

# Multiple tested versions can be supported in the future.
TESTED_IMMICH_GO_VERSIONS = frozenset({
    "0.32.0",
})

# Minimum version the GUI is willing to treat as supported.
MIN_SUPPORTED_IMMICH_GO_VERSION = "0.32.0"

# Highest version the GUI has been tested against.
MAX_KNOWN_COMPATIBLE_IMMICH_GO_VERSION = "0.32.0"


VERSION_NOTES = {
    "0.32.0": (
        "GUI-tested version. Upstream removed the ReplaceAsset API. "
        "The asset.replace API-key permission is no longer required. "
        "No known immich-go CLI flag breakage for this GUI."
    ),
}


BREAKING_INDICATORS = [
    r"\bbreaking\s+change",
    r"\bbreaking\b",
    r"\bBREAKING\b",
    r"\bremoved\b.*\bflag\b",
    r"\brenamed\b.*\bflag\b",
    r"\bincompatible\b",
    r"\bdeprecat(ed|ion)\b",
]

_BREAKING_RE = re.compile(
    "|".join(BREAKING_INDICATORS),
    re.IGNORECASE,
)
```

---

## 8.2 Required module-level compatibility functions

```python
def clean_version(version: str) -> str:
    """
    Normalize version text.

    Examples:
        "v0.32.0" -> "0.32.0"
        "0.32.0, built ..." -> "0.32.0"
    """
    ...


def parse_version_output(text: str) -> str:
    """
    Parse output from:
        immich-go version
    """
    ...


def get_version_support(version: str) -> VersionSupport:
    """
    Return support status for a binary version.
    """
    ...
```

### Required support logic

```python
def get_version_support(version: str) -> VersionSupport:
    version = clean_version(version)

    try:
        v = Version(version)
    except InvalidVersion:
        return VersionSupport.UNKNOWN

    min_v = Version(MIN_SUPPORTED_IMMICH_GO_VERSION)
    max_v = Version(MAX_KNOWN_COMPATIBLE_IMMICH_GO_VERSION)

    if v < min_v:
        return VersionSupport.UNSUPPORTED_OLD

    if version in TESTED_IMMICH_GO_VERSIONS:
        return VersionSupport.TESTED

    if v > max_v:
        return VersionSupport.UNTESTED_NEW

    return VersionSupport.UNTESTED_BUT_MAY_WORK
```

---

## 8.3 Required metadata functions

Keep compatibility with existing metadata format but upgrade it safely.

```python
def load_binary_metadata() -> dict:
    ...


def save_binary_metadata(meta: dict) -> None:
    ...


def get_binary_path(meta: dict | None = None) -> str:
    ...
```

### Metadata schema version 2

New metadata should look like:

```json
{
  "schema_version": 2,
  "selected_version": "0.32.0",
  "manual_path": "",
  "versions": {
    "0.32.0": {
      "path": "/home/user/.immich-go-gui/bin/0.32.0/immich-go",
      "downloaded_at": "2026-07-22T00:00:00+00:00",
      "gui_tested": true,
      "support_status": "tested",
      "sha256": "",
      "release_url": ""
    }
  }
}
```

Migration rules:

```python
if meta.get("schema_version", 1) < 2:
    for version, record in meta.get("versions", {}).items():
        record.setdefault("gui_tested", version in TESTED_IMMICH_GO_VERSIONS)
        record.setdefault(
            "support_status",
            get_version_support(version).value,
        )
        record.setdefault("sha256", "")
        record.setdefault("release_url", "")

    meta["schema_version"] = 2
```

Do not delete old version records.

---

## 8.4 Required `BinaryManager` class

Create a class so the GUI can use one object.

```python
class BinaryManager:
    def __init__(
        self,
        base_dir: str | None = None,
        metadata_path: str | None = None,
        os_name: str | None = None,
        arch: str | None = None,
    ):
        ...

    def load_metadata(self) -> dict:
        ...

    def save_metadata(self, meta: dict) -> None:
        ...

    def resolve_binary_path(self, meta: dict | None = None) -> str:
        ...

    def check_binary(self) -> BinaryStatus:
        ...

    def get_latest_version(self) -> str | None:
        ...

    def get_release_notes(self, version: str) -> str:
        ...

    def get_download_url(self, version: str | None = None) -> str | None:
        ...

    def evaluate_update(
        self,
        current_version: str,
        latest_version: str,
        allow_untested: bool = False,
        release_notes: str = "",
    ) -> UpdateDecision:
        ...

    def download_archive(
        self,
        url: str,
        progress_cb=None,
    ) -> bytes:
        ...

    def extract_binary(
        self,
        archive_bytes: bytes,
        download_url: str,
        version: str,
    ) -> str:
        ...

    def select_version(
        self,
        version: str,
        binary_path: str,
        sha256: str = "",
        release_url: str = "",
    ) -> None:
        ...
```

---

## 8.5 Required `check_binary()` behavior

`check_binary()` should:

1. Resolve binary path.
2. If missing, return:

```python
BinaryStatus(
    state="err",
    card_text="Binary: Missing",
    version_text="Not found",
    support=VersionSupport.UNKNOWN,
    message="Binary not found.",
)
```

3. If not executable on Linux/macOS, return error.
4. Run:

```python
subprocess.run([binary_path, "version"], capture_output=True, text=True, timeout=2)
```

5. Parse version using `parse_version_output()`.
6. Determine support using `get_version_support()`.

### Status rules

| Support | UI state | Card text example |
|---|---:|---|
| TESTED | ok | `Binary: 0.32.0 (tested)` |
| UNTESTED_BUT_MAY_WORK | warn | `Binary: 0.33.0 (untested)` |
| UNTESTED_NEW | warn | `Binary: 0.34.0 (newer than tested)` |
| UNSUPPORTED_OLD | warn | `Binary: 0.31.0 (older than supported)` |
| UNKNOWN | warn | `Binary: Unknown version` |

Do not block the whole GUI for unsupported old versions, but clearly warn.

---

## 8.6 Required update policy

The update policy must handle v0.32 as the tested version.

### If latest version is tested

Example:

```python
latest_version = "0.32.0"
```

Return:

```python
UpdateDecision(
    allowed=True,
    requires_confirmation=True,
    severity=UpdateSeverity.INFO,
    message="This version has been tested with this GUI.",
)
```

### If latest version is newer than tested

Example:

```python
latest_version = "0.33.0"
```

If `allow_untested=False`:

```python
UpdateDecision(
    allowed=False,
    requires_confirmation=False,
    severity=UpdateSeverity.WARNING,
    message=(
        "immich-go 0.33.0 is newer than the tested version 0.32.0. "
        "Automatic update is disabled for untested versions. "
        "Review release notes or enable untested updates in settings."
    ),
)
```

If `allow_untested=True`:

```python
UpdateDecision(
    allowed=True,
    requires_confirmation=True,
    severity=UpdateSeverity.WARNING,
    message=(
        "immich-go 0.33.0 has not been tested with this GUI. "
        "Review release notes before continuing."
    ),
)
```

### If release notes contain breaking indicators

For untested versions, add a warning:

```text
Release notes may contain breaking changes.
```

But do not use release-note keywords alone to block a tested version.

Tested versions override release-note heuristics.

---

## 8.7 Required download and extraction behavior

Move the existing non-UI download and extraction logic into `BinaryManager`.

The GUI may still show a progress dialog and run the download in a `QThread`.

But the core logic must be:

```python
content = binary_manager.download_archive(url, progress_cb)
binary_path = binary_manager.extract_binary(content, url, version)
binary_manager.select_version(version, binary_path, sha256=...)
```

### Required safety additions

Add SHA256 calculation:

```python
def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

Store the hash in metadata.

This does not require upstream checksums, but it gives you a recorded hash for future verification.

---

# 9. File 5: `immichgo_config.py`

## Purpose

Handle user configuration in TOML.

This file must not import PySide6.

It may use:

```python
keyring
tomllib / tomli
tomli_w
pathlib
os
dataclasses
```

---

# 10. Secrets Policy: Are We Overthinking It?

Short answer:

> No, we are not overthinking it.  
> But storing secrets in plaintext config is acceptable only if the threat model accepts it.

Many projects use `.env` files with plaintext secrets.

That is common.

But plaintext secrets have risks:

1. accidental git commit
2. accidental upload/share
3. screen sharing
4. backup leakage
5. other local processes running as the same user
6. crash logs or debug exports
7. file permissions being too open

For a desktop GUI, OS keyring is usually better as the default.

However, plaintext TOML can be supported as an explicit opt-in.

---

## Recommended secret policy

Use this policy:

### Default

```toml
[secrets]
provider = "keyring"
```

API key is stored in OS keyring.

### Optional plaintext mode

```toml
[secrets]
provider = "config"
```

API key is stored in a separate file:

```text
secrets.toml
```

with best-effort permissions:

```text
0600 on Linux/macOS
```

The main `config.toml` should not contain the API key.

This gives you the simplicity of file-based secrets without putting the secret in the main config file.

---

# 11. Config File Locations

The config file must be user-level, not project-level.

Do not create or use:

```text
./immich_go_gui_config.toml
```

Use:

### Linux

```text
$XDG_CONFIG_HOME/immich-go-gui/config.toml
```

or:

```text
~/.config/immich-go-gui/config.toml
```

### macOS

```text
~/Library/Application Support/immich-go-gui/config.toml
```

### Windows

```text
%APPDATA%/immich-go-gui/config.toml
```

Secrets file:

```text
<same directory>/secrets.toml
```

Allow override with environment variable:

```text
IMMICH_GO_GUI_CONFIG=/path/to/config.toml
```

If `IMMICH_GO_GUI_CONFIG` is set, secrets file should be placed next to it:

```text
/path/to/secrets.toml
```

---

# 12. Required TOML Config Schema

Use schema version 2.

Example:

```toml
schema_version = 2

[general]
theme = "system"
advanced_mode = false
allow_untested_updates = false

[server]
url = "http://localhost:2283"
skip_ssl = false

[secrets]
provider = "keyring"   # "keyring" or "config"

[advanced]
client_timeout_minutes = 20
concurrent_tasks = 0    # 0 means automatic/default
device_uuid = ""
on_errors = "stop"      # "stop" | "continue" | "custom"
on_errors_tolerance = 10
pause_immich_jobs = true

[form_state]
# Reserved for future full form-state persistence.
# Do not implement full form-state persistence in this refactor.
```

---

## Important notes

### `concurrent_tasks = 0`

Means use automatic default:

```python
min(max(os.cpu_count() or 2, 1), 20)
```

### `on_errors`

TOML should store:

```toml
on_errors = "custom"
```

The UI may display:

```text
custom…
```

Mapping:

```python
"custom" <-> "custom…"
```

### `allow_untested_updates`

Default:

```toml
allow_untested_updates = false
```

If true, the GUI may prompt to download untested newer `immich-go` versions.

---

# 13. Required `AppConfig` Model

Put this in `immichgo_models.py` or `immichgo_config.py`.

If placed in `immichgo_models.py`, keep it pure.

```python
@dataclass
class AppConfig:
    schema_version: int = 2

    theme_mode: str = "system"
    advanced_mode: bool = False
    allow_untested_updates: bool = False

    server_url: str = ""
    skip_ssl: bool = False

    secrets_provider: str = "keyring"

    client_timeout_minutes: int = 20
    concurrent_tasks: int = 0
    device_uuid: str = ""
    on_errors: str = "stop"
    on_errors_tolerance: int = 10
    pause_immich_jobs: bool = True

    form_state: dict = field(default_factory=dict)
```

---

# 14. Required Config Functions

```python
def default_config_dir() -> Path:
    ...


def default_config_path() -> Path:
    ...


def default_secrets_path() -> Path:
    ...


def load_config(path: Path | None = None) -> AppConfig:
    ...


def save_config(config: AppConfig, path: Path | None = None) -> None:
    ...


def load_secrets(path: Path | None = None) -> dict:
    ...


def save_secrets(secrets: dict, path: Path | None = None) -> None:
    ...


def get_api_key(config: AppConfig) -> str:
    ...


def set_api_key(value: str, config: AppConfig) -> None:
    ...


def clear_api_key(config: AppConfig) -> None:
    ...
```

---

## 14.1 Secret resolution order

Use this order:

1. Environment variable:

```text
IMMICH_GO_GUI_API_KEY
```

2. If `config.secrets_provider == "config"`:

```text
secrets.toml
```

3. If `config.secrets_provider == "keyring"`:

```text
OS keyring
```

4. Empty string.

Example:

```python
def get_api_key(config: AppConfig) -> str:
    env_value = os.environ.get("IMMICH_GO_GUI_API_KEY", "").strip()
    if env_value:
        return env_value

    if config.secrets_provider == "config":
        secrets = load_secrets()
        return str(secrets.get("api_key", "")).strip()

    return SecretStore.get_api_key()
```

---

## 14.2 Saving secrets

```python
def set_api_key(value: str, config: AppConfig) -> None:
    value = value.strip()

    if config.secrets_provider == "config":
        secrets = load_secrets()
        secrets["api_key"] = value
        save_secrets(secrets)

        # Best-effort cleanup from keyring.
        SecretStore.clear_api_key()
    else:
        SecretStore.set_api_key(value)

        # Best-effort cleanup from plaintext secrets file.
        secrets = load_secrets()
        if "api_key" in secrets:
            secrets.pop("api_key", None)
            save_secrets(secrets)
```

---

## 14.3 File permissions

For `secrets.toml`:

```python
if os.name == "posix":
    os.chmod(path, 0o600)
```

For `config.toml`:

```python
if os.name == "posix":
    os.chmod(path, 0o644)
```

Use atomic writes:

```python
def _atomic_write_text(path: Path, text: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")

    if mode is not None and os.name == "posix":
        os.chmod(tmp, mode)

    os.replace(tmp, path)
```

---

# 15. Required `SecretStore`

Move the existing keyring helper into `immichgo_config.py`.

```python
class SecretStore:
    SERVICE_NAME = "immich-go-gui"

    @staticmethod
    def set_api_key(api_key: str) -> None:
        ...

    @staticmethod
    def get_api_key() -> str:
        ...

    @staticmethod
    def clear_api_key() -> None:
        ...
```

Do not move `migrate_from_qsettings()` into core if it requires `QSettings`.

Keep that migration helper in `app.py`.

---

# 16. Required Changes in `app.py`

The GUI should become thin.

It should:

1. collect widget state into dictionaries
2. call core functions
3. display results

It should not contain detailed command-building logic.

---

## 16.1 Add imports

```python
from immichgo_models import (
    AppConfig,
    BinaryStatus,
    CommandPlan,
    UpdateDecision,
    UpdateSeverity,
    ValidationResult,
    VersionSupport,
)

from immichgo_schema import (
    TAB_COMMANDS,
    UPLOAD_TABS,
)

from immichgo_commands import (
    build_environment,
    build_plan_from_state,
    collect_paths,
    mask_command_for_display,
    normalize_server_url,
    validate_date_range,
    validate_state,
)

from immichgo_binary import (
    BinaryManager,
    TESTED_IMMICH_GO_VERSION,
    get_binary_path,
    load_binary_metadata,
    save_binary_metadata,
)

from immichgo_config import (
    SecretStore,
    get_api_key,
    load_config,
    save_config,
    set_api_key,
)
```

Also keep backward-compatible imports for tests.

---

## 16.2 Initialize core objects

In `ImmichGoGUI.__init__()`:

```python
self.binary_manager = BinaryManager()
self.app_config = load_config()
```

---

## 16.3 Add state collection methods

### Global config state

```python
def _collect_config_state(self) -> dict:
    cpu_default = min(max(os.cpu_count() or 2, 1), 20)

    return {
        "server": self.inputs["config"]["server"].text(),
        "api_key": self.inputs["config"]["api_key"].text().strip(),
        "skip-ssl": self.inputs["config"]["skip-ssl"].isChecked(),
        "client_timeout": self.inputs["config"]["client_timeout"].value(),
        "concurrent": self.inputs["config"]["concurrent"].value(),
        "concurrent_default": cpu_default,
        "device_uuid": self.inputs["config"]["device_uuid"].text().strip(),
        "on_errors": self.inputs["config"]["on_errors"].currentText(),
        "on_errors_tolerance": self.inputs["config"]["on_errors_tolerance"].value(),
        "pause_jobs": self.inputs["config"]["pause_jobs"].isChecked(),
    }
```

---

### Tab state collection

Create:

```python
def _collect_tab_state(self, tab_key: str) -> dict:
    if tab_key == "upload-folder":
        return self._collect_upload_folder_state()
    elif tab_key == "upload-gp":
        return self._collect_upload_gp_state()
    elif tab_key == "upload-immich":
        return self._collect_upload_immich_state()
    elif tab_key == "archive-folder":
        return self._collect_archive_folder_state()
    elif tab_key == "archive-immich":
        return self._collect_archive_immich_state()
    elif tab_key == "stack":
        return self._collect_stack_state()

    return {}
```

---

### Example: upload-folder collector

```python
def _collect_upload_folder_state(self) -> dict:
    c = self.inputs["upload-folder"]

    return {
        "path": c["path"].text(),
        "include-type": c["include-type"].currentText(),
        "folder-album": c["folder-album"].currentText(),
        "into-album": c["into-album"].text(),
        "manage-burst": c["manage-burst"].currentText(),
        "manage-raw-jpeg": c["manage-raw-jpeg"].currentText(),
        "manage-heic-jpeg": c["manage-heic-jpeg"].currentText(),
        "date-range": c["date-range"].text(),
        "include-ext": c["include-ext"].text(),
        "exclude-ext": c["exclude-ext"].text(),
        "ban-file": c["ban-file"].toPlainText(),
        "ignore-sidecar": c["ignore-sidecar"].isChecked(),
        "date-from-name": c["date-from-name"].isChecked(),
        "tag": c["tag"].text(),
        "session-tag": c["session-tag"].isChecked(),
        "folder-tags": c["folder-tags"].isChecked(),
        "on-errors": c["on-errors"].currentText(),
        "overwrite": c["overwrite"].isChecked(),
        "pause-jobs": c["pause-jobs"].isChecked(),
        "log-level": c["log-level"].currentText(),
        "api-trace": c["api-trace"].isChecked(),
    }
```

The AI agent must create equivalent collectors for all other tabs using the state dictionary contracts above.

---

## 16.4 Replace `build_plan()`

Replace the current large `build_plan()` with:

```python
def build_plan(self, dry_run: bool) -> CommandPlan:
    tab_key = self._get_active_tab_key()

    if tab_key == "config":
        return CommandPlan(
            errors=["No executable tab selected."],
            tab_key=tab_key,
        )

    config_state = self._collect_config_state()
    tab_state = self._collect_tab_state(tab_key)

    binary_path = getattr(self, "binary_path", "")
    if not binary_path:
        binary_path = self.binary_manager.resolve_binary_path() or "./immich-go"

    return build_plan_from_state(
        tab_key=tab_key,
        config_state=config_state,
        tab_state=tab_state,
        binary_path=binary_path,
        dry_run=dry_run,
    )
```

Keep:

```python
def build_command(self, dry_run: bool) -> list[str]:
    return self.build_plan(dry_run).argv
```

---

## 16.5 Replace `validate_inputs()`

```python
def validate_inputs(self) -> ValidationResult:
    tab_key = self._get_active_tab_key()

    if tab_key == "config":
        return ValidationResult()

    config_state = self._collect_config_state()
    tab_state = self._collect_tab_state(tab_key)

    return validate_state(
        tab_key=tab_key,
        config_state=config_state,
        tab_state=tab_state,
    )
```

---

## 16.6 Replace binary version checking

Use:

```python
def check_binary_version(self):
    status = self.binary_manager.check_binary()

    self.binary_path = self.binary_manager.resolve_binary_path()
    self.current_version = status.version_text

    self._set_binary_status(
        status.state,
        status.card_text,
        status.version_text,
    )
```

Keep `_set_binary_status()` in `app.py` because it updates UI widgets.

---

## 16.7 Replace update checking

Use `BinaryManager.evaluate_update()`.

Example:

```python
def check_for_updates(self):
    self.check_binary_version()

    latest_version = self.binary_manager.get_latest_version()
    if not latest_version:
        QMessageBox.warning(
            self,
            "Update Check",
            "Failed to fetch the latest version information from GitHub.",
        )
        return

    current_version = getattr(self, "current_version", "Unknown")

    if clean_version(current_version) == clean_version(latest_version):
        QMessageBox.information(
            self,
            "Update Check",
            f"You are already on the latest version ({current_version}).",
        )
        return

    release_notes = self.binary_manager.get_release_notes(latest_version)

    decision = self.binary_manager.evaluate_update(
        current_version=current_version,
        latest_version=latest_version,
        allow_untested=self.app_config.allow_untested_updates,
        release_notes=release_notes,
    )

    if not decision.allowed:
        QMessageBox.warning(
            self,
            "Update Not Allowed",
            decision.message,
        )
        return

    if decision.requires_confirmation:
        reply = QMessageBox.question(
            self,
            "Update Available",
            f"Latest version: {latest_version}\n"
            f"Current version: {current_version}\n\n"
            f"{decision.message}\n\n"
            f"Do you want to download and install {latest_version}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

    self.update_binary(version=latest_version, force_download=True)
```

The actual download dialog can remain in `app.py`, but it should call:

```python
self.binary_manager.download_archive(...)
self.binary_manager.extract_binary(...)
self.binary_manager.select_version(...)
```

---

# 17. Config Load/Save Changes in `app.py`

## 17.1 Load configuration

Replace current QSettings-only loading with TOML loading.

```python
def load_configuration(self):
    self.app_config = load_config()

    # One-time migration from old QSettings if TOML does not exist.
    if not default_config_path().exists():
        self._migrate_legacy_qsettings_to_config()
        self.app_config = load_config()

    self.inputs["config"]["server"].setText(self.app_config.server_url)
    self.inputs["config"]["skip-ssl"].setChecked(self.app_config.skip_ssl)

    self.inputs["config"]["api_key"].setText(
        get_api_key(self.app_config)
    )

    self.inputs["config"]["client_timeout"].setValue(
        self.app_config.client_timeout_minutes
    )

    if self.app_config.concurrent_tasks > 0:
        self.inputs["config"]["concurrent"].setValue(
            self.app_config.concurrent_tasks
        )

    self.inputs["config"]["device_uuid"].setText(
        self.app_config.device_uuid
    )

    if self.app_config.on_errors == "custom":
        self.inputs["config"]["on_errors"].setCurrentText("custom…")
    else:
        self.inputs["config"]["on_errors"].setCurrentText(
            self.app_config.on_errors
        )

    self.inputs["config"]["on_errors_tolerance"].setValue(
        self.app_config.on_errors_tolerance
    )

    self.inputs["config"]["pause_jobs"].setChecked(
        self.app_config.pause_immich_jobs
    )

    self.theme_mode = normalize_theme_mode(self.app_config.theme_mode)

    if hasattr(self, "theme_mode_combo"):
        self.theme_mode_combo.blockSignals(True)
        self.theme_mode_combo.setCurrentText(self.theme_mode)
        self.theme_mode_combo.blockSignals(False)

    self.apply_theme(self.theme_mode)
```

---

## 17.2 Save configuration

```python
def save_configuration(self):
    self.app_config.server_url = self.inputs["config"]["server"].text()
    self.app_config.skip_ssl = self.inputs["config"]["skip-ssl"].isChecked()

    self.app_config.client_timeout_minutes = (
        self.inputs["config"]["client_timeout"].value()
    )

    self.app_config.concurrent_tasks = (
        self.inputs["config"]["concurrent"].value()
    )

    self.app_config.device_uuid = (
        self.inputs["config"]["device_uuid"].text().strip()
    )

    on_errors_text = self.inputs["config"]["on_errors"].currentText()
    if on_errors_text == "custom…":
        self.app_config.on_errors = "custom"
    else:
        self.app_config.on_errors = on_errors_text

    self.app_config.on_errors_tolerance = (
        self.inputs["config"]["on_errors_tolerance"].value()
    )

    self.app_config.pause_immich_jobs = (
        self.inputs["config"]["pause_jobs"].isChecked()
    )

    if hasattr(self, "theme_mode_combo"):
        self.app_config.theme_mode = self.theme_mode_combo.currentText()

    save_config(self.app_config)

    api_key = self.inputs["config"]["api_key"].text().strip()
    set_api_key(api_key, self.app_config)

    QMessageBox.information(
        self,
        "Saved",
        "Configuration saved successfully.",
    )
```

---

## 17.3 Legacy QSettings migration

Keep this in `app.py` because it uses `QSettings`.

```python
def _migrate_legacy_qsettings_to_config(self):
    cfg = AppConfig()

    cfg.server_url = self.settings.value("server_url", "")
    cfg.skip_ssl = self.settings.value("skip_ssl", False, type=bool)
    cfg.theme_mode = normalize_theme_mode(
        self.settings.value("theme_mode", THEME_SYSTEM)
    )

    save_config(cfg)

    # Migrate old plaintext API key from QSettings to secret storage.
    SecretStore.migrate_from_qsettings(self.settings)
```

You may keep `SecretStore.migrate_from_qsettings()` as a thin helper in `app.py` or make it accept a settings-like object.

---

# 18. Dependencies

Add these dependencies if not already present:

```text
requests
keyring
packaging
tomli-w
tomli; python_version < "3.11"
```

`requests` and `keyring` are already used.

New required dependencies:

```text
packaging
tomli-w
tomli
```

Use this import pattern in `immichgo_config.py`:

```python
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import tomli_w
```

---

# 19. Tests That Must Be Added

Add tests without Qt where possible.

## 19.1 Command builder tests

```python
def test_build_plan_from_state_upload_folder_golden():
    config_state = {
        "server": "http://localhost:2283",
        "api_key": "test-key",
        "skip-ssl": False,
        "client_timeout": 20,
        "concurrent": 8,
        "concurrent_default": 8,
        "device_uuid": "",
        "on_errors": "stop",
        "on_errors_tolerance": 10,
        "pause_jobs": True,
    }

    tab_state = {
        "path": "/photos",
        "include-type": "all",
        "folder-album": "NONE",
        "into-album": "",
        "manage-burst": "Stack",
        "manage-raw-jpeg": "NoStack",
        "manage-heic-jpeg": "NoStack",
        "date-range": "",
        "include-ext": "",
        "exclude-ext": "",
        "ban-file": "",
        "ignore-sidecar": False,
        "date-from-name": True,
        "tag": "",
        "session-tag": False,
        "folder-tags": False,
        "on-errors": "stop",
        "overwrite": False,
        "pause-jobs": True,
        "log-level": "INFO",
        "api-trace": False,
    }

    plan = build_plan_from_state(
        tab_key="upload-folder",
        config_state=config_state,
        tab_state=tab_state,
        binary_path="./immich-go",
        dry_run=False,
        base_env={},
    )

    assert plan.argv == [
        "upload",
        "from-folder",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "/photos",
    ]

    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert not any("--api-key" in part for part in plan.argv)
```

---

## 19.2 Binary version support tests

```python
from immichgo_binary import get_version_support
from immichgo_models import VersionSupport


def test_version_support_tested():
    assert get_version_support("0.32.0") == VersionSupport.TESTED
    assert get_version_support("v0.32.0") == VersionSupport.TESTED


def test_version_support_unsupported_old():
    assert get_version_support("0.31.0") == VersionSupport.UNSUPPORTED_OLD


def test_version_support_untested_new():
    assert get_version_support("0.33.0") == VersionSupport.UNTESTED_NEW
```

---

## 19.3 Update decision tests

```python
def test_update_decision_allows_tested_version():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.31.0",
        latest_version="0.32.0",
        allow_untested=False,
        release_notes="",
    )

    assert decision.allowed is True
    assert decision.requires_confirmation is True


def test_update_decision_blocks_untested_by_default():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.32.0",
        latest_version="0.33.0",
        allow_untested=False,
        release_notes="",
    )

    assert decision.allowed is False


def test_update_decision_allows_untested_when_enabled():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.32.0",
        latest_version="0.33.0",
        allow_untested=True,
        release_notes="",
    )

    assert decision.allowed is True
    assert decision.requires_confirmation is True
```

---

## 19.4 Config tests

```python
def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "IMMICH_GO_GUI_CONFIG",
        str(tmp_path / "config.toml"),
    )

    cfg = AppConfig()
    cfg.server_url = "http://localhost:2283"
    cfg.skip_ssl = True
    cfg.client_timeout_minutes = 60

    save_config(cfg)
    loaded = load_config()

    assert loaded.server_url == "http://localhost:2283"
    assert loaded.skip_ssl is True
    assert loaded.client_timeout_minutes == 60
```

---

# 20. Step-by-Step Implementation Order

The AI agent should implement in this order.

---

## Step 1: Create `immichgo_models.py`

Move:

```python
CommandPlan
ValidationResult
```

Add:

```python
VersionSupport
UpdateSeverity
BinaryStatus
UpdateDecision
AppConfig
```

Acceptance:

```bash
python -c "import immichgo_models"
```

works without PySide6.

---

## Step 2: Create `immichgo_schema.py`

Move/add:

```python
TAB_COMMANDS
UPLOAD_TABS
SERVER_REQUIRED_TABS
SERVERLESS_TABS
SECRET_FLAGS
ENV_KEY_MAP
COMPATIBILITY_MATRIX
```

Acceptance:

```bash
python -c "import immichgo_schema"
```

works without PySide6.

---

## Step 3: Create `immichgo_commands.py`

Move:

```python
collect_paths
normalize_server_url
mask_command_for_display
validate_date_range
build_environment
```

Add:

```python
validate_state
build_plan_from_state
```

Then make `app.py` use them.

Acceptance:

- existing tests pass
- no PySide6 import in `immichgo_commands.py`
- golden command tests pass

---

## Step 4: Refactor `app.py` to collect state dictionaries

Add:

```python
_collect_config_state()
_collect_tab_state()
_collect_upload_folder_state()
_collect_upload_gp_state()
_collect_upload_immich_state()
_collect_archive_folder_state()
_collect_archive_immich_state()
_collect_stack_state()
```

Replace:

```python
build_plan()
validate_inputs()
```

Acceptance:

- GUI behavior unchanged
- existing tests pass
- command previews unchanged

---

## Step 5: Create `immichgo_binary.py`

Move binary logic out of `app.py`.

Add:

```python
BinaryManager
get_version_support
TESTED_IMMICH_GO_VERSIONS
MIN_SUPPORTED_IMMICH_GO_VERSION
MAX_KNOWN_COMPATIBLE_IMMICH_GO_VERSION
VERSION_NOTES
```

Acceptance:

- binary version check still works
- update check still works
- no PySide6 import in `immichgo_binary.py`
- tested version is `0.32.0`

---

## Step 6: Create `immichgo_config.py`

Add TOML config loading/saving.

Add:

```python
AppConfig support
SecretStore
get_api_key
set_api_key
load_config
save_config
load_secrets
save_secrets
```

Acceptance:

- config loads from TOML
- config saves to TOML
- API key default remains keyring
- optional plaintext secrets go to `secrets.toml`
- no PySide6 import in `immichgo_config.py`

---

## Step 7: Update `app.py` config load/save

Use:

```python
load_config()
save_config()
get_api_key()
set_api_key()
```

Keep one-time QSettings migration.

Acceptance:

- old users do not lose server URL/theme/API key
- new config file is created in user config directory
- legacy `immich_go_gui_config.toml` is not used

---

## Step 8: Run all tests

```bash
pytest
```

All tests must pass.

---

# 21. Definition of Done

The refactor is complete when:

1. These files exist:

```text
immichgo_models.py
immichgo_schema.py
immichgo_commands.py
immichgo_binary.py
immichgo_config.py
```

2. None of those files import PySide6.

3. `app.py` no longer contains the main command-building logic.

4. `app.py` only collects widget state and calls core functions.

5. Existing golden tests pass without changing expected command output.

6. API keys never appear in `CommandPlan.argv`.

7. Binary manager treats `0.32.0` as tested.

8. Binary manager warns for untested newer versions.

9. Binary manager blocks or warns according to `allow_untested_updates`.

10. Config is stored in a user-level TOML file.

11. Secrets default to OS keyring.

12. Plaintext secrets are optional and stored in `secrets.toml`, not main config.

13. Legacy `immich_go_gui_config.toml` is ignored.

14. `pytest` passes.

---

# 22. Copy/Paste Prompt for the AI Agent

You can give the following prompt to the AI agent.

---

```text
You are refactoring a PySide6 GUI for immich-go.

Your job is to decouple core logic from the UI without changing existing behavior.

Follow these rules strictly:

1. Do not rewrite the UI.
2. Do not change command output order.
3. Existing tests in test_app.py must continue to pass.
4. Do not import PySide6 in any new core module.
5. Do not show dialogs from core modules.
6. Keep API keys out of argv.
7. Do not use the legacy immich_go_gui_config.toml.
8. Do not perform network calls or file writes on module import.

Create these files:

immichgo_models.py
immichgo_schema.py
immichgo_commands.py
immichgo_binary.py
immichgo_config.py

Use the following responsibilities:

immichgo_models.py:
- Pure dataclasses and enums.
- Include CommandPlan, ValidationResult, VersionSupport, UpdateSeverity, BinaryStatus, UpdateDecision, AppConfig.

immichgo_schema.py:
- Stable constants.
- Include TAB_COMMANDS, UPLOAD_TABS, SERVER_REQUIRED_TABS, SERVERLESS_TABS, SECRET_FLAGS, ENV_KEY_MAP, COMPATIBILITY_MATRIX.
- Do not build a full dynamic schema engine yet.

immichgo_commands.py:
- Pure command logic.
- Move collect_paths, normalize_server_url, mask_command_for_display, validate_date_range, build_environment.
- Add validate_state and build_plan_from_state.
- build_plan_from_state accepts plain dictionaries, not Qt widgets.
- Preserve the exact current immich-go argv order from app.py.
- Preserve current golden test expectations.

immichgo_binary.py:
- Binary management.
- Move metadata loading/saving, binary path resolution, version parsing, download URL logic, release note checking, extraction logic.
- Add BinaryManager.
- Add tested version handling.
- Set RECOMMENDED_IMMICH_GO_VERSION = "0.32.0".
- Set TESTED_IMMICH_GO_VERSIONS = {"0.32.0"}.
- Set MIN_SUPPORTED_IMMICH_GO_VERSION = "0.32.0".
- Set MAX_KNOWN_COMPATIBLE_IMMICH_GO_VERSION = "0.32.0".
- Add get_version_support().
- Add evaluate_update().
- Tested versions should be allowed.
- Untested newer versions should be blocked by default unless allow_untested=True.
- Release-note keyword scanning is only a heuristic and must not block tested versions.

immichgo_config.py:
- TOML config loading/saving.
- Use user-level config directory.
- Support IMMICH_GO_GUI_CONFIG override.
- Default config file: config.toml.
- Default secrets file: secrets.toml.
- Do not store API key in main config.toml.
- Default secrets provider is keyring.
- Optional secrets provider "config" stores api_key in secrets.toml with 0600 on POSIX.
- Move SecretStore keyring helper here.
- Do not require QSettings here.

Modify app.py as follows:

- Import from the new modules.
- Keep backward-compatible re-exports for existing tests.
- Add methods to collect widget state into dictionaries:
  _collect_config_state()
  _collect_tab_state()
  _collect_upload_folder_state()
  _collect_upload_gp_state()
  _collect_upload_immich_state()
  _collect_archive_folder_state()
  _collect_archive_immich_state()
  _collect_stack_state()

- Replace build_plan() with a thin wrapper that calls build_plan_from_state().
- Replace validate_inputs() with a thin wrapper that calls validate_state().
- Replace binary version/update logic with BinaryManager calls.
- Replace config load/save with TOML config functions.
- Keep one-time QSettings migration in app.py.
- Keep ProcessTracker and terminal execution in app.py for now.

Use these state dictionary contracts:

config_state:
{
    "server": str,
    "api_key": str,
    "skip-ssl": bool,
    "client_timeout": int,
    "concurrent": int,
    "concurrent_default": int,
    "device_uuid": str,
    "on_errors": str,
    "on_errors_tolerance": int,
    "pause_jobs": bool,
}

upload-folder tab_state:
{
    "path": str,
    "include-type": str,
    "folder-album": str,
    "into-album": str,
    "manage-burst": str,
    "manage-raw-jpeg": str,
    "manage-heic-jpeg": str,
    "date-range": str,
    "include-ext": str,
    "exclude-ext": str,
    "ban-file": str,
    "ignore-sidecar": bool,
    "date-from-name": bool,
    "tag": str,
    "session-tag": bool,
    "folder-tags": bool,
    "on-errors": str,
    "overwrite": bool,
    "pause-jobs": bool,
    "log-level": str,
    "api-trace": bool,
}

upload-gp tab_state:
{
    "path": str,
    "include-type": str,
    "into-album": str,
    "include-unmatched": bool,
    "include-partner": bool,
    "sync-albums": bool,
    "manage-burst": str,
    "manage-heic-jpeg": str,
    "from-album-name": str,
    "include-archived": bool,
    "include-trashed": bool,
    "partner-album": str,
    "takeout-tag": bool,
    "people-tag": bool,
    "tag": str,
    "session-tag": bool,
    "on-errors": str,
    "pause-jobs": bool,
    "log-level": str,
    "api-trace": bool,
}

upload-immich tab_state:
{
    "from-server": str,
    "from-api-key": str,
    "from-client-timeout": int,
    "from-favorite": bool,
    "from-archived": bool,
    "from-trash": bool,
    "from-date-range": str,
    "from-albums": str,
    "from-minimal-rating": int,
    "from-people": str,
    "from-tags": str,
    "from-city": str,
    "from-state": str,
    "from-country": str,
    "from-make": str,
    "from-model": str,
    "from-skip-ssl": bool,
    "on-errors": str,
    "log-level": str,
    "api-trace": bool,
}

archive-folder tab_state:
{
    "path": str,
    "write-to": str,
    "manage-raw-jpeg": str,
    "date-range": str,
    "log-level": str,
}

archive-immich tab_state:
{
    "write-to": str,
    "manage-burst": str,
    "manage-raw-jpeg": str,
    "from-date-range": str,
    "from-albums": str,
    "log-level": str,
}

stack tab_state:
{
    "manage-burst": str,
    "manage-raw-jpeg": str,
    "manage-heic-jpeg": str,
    "time-zone": str,
    "manage-epson": bool,
    "log-level": str,
    "api-trace": bool,
}

Command building requirements:

- Global --log-level must appear before the command token.
- Command tokens come from TAB_COMMANDS.
- Server flags are not emitted for archive-folder.
- API keys are never emitted as argv flags.
- API keys are passed via environment variables.
- Preserve the existing flag emission order from app.py.
- Dry-run is appended to command options before paths.
- Paths are always last.
- Existing golden tests must pass unchanged.

Validation requirements:

- Server URL and API key are required for server-required tabs.
- archive-folder does not require server URL or API key.
- upload-folder requires path.
- upload-gp requires path.
- upload-immich requires from-server and from-api-key.
- archive-folder requires path and write-to.
- archive-immich requires write-to.
- Validate non-empty date-range and from-date-range fields using validate_date_range().

Config requirements:

- Use TOML config in the user config directory.
- Do not use legacy immich_go_gui_config.toml.
- Use schema_version = 2.
- Store non-secret settings in config.toml.
- Store secrets only in keyring by default.
- If secrets.provider = "config", store api_key in secrets.toml.
- secrets.toml should be chmod 0600 on POSIX.
- Support IMMICH_GO_GUI_API_KEY environment variable as runtime override.
- Support IMMICH_GO_GUI_CONFIG environment variable for config path override.

Binary requirements:

- Treat immich-go 0.32.0 as the tested version.
- Add VERSION_NOTES for 0.32.0 mentioning ReplaceAsset API removal and asset.replace permission no longer being required.
- Add version support states:
  UNKNOWN
  UNSUPPORTED_OLD
  TESTED
  UNTESTED_BUT_MAY_WORK
  UNTESTED_NEW
- Add update decision logic.
- Tested updates are allowed with confirmation.
- Untested updates are blocked by default unless allow_untested_updates is true.
- Release-note breaking-change keywords are only a heuristic.
- Tested versions override release-note heuristics.

Testing requirements:

- Keep existing tests passing.
- Add pure tests for build_plan_from_state.
- Add tests for get_version_support.
- Add tests for evaluate_update.
- Add tests for TOML config roundtrip.
- Do not make network calls in tests.

When finished:

- app.py should be thinner.
- Core modules should be Qt-independent.
- Command generation should be separate from UI.
- Binary compatibility should be explicit.
- Config should be TOML-based.
- Secrets should be handled safely.
```