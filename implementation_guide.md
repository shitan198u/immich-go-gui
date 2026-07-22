Yes — I understand the current state.

I’m assuming by **“Section 3”** you mean **Section 3 from my original critique**:  
**CLI correctness and compatibility**.

That is the right section to focus on next, because it is the area most likely to cause real runtime failures:

- emitting flags that a given `immich-go` subcommand does not support
- missing required flags
- using global flags in the wrong place
- wrong environment-variable names
- accidental interference from an `immich-go.toml` file in the working directory
- UI options that generate invalid CLI arguments

Below is:

1. a **verification review** of the milestones you just completed  
2. a **detailed AI-agent implementation guide for Section 3**

---

# Part A — Verification Review of Milestones 1–4

Based on your summary, the work **appears directionally correct** and aligned with the guidelines.

However, since I cannot see the final changed code directly, I can only verify this at the **architectural / reported implementation** level, not line-by-line.

## A.1 Overall verdict

### Likely done correctly
- Section 8: validation and network helpers introduced
- Section 6: secret storage made profile-aware and failure-aware
- Section 5: profiles and form-state persistence added
- Section 4: process tracker and terminal launcher modularized

The commit sequence also looks clean and sensible:

```text
dfe1123 Add validation and network helpers
7dac6d2 Integrate stronger validation into command builder and UI
2c1ef68 Make secret storage profile-aware and failure-aware
f0ea601 Add profile manager and profile-scoped config storage
417c567 Add profile UI and form-state persistence
ce24127 Add process tracker and terminal launcher modules
6d0a7af Integrate process tracking and terminal launcher into app UI
```

And the test result is a very good sign:

```text
73 passed in 0.65s
```

---

## A.2 Important discrepancy

You wrote:

> All five implementation milestones ... have been successfully completed

But the walkthrough only lists **four** implemented milestones:

1. Section 8
2. Section 6
3. Section 5
4. Section 4

### Missing from the list
- **Section 7: Binary management improvements**

So unless Section 7 was completed elsewhere and not listed, the statement should be:

> All four currently targeted milestones have been completed.

This matters because Section 3 will interact with binary resolution and CLI help capture, so we need to be clear whether Section 7 is already in place.

---

## A.3 Milestone-by-milestone verification checklist

Use this as a quick audit to confirm the implementation truly matches the guidelines.

---

# Milestone 1 — Section 8: Validation and Input Quality

## What should now be true
The following should exist:

- `core/validation.py`
- `core/network.py`

And `core/command_builder.py` should use:

- `clean_date_range()`
- `normalize_extensions_csv()`
- `normalize_list_csv()`

Also:
- destructive mode warnings should be present
- Configuration page should have a **Test Connection** button

## What to verify manually

### 1. Date validation is semantic, not just regex
Check that invalid dates are rejected:

- `2023-13`
- `2023-02-30`
- `2024-00-10`

And that this is accepted:

- `2023-01-01, 2023-12-31`

### 2. Extension normalization is actually used
If user enters:

```text
JPG, .png, heic
```

the generated command should use:

```text
.jpg,.png,.heic
```

### 3. Warnings appear in confirm dialog
For:
- `KeepRaw`
- `KeepJPG`
- `KeepHeic`
- `StackKeepJPEG`

and ideally:
- `StackKeepRaw`

### 4. Test Connection does not leak API key
The result message must never include the API key.

## Red flags
- date validation still regex-only
- extension normalization defined but not used in command builder
- warnings only in validation result but not shown in confirm dialog
- Test Connection prints secrets in error text

---

# Milestone 2 — Section 6: Security and Secret Management

## What should now be true
- secrets are profile-scoped
- keyring entries use a profile prefix
- migration does not delete old secrets unless new storage succeeded
- fallback to local secrets file works
- admin API key support exists via environment only

## What to verify manually

### 1. Keyring names are profile-scoped
For default profile, expected style:

```text
default:api_key
default:admin_api_key
```

For another profile:

```text
work:api_key
work:admin_api_key
```

### 2. No secrets in argv
Search generated plans and command previews for:

- `--api-key=`
- `--from-api-key=`
- `--admin-api-key=`
- `--from-admin-api-key=`

They should **not** appear in `argv`.

### 3. No secrets in saved form state
Inspect saved profile `config.toml` and confirm `form_state` does **not** contain:

