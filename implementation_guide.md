# Detailed Implementation Guide  
## Focus: Sections 4, 5, 6, 7, 8  
### For: Immich-Go GUI after `core/` refactor

This document is written as a **handoff guide for an implementation agent**.  
It is intentionally explicit so that the agent can execute without making architectural mistakes.

---

# 0. Scope, Constraints, and Non-Negotiables

## In scope
Implement improvements for:

- **Section 4**: Process execution and run tracking
- **Section 5**: User profiles
- **Section 6**: Security and secret management
- **Section 7**: Binary management improvements
- **Section 8**: Validation and input quality

## Explicit constraints
The agent **must respect** the following:

1. **Do not introduce `--no-ui` as the default execution model.**
   - The external terminal launch is intentional.
   - Do **not** replace it with an embedded runner.
   - Do **not** make `--no-ui` the primary run path.

2. **Ignore old legacy flat config migration from the uploaded `immich_go_gui_config.toml`.**
   - Do not build a migration path from that old flat schema.
   - However, **do not lose the current single-profile config** when introducing profiles.

3. **Preserve the new `core/` architecture.**
   - No new backend logic should be placed directly in `app.py` if it can reasonably live in `core/`.
   - `core/` modules must remain **Qt-free** unless explicitly stated otherwise.

4. **Secrets must never leak into:**
   - `argv`
   - logs
   - message boxes
   - saved form state
   - bundled code output
   - temporary scripts unless absolutely necessary, and then only with strict permissions and cleanup

5. **All changes must be testable without network access.**
   - Use mocks / monkeypatching for:
     - GitHub API
     - downloads
     - keyring
     - subprocess
     - requests

6. **Keep the app working at every step.**
   - Run tests frequently.
   - Prefer small, verifiable increments.

---

# 1. Target Architecture After This Work

## Existing modules
These already exist after refactor:

- `core/models.py`
- `core/cli_schema.py`
- `core/config_manager.py`
- `core/binary_manager.py`
- `core/command_builder.py`
- `core/__init__.py`

## New modules to create
Create these new backend modules:

- `core/process_tracker.py`
- `core/terminal_launcher.py`
- `core/profile_manager.py`
- `core/validation.py`
- `core/network.py`

## Responsibility split

### `core/process_tracker.py`
- lock creation
- lock parsing
- stale lock detection
- active lock scanning
- manual reset support

### `core/terminal_launcher.py`
- external terminal launch logic
- platform-specific launch behavior
- temporary runner script creation
- environment handling for external terminals

### `core/profile_manager.py`
- profile listing
- active profile selection
- create/rename/duplicate/delete profiles
- profile paths
- one-time migration from single-config mode to `default` profile

### `core/validation.py`
- date range validation
- CSV normalization
- path sanity checks
- destination/source relationship checks

### `core/network.py`
- Immich server connection testing

---

# 2. Implementation Order

Use this exact order unless there is a very strong reason not to:

1. **Baseline verification**
2. **Section 8: validation and input quality**
3. **Section 6: secret management foundation**
4. **Section 5: profiles and form-state persistence**
5. **Section 4: process tracking and terminal launch hardening**
6. **Section 7: binary management improvements**
7. **Final integration, tests, docs**

This order reduces risk because:

- validation is isolated and low-risk
- profiles depend on clean secret/config handling
- process tracking is UI-adjacent but backend-heavy
- binary management is the most external-system-sensitive part

---

# 3. Baseline Verification Before Any Code Changes

## Required checks
Before modifying anything:

1. Confirm the app imports correctly after the `core/` refactor.
2. Run:
   ```bash
   uv run pytest test_app.py
   ```
3. Confirm all current tests pass.
4. Confirm the GUI starts.

## If tests fail
Do not proceed with feature work.  
Fix the refactor fallout first.

---

# 4. Section 8 — Validation and Input Quality

## Goal
Make input validation stronger, cleaner, and more predictable.

---

## 4.1 Create `core/validation.py`

This module must be pure Python and Qt-free.

### Required functions

```python
def clean_date_range(text: str) -> str:
    """
    Normalize date range input.
    - strip outer whitespace
    - remove spaces around comma
    - return empty string if blank
    """

def validate_date_range(text: str) -> tuple[bool, str | None]:
    """
    Return (is_valid, error_message).
    Accept:
      - YYYY
      - YYYY-MM
      - YYYY-MM-DD
      - start,end
    Reject:
      - invalid months
      - invalid days
      - impossible dates
      - start > end when comparable
    """

def normalize_extensions_csv(value: str) -> str:
    """
    Normalize extension lists.
    - split on comma
    - trim whitespace
    - lowercase
    - ensure leading dot
    - remove empties
    - deduplicate while preserving order
    - rejoin with commas
    """

def normalize_list_csv(value: str) -> list[str]:
    """
    Normalize generic comma-separated lists:
    - tags
    - albums
    - people
    Do not lowercase.
    """

def has_glob_pattern(text: str) -> bool:
    """
    Return True if text contains *, ?, [ or ]
    """

def expand_source_paths(raw_text: str) -> tuple[list[str], list[str]]:
    """
    For multi-line path input:
    - split lines
    - strip lines
    - expand globs
    - return (expanded_paths, warnings)

    Warnings:
    - non-glob line that does not exist
    - glob line that matches nothing
    """

def validate_destination_folder(
    write_to: str,
    source_paths: list[str],
) -> list[str]:
    """
    Return warnings/errors for destination folder.
    - warn if destination is inside a source path
    - warn if destination exists but is not a directory
    - warn if destination exists and is not writable
    """
```

