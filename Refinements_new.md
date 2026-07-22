# Detailed Improvement & Long-Term Maintenance Guide for Immich-Go GUI

This guide is based on the current `app.py`, `test_app.py`, `Immich-go_cli_doc.md`, and `immich_go_gui_config.toml`.

The main goal is:

> Make the GUI easier to maintain, safer to evolve, and resilient against future `immich-go` CLI breaking changes by decoupling the UI from the actual CLI command construction.

---

## 1. Current Project Understanding

Your project is a PySide6 GUI wrapper around the `immich-go` CLI.

It currently provides:

- Configuration page:
  - Immich server URL
  - API key
  - SSL skip
  - Binary management
  - Theme
  - Advanced global options:
    - client timeout
    - concurrent tasks
    - device UUID
    - error handling
    - pause Immich jobs

- Upload page:
  - `upload from-folder`
  - `upload from-google-photos`
  - `upload from-immich`

- Archive page:
  - `archive from-folder`
  - `archive from-immich`

- Stack page:
  - `stack`

It also includes:

- Binary download/update management.
- API key storage using OS keyring.
- Command preview with secret masking.
- External terminal execution.
- Process lock tracking.
- Theme support.
- A good start on tests, especially golden command tests.

This is already a strong foundation.

---

## 2. Main Long-Term Risk: UI Is Coupled to CLI Details

The biggest maintainability risk right now is that the UI and the CLI command construction are tightly mixed.

For example, `build_plan()` currently knows:

- Qt widgets
- tab keys
- CLI flag names
- CLI flag syntax
- environment variable names
- defaults
- special cases per tab
- dry-run behavior
- warnings
- secret handling

This means that when `immich-go` changes a flag, renames a flag, removes a flag, changes a default, or introduces a new subcommand, you may need to modify UI code directly.

That is fragile.

The long-term solution is:

> The UI should only express user intent.
>
> A separate compatibility layer should translate that intent into the correct `immich-go` command for the detected binary version.

---

## 3. Target Architecture

You do not need to split the project into many files immediately. But you should introduce clear logical layers.

The recommended architecture is:

```text
UI Layer
  |
  | user edits forms
  v
Intent / State Layer
  |
  | typed representation of what the user wants
  v
Compatibility / Command Schema Layer
  |
  | knows immich-go versions, flags, renamed flags, removed flags
  v
Command Builder
  |
  | produces argv + env + warnings + errors
  v
Runner / Execution Layer
  |
  | runs in terminal or internal process
  v
immich-go binary
```

The important rule is:

> UI widgets should never directly know CLI flag names.

Instead of this:

```python
cmd_opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
```

The UI should produce something like:

```python
intent = UploadFolderIntent(
    path="/photos",
    manage_burst="Stack",
    manage_raw_jpeg="NoStack",
    manage_heic_jpeg="NoStack",
)
```

Then a separate builder decides:

```python
argv = builder.build(intent, binary_version="0.31.0")
```

---

## 4. Recommended Decoupling Strategy

You can do this gradually without freezing development.

Use the “strangler fig” approach:

1. Keep `app.py` working.
2. Create a small core module.
3. Move pure logic into it.
4. Make `app.py` call the core module.
5. Gradually replace direct widget-to-flag logic.

Since you are okay with a few decoupled splits, I recommend starting with one or two files only.

### Minimal first split

Start with:

```text
app.py
immichgo_core.py
```

Later, if it grows, split into:

```text
app.py
immichgo/
    __init__.py
    model.py
    schema.py
    builder.py
    binary.py
    runner.py
    compat.py
```

But for now, one `immichgo_core.py` file is enough.

---

## 5. Core Principle: Separate Intent from CLI Flags

Define stable internal names for user-facing options.

These internal names should not change just because `immich-go` changes.

For example:

| Internal intent key | Current CLI flag |
|---|---|
| `upload_folder.manage_burst` | `--manage-burst` |
| `upload_folder.manage_raw_jpeg` | `--manage-raw-jpeg` |
| `upload_folder.manage_heic_jpeg` | `--manage-heic-jpeg` |
| `upload_folder.date_range` | `--date-range` |
| `upload_folder.include_type` | `--include-type` |
| `upload_gp.include_unmatched` | `--include-unmatched` |
| `upload_gp.include_partner` | `--include-partner` |
| `upload_gp.sync_albums` | `--sync-albums` |
| `upload_immich.from_favorite` | `--from-favorite` |
| `upload_immich.from_albums` | `--from-albums` |
| `stack.manage_epson` | `--manage-epson-fastfoto` |

The UI should bind to the internal intent key.

The compatibility layer maps that key to the actual CLI flag.

---

## 6. Introduce a Versioned Command Schema

This is the most important long-term improvement.

Create a schema describing each option.

Example concept:

```python
@dataclass
class OptionSpec:
    key: str
    label: str
    kind: str  # text, bool, choice, int, paths
    default: object
    cli_flag: str | None = None
    env_var: str | None = None
    choices: list[str] | None = None
    minimum: int | None = None
    maximum: int | None = None
    since: str | None = None
    removed_in: str | None = None
    renamed_to: str | None = None
    warning: str | None = None
    applies_to: tuple[str, ...] = ()
```