- `api_key`
- `from-api-key`
- `admin_api_key`
- any other secret field

### 4. Migration is non-destructive
If keyring write fails, old secret must not be removed.

## Red flags
- old QSettings key removed even if new storage failed
- admin API key visible in command preview
- secrets saved into `form_state`
- fallback to file happens silently with no user-visible indication

---

# Milestone 3 — Section 5: Profiles and Form-State Persistence

## What should now be true
- profile storage uses:
  ```text
  profiles.toml
  profiles/<name>/config.toml
  profiles/<name>/secrets.toml
  ```
- default profile always exists
- active profile persists across restarts
- profile switching prompts before discarding changes
- window title shows active profile
- form state is saved/restored per profile

## What to verify manually

### 1. First-run migration
If an old single-profile config existed, it should now be under:

```text
profiles/default/config.toml
```

### 2. Profile operations
Confirm:
- create works
- rename works
- duplicate works
- delete works
- default cannot be deleted
- active profile switches correctly

### 3. Secrets remain isolated per profile
If profile A has an API key and profile B does not, switching to B should not show A’s key.

### 4. Form state restoration
After restart:
- text fields restore
- checkboxes restore
- combo boxes restore
- spin boxes restore

But secrets should restore only through secret storage, not `form_state`.

## Red flags
- profile rename does not rename keyring entries
- delete profile leaves keyring secrets behind
- switching profiles silently overwrites current profile
- form state includes secrets
- active profile not persisted

---

# Milestone 4 — Section 4: Process Execution and Run Tracking

## What should now be true
- old inline `ProcessTracker` removed from `app.py`
- new modules exist:
  - `core/process_tracker.py`
  - `core/terminal_launcher.py`
- external terminal launch remains the default
- lock tracking is more robust
- stale lock cleanup exists
- `File → Reset Run State` exists
- `closeEvent` warns if a command is still running

## What to verify manually

### 1. External terminal still opens
This is a hard requirement.

The app must **not** have switched to embedded `--no-ui` execution.

### 2. Lock lifecycle works
- lock created on run
- lock removed when terminal command finishes
- GUI re-enables buttons after lock disappears

### 3. Stale lock handling
If a stale lock exists:
- startup cleanup should remove it if safe
- or manual reset should clear it

### 4. Temporary scripts are secure
On Unix-like systems:
- temp run directory should be `0700`
- env file should be `0600`
- secrets should not be embedded into visible command strings

### 5. Windows batch file does not contain secrets
The `.bat` file should contain the command, but not API keys.

## Red flags
- any use of `--no-ui` as primary execution path
- secrets written into `.bat`, AppleScript, or inline shell strings
- use of `QThread.terminate()`
- no close warning when lock active
- no manual reset action
- Linux terminal launching still uses fragile inline command strings only

---

## A.4 My verification conclusion

### Based on your summary:
**The implementation appears broadly correct and aligned with the guidelines.**

### But before starting Section 3, I strongly recommend confirming these five high-risk items:
1. no secrets in `form_state`
2. no secrets in terminal launch scripts
3. no `--no-ui` execution path introduced
4. profile-scoped secret migration is non-destructive
5. validation helpers are actually wired into command building

If those five are clean, you are in a good position to begin Section 3.

---

# Part B — AI Agent Implementation Guide  
# Section 3: CLI Correctness and Compatibility

This is the detailed handoff guide for an AI agent.

---

# 1. Purpose of This Section

The goal of Section 3 is to make the GUI **CLI-correct by construction**.

The GUI must not be able to silently generate invalid `immich-go` commands.

This section is about preventing bugs like:

- sending `--client-timeout` to a subcommand that does not support it
- sending `--include-type` to a subcommand where it may be invalid
- missing required source/destination flags
- using wrong environment-variable names
- accidental ingestion of a user’s local `immich-go.toml`
- flag drift between GUI code and actual `immich-go` releases

---

# 2. Scope

## In scope
- audit and correct all existing tabs:
  - `upload-folder`
  - `upload-gp`
  - `upload-immich`
  - `archive-folder`
  - `archive-immich`
  - `stack`
- introduce a CLI compatibility / contract-testing system
- introduce a schema-driven or allowlist-driven flag emission system
- add missing high-priority flags for existing tabs
- add golden command tests
- isolate execution from stray `immich-go.toml` files
- add optional runtime CLI compatibility checking