---

## 4.2 Date range rules

### Accept
- `2023`
- `2023-07`
- `2023-07-15`
- `2023-01-01,2023-12-31`
- `2023-01-01, 2023-12-31`  ← spaces after comma must be accepted

### Reject
- `2023-13`
- `2023-02-30`
- `2023-00-10`
- `abcd`
- `2023-01-01,2022-12-31` when both are comparable and start > end

### Implementation notes
- Use `datetime` for semantic validation.
- For partial dates:
  - `YYYY` → January 1
  - `YYYY-MM` → first day of month
- If both sides are comparable, ensure start <= end.
- If mixed precision makes exact comparison ambiguous, prefer a **warning**, not a hard error, unless clearly invalid.

---

## 4.3 CSV normalization rules

### Extensions
Input:
```text
.JPG, png , .heic, jpg
```

Output:
```text
.jpg,.png,.heic
```

Rules:
- trim
- lowercase
- add leading dot if missing
- remove duplicates
- preserve first-seen order

### Generic lists
For:
- tags
- people
- albums

Input:
```text
 vacation,  family/reunion ,
```

Output:
```python
["vacation", "family/reunion"]
```

Rules:
- trim
- remove empty items
- preserve case
- preserve hierarchy separators like `/`

---

## 4.4 Path validation rules

### Source path behavior
For local source fields:

- If line is **not** a glob:
  - if path does not exist → warning
- If line **is** a glob:
  - if it expands to zero items → warning

Do **not** make these hard errors unless the field is completely empty when required.

### Destination behavior
For archive destination fields:

- If destination exists and is not a directory → warning/error
- If destination is inside source path → warning
- If destination exists and is not writable → warning/error

Example warning:
```text
Destination folder is inside the source path. Future runs may include archived output.
```

---

## 4.5 Integrate validation into `core/command_builder.py`

Update command building so it uses normalized values.

### Required changes
Use:

- `clean_date_range()` before appending any `--date-range` or `--from-date-range`
- `normalize_extensions_csv()` for:
  - `include-ext`
  - `exclude-ext`
- `normalize_list_csv()` for:
  - tags
  - albums
  - people

### Example
Instead of directly using raw text:

```python
if tab_state.get("include-ext"):
    cmd_opts.append(f"--include-extensions={tab_state['include-ext']}")
```

Use:

```python
exts = normalize_extensions_csv(tab_state.get("include-ext", ""))
if exts:
    cmd_opts.append(f"--include-extensions={exts}")
```

---

## 4.6 Add destructive-option warnings in `core/command_builder.py`

Add warnings for modes that may delete one side of a pair.

### Trigger warnings for
- `manage-raw-jpeg`
  - `KeepRaw`
  - `KeepJPG`
- `manage-heic-jpeg`
  - `KeepHeic`
  - `KeepJPG`
- `manage-burst`
  - `StackKeepRaw`
  - `StackKeepJPEG`

### Warning style
Example:

```text
RAW+JPEG mode KeepJPG may delete the RAW file from paired assets.
```

```text
HEIC+JPEG mode KeepHeic may delete the JPEG file from paired assets.
```

```text
Burst mode StackKeepJPEG may discard non-cover burst frames.
```

These warnings must appear in `CommandPlan.warnings`.

---

## 4.7 Create `core/network.py`

This module must be Qt-free.

### Required dataclass

```python
from dataclasses import dataclass

@dataclass
class ConnectionTestResult:
    ok: bool
    message: str
    status_code: int | None = None
    server_version: str | None = None
```

### Required function

```python
def test_immich_connection(
    server_url: str,
    api_key: str,
    skip_ssl: bool,
    timeout: float = 6.0,
) -> ConnectionTestResult:
    """
    Test connectivity and API key validity against an Immich server.
    """
```

### Behavior
1. Normalize server URL.
2. Try:
   ```text
   GET {server}/api/server/about
   ```
   with header:
   ```text
   x-api-key: <api_key>
   ```
3. Use:
   ```python
   verify=not skip_ssl
   ```
4. Interpret results:
   - `200` → success
   - `401` / `403` → API key invalid or insufficient
   - `404` → server responded but endpoint missing; try ping fallback if desired
   - SSL error → clear SSL message
   - connection error → unreachable

### Important
Do **not** print or return the API key in any message.

---

## 4.8 Update `app.py` to use the new validation helpers

### Required UI changes

#### A. Add “Test Connection” button
Place it in the Configuration page, inside the server connection card.

Behavior:
- read current server URL and API key from the form
- call `test_immich_connection()`
- show result in a message box

#### B. Show validation warnings before run
Currently, the confirm dialog shows `CommandPlan.warnings`.

Make sure validation warnings are also included.

Recommended flow in `show_confirm_dialog()`:

1. Run validation
2. If errors → block and show errors
3. Build plan
4. Prepend validation warnings to plan warnings
5. Show confirm dialog

#### C. Fix config-tab server status
When active tab is `config`, do not blindly show `Server: Ready`.

Instead:
- if server and API key are present → `Server: Configured`
- if missing → `Server: Not Set`

---

## 4.9 Section 8 test requirements

Add tests for:

### Date validation
- valid single year
- valid year-month
- valid full date
- valid range with spaces
- invalid month
- invalid day
- start after end

### CSV normalization
- extension trimming
- extension dot insertion
- lowercasing
- dedupe
- tag trimming
- empty item removal