Example:

```python
UPLOAD_FOLDER_OPTIONS = [
    OptionSpec(
        key="manage_burst",
        label="Burst Photos",
        kind="choice",
        default="NoStack",
        cli_flag="--manage-burst",
        choices=[
            "NoStack",
            "Stack",
            "StackKeepRaw",
            "StackKeepJPEG",
        ],
        since="0.20.0",
    ),
    OptionSpec(
        key="manage_raw_jpeg",
        label="RAW + JPEG Pairs",
        kind="choice",
        default="NoStack",
        cli_flag="--manage-raw-jpeg",
        choices=[
            "NoStack",
            "KeepRaw",
            "KeepJPG",
            "StackCoverRaw",
            "StackCoverJPG",
        ],
    ),
    OptionSpec(
        key="date_range",
        label="Date Range",
        kind="text",
        default="",
        cli_flag="--date-range",
    ),
]
```

Then the builder can use this schema instead of hardcoded `if` blocks.

---

## 7. Handle Future Breaking Changes Cleanly

`immich-go` will change.

You need a compatibility model.

### 7.1 Store compatibility metadata per version

Example:

```python
VERSION_COMPATIBILITY = {
    "0.31.0": {
        "tested": True,
        "notes": "Current GUI-tested version.",
    },
    "0.32.0": {
        "tested": False,
        "removed_flags": [],
        "renamed_flags": {},
        "notes": "ReplaceAsset API removed upstream, but no known GUI flag breakage.",
    },
}
```

If a future version renames a flag:

```python
"0.35.0": {
    "tested": False,
    "renamed_flags": {
        "--manage-epson-fastfoto": "--epson-fastfoto",
    },
}
```

The builder can then translate:

```python
flag = spec.cli_flag
flag = profile.rename_flag(flag)
if profile.is_removed(flag):
    plan.warnings.append(f"{flag} is not supported by this immich-go version.")
else:
    argv.append(...)
```

### 7.2 Do not rely only on release-note keyword scanning

Your current code checks release notes for words like:

```python
breaking
removed
renamed
incompatible
deprecated
```

This is useful, but too broad.

For example, a release note might say:

> Removed unused internal flag.

or:

> Deprecated an obscure option not used by the GUI.

That does not necessarily mean your GUI breaks.

Better approach:

1. Use release-note scanning as a warning signal.
2. Maintain a real compatibility database.
3. Add automated flag-existence tests.
4. Mark releases as “GUI tested” only after verification.

---

## 8. Recommended Compatibility Workflow for New immich-go Releases

Create a repeatable release process.

### When a new `immich-go` version appears

#### Step 1: Detect new release

Your GUI already checks GitHub releases.

Keep that.

#### Step 2: Automatically compare flags

Add a maintenance script or CI job that runs:

```bash
immich-go upload from-folder --help
immich-go upload from-google-photos --help
immich-go upload from-immich --help
immich-go archive from-folder --help
immich-go archive from-immich --help
immich-go stack --help
```

Then extract the available flags.

Compare against the previous version.

Output something like:

```text
Added flags:
  --new-flag

Removed flags:
  --old-flag

Renamed flags:
  possible rename: --old-flag -> --new-flag
```

This can be semi-automatic.

#### Step 3: Update compatibility schema

If nothing changed, mark the version as compatible.

If something changed, update the schema:

```python
OptionSpec(
    key="manage_epson",
    cli_flag="--manage-epson-fastfoto",
    removed_in="0.36.0",
    renamed_to="--epson-fastfoto",
)
```

#### Step 4: Update golden tests

Golden tests are your safety net.

Example:

```python
def test_golden_upload_folder_0_31():
    ...
```

Add new golden tests per supported version when necessary.

#### Step 5: Bump tested version

```python
TESTED_IMMICH_GO_VERSION = "0.32.0"
```

---

## 9. Suggested Module Boundaries

For now, you can keep this inside one file: `immichgo_core.py`.

But logically separate these parts.

### 9.1 Models

Pure data structures.

```python
@dataclass
class CommandPlan:
    argv: list[str]
    env: dict[str, str]
    display_argv: list[str]
    warnings: list[str]
    errors: list[str]
    tab_key: str
    dry_run: bool
    binary_path: str
```

Also define intent models:

```python
@dataclass
class UploadFolderIntent:
    path: str = ""
    include_type: str = "all"
    folder_album: str = "NONE"
    into_album: str = ""
    manage_burst: str = "NoStack"
    manage_raw_jpeg: str = "NoStack"
    manage_heic_jpeg: str = "NoStack"
    date_range: str = ""
    include_extensions: str = ""
    exclude_extensions: str = ""
    ban_file: str = ""
    ignore_sidecar_files: bool = False
    date_from_name: bool = True
    tags: str = ""
    session_tag: bool = False
    folder_as_tags: bool = False
    overwrite: bool = False
    api_trace: bool = False
    log_level: str = "INFO"
```

Similarly:

```python
UploadGooglePhotosIntent
UploadImmichIntent
ArchiveFolderIntent
ArchiveImmichIntent
StackIntent
GlobalConfigIntent
```