## Out of scope for now
Do **not** implement these yet unless explicitly instructed:

- new source tabs:
  - `from-icloud`
  - `from-picasa`
  - `archive from-google-photos`
- full embedded log viewer
- binary management improvements from Section 7
- internationalization
- major visual redesign

---

# 3. Non-Negotiable Rules

The agent must obey all of the following:

## 3.1 Preserve external terminal execution
- Do **not** introduce `--no-ui` as the default run path.
- Do **not** replace external terminal execution with an embedded runner.

## 3.2 Preserve secret handling
- API keys must remain out of `argv`.
- Admin API keys must remain out of `argv`.
- Secrets must only be passed through environment variables or secure temporary files with strict permissions.

## 3.3 Preserve `core/` architecture
- No new backend logic in `app.py` if it can live in `core/`.
- `core/` modules must remain Qt-free unless absolutely unavoidable.

## 3.4 Do not guess CLI compatibility
- If a flag’s validity is uncertain, verify against:
  - captured `--help`
  - the official CLI documentation
  - a real binary dry-run/help output

## 3.5 Prefer failing safely over emitting invalid commands
- If the GUI cannot determine that a flag is valid for a tab, it must not emit it.
- In tests, invalid emission should fail loudly.

---

# 4. Current High-Risk Areas to Fix First

Before adding many new features, the agent must audit these known risk areas.

## 4.1 Possibly invalid flag emission
These must be verified immediately:

### `archive-folder`
- `--client-timeout` may be invalid for local archive operations

### `upload-gp`
- `--include-type` may be invalid for Google Photos import
- `--into-album` may be invalid for Google Photos import

### `upload-folder`
- missing `--recursive`
- missing `--album-path-joiner`
- missing `--album-picasa`
- missing `--manage-epson-fastfoto`

### `upload-gp`
- missing `--manage-raw-jpeg`
- missing `--include-untitled-albums`
- possibly missing `--date-range`

### `upload-immich`
- missing many `--from-*` filters

### `archive-immich`
- missing many `--from-*` filters

### `stack`
- verify `--client-timeout`
- verify `--admin-api-key` environment naming
- verify whether pause-job behavior is applicable

---

# 5. Target Architecture for Section 3

Create or extend these modules:

## New modules
- `core/cli_help.py`
- `core/cli_contract.py`

## Extended modules
- `core/cli_schema.py`
- `core/command_builder.py`
- `core/models.py`
- `app.py`

## New scripts
- `scripts/capture_cli_help.py`

## New test assets
- `tests/fixtures/cli_help/<version>/...`
- `tests/fixtures/command_states/...`
- `tests/golden/...`

---

# 6. Phase 1 — Capture CLI Help and Build a Contract System

## 6.1 Goal
Create a reliable source of truth for which flags exist on each `immich-go` command/subcommand.

---

## 6.2 Create `scripts/capture_cli_help.py`

This script must:

1. resolve the active `immich-go` binary path
2. run `--help` for relevant commands
3. write output into versioned fixture files

### Required help targets
At minimum:

```text
--help
upload --help
upload from-folder --help
upload from-google-photos --help
upload from-immich --help
archive --help
archive from-folder --help
archive from-immich --help
stack --help
```

### Recommended output layout
```text
tests/fixtures/cli_help/0.32.0/root.txt
tests/fixtures/cli_help/0.32.0/upload.txt
tests/fixtures/cli_help/0.32.0/upload_from-folder.txt
tests/fixtures/cli_help/0.32.0/upload_from-google-photos.txt
tests/fixtures/cli_help/0.32.0/upload_from-immich.txt
tests/fixtures/cli_help/0.32.0/archive.txt
tests/fixtures/cli_help/0.32.0/archive_from-folder.txt
tests/fixtures/cli_help/0.32.0/archive_from-immich.txt
tests/fixtures/cli_help/0.32.0/stack.txt
tests/fixtures/cli_help/0.32.0/manifest.json
```

### `manifest.json` should contain
```json
{
  "version": "0.32.0",
  "captured_at": "2026-07-23T00:00:00Z",
  "binary_path": "/home/user/.immich-go-gui/bin/0.32.0/immich-go",
  "commands": {
    "upload-folder": ["upload", "from-folder"]
  }
}
```