### Path validation
- existing folder
- missing non-glob path
- glob with no matches
- glob with matches
- destination inside source

### Connection test
Mock `requests.get` and test:
- success
- invalid key
- unreachable
- SSL failure

---

# 5. Section 6 — Security and Secret Management

This section should be implemented **before profiles**, because profiles need profile-aware secrets.

---

## 5.1 Goals

Implement:

1. No silent keyring failures
2. Safe migration that cannot lose secrets
3. Secret provider choice with local fallback
4. Optional admin API key support
5. Better destructive-option warnings

---

## 5.2 Make `SecretStore` profile-aware and failure-aware

Update `core/config_manager.py`.

### New secret keys
Support at least:

- `api_key`
- `admin_api_key`

### New return behavior
Secret-setting operations must report success/failure.

Add a result type:

```python
from dataclasses import dataclass

@dataclass
class SecretSaveResult:
    ok: bool
    provider_used: str
    message: str = ""
```

### Required functions

```python
class SecretStore:
    SERVICE_NAME = "immich-go-gui"

    @staticmethod
    def set_secret(profile_name: str, key: str, value: str) -> bool:
        ...

    @staticmethod
    def get_secret(profile_name: str, key: str) -> str:
        ...

    @staticmethod
    def clear_secret(profile_name: str, key: str) -> None:
        ...

    @staticmethod
    def copy_secrets(src_profile: str, dst_profile: str) -> None:
        ...
```

### Keyring username convention
Use profile-scoped usernames:

```text
{profile_name}:api_key
{profile_name}:admin_api_key
```

Example:
```text
default:api_key
work:admin_api_key
```

### Legacy compatibility
For the `default` profile only:
- if `default:api_key` is missing
- but old `immich_api_key` exists
- read old key
- write new profile-scoped key
- only delete old key if write succeeds

---

## 5.3 Prevent secret loss during migration

Current behavior must change:

### Bad pattern
Do **not** do:
1. write new secret
2. delete old secret
3. ignore write failure

### Correct pattern
Do:
1. write new secret
2. verify it can be read back
3. only then delete old secret

This applies to:
- QSettings migration
- keyring-to-file fallback
- file-to-keyring migration

---

## 5.4 Add secret provider fallback behavior

The app already has:

```python
AppConfig.secrets_provider
```

Make it usable.

### Supported values
- `"keyring"`
- `"config"`

### Resolution order for reading secrets

#### If provider == `"config"`
1. environment override
2. `secrets.toml`
3. keyring fallback

#### If provider == `"keyring"`
1. environment override
2. keyring
3. `secrets.toml` fallback

This makes local file storage a true fallback.

---

## 5.5 Saving secrets with fallback

When saving a secret:

### If provider == `"keyring"`
Try keyring first.

If keyring write fails:
- save to `secrets.toml`
- switch effective provider to `"config"`
- return a result explaining fallback happened

### If provider == `"config"`
- save to `secrets.toml`
- clear keyring copy for that secret

---

## 5.6 Add admin API key support

### Storage
Add support for an optional `admin_api_key`.

Use the same secret storage system:
- keyring or local fallback
- profile-scoped

### UI
Add an optional field in the Configuration page.

Recommended placement:
- create a new card: **Security**
- fields:
  - Secret storage provider
  - Admin API Key

### Command/environment integration
Do **not** put admin API key in `argv`.

Use environment variables.

Update `core/cli_schema.py` and `core/command_builder.py` to support:

- `IMMICH_GO_UPLOAD_ADMIN_API_KEY`
- `IMMICH_GO_STACK_ADMIN_API_KEY`

If you also implement source admin key for `upload from-immich` later, use:

- `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY`

For now, the main admin key is enough.

---

## 5.7 Add secret provider UI

### Configuration page changes
Add a **Security** card.

#### Fields
1. **Secret Storage**
   - `OS Keyring (recommended)`
   - `Local secrets file`

2. **Admin API Key**
   - password field
   - optional

3. Optional helper label:
   - show local secrets file path when local provider is selected

### Behavior
- changing provider should not instantly move secrets
- secrets are reconciled on **Save Configuration**

---

## 5.8 Surface secret-storage problems

Do not fail silently.

### If keyring is unavailable
Show a non-blocking warning such as:

```text
OS keyring is unavailable. The secret was saved to the local secrets file instead.
```

### If local secrets file is used
Ensure POSIX permissions are `0600` where supported.

---

## 5.9 Section 6 test requirements

Add tests for:

### Secret store
- set/get/clear with mocked keyring
- keyring failure falls back to file
- provider `"config"` reads file first
- provider `"keyring"` reads keyring first
- migration does not delete old secret if new write fails

### Admin key
- admin key saved and retrieved correctly
- admin key never appears in argv
- admin key appears masked in environment preview if shown

---

# 6. Section 5 — User Profiles

## Goal
Allow users to create and switch between configuration profiles.

---

## 6.1 Product requirements

1. There must always be a `default` profile.
2. On first run, the app should use `default`.
3. Users can:
   - create profiles
   - switch profiles
   - rename profiles
   - duplicate profiles
   - delete profiles
4. The active profile should be obvious in the UI.
5. Profile data must include:
   - server config
   - advanced config
   - theme
   - secret provider choice
   - saved form state
6. Secrets must be profile-scoped.

---

## 6.2 Ignore old flat config migration
Do **not** implement migration from the old uploaded flat TOML schema.

However, **do** migrate the current single-profile config into `default` if needed.

---