### 9.2 Schema

Declarative option definitions.

```python
OPTION_SPECS = {
    "upload-folder": [...],
    "upload-gp": [...],
    "upload-immich": [...],
    "archive-folder": [...],
    "archive-immich": [...],
    "stack": [...],
}
```

### 9.3 Builder

Pure function:

```python
def build_plan(
    tab_key: str,
    global_config: GlobalConfigIntent,
    intent: object,
    binary_version: str,
    binary_path: str,
    dry_run: bool,
) -> CommandPlan:
    ...
```

This function should not import PySide6.

That is very important.

### 9.4 Binary manager

Handles:

- binary path resolution
- version detection
- downloads
- checksums
- metadata
- compatibility status

### 9.5 Runner

Handles execution:

- external terminal
- internal QProcess
- lock files
- environment passing
- secret masking

---

## 10. Refactor `build_plan()` Gradually

Your current `build_plan()` is the main place to refactor.

Do not rewrite it all at once.

### Phase 1: Extract pure helpers

Move these out of UI code:

```python
normalize_server_url()
collect_paths()
mask_command_for_display()
validate_date_range()
build_environment()
```

You already have many of these.

Make them fully independent from Qt.

### Phase 2: Introduce intent collection

Add methods in the GUI like:

```python
def collect_global_config(self) -> GlobalConfigIntent:
    ...

def collect_upload_folder_intent(self) -> UploadFolderIntent:
    ...

def collect_upload_gp_intent(self) -> UploadGooglePhotosIntent:
    ...
```

Then `build_plan()` becomes:

```python
def build_plan(self, dry_run: bool) -> CommandPlan:
    tab_key = self._get_active_tab_key()
    global_config = self.collect_global_config()

    if tab_key == "upload-folder":
        intent = self.collect_upload_folder_intent()
    elif tab_key == "upload-gp":
        intent = self.collect_upload_gp_intent()
    ...

    return core.build_plan(
        tab_key=tab_key,
        global_config=global_config,
        intent=intent,
        binary_version=self.current_version,
        binary_path=self.binary_path,
        dry_run=dry_run,
    )
```

This is a huge improvement.

Now the UI only collects state.

The core decides how to turn state into CLI arguments.

---

## 11. Make the Core UI-Independent

The core module should not know about:

- `QLineEdit`
- `QComboBox`
- `QCheckBox`
- `QPlainTextEdit`
- `QSettings`
- `QFileDialog`
- theme
- sidebar
- tabs

It should only know:

- intent dataclasses
- option specs
- version compatibility
- argv generation
- env generation
- validation
- warnings

This gives you major benefits:

- You can test command building without Qt.
- You can support future CLI versions without touching UI code.
- You can reuse the core for CLI automation or headless mode.
- You can generate config files instead of command lines later.
- You can show better warnings and compatibility messages.

---

## 12. Add Version-Aware Command Building

The builder should know the binary version.

Example:

```python
def build_plan(..., binary_version: str):
    profile = get_version_profile(binary_version)
```

A version profile can answer:

```python
profile.supports_flag("--manage-burst")
profile.rename_flag("--old-flag")
profile.is_removed("--some-flag")
profile.is_option_supported("upload_folder.manage_burst")
```

Example:

```python
@dataclass
class VersionProfile:
    version: str
    tested: bool
    renamed_flags: dict[str, str]
    removed_flags: set[str]
    added_flags: set[str]

    def resolve_flag(self, flag: str) -> str | None:
        if flag in self.removed_flags:
            return None
        return self.renamed_flags.get(flag, flag)
```

Then:

```python
flag = profile.resolve_flag(spec.cli_flag)

if flag is None:
    plan.warnings.append(
        f"{spec.label} is not supported by immich-go {profile.version}."
    )
else:
    cmd_opts.append(f"{flag}={value}")
```

---

## 13. Add Capability Detection from `--help`

For extra safety, you can parse the CLI help output.

This is useful when the user manually selects a newer untested binary.

Example:

```bash
immich-go upload from-folder --help
```

You can extract flags using a regex like:

```python
re.findall(r"--[a-zA-Z0-9\-]+", help_text)
```

Then cache the result:

```python
~/.immich-go-gui/cache/help/0.31.0/upload-from-folder.json
```

Before running a command, the builder can verify:

```python
if "--manage-burst" not in help_flags:
    plan.warnings.append("This binary does not appear to support --manage-burst.")
```

This is not perfect, but it is much better than blindly assuming compatibility.

### Suggested behavior

For tested versions:

- Use built-in compatibility profile.

For untested newer versions:

- Use help parsing.
- Warn if unknown flags are missing.
- Optionally allow “advanced override”.

For older unsupported versions:

- Show a clear warning.
- Disable unsupported options.

---

## 14. Improve Binary Management

Your binary manager is already useful, but it can be made safer.

### 14.1 Add checksum verification

Currently the binary is downloaded and extracted.

If GitHub release provides checksums, verify them.

If not, at least:

1. Calculate SHA256 after download.
2. Store it in metadata.
3. Warn if an existing binary’s hash changes unexpectedly.

Example metadata:

```json
{
  "selected_version": "0.31.0",
  "versions": {
    "0.31.0": {
      "path": "/home/user/.immich-go-gui/bin/0.31.0/immich-go",
      "sha256": "...",
      "downloaded_at": "...",
      "gui_tested": true
    }
  }
}
```

### 14.2 Add tested compatibility range

Instead of only:

```python
TESTED_IMMICH_GO_VERSION = "0.31.0"
```

Use:

```python
MIN_SUPPORTED_IMMICH_GO_VERSION = "0.30.0"
TESTED_IMMICH_GO_VERSION = "0.31.0"
MAX_KNOWN_COMPATIBLE_VERSION = "0.32.0"
```

Then status can be:

| Detected version | Status |
|---|---|
| older than minimum | unsupported |
| between min and tested | supported |
| newer than tested but within known max | probably compatible |
| newer than known max | untested |

### 14.3 Add version selector

Since you already store multiple versions, expose this in advanced settings:

```text
Binary version:
  0.31.0 - tested
  0.32.0 - untested
  manual path
```

This helps when a new version introduces trouble.

The user can roll back.

---

## 15. Improve Configuration Persistence

Right now, the GUI saves only a few things:

- server URL
- API key via keyring
- skip SSL
- theme

But many user options are not persisted.

That can be frustrating.

### Recommended persistence strategy

Use three layers:

#### 1. Secrets

Store in OS keyring.

Examples:

- Immich API key
- source Immich API key for `upload from-immich`

Never store these in plain TOML.

#### 2. User preferences

Store in `QSettings` or JSON.

Examples:

- theme
- last used paths
- last used tabs
- advanced mode
- selected binary version

#### 3. Form state / presets

Store per-tab form values.

Examples:

- upload-folder options
- archive options
- stack options

You can store these in JSON:

```text
~/.config/immich-go-gui/form-state.json
```

Or inside `QSettings`.

### Avoid using the existing giant TOML as-is

The provided `immich_go_gui_config.toml` contains many duplicated and confusing keys, for example:

```toml
upload_folder_sync_albums = true
upload_folder_include_partner = true
upload_folder_takeout_tag = true
```

These do not make sense for `upload from-folder`.

That config structure looks legacy and will be hard to maintain.

Instead, define a clean versioned schema:

```json
{
  "schema_version": 1,
  "global": {
    "server_url": "",
    "skip_ssl": false,
    "client_timeout": 20,
    "concurrent_tasks": 8
  },
  "upload_folder": {
    "path": "",
    "include_type": "all",
    "manage_burst": "NoStack"
  },
  "upload_google_photos": {
    "paths": [],
    "include_partner": true,
    "sync_albums": true
  }
}
```

You can later support import/export to TOML if desired.

---

## 16. Consider Generating immich-go Config Files

`immich-go` supports TOML/YAML/JSON config files.

This could be useful.

Instead of generating only:

```bash
immich-go upload from-folder --server=... --manage-burst=Stack /photos
```

The GUI could generate:

```toml
concurrent-tasks = 8

[upload]
server = "http://localhost:2283"

[upload.from-folder]
manage-burst = "Stack"
```

Then run:

```bash
immich-go --config=/tmp/immich-go-gui-run.toml upload from-folder /photos
```

### Benefits

- Easier to review.
- Less shell quoting trouble.
- Useful for saving reusable profiles.
- Can be used for “Export immich-go config”.

### Drawbacks

- Still needs versioned mapping.
- Config key names may also change.
- Temporary file management is required.

This should not be the first refactor, but it is a good future feature.

A nice user-facing feature would be:

> Export current action as immich-go TOML config.

---

## 17. Improve Validation

You already have:

```python
validate_date_range()
```

But it does not appear to be wired strongly into the UI.

### Recommended validation improvements

#### 17.1 Inline validation

Show validation messages near fields, not only in message boxes.

Examples:

- Invalid date range.
- Source path does not exist.
- Destination folder is not writable.
- No takeout ZIP selected.
- Server URL invalid.
- API key empty.
- Source server missing for `upload from-immich`.

#### 17.2 Path validation

For upload-folder:

```python
if not os.path.exists(path):
    warning("Source path does not exist.")
```

For glob patterns:

```python
expanded = collect_paths(raw_text)
if not expanded:
    warning("Pattern matched no files.")
```

#### 17.3 Destructive option warnings

You currently warn for overwrite.

Add warnings for options that may cause data loss or unexpected behavior:

| Option | Warning |
|---|---|
| `--overwrite` | May replace existing assets. |
| `--manage-raw-jpeg=KeepRaw` | JPEG may be removed/skipped. |
| `--manage-raw-jpeg=KeepJPG` | RAW may be removed/skipped. |
| `--manage-heic-jpeg=KeepHeic` | JPEG may be removed/skipped. |
| `--manage-heic-jpeg=KeepJPG` | HEIC may be removed/skipped. |
| `--include-trashed=true` | Imports trashed Google Photos items. |
| `--from-trash=true` | Includes trashed assets from source Immich. |
| `--skip-verify-ssl` | Reduces transport security. |

#### 17.4 Conflict warnings

Examples:

- `folder-as-album` and `into-album` both set.
- Date range invalid.
- `include-extensions` and `exclude-extensions` overlap.
- `from-albums` and `from-date-range` very broad.

---

## 18. Improve Execution Experience

Currently the GUI launches `immich-go` in an external terminal.

This is simple and useful, but has limitations:

- GUI cannot see output.
- GUI cannot show progress.
- If terminal emulator is missing, execution fails.
- Process tracking depends on lock files.

### Recommended execution modes

#### Mode 1: External terminal

Keep this as the default for advanced users.

Good for long-running operations.

#### Mode 2: Internal runner

Add an optional internal runner using `QProcess`.

This would allow:

- output panel
- progress parsing
- cancel button
- log copying
- dry-run preview inside GUI

For internal mode, use:

```bash
immich-go --no-ui --log-level=INFO ...
```

Possibly also:

```bash
--log-type=json
```

if you want structured parsing later.

#### Mode 3: Copy command

Already partially possible through preview dialog.

Make it prominent:

> Copy command to clipboard.

This is very useful for troubleshooting.

---

## 19. Add Presets

Presets would make the GUI much more user-friendly.

Based on the `immich-go` documentation, you can provide safe presets.

### Example presets

#### Fast LAN upload

```text
concurrent-tasks = 16
client-timeout = 30m
pause-immich-jobs = true
```

#### Slow/unstable connection

```text
concurrent-tasks = 2
client-timeout = 120m
on-errors = continue
```

#### Large Google Takeout

```text
concurrent-tasks = 4
client-timeout = 60m
pause-immich-jobs = true
on-errors = continue
session-tag = true
```

#### Safe stack preview

```text
dry-run = true
log-level = DEBUG
```

#### Server backup

```text
archive from-immich
write-to-folder = chosen by user
```

Presets can be stored as JSON and applied to the intent model.

---

## 20. Improve Testing Strategy

Your current tests are already valuable.

But you can make them stronger and more future-proof.

### 20.1 Separate core tests from GUI tests

Create tests that do not require Qt.

Example:

```python
def test_core_build_upload_folder():
    intent = UploadFolderIntent(
        path="/photos",
        manage_burst="Stack",
    )

    plan = core.build_plan(
        tab_key="upload-folder",
        global_config=...,
        intent=intent,
        binary_version="0.31.0",
        binary_path="./immich-go",
        dry_run=False,
    )

    assert plan.argv == [
        "upload",
        "from-folder",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "/photos",
    ]
```

These tests are fast and stable.

### 20.2 Keep golden command tests

Golden tests are excellent.

Keep them.

But move them to core-level tests where possible.

### 20.3 Add version-specific golden tests

Example:

```python
def test_golden_upload_folder_0_31():
    ...

def test_golden_upload_folder_0_32():
    ...
```

If a future version changes flags, you add a new golden file instead of breaking old expectations.

### 20.4 Add schema tests

Test that every option spec is valid:

```python
def test_option_specs_have_unique_keys():
    ...

def test_choice_specs_have_defaults_in_choices():
    ...

def test_no_unknown_tab_keys():
    ...
```

### 20.5 Add compatibility tests

Example:

```python
def test_removed_flag_is_not_emitted():
    intent = UploadFolderIntent(...)
    plan = build_plan(..., binary_version="0.99.0")
    assert "--removed-flag" not in plan.argv
```

### 20.6 Add help-based contract tests

Optional but powerful.

If you have the binary in CI:

```python
def test_generated_flags_exist_in_binary_help():
    help_text = run(["immich-go", "upload", "from-folder", "--help"])
    for flag in USED_UPLOAD_FOLDER_FLAGS:
        assert flag in help_text
```

This can catch upstream breaking changes early.

---

## 21. Suggested Refactoring Roadmap

Here is a practical phased plan.

---

# Phase 1: Stabilize and Extract Core

Goal: no behavior change, but better structure.

### Tasks

1. Create `immichgo_core.py`.
2. Move pure utilities there:
   - `normalize_server_url`
   - `collect_paths`
   - `mask_command_for_display`
   - `validate_date_range`
   - `CommandPlan`
   - `ValidationResult`
3. Keep `app.py` importing from it.
4. Add tests for all moved utilities.
5. Ensure no Qt imports in `immichgo_core.py`.

### Acceptance criteria

- Existing tests pass.
- Core file has no PySide6 imports.
- Command masking and URL normalization are tested independently.

---

# Phase 2: Introduce Intent Dataclasses

Goal: stop passing widget state directly into command logic.

### Tasks

1. Add dataclasses:
   - `GlobalConfigIntent`
   - `UploadFolderIntent`
   - `UploadGooglePhotosIntent`
   - `UploadImmichIntent`
   - `ArchiveFolderIntent`
   - `ArchiveImmichIntent`
   - `StackIntent`
2. Add GUI methods:
   - `collect_global_config()`
   - `collect_upload_folder_intent()`
   - etc.
3. Make `build_plan()` use these intents.

### Acceptance criteria

- UI widgets are only read inside collector methods.
- Core builder receives dataclasses, not widgets.
- Existing golden tests still pass.

---

# Phase 3: Move Command Building into Core

Goal: make command generation UI-independent.