### Important
- The script must not require Qt.
- It may import `core.binary_manager` if useful.
- It must support an explicit binary path argument.

---

## 6.3 Create `core/cli_help.py`

This module parses help text and extracts flag names.

### Required functions

```python
def parse_help_flags(help_text: str) -> set[str]:
    """
    Extract flag names from --help output.
    Returns names without leading dashes.
    Example: 'recursive', 'include-type', 'from-date-range'
    """

def load_help_fixture(version: str, help_name: str) -> set[str]:
    """
    Load captured help fixture for a given version and help target.
    """

def help_name_for_tab(tab_key: str) -> str:
    """
    Map GUI tab key to fixture name.
    Example:
      'upload-folder' -> 'upload_from-folder'
    """
```

### Parser requirements
Must recognize:
- `--recursive`
- `--include-type`
- `--from-date-range`
- `-s, --server`
- boolean flags
- flags with defaults

Must ignore:
- `--help`

---

# 7. Phase 2 — Create a Flag Registry / Allowlist System

## 7.1 Goal
Move away from “emit flags manually and hope they are valid”.

Instead, define an explicit allowlist of valid flags per tab.

---

## 7.2 Extend `core/cli_schema.py`

Add a schema-like registry.

### Recommended data structures

```python
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
    name: str                 # flag name without --
    kind: FlagKind
    scope: Literal["global", "command", "subcommand"]
    default: Any = None
    secret: bool = False
    emit_in_argv: bool = True
    env_name: str | None = None
    notes: str = ""
```

Then define:

```python
FLAG_DEFS: dict[str, FlagDef] = {
    "server": FlagDef(name="server", kind="str", scope="command"),
    "api-key": FlagDef(name="api-key", kind="str", scope="command", secret=True, emit_in_argv=False),
    ...
}
```

And:

```python
TAB_ALLOWED_FLAGS: dict[str, frozenset[str]] = {
    "upload-folder": frozenset({
        "server",
        "skip-verify-ssl",
        "client-timeout",
        "dry-run",
        "concurrent-tasks",
        "overwrite",
        "pause-immich-jobs",
        "on-errors",
        "session-tag",
        "tag",
        "device-uuid",
        "api-trace",
        "log-level",
        "recursive",
        "date-from-name",
        "ignore-sidecar-files",
        "include-extensions",
        "exclude-extensions",
        "include-type",
        "ban-file",
        "date-range",
        "folder-as-album",
        "folder-as-tags",
        "album-path-joiner",
        "album-picasa",
        "into-album",
        "manage-burst",
        "manage-raw-jpeg",
        "manage-heic-jpeg",
        "manage-epson-fastfoto",
    }),
    ...
}
```

---

## 7.3 Add helper functions

```python
def flag_allowed_for_tab(tab_key: str, flag_name: str) -> bool:
    ...

def assert_flag_allowed(tab_key: str, flag_name: str) -> None:
    ...
```

### Behavior
- In tests, `assert_flag_allowed()` should raise on violation.
- In production command building, violation should become a clear internal error, not silent emission.

---

# 8. Phase 3 — Add Contract Tests

## 8.1 Goal
Ensure every flag the GUI can emit is actually valid for that tab.

---

## 8.2 Required tests

### Test 1: Registry flags exist in help fixtures
For each tab:
- for each flag in `TAB_ALLOWED_FLAGS[tab]`
- assert flag exists in parsed help fixture for that tab

### Test 2: Builder-emitted flags are allowed
For representative states:
- build command plan
- extract emitted flags
- assert each emitted flag is allowed for that tab

### Test 3: No secret flags in argv
For all tabs:
- assert `argv` does not contain:
  - `--api-key`
  - `--from-api-key`
  - `--admin-api-key`
  - `--from-admin-api-key`

### Test 4: Environment names match expected pattern
For each secret-bearing environment variable:
- assert it matches the documented pattern:
  ```text
  IMMICH_GO_<COMMAND>[_<SUBCOMMAND>]_<OPTION_NAME>
  ```

### Test 5: Golden command tests
For saved state fixtures:
- build plan
- compare against expected `argv`
- compare against expected secret env keys

---

## 8.3 Recommended test file layout
If keeping everything in `test_app.py`, add clearly separated sections.

Otherwise create:

```text
tests/test_cli_help.py
tests/test_cli_contract.py
tests/test_command_golden.py
```

---

# 9. Phase 4 — Refactor Command Builder to Use Allowlists

## 9.1 Goal
Make `core/command_builder.py` enforce correctness internally.

---

## 9.2 Introduce an emitter helper

Recommended internal helper:

```python
class FlagEmitter:
    def __init__(self, tab_key: str, strict: bool = True):
        self.tab_key = tab_key
        self.strict = strict
        self.opts: list[str] = []
        self.errors: list[str] = []

    def add_value(self, flag: str, value: str) -> None:
        ...

    def add_bool(self, flag: str, value: bool, default: bool = False) -> None:
        ...

    def add_bool_true_only(self, flag: str, value: bool) -> None:
        ...

    def add_bool_false_if_disabled(self, flag: str, value: bool, default: bool = True) -> None:
        ...

    def add_repeat_from_csv(self, flag: str, csv_value: str, normalize=None) -> None:
        ...

    def add_repeat_from_lines(self, flag: str, text_value: str) -> None:
        ...
```

### Rules
- every method checks `flag_allowed_for_tab()`
- if not allowed:
  - in strict mode raise or record error
  - never silently append

---

## 9.3 Preserve public API
Do **not** break:

```python
build_plan_from_state(...)
```

It must continue returning `CommandPlan`.

Only refactor internals.

---

# 10. Phase 5 — Fix Known Flag Correctness Issues

This is the most important implementation phase.

---

## 10.1 Global rules for flag emission

### A. Server flags
- `--server` should be emitted only for server-required tabs
- `archive-folder` must not receive `--server`

### B. Client timeout
- emit `--client-timeout` only if help fixture confirms support for that tab
- likely remove from `archive-folder`

### C. API trace
- emit `--api-trace` only where supported

### D. Boolean defaults
Only emit boolean flags when they differ from CLI defaults, unless explicit clarity is needed.

Examples:
- if default is true and user disables it → emit `--flag=false`
- if default is false and user enables it → emit `--flag=true`

---

## 10.2 Tab-specific corrections

### `upload-folder`
Must support:
- `--recursive`
- `--album-path-joiner`
- `--album-picasa`
- `--manage-epson-fastfoto`

Recommended emission rules:
- `recursive` default true  
  - if unchecked → `--recursive=false`
- `album-path-joiner`
  - emit only if non-empty
- `album-picasa`
  - emit only if checked
- `manage-epson-fastfoto`
  - emit only if checked

---

### `upload-gp`
Must verify and then either keep or remove:
- `--include-type`
- `--into-album`

Must add if supported:
- `--manage-raw-jpeg`
- `--include-untitled-albums`
- `--date-range`

Recommended emission rules:
- `manage-raw-jpeg`
  - emit if not `NoStack`
- `include-untitled-albums`
  - emit if checked
- `date-range`
  - emit if non-empty after `clean_date_range()`

---

### `upload-immich`
Add missing source filters if supported:

- `--from-include-type`
- `--from-include-extensions`
- `--from-exclude-extensions`
- `--from-partners`
- `--from-time-zone`
- `--from-no-album`
- `--from-device-uuid`
- `--from-api-trace`
- `--from-dry-run`
- `--from-pause-immich-jobs`

Also support source admin key via environment only:
- `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY`

Do **not** add `--from-admin-api-key` to argv.

---

### `archive-folder`
Verify and add filtering options if supported:

- `--include-type`
- `--include-extensions`
- `--exclude-extensions`
- `--ban-file`
- `--ignore-sidecar-files`
- `--date-from-name`
- possibly `--recursive`

Important:
- remove `--client-timeout` unless confirmed valid

---

### `archive-immich`
Add missing `from-immich` filters if supported:

- `--from-favorite`
- `--from-archived`
- `--from-trash`
- `--from-minimal-rating`
- `--from-people`
- `--from-tags`
- `--from-city`
- `--from-state`
- `--from-country`
- `--from-make`
- `--from-model`
- `--from-include-type`
- `--from-include-extensions`
- `--from-exclude-extensions`
- `--from-partners`
- `--from-time-zone`
- `--from-no-album`

---

### `stack`
Verify:
- `--client-timeout`
- `--admin-api-key` environment support
- whether any pause-job flag is valid