## 6.3 Profile storage layout

Use this layout:

```text
<config_dir>/
  profiles.toml
  profiles/
    default/
      config.toml
      secrets.toml
    work/
      config.toml
      secrets.toml
```

### `profiles.toml`
This is the global profile index.

Example:

```toml
schema_version = 1
active_profile = "default"

[[profiles]]
name = "default"
created_at = "2026-07-22T00:00:00Z"

[[profiles]]
name = "work"
created_at = "2026-07-22T00:00:00Z"
```

---

## 6.4 Create `core/profile_manager.py`

This module must be Qt-free.

### Required dataclass

```python
from dataclasses import dataclass

@dataclass
class ProfileInfo:
    name: str
    active: bool = False
    created_at: str = ""
    config_path: str = ""
```

### Required functions

```python
def profiles_root() -> Path:
    ...

def global_profiles_path() -> Path:
    ...

def sanitize_profile_name(name: str) -> str:
    ...

def validate_profile_name(name: str) -> tuple[bool, str | None]:
    ...

def ensure_default_profile() -> None:
    ...

def migrate_single_config_to_default() -> None:
    ...

def list_profiles() -> list[ProfileInfo]:
    ...

def active_profile_name() -> str:
    ...

def set_active_profile_name(name: str) -> None:
    ...

def profile_dir(name: str) -> Path:
    ...

def profile_config_path(name: str) -> Path:
    ...

def profile_secrets_path(name: str) -> Path:
    ...

def create_profile(name: str, copy_from: str | None = None) -> ProfileInfo:
    ...

def rename_profile(old_name: str, new_name: str) -> None:
    ...

def duplicate_profile(source_name: str, new_name: str) -> ProfileInfo:
    ...

def delete_profile(name: str) -> None:
    ...
```

---

## 6.5 Profile name rules

### Allow
- letters
- numbers
- spaces
- hyphen
- underscore

### Reject
- empty names
- path separators
- `.`
- `..`
- duplicate names after normalization

Recommended validation regex:

```python
^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$
```

---

## 6.6 One-time migration from single-config mode

This is **required** so current users do not lose their settings.

### Condition
If:
- old single config file exists at `<config_dir>/config.toml`
- and `profiles/` does not exist

Then:
1. create `profiles/default/`
2. move old `config.toml` to `profiles/default/config.toml`
3. if `secrets.toml` exists, move it to `profiles/default/secrets.toml`
4. create `profiles.toml` with active profile `default`
5. optionally keep a backup like `config.toml.pre-profile.bak`

### Important
Do **not** delete user data during this migration.

---

## 6.7 Update `core/config_manager.py` for profiles

### Required behavior
- `default_config_path()` should now return the config path for the **active profile**
- `default_secrets_path()` should return the secrets path for the **active profile**
- `load_config()` should accept an optional `profile_name`
- `save_config()` should accept an optional `profile_name`

### Recommended signatures

```python
def load_config(profile_name: str | None = None) -> AppConfig:
    ...

def save_config(config: AppConfig, profile_name: str | None = None) -> None:
    ...
```

If `profile_name` is `None`, use active profile.

---

## 6.8 Add profile-aware fields to `AppConfig`

Update `core/models.py`.

Add at least:

```python
profile_name: str = "default"
preferred_terminal: str = "auto"
```

### Notes
- `profile_name` is mostly for convenience in-memory
- `preferred_terminal` will be used in Section 4

---

## 6.9 Persist form state per profile

This is required.

### Goal
When the user saves configuration, also save the current form state.

### What to persist
Persist non-secret widget states for all tabs:

- `QLineEdit` → text
- `QPlainTextEdit` → plain text
- `QCheckBox` → checked
- `QComboBox` → current text
- `QSpinBox` → value

### What **not** to persist
Never persist secret fields into `form_state`.

Skip keys such as:
- `api_key`
- `from-api-key`
- `admin_api_key`
- any future secret-bearing fields

Also skip non-user-editable fields like:
- `target-server`

---

## 6.10 Implement form-state helpers in `app.py`

Add two methods:

```python
def collect_form_state(self) -> dict:
    ...

def apply_form_state(self, state: dict) -> None:
    ...
```

### `collect_form_state()`
Iterate over:

```python
self.inputs
```

Build a nested dict:

```python
{
  "upload-folder": {
    "path": "...",
    "include-type": "IMAGE",
    ...
  },
  "upload-gp": {
    ...
  }
}
```

### `apply_form_state()`
For each stored value:
- block signals where appropriate
- restore widget state
- ignore unknown keys safely

---

## 6.11 Save/load advanced mode and update policy

Also persist:

- `advanced_mode`
- `allow_untested_updates`

### Required UI additions
Add to Configuration → Advanced:

1. Checkbox:
   - `Allow untested immich-go updates`

2. Optional combo:
   - `Preferred Terminal`
   - values:
     - `Auto`
     - `gnome-terminal`
     - `konsole`
     - `xfce4-terminal`
     - `xterm`
     - `x-terminal-emulator`

The terminal preference is optional in UI but recommended.

---

## 6.12 Add profile UI

Because there is already a menu bar with **File** and **Help**, add a new top-level menu:

```text
Profiles
```

Place it between **File** and **Help** if possible.

---

## 6.13 Profiles menu structure

The menu must contain:

- New Profile…
- Duplicate Active Profile…
- Rename Active Profile…
- Delete Active Profile…
- separator
- list of profiles with checkmark on active profile