### Tasks

1. Move `build_plan()` logic into core.
2. Make it accept:
   - tab key
   - global intent
   - tab intent
   - binary version
   - binary path
   - dry-run flag
3. Return `CommandPlan`.

### Acceptance criteria

- You can build commands without creating the GUI.
- Tests can call core builder directly.
- `app.py` becomes thinner.

---

# Phase 4: Introduce Option Schema

Goal: replace repeated hardcoded flag logic with declarative specs.

### Tasks

1. Define `OptionSpec`.
2. Define specs for each tab.
3. Make builder iterate over specs.
4. Keep special cases explicit where needed.

### Acceptance criteria

- Adding a simple new option requires:
  - adding UI widget
  - adding intent field
  - adding option spec
- No large `if` chain modification.

---

# Phase 5: Add Version Profiles

Goal: handle different `immich-go` versions safely.

### Tasks

1. Add `VersionProfile`.
2. Add compatibility metadata.
3. Use detected binary version in builder.
4. Add warnings for unsupported options.

### Acceptance criteria

- If a flag is removed in a version, builder does not emit it.
- If a flag is renamed, builder emits the new flag.
- GUI shows compatibility warnings.

---

# Phase 6: Improve Binary Update Flow

Goal: make updates safer.

### Tasks

1. Add checksum/hash storage.
2. Add tested version range.
3. Add advanced binary version selector.
4. Improve release-note checking.
5. Add “untested version” warning.

### Acceptance criteria

- User can roll back to a known good version.
- GUI distinguishes tested/untested binaries.
- Downloads are more transparent.

---

# Phase 7: Improve Execution and Observability

Goal: better run feedback.

### Tasks

1. Add optional internal runner.
2. Add output/log panel.
3. Add `--no-ui` support for internal runs.
4. Add log file selection.
5. Add “Open log” button.
6. Add command history.

### Acceptance criteria

- User can run dry-run inside GUI.
- User can copy full command.
- User can see errors without only relying on terminal.

---

## 22. Specific Improvements for `immich-go` Breaking Changes

This deserves special attention.

### 22.1 Never scatter CLI flag strings across UI code

Bad:

```python
if c["manage-burst"].currentText() != "NoStack":
    cmd_opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
```

Better:

```python
spec = get_option_spec("upload-folder", "manage_burst")
value = intent.manage_burst
append_option(plan, spec, value, profile)
```

### 22.2 Keep a flag inventory

Maintain something like:

```python
KNOWN_FLAGS = {
    "upload-folder": {
        "--include-type",
        "--folder-as-album",
        "--into-album",
        "--manage-burst",
        "--manage-raw-jpeg",
        "--manage-heic-jpeg",
        "--date-range",
        "--include-extensions",
        "--exclude-extensions",
        "--ban-file",
        "--ignore-sidecar-files",
        "--date-from-name",
        "--tag",
        "--session-tag",
        "--folder-as-tags",
        "--overwrite",
        "--api-trace",
    },
}
```

Then compare against binary help output.

### 22.3 Mark options as optional or required

Some options are essential:

- source path
- server URL
- API key
- destination folder for archive

Some are optional:

- tags
- filters
- stacking options

If an optional flag is unsupported, warn and continue.

If a required capability is unsupported, block.

### 22.4 Add “compatibility mode”

For unknown newer versions:

```text
Compatibility mode:
  [ ] Strict: only use flags verified by help output
  [ ] Permissive: try anyway
```

Strict mode is safer.

Permissive mode helps when help parsing fails.

---

## 23. Suggested Internal Data Model

Here is a practical model you can adopt.

### Global configuration

```python
@dataclass
class GlobalConfigIntent:
    server_url: str = ""
    api_key: str = ""
    skip_ssl: bool = False
    client_timeout_minutes: int = 20
    concurrent_tasks: int = 8
    device_uuid: str = ""
    on_errors: str = "stop"
    on_errors_tolerance: int = 10
    pause_immich_jobs: bool = True
```

### Upload folder

```python
@dataclass
class UploadFolderIntent:
    path: str = ""
    include_type: str = "all"
    folder_as_album: str = "NONE"
    into_album: str = ""
    manage_burst: str = "NoStack"
    manage_raw_jpeg: str = "NoStack"
    manage_heic_jpeg: str = "NoStack"
    date_range: str = ""
    include_extensions: str = ""
    exclude_extensions: str = ""
    ban_file: str = ""
    ignore_sidecar_files: bool = False
    date_from_name: bool = True
    tags: str = ""
    session_tag: bool = False
    folder_as_tags: bool = False
    overwrite: bool = False
    api_trace: bool = False
    log_level: str = "INFO"
```

### Google Photos

```python
@dataclass
class UploadGooglePhotosIntent:
    paths_text: str = ""
    include_type: str = "all"
    into_album: str = ""
    include_unmatched: bool = False
    include_partner: bool = True
    sync_albums: bool = True
    manage_burst: str = "NoStack"
    manage_heic_jpeg: str = "NoStack"
    from_album_name: str = ""
    include_archived: bool = True
    include_trashed: bool = False
    partner_shared_album: str = ""
    takeout_tag: bool = True
    people_tag: bool = True
    tags: str = ""
    session_tag: bool = False
    api_trace: bool = False
    log_level: str = "INFO"
```

### Upload from Immich

```python
@dataclass
class UploadImmichIntent:
    from_server: str = ""
    from_api_key: str = ""
    from_client_timeout_minutes: int = 20
    from_favorite: bool = False
    from_archived: bool = False
    from_trash: bool = False
    from_date_range: str = ""
    from_albums: str = ""
    from_minimal_rating: int = 0
    from_people: str = ""
    from_tags: str = ""
    from_city: str = ""
    from_state: str = ""
    from_country: str = ""
    from_make: str = ""
    from_model: str = ""
    from_skip_ssl: bool = False
    api_trace: bool = False
    log_level: str = "INFO"
```

### Archive folder

```python
@dataclass
class ArchiveFolderIntent:
    path: str = ""
    write_to_folder: str = ""
    manage_raw_jpeg: str = "NoStack"
    date_range: str = ""
    log_level: str = "INFO"
```

### Archive Immich

```python
@dataclass
class ArchiveImmichIntent:
    write_to_folder: str = ""
    manage_burst: str = "NoStack"
    manage_raw_jpeg: str = "NoStack"
    from_date_range: str = ""
    from_albums: str = ""
    log_level: str = "INFO"
```

### Stack

```python
@dataclass
class StackIntent:
    manage_burst: str = "NoStack"
    manage_raw_jpeg: str = "NoStack"
    manage_heic_jpeg: str = "NoStack"
    time_zone: str = ""
    manage_epson_fastfoto: bool = False
    api_trace: bool = False
    log_level: str = "INFO"
```

---

## 24. Example Core Builder Pattern

Here is a simplified example of the direction.

```python
def append_choice_option(plan, profile, spec, value):
    if value == spec.default:
        return

    flag = profile.resolve_flag(spec.cli_flag)

    if flag is None:
        plan.warnings.append(
            f"{spec.label} is not supported by immich-go {profile.version}."
        )
        return

    plan.argv.append(f"{flag}={value}")


def append_bool_option(plan, profile, spec, value):
    if value == spec.default:
        return

    flag = profile.resolve_flag(spec.cli_flag)

    if flag is None:
        plan.warnings.append(
            f"{spec.label} is not supported by immich-go {profile.version}."
        )
        return

    if value:
        plan.argv.append(flag)
    else:
        plan.argv.append(f"{flag}=false")
```

Then:

```python
append_choice_option(
    plan,
    profile,
    UPLOAD_FOLDER_MANAGE_BURST_SPEC,
    intent.manage_burst,
)
```

This makes future changes easier.

If `immich-go` renames `--manage-burst`, you update the profile/spec only.

---

## 25. Improve Secret Handling

Your current approach is already good because API keys are not placed directly in argv.

But you can improve further.

### Current approach

API key is passed via environment variable:

```python
IMMICH_GO_UPLOAD_API_KEY
```

This is better than:

```bash
--api-key=secret
```

because command-line arguments can be visible in process listings.

### Additional improvements

#### 1. Mask environment variables in preview

You already do this.

Keep it.

#### 2. Consider ephemeral config file with strict permissions

For advanced security, generate a temporary config file:

```text
/tmp/immich-go-gui-1234.toml
```

With:

```toml
[upload]
api-key = "secret"
```

Then:

```bash
chmod 600 /tmp/immich-go-gui-1234.toml
immich-go --config=/tmp/immich-go-gui-1234.toml upload from-folder /photos
```

Delete after execution.

This avoids putting secrets in environment variables, but introduces temporary file management.

You could make this optional.

#### 3. Never log secrets

Ensure logs, crash reports, and command previews never include:

- API key
- from API key
- admin API key

You already mask them, but keep strict tests for this.

---

## 26. Improve User Experience

### 26.1 Show compatibility banner

Examples:

```text
Binary 0.31.0 is fully tested with this GUI.
```

or:

```text
Binary 0.33.0 is newer than the tested version. Some options may behave differently.
```

or:

```text
Binary 0.29.0 is older than the minimum supported version.
```

### 26.2 Add contextual help

Each option can link to the relevant section of the `immich-go` documentation.

Examples:

- `--manage-burst` → burst detection docs
- `--manage-raw-jpeg` → RAW+JPEG pairing docs
- `--folder-as-album` → album organization docs
- `--from-date-range` → date range docs

### 26.3 Add “What will happen?” summary

Before running, show a human-readable summary:

```text
Action:
  Upload local folder to Immich.

Source:
  /photos

Server:
  http://localhost:2283

Options:
  - Stack burst photos
  - Keep RAW as cover for RAW+JPEG pairs
  - Create albums from folders

Safety:
  - Dry run: no files will be changed
```

This is friendlier than only showing the raw command.

### 26.4 Add command history

Store recent command plans:

- timestamp
- tab
- dry-run/live
- masked command
- result if internal runner is used

This helps users repeat operations safely.

---

## 27. Suggested File Layout for the Future

You do not need this immediately.

But when the project grows, this is a clean layout:

```text
immich-go-gui/
    app.py
    theme.py
    immichgo/
        __init__.py
        model.py
        schema.py
        builder.py
        compat.py
        binary.py
        runner.py
        secrets.py
    ui/
        __init__.py
        main_window.py
        widgets.py
        pages/
            config.py
            upload.py
            archive.py
            stack.py
    tests/
        test_core_builder.py
        test_core_compat.py
        test_gui_smoke.py
        golden/
            upload_folder_0_31.json
            upload_gp_0_31.json
            stack_0_31.json
```

But again, you can start with just:

```text
app.py
immichgo_core.py
```

---

## 28. Prioritized Improvement Backlog

Here is what I would prioritize.

---

### High Priority

These give the biggest maintainability gain.

#### 1. Extract core command builder

Move command generation out of UI.

#### 2. Introduce intent dataclasses

Stop passing widgets into builder logic.

#### 3. Add version profile system

Prepare for future breaking changes.

#### 4. Add more golden tests

Protect command generation behavior.

#### 5. Wire date-range and path validation into UI

Prevent user errors.

#### 6. Add destructive option warnings

Especially for `KeepRaw`, `KeepJPG`, `KeepHeic`, trash import, overwrite.

#### 7. Persist form state

Users should not lose options after restart.

---

### Medium Priority

#### 1. Schema-driven option definitions

Reduces duplicated logic.

#### 2. Help-based flag verification

Detect unsupported flags in untested binaries.

#### 3. Internal runner with output panel

Better UX.

#### 4. Presets

Easier for non-expert users.

#### 5. Binary checksum/hash verification

Safer updates.

#### 6. Compatibility banner

Clearer version status.

---

### Lower Priority

#### 1. Generate immich-go TOML config files

Nice advanced feature.

#### 2. Dynamic UI generation from schema

Powerful but probably overkill for now.

#### 3. Command history

Useful but not urgent.

#### 4. Internationalization

Only if needed.

#### 5. Full plugin architecture

Not necessary yet.

---

## 29. Specific Recommendations Based on Current Code

### 29.1 Keep API keys out of argv

This is correct. Keep it.

### 29.2 Keep secret masking tests

These are valuable.

### 29.3 Avoid using the giant legacy TOML directly

The current `immich_go_gui_config.toml` seems hard to maintain.

Prefer:

- keyring for secrets
- JSON/QSettings for GUI state
- optional exported immich-go TOML for CLI reuse

### 29.4 Make `archive-folder` behavior explicit

`archive from-folder` does not need a server.

The tests already check this.

Make the UI clearly say:

> Archive from folder reorganizes local files and does not require an Immich server.

### 29.5 Add dry-run recommendation for stack

Stacking modifies existing server assets.

For stack, show:

> Stacking changes assets already on the server. Running a dry run first is recommended.

You could even make “Preview (Dry Run)” visually primary on the stack page.

### 29.6 Add warnings for Google Takeout completeness

From the CLI docs, incomplete takeouts are a common issue.

Add a hint:

```text
Make sure all takeout ZIP parts are present.
You can add multiple ZIP paths, one per line, or use a glob like takeout-*.zip.
```

You already support this, but make it more visible.

---

## 30. Example Future Maintenance Flow

Suppose `immich-go 0.35.0` renames:

```text
--manage-epson-fastfoto
```

to:

```text
--epson-fastfoto
```

### Without decoupling

You would need to search UI code for:

```python
--manage-epson-fastfoto
```

and modify it.

### With decoupling

You update one compatibility entry:

```python
"0.35.0": {
    "renamed_flags": {
        "--manage-epson-fastfoto": "--epson-fastfoto",
    },
}
```

The UI still uses:

```python
manage_epson_fastfoto = True
```

The builder emits:

```bash
--epson-fastfoto=true
```

for version `0.35.0`, and:

```bash
--manage-epson-fastfoto=true
```

for older versions.

That is the long-term win.

---

## 31. Recommended Definition of Done for the Refactor

Consider the refactor complete when:

1. `app.py` no longer contains detailed CLI flag construction.
2. UI widgets only collect user intent.
3. Core builder is pure Python and has no Qt imports.
4. Every tab has an intent dataclass.
5. Every option has a stable internal key.
6. Command generation is driven by schema/specs.
7. Binary version is used to resolve flags.
8. Removed or renamed flags are handled by compatibility profiles.
9. Golden tests exist for all tabs.
10. Secrets never appear in argv, logs, or previews.
11. Users see clear warnings for unsupported or destructive options.
12. A new `immich-go` release can be supported mostly by updating compatibility data and tests.

---

## 32. Final Recommended Direction

The most important improvement is this:

> Turn the GUI into an intent editor, and turn `immich-go` command construction into a version-aware core service.

In practical terms:

1. Start with `immichgo_core.py`.
2. Move pure command logic there.
3. Introduce intent dataclasses.
4. Add version profiles.
5. Add schema-driven option mapping.
6. Add compatibility tests.
7. Improve binary update safety.
8. Improve validation, warnings, and execution feedback.

This will make the project much easier to maintain as `immich-go` evolves.

The GUI will become more stable, users will get better warnings, and future CLI breaking changes will usually require changes only in the compatibility layer, not across the UI.