Do not add unsupported flags.

---

# 11. Phase 6 — Isolate Execution from User `immich-go` Config Files

This is a subtle but major bug source.

## 11.1 Problem
`immich-go` may read a local config file from the current working directory.

If the external terminal starts in a directory containing:

```text
immich-go.toml
immich-go.yaml
immich-go.json
```

then the executed command may inherit unexpected settings.

---

## 11.2 Required behavior
The GUI must ensure that launched commands run in an isolated working directory.

### Preferred implementation
In `core/terminal_launcher.py`:

#### Unix runner script
Add:

```bash
cd "$RUN_DIR"
```

before executing `immich-go`.

#### Windows batch file
Add:

```bat
cd /d "%~dp0"
```

before executing the binary.

---

## 11.3 Optional stronger isolation
If contract/live testing confirms it is safe, also add:

```text
--config=<empty-generated-config>
```

But do **not** do this blindly.

### Recommended order
1. first implement working-directory isolation
2. only add explicit `--config` after verifying with real binary help/dry-run

---

# 12. Phase 7 — Add Runtime CLI Compatibility Checker

This is optional but highly recommended.

---

## 12.1 Create `core/cli_contract.py`

### Required dataclass

```python
from dataclasses import dataclass, field

@dataclass
class CompatibilityReport:
    ok: bool
    version: str = ""
    missing_flags: dict[str, list[str]] = field(default_factory=dict)
    unknown_emitted_flags: dict[str, list[str]] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
```

### Required functions

```python
def check_binary_help(
    binary_path: str,
    version: str | None = None,
) -> CompatibilityReport:
    """
    Run --help against the binary and compare with GUI flag registry.
    """

def check_fixtures(version: str) -> CompatibilityReport:
    """
    Compare GUI registry against captured fixtures for a version.
    """
```

---

## 12.2 Add UI entry point
Add a menu item:

```text
Help → Check CLI Compatibility
```

Behavior:
- run check against current binary if available
- otherwise use fixtures for tested version
- show report dialog

Report should include:
- checked version
- any missing flags
- any GUI-emitted flags not present in help
- overall pass/fail

---

# 13. Phase 8 — Golden Command Test Fixtures

## 13.1 Create state fixtures
Create JSON state fixtures for each tab.

Example:

```text
tests/fixtures/command_states/upload_folder_simple.json
tests/fixtures/command_states/upload_folder_advanced.json
tests/fixtures/command_states/upload_gp_simple.json
tests/fixtures/command_states/upload_gp_advanced.json
tests/fixtures/command_states/upload_immich_advanced.json
tests/fixtures/command_states/archive_folder_simple.json
tests/fixtures/command_states/archive_immich_advanced.json
tests/fixtures/command_states_stack_simple.json
```

Each fixture should contain:

```json
{
  "tab_key": "upload-folder",
  "dry_run": false,
  "config_state": {
    "server": "http://localhost:2283",
    "api_key": "dummy",
    "skip-ssl": false,
    "client_timeout": 20,
    "concurrent": 8,
    "concurrent_default": 8,
    "device_uuid": "",
    "on_errors": "stop",
    "on_errors_tolerance": 10,
    "pause_jobs": true
  },
  "tab_state": {
    "path": "/photos",
    "include-type": "all",
    "folder-album": "NONE",
    "into-album": "",
    "manage-burst": "NoStack",
    "manage-raw-jpeg": "NoStack",
    "manage-heic-jpeg": "NoStack"
  }
}
```

---

## 13.2 Create expected outputs
For each fixture, store expected:

- `argv`
- secret env key names
- warnings

Do not store actual secret values.

---

## 13.3 Golden test behavior
For each fixture:
1. load state
2. call `build_plan_from_state()`
3. compare:
   - `plan.argv`
   - sorted secret env keys
   - warnings

---

# 14. UI Changes Required for Section 3

The agent must update the UI only where needed to support corrected/added CLI flags.

---

## 14.1 `upload-folder`
Add to Advanced Options:

- `Recursive` checkbox
- `Album Path Joiner` text field
- `Use Picasa Album Names` checkbox
- `Manage Epson FastFoto` checkbox

---

## 14.2 `upload-gp`
Add:

- `RAW + JPEG Pairs` combo
- `Include Untitled Albums` checkbox
- `Date Range` text field