### Behavior
- clicking a profile switches to it
- active profile is checked
- deleting active profile is not allowed unless switching to `default` first

---

## 6.14 Profile dialogs

Use simple dialogs.

### New Profile
Ask for:
- profile name

Validation:
- must be valid
- must not already exist

### Duplicate Profile
Ask for:
- new profile name

Copy:
- config.toml
- secrets.toml if present
- keyring secrets for that profile

### Rename Profile
Ask for:
- new name

Update:
- directory name
- profile index
- keyring secret usernames

### Delete Profile
Confirm before deleting.

Rules:
- cannot delete `default`
- if deleting active profile, switch to `default` first
- delete profile directory
- clear profile-scoped keyring secrets

---

## 6.15 Profile switching behavior

When switching profiles:

### Recommended flow
1. Ask:
   ```text
   Save changes to current profile before switching?
   ```
   Buttons:
   - Save
   - Discard
   - Cancel

2. If Save:
   - save current configuration and form state

3. If Discard:
   - do not save

4. If Cancel:
   - abort switch

5. Then:
   - set active profile
   - load configuration
   - apply form state
   - update window title / status

---

## 6.16 Show active profile in UI

Minimum requirement:
- show active profile in window title

Example:

```text
Immich Go GUI — default
```

Better:
- also show it in the Configuration page

---

## 6.17 Section 5 test requirements

Add tests for:

### Profile manager
- default profile creation
- create profile
- duplicate profile
- rename profile
- delete profile
- active profile persistence
- invalid profile names rejected

### Config integration
- save/load roundtrip per profile
- form state saved and restored
- secrets are not stored in form state

### Migration
- old single config migrates to `default`
- no data loss during migration

---

# 7. Section 4 — Process Execution and Run Tracking

## Goal
Make external terminal execution more robust without changing the external-terminal design.

---

## 7.1 Hard constraint
Do **not** replace external terminal execution with an embedded `--no-ui` runner.

---

## 7.2 Create `core/process_tracker.py`

This module must be Qt-free.

### Required dataclass

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class RunLock:
    run_id: str
    lock_path: Path
    gui_pid: int
    started_at: str
    tab_key: str
    command_summary: str
    binary_path: str
    shell_pid: int | None = None
```

### Required functions

```python
def lock_dir() -> Path:
    ...

def create_lock(
    tab_key: str,
    command_summary: str,
    binary_path: str,
) -> Path:
    ...

def release_lock(lock_path: Path) -> None:
    ...

def read_lock(lock_path: Path) -> RunLock | None:
    ...

def is_lock_active(lock_path: Path) -> bool:
    ...

def scan_locks() -> list[RunLock]:
    ...

def cleanup_stale_locks() -> int:
    ...

def reset_all_locks() -> int:
    ...
```

---

## 7.3 Lock file format

Use JSON lock files.

Example:

```json
{
  "run_id": "abc123",
  "gui_pid": 4321,
  "started_at": "2026-07-22T10:00:00Z",
  "tab_key": "upload-folder",
  "command_summary": "upload from-folder",
  "binary_path": "/home/user/.immich-go-gui/bin/0.32.0/immich-go",
  "shell_pid": null
}
```

---

## 7.4 Stale lock detection

### POSIX behavior
If `shell_pid` is known:
- use `os.kill(pid, 0)` to check if alive
- if dead → stale

If `shell_pid` is unknown:
- treat lock as active if file exists

### Windows behavior
Because reliable child PID detection is harder:
- do not aggressively auto-delete recent locks
- provide manual reset
- optionally delete very old locks after a safe threshold, e.g. 7 days

---

## 7.5 Startup lock handling

On app startup:

1. call `cleanup_stale_locks()`
2. call `scan_locks()`
3. if any active locks exist:
   - show running warning
   - disable Run / Dry Run buttons
   - optionally remember the first active lock path

---

## 7.6 Add manual reset

Add a menu action:

```text
File → Reset Run State
```

Behavior:
- confirm with user
- call `reset_all_locks()`
- re-enable buttons
- hide warning

This is essential for recovery after crashes.

---

## 7.7 Add close warning

Implement `closeEvent()` in `app.py`.

If active locks exist:

Ask:

```text
A command appears to still be running in an external terminal.
Close the GUI anyway?
```

Buttons:
- Yes
- No

Default: No

---

## 7.8 Create `core/terminal_launcher.py`

This module must be Qt-free except if absolutely unavoidable.  
Prefer pure Python + subprocess.

### Required result type

```python
from dataclasses import dataclass

@dataclass
class LaunchResult:
    ok: bool
    message: str = ""
```

### Required function

```python
def launch_external_terminal(
    command: list[str],
    env: dict[str, str],
    lock_path: Path,
    preferred_terminal: str = "auto",
) -> LaunchResult:
    ...
```

---

## 7.9 Unix terminal strategy

For Linux and macOS, do **not** rely on fragile inline shell strings.

Instead:

1. create a temporary run directory with permissions `0700`
2. write an environment file with permissions `0600`
3. write a runner script with permissions `0700`
4. launch the script in a terminal

---

## 7.10 Unix environment file

Example `env.sh`:

```bash
export IMMICH_GO_UPLOAD_SERVER='http://localhost:2283'
export IMMICH_GO_UPLOAD_API_KEY='secret'
```

### Rules
- file permissions must be `0600`
- use proper single-quote escaping
- delete after command finishes

---

## 7.11 Unix runner script

Example `run.sh`:

```bash
#!/usr/bin/env bash
set -a
source '/tmp/immich-go-gui-run-xyz/env.sh'
set +a