Then verify:
- whether `Media Type` should remain
- whether `Put all into Album` should remain

If contract testing shows those flags are invalid for `from-google-photos`, remove or hide them.

---

## 14.3 `upload-immich`
Add advanced source-filter fields:

- Source Include Type
- Source Include Extensions
- Source Exclude Extensions
- Include Partners
- Time Zone Override
- No Album Only
- Source Device UUID
- Source API Trace
- Source Dry Run
- Source Pause Jobs

If source admin key support is desired:
- add an optional secret field
- store via secret manager
- pass via environment only

---

## 14.4 `archive-folder`
Add advanced filtering fields:

- Media Type
- Include Extensions
- Exclude Extensions
- Ban File Patterns
- Ignore Sidecar Files
- Guess Dates From Filenames
- Recursive (if confirmed valid)

---

## 14.5 `archive-immich`
Add advanced source-filter fields:

- Only Favorites
- Include Archived
- Include Trashed
- Minimum Rating
- Filter by People
- Filter by Tags
- City / State / Country
- Camera Make / Model
- Include Type
- Include Extensions
- Exclude Extensions
- Include Partners
- Time Zone Override
- No Album Only

---

## 14.6 `stack`
No major new fields required immediately, except:
- verify admin key handling
- verify timeout handling

---

# 15. Required Updates to `core/command_builder.py`

The agent must ensure:

## 15.1 All date fields are cleaned
Use:

```python
clean_date_range()
```

for:
- `date-range`
- `from-date-range`

---

## 15.2 All extension fields are normalized
Use:

```python
normalize_extensions_csv()
```

for:
- `include-extensions`
- `exclude-extensions`
- `from-include-extensions`
- `from-exclude-extensions`

---

## 15.3 All comma-separated repeat fields are normalized
Use:

```python
normalize_list_csv()
```

for:
- tags
- albums
- people
- other repeatable text filters

---

## 15.4 Repeatable flags remain repeatable
Use multiple flag instances:

```text
--tag=A --tag=B
--from-albums=X --from-albums=Y
```

Do not collapse repeatable flags into one comma-joined flag unless CLI explicitly supports that form.

---

# 16. Required Updates to `core/cli_schema.py`

The agent must:

1. define `FLAG_DEFS`
2. define `TAB_ALLOWED_FLAGS`
3. update `ENV_KEY_MAP` for admin keys if not already complete
4. add secret flag definitions for:
   - `--admin-api-key`
   - `--from-admin-api-key`

---

# 17. Required Updates to Tests

The agent must add tests for:

## 17.1 Help parsing
- parse flags from sample help text
- ignore `--help`
- handle shorthand + longhand lines

## 17.2 Contract tests
- allowed flags exist in fixtures
- emitted flags are allowed
- no unsupported flags emitted

## 17.3 Golden tests
- simple and advanced state per tab
- dry-run on/off
- warnings present for destructive modes

## 17.4 Config isolation tests
- terminal launcher script changes into isolated directory
- Windows batch includes `cd /d "%~dp0"`

## 17.5 Secret hygiene tests
- no secret flags in argv
- no secret values in golden outputs
- admin key only in env

---

# 18. Suggested Implementation Order

The agent should follow this exact order:

## Step 1
Create:
- `scripts/capture_cli_help.py`
- `core/cli_help.py`

Capture fixtures for tested version.

## Step 2
Extend:
- `core/cli_schema.py`

Add:
- `FLAG_DEFS`
- `TAB_ALLOWED_FLAGS`

## Step 3
Add contract tests using fixtures.

## Step 4
Refactor `core/command_builder.py` to use allowlist/emitter internally.

## Step 5
Fix known invalid/missing flags for existing tabs.

## Step 6
Add golden command tests.

## Step 7
Implement working-directory isolation in terminal launcher.

## Step 8
Add optional runtime compatibility checker and Help menu action.

---

# 19. Definition of Done for Section 3

Section 3 is complete when all of the following are true:

## Correctness
- Every flag emitted by the GUI is allowed for that tab.
- Every allowed flag is confirmed by help fixture or live help.
- Known questionable flags have been verified or removed.
- Missing high-priority flags for existing tabs have been added.
- Date/extension/list normalization is consistently used.
- Execution is isolated from stray `immich-go` config files.

## Safety
- No secrets in argv.
- No secrets in golden test outputs.
- Admin keys only passed via environment.
- External terminal execution preserved.

## Tests
- Contract tests pass.
- Golden tests pass.
- Help parser tests pass.
- Existing test suite still passes.

## UI
- New fields exist for newly supported flags.
- Invalid/unsupported fields are removed or hidden.
- Compatibility checker is available in Help menu.

---

# 20. Common Mistakes the Agent Must Avoid

## 20.1 Do not add flags because they “probably exist”
Verify first.

## 20.2 Do not remove UI fields blindly
If a flag appears unsupported:
- verify against fixtures/live help
- then disable emission or remove UI field

## 20.3 Do not break secret handling
Never move API keys into argv.

## 20.4 Do not reintroduce `--no-ui`
This is explicitly unwanted.

## 20.5 Do not put backend logic in `app.py`
Keep it in `core/`.

## 20.6 Do not assume one flag set works for all subcommands
`upload`, `archive`, and `stack` are not identical in flag support.

## 20.7 Do not forget working-directory isolation
This is a subtle but serious bug source.

---

# 21. Paste-Ready Agent Prompt

You can hand the following prompt to the implementation agent:

---

## Agent Prompt

You are working on the Immich-Go GUI project after the `core/` refactor.

Your task is to implement **Section 3: CLI Correctness and Compatibility**.

### Hard constraints
- Do not introduce `--no-ui` execution.
- Do not replace external terminal launching.
- Do not put API keys or admin keys in `argv`.
- Keep backend logic in `core/`.
- Keep `core/` modules Qt-free where possible.
- Do not guess CLI flag compatibility. Verify against captured `--help` fixtures or live binary help.
- Preserve existing public APIs unless explicitly refactoring internally.

### Tasks
1. Create `scripts/capture_cli_help.py` to capture `immich-go --help` output for all relevant commands into versioned fixtures.
2. Create `core/cli_help.py` to parse help output and extract flag names.
3. Extend `core/cli_schema.py` with:
   - `FLAG_DEFS`
   - `TAB_ALLOWED_FLAGS`
   - helper functions for flag allowance checks
4. Add contract tests that verify:
   - every allowed flag exists in help fixtures
   - every emitted flag is allowed for its tab
   - no secret flags appear in argv
5. Refactor `core/command_builder.py` to use an internal allowlist-driven emitter.
6. Fix known flag correctness issues:
   - verify/remove unsupported flags
   - add missing high-priority flags for existing tabs
   - normalize dates, extensions, and list fields consistently
7. Add golden command tests for simple and advanced states for each existing tab.
8. Ensure launched commands run in an isolated working directory so stray `immich-go.toml` files are not picked up.
9. Add `core/cli_contract.py` and a Help menu action to check CLI compatibility at runtime.

### Existing tabs to support
- upload-folder
- upload-gp
- upload-immich
- archive-folder
- archive-immich
- stack

### Out of scope
- new source tabs (`from-icloud`, `from-picasa`, etc.)
- binary management improvements
- embedded log viewer
- internationalization

### Acceptance criteria
- all current tests pass
- new contract tests pass
- golden tests pass
- no secrets in argv
- external terminal execution still works
- no invalid flags are emitted
- working directory isolation is implemented

---

# 22. My Recommendation for How to Execute This

If you want the safest path, do **not** ask the agent to do all of Section 3 in one giant pass.

Instead, split it like this:

## Pass 1 — Safety and contract foundation
- help capture script
- help parser
- flag registry
- contract tests
- golden tests

## Pass 2 — Correct existing builder
- remove/verify questionable flags
- enforce allowlist
- fix normalization gaps
- isolate working directory

## Pass 3 — Add missing flags/UI
- upload-folder missing flags
- upload-gp missing flags
- upload-immich missing filters
- archive-immich missing filters

## Pass 4 — Runtime checker
- compatibility report
- Help menu action

This is much less likely to introduce regressions.

---

If you want, next I can do one of these for you:

1. **Write the exact `core/cli_help.py` and `core/cli_contract.py` skeleton code**
2. **Write the exact `TAB_ALLOWED_FLAGS` table for all current tabs**
3. **Write the exact golden test fixture format and sample JSONs**
4. **Turn this into a stricter, ticket-by-ticket agent task list**