cleanup() {
  rm -f '/tmp/immich-go-gui-run-xyz/lockfile'
  rm -rf '/tmp/immich-go-gui-run-xyz'
}

trap cleanup EXIT INT TERM

/path/to/immich-go upload from-folder /photos
code=$?

trap - EXIT INT TERM
cleanup

echo
echo "immich-go exited with code $code"
exec bash
```

### Important
- The command line must be quoted safely.
- Secrets should be in `env.sh`, not in the visible command line.
- Cleanup must remove both lock and temp directory.

---

## 7.12 macOS launch method

Do not embed huge command strings directly into AppleScript.

Use `osascript` with arguments.

Recommended approach:

```python
subprocess.Popen([
    "osascript",
    "-e", "on run argv",
    "-e", "tell application \"Terminal\" to do script (item 1 of argv)",
    "-e", "end run",
    str(run_script_path),
])
```

This avoids AppleScript quoting bugs.

---

## 7.13 Linux terminal fallback order

Try in this order:

1. user-preferred terminal if configured
2. `x-terminal-emulator`
3. `gnome-terminal`
4. `konsole`
5. `xfce4-terminal`
6. `xterm`

### Suggested argument patterns
- `x-terminal-emulator -e /path/to/run.sh`
- `gnome-terminal -- /path/to/run.sh`
- `konsole -e /path/to/run.sh`
- `xfce4-terminal -e /path/to/run.sh`
- `xterm -hold -e /path/to/run.sh`

If none are found:
- clean up lock/temp
- return failure

---

## 7.14 Windows terminal strategy

Keep external console behavior.

### Recommended launch
Instead of nested `cmd /c start cmd /k ...`, prefer:

```python
subprocess.Popen(
    ["cmd", "/k", bat_path],
    creationflags=subprocess.CREATE_NEW_CONSOLE,
    env=env,
)
```

### Batch file content
The `.bat` file should contain:
- the command
- lock deletion
- final exit code display

Example:

```bat
@echo off
/path/to/immich-go.exe upload from-folder C:\photos
set ERR=%ERRORLEVEL%
del /f "C:\Temp\...\run.lock" 2>nul
echo.
echo immich-go exited with code %ERR%
```

### Important
- Do **not** write secrets into the `.bat` file.
- Pass secrets via environment to `Popen`.

---

## 7.15 Replace the old `ProcessTracker` in `app.py`

Remove the old inline `ProcessTracker` class from `app.py`.

Use:
- `core/process_tracker.py`
- `core/terminal_launcher.py`

---

## 7.16 Update `run_command()` in `app.py`

New flow:

1. Build `CommandPlan`
2. Create lock file
3. Call `launch_external_terminal()`
4. If launch fails:
   - release lock
   - show error
   - re-enable buttons
5. If launch succeeds:
   - store active lock path
   - start timer
   - disable Run / Dry Run
   - show running warning

---

## 7.17 Update timer logic

The timer should check:

```python
is_lock_active(self.active_lock_path)
```

When inactive:
- stop timer
- clear active lock
- re-enable buttons
- hide warning

---

## 7.18 Section 4 test requirements

Add tests for:

### Process tracker
- create lock
- read lock
- release lock
- scan locks
- stale lock cleanup on POSIX with mocked `os.kill`
- reset all locks

### Terminal launcher
Mock `subprocess.Popen`.

Test:
- Unix script creation
- env file permissions
- command does not contain secrets
- macOS launch command shape
- Linux fallback order
- Windows launch command shape
- failure path cleans up lock

---

# 8. Section 7 — Binary Management Improvements

## Goal
Make binary discovery, download, verification, and selection safer and more robust.

---

## 8.1 Important note
The agent must **test download URL logic while writing it**.

Do not assume asset naming is stable.

---

## 8.2 Update `core/binary_manager.py`

### Required new dataclasses

```python
from dataclasses import dataclass

@dataclass
class ReleaseAsset:
    name: str
    url: str
    size: int | None = None

@dataclass
class InstalledVersion:
    version: str
    path: str
    downloaded_at: str
    gui_tested: bool
    support_status: str
    sha256: str
    selected: bool = False

@dataclass
class InstallResult:
    ok: bool
    version: str = ""
    binary_path: str = ""
    sha256: str = ""
    checksum_verified: bool = False
    message: str = ""
```

---

## 8.3 Use GitHub release assets instead of hardcoded URL construction

### Current problem
Constructing URLs like:

```text
immich-go_{version}_{os}_{arch}.zip
```

is brittle.

### New behavior
Fetch release metadata and inspect `assets`.

Endpoints:
- latest:
  ```text
  https://api.github.com/repos/simulot/immich-go/releases/latest
  ```
- specific tag:
  ```text
  https://api.github.com/repos/simulot/immich-go/releases/tags/v{version}
  ```

### Required headers
Always send:

```python
{
    "Accept": "application/vnd.github+json",
    "User-Agent": "immich-go-gui",
}
```

If available, include token from environment:

- `IMMICH_GO_GUI_GITHUB_TOKEN`
- or optionally `GITHUB_TOKEN`

---

## 8.4 Asset selection logic

Implement:

```python
def select_asset_url(release_json: dict, os_name: str, arch: str) -> str | None:
    ...
```

### Matching rules
Normalize asset names and match by:

- OS tokens:
  - `windows`
  - `darwin`
  - `linux`
  - `freebsd`

- Arch tokens:
  - `x86_64`
  - `amd64`
  - `arm64`
  - `aarch64`
  - `i386`

- Extension:
  - `.zip` on Windows
  - `.tar.gz` or `.tgz` elsewhere

### Important
Support both naming styles:

- `immich-go_Windows_x86_64.zip`
- `immich-go_0.32.0_Windows_x86_64.zip`

Do not require version in the asset name.

### Fallback
If asset API lookup fails, you may fall back to constructed URL, but only as a fallback.

---

## 8.5 Add checksum support

### Behavior
When installing a version:

1. inspect release assets
2. look for checksum-like files:
   - `checksums.txt`
   - `sha256sums.txt`
   - anything containing `sha256`
3. if found:
   - download it
   - parse expected hash for selected archive
   - verify downloaded archive
4. if not found:
   - proceed
   - mark `checksum_verified = False`

### InstallResult must report
- whether checksum was verified
- computed SHA256
- final binary path

---

## 8.6 Download to file, not memory

Replace in-memory download with streaming to a temporary file.

### Required function

```python
def download_to_file(
    url: str,
    dest_path: Path,
    progress_cb=None,
    cancel_event=None,
    retries: int = 3,
) -> None:
    ...
```

### Requirements
- stream in chunks
- support progress callback
- support cancellation
- retry transient failures
- raise on final failure

---

## 8.7 Improve cancellation

Do **not** use `QThread.terminate()`.

Instead:

- worker has a cancel flag / event
- download loop checks it
- worker exits gracefully

---

## 8.8 Improve update evaluation logic

Update:

```python
def evaluate_update(...)
```

### Required behavior

#### Case 1: latest == current
Return:
- allowed = False
- message = already up to date

#### Case 2: latest < current
Return:
- allowed = False
- message = current is newer than latest release

#### Case 3: latest > current and tested
Return:
- allowed = True
- requires confirmation = True

#### Case 4: latest > current and untested
If `allow_untested` is False:
- block

If True:
- allow with strong confirmation

---

## 8.9 Add installed version management

Implement:

```python
def list_installed_versions() -> list[InstalledVersion]:
    ...

def delete_version(version: str) -> bool:
    ...
```

### Rules
- list all versions under binary base dir
- mark selected version
- prevent deleting selected version unless selection is cleared first
  - or automatically clear selection after delete and re-resolve binary path

---

## 8.10 Add post-install verification

After extraction:

1. run:
   ```bash
   binary version
   ```
2. parse output
3. compare against expected version
4. if mismatch, warn but do not necessarily fail hard

Use a longer timeout than 3 seconds.  
Recommended: 10 seconds.

---

## 8.11 macOS quarantine handling

After extracting on macOS, try:

```bash
xattr -d com.apple.quarantine /path/to/immich-go
```

Ignore errors if command fails.

---

## 8.12 Update binary UI in `app.py`

### Required changes

#### A. Replace download thread
Use a worker that:
- calls `BinaryManager.install_version(...)`
- emits progress
- emits success/failure
- supports cancel

#### B. Progress dialog
- show determinate progress if content-length known
- show indeterminate progress otherwise
- cancel must be graceful

#### C. Add “Manage Versions” button
Place it in the Binary Management card.

Dialog should show:
- version
- tested/untested status
- path
- short SHA
- selected marker

Actions:
- Select
- Delete
- Close

#### D. Add UI for untested updates
Add checkbox in Advanced Configuration:

```text
Allow untested immich-go updates
```

Persist it.

#### E. Debounce manual binary path checking
Do not run binary version check on every keystroke.

Use:
- `editingFinished`
- or a debounce timer

---

## 8.13 Section 7 test requirements

Add tests with mocked GitHub API and mocked downloads.

### Asset selection tests
Test matching for:
- Windows x86_64
- Darwin arm64
- Linux x86_64
- asset names with version
- asset names without version
- unknown arch fallback

### Update evaluation tests
- already latest
- current newer than latest
- tested update allowed
- untested update blocked
- untested update allowed when enabled
- breaking release notes increase caution

### Download tests
- retry after transient failure
- cancel stops download
- checksum verified when available
- checksum missing is reported correctly

### Installed versions tests
- list versions
- select version
- delete version
- delete selected version behavior

---

# 9. Final Integration Requirements

After implementing all sections, ensure the following are true.

---

## 9.1 `core/__init__.py`
Export the important public types and helpers cleanly.

At minimum, export:

- models
- profile manager helpers
- config helpers
- binary manager
- command builder
- validation helpers
- network test helper
- process tracker helpers
- terminal launcher helper

---

## 9.2 `app.py` should become thinner

Move as much logic as possible out of `app.py`.

`app.py` should mostly handle:
- widget construction
- signal wiring
- calling backend functions
- displaying results

It should **not** contain:
- process tracker implementation
- terminal launch implementation
- profile storage implementation
- binary download implementation
- validation implementation

---

## 9.3 Secrets hygiene checklist

Verify:

- API keys are not in `argv`
- admin keys are not in `argv`
- secret fields are excluded from saved form state
- secret values are not printed in logs
- temporary Unix env files are:
  - `0600`
  - deleted after run
- Windows batch files do not contain secrets

---

## 9.4 Profiles hygiene checklist

Verify:

- default profile always exists
- active profile persists across restarts
- switching profiles loads the correct config
- secrets are profile-scoped
- deleting a profile cleans up secrets
- renaming a profile updates secrets correctly
- form state is restored per profile

---

## 9.5 Process execution hygiene checklist

Verify:

- external terminal still opens
- lock file is created
- lock file is removed when command finishes
- stale locks can be cleaned
- manual reset works
- app close warns if a lock is active
- Linux/macOS/Windows launch paths are all handled

---

## 9.6 Binary management hygiene checklist

Verify:

- latest version check works
- asset URL selection works
- download can be cancelled
- checksum status is reported
- installed versions can be listed
- selected version can be changed
- update logic does not accidentally downgrade
- manual binary path is debounced

---

# 10. Suggested Test Plan

Use `pytest` and keep all tests offline.

---

## 10.1 Recommended new test files
If the project currently uses one big `test_app.py`, you may either:

- extend `test_app.py`, or
- create focused test files

Recommended files:

- `tests/test_validation.py`
- `tests/test_network.py`
- `tests/test_profile_manager.py`
- `tests/test_config_manager.py`
- `tests/test_process_tracker.py`
- `tests/test_terminal_launcher.py`
- `tests/test_binary_manager.py`

If the repo currently expects only `test_app.py`, then add the tests there in clearly separated sections.

---

## 10.2 Minimum test coverage by area

### Validation
- date parsing
- extension normalization
- list normalization
- path warnings
- destination-inside-source warning

### Network
- success
- unauthorized
- connection error
- SSL error

### Profiles
- create
- rename
- duplicate
- delete
- active profile persistence
- migration from single config

### Secrets
- keyring success
- keyring failure fallback
- no secret loss during migration
- admin key storage

### Process tracking
- lock lifecycle
- stale detection
- reset

### Terminal launching
- script creation
- platform launch shape
- no secrets in command string
- cleanup on failure

### Binary management
- asset matching
- update evaluation
- download retry/cancel
- checksum verification
- installed version management

---

# 11. UI/UX Requirements

## 11.1 Configuration page
Must include:

- Server URL
- API Key
- Skip SSL
- Test Connection button
- Security card
  - secret provider
  - admin API key
- Binary Management card
  - Check for Updates
  - Manage Versions
  - Manual Binary Path
- Appearance card
  - theme selector
- Advanced card
  - client timeout
  - concurrent tasks
  - device UUID
  - on errors
  - pause jobs
  - allow untested updates
  - preferred terminal

---

## 11.2 Menu bar
Must include:

- File
- Profiles
- Help

### File menu
Add:
- Reset Run State

### Profiles menu
Add:
- New Profile…
- Duplicate Active Profile…
- Rename Active Profile…
- Delete Active Profile…
- separator
- profile list

---

## 11.3 Window title
Show active profile:

```text
Immich Go GUI — default
```

---

# 12. Common Mistakes the Agent Must Avoid

## 12.1 Do not add `--no-ui` as the main execution path
This is explicitly unwanted.

## 12.2 Do not store secrets in form state
This is a major security mistake.

## 12.3 Do not delete old secrets before confirming new storage succeeded
This can cause secret loss.

## 12.4 Do not hardcode GitHub asset filenames as the only strategy
Use release asset metadata.

## 12.5 Do not use `QThread.terminate()`
Use cooperative cancellation.

## 12.6 Do not leave process tracking logic inside `app.py`
Move it to `core/process_tracker.py`.

## 12.7 Do not leave terminal launch logic inside `app.py`
Move it to `core/terminal_launcher.py`.

## 12.8 Do not break existing `core/` boundaries
Qt-free backend modules must stay Qt-free.

## 12.9 Do not ignore stale locks
Provide cleanup and manual reset.

## 12.10 Do not forget to update tests after refactor
Every behavior change needs test coverage.

---

# 13. Definition of Done

This work is complete when all of the following are true:

## Functionality
- External terminal execution is preserved
- Lock files are robust and recoverable
- Profiles work end-to-end
- Secrets are profile-aware and fallback-safe
- Admin API key support exists
- Validation is stronger and normalized
- Connection testing works
- Binary downloads use release assets
- Update logic prevents accidental downgrade
- Installed versions can be managed

## Code quality
- New backend logic lives in `core/`
- `app.py` is thinner
- No secrets in argv/logs/form state
- No silent secret loss
- No fragile terminal string escaping where avoidable

## Tests
- All old tests pass
- New tests cover all major new behavior
- No test requires real network access

## Manual verification
- GUI starts
- Profiles can be created/switched/deleted
- Run command opens terminal
- Lock state recovers after restart
- Binary update flow works with mocked or real manual verification
- Connection test works

---

# 14. Recommended Commit Sequence

If the agent is working in version control, use this commit sequence:

1. `Add validation and network helpers`
2. `Integrate stronger validation into command builder and UI`
3. `Make secret storage profile-aware and failure-aware`
4. `Add profile manager and profile-scoped config storage`
5. `Add profile UI and form-state persistence`
6. `Add process tracker and terminal launcher modules`
7. `Integrate hardened external terminal execution`
8. `Improve binary manager asset discovery and install flow`
9. `Add binary version management UI`
10. `Expand test coverage and finalize docs`

---

# 15. Final Note to the Agent

The most important design principles are:

1. **Do not change the external terminal behavior.**
2. **Do not lose user secrets.**
3. **Do not hardcode fragile behavior when a robust API-driven approach is possible.**
4. **Keep backend logic in `core/`.**
5. **Make every new behavior testable offline.**

If a choice is unclear, prefer:
- safety over convenience
- explicit recovery over silent failure
- profile-scoped isolation over global state
- robust fallbacks over brittle assumptions

---
