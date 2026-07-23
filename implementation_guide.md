Below is a **detailed, handoff-ready AI agent guide for Phase 2**.

This guide assumes:

- **Phase 1 critical fixes are already done**
  - `--write-to-folder`
  - `archive from-immich` source model
  - `plan.errors` surfaced
  - running-state boolean fixed
  - stale-lock detection improved
  - terminal secret forwarding improved
  - invalid archive controls removed
  - many missing flags already added

- **Phase 2 goal** is:
  > make the existing GUI complete, trustworthy, and release-ready for the currently supported tabs.

This Phase 2 guide intentionally **does not** focus on:

- accessibility overhaul
- documentation site / manual writing
- adding brand-new product features or new source tabs unless explicitly requested later

---

# Phase 2 AI Agent Guide — Completeness, Safety, and Release Readiness

## 1. Phase 2 mission

The agent’s job in Phase 2 is to eliminate the remaining “almost there” problems:

1. **Every visible control must do something real**
2. **Every emitted flag must be valid for the exact CLI subcommand**
3. **Every important CLI option for existing tabs should be exposed**
4. **Simple mode must stay simple; Advanced mode must expose power-user options**
5. **Validation must catch bad input before execution**
6. **Secret/profile operations must not silently lose data**
7. **Binary update flow must be safe and predictable**
8. **Compatibility checking must be fixture-driven and truthful**
9. **Tests must prove the GUI is not lying to the user**
10. **The app must be ready for a release-candidate build**

---

## 2. Definition of done for Phase 2

Phase 2 is complete only when all of the following are true:

### 2.1 Functional completeness
- All existing tabs expose the important CLI flags for their subcommands
- No UI control is decorative
- No invalid flag can be emitted
- Simple/Advanced mode behavior is consistent and persisted

### 2.2 Command correctness
- `upload-folder`, `upload-gp`, `upload-immich`, `archive-folder`, `archive-immich`, and `stack` all generate correct commands
- Boolean defaults are handled correctly
- Repeatable flags are emitted correctly
- CSV flags are normalized correctly
- Secrets never appear in `argv`

### 2.3 Validation and safety
- Required fields are validated
- Paths are normalized and checked where appropriate
- Destination warnings are shown for archive workflows
- Destructive options show warnings
- Server URL format is validated
- `plan.errors` block execution

### 2.4 Persistence
- Form state persists across restarts
- Advanced mode persists
- Preferred terminal and untested-update preference persist
- Profile switching preserves secrets safely
- Secret copy/rename operations verify success before deleting old secrets

### 2.5 Binary management
- Update flow cannot accidentally downgrade
- Download URL selection is based on real release assets where possible
- Download cancellation is cooperative, not `QThread.terminate()`
- `update_binary()` returns truthful success/failure
- Extracted binary is verified after install

### 2.6 Compatibility checking
- CLI help fixtures exist and are committed
- Missing fixtures are treated as failure, not silently ignored
- Compatibility dialog merges fixture + live-binary results
- Tests verify allowed flags against fixtures

### 2.7 Test coverage
- Every tab has golden command tests
- Every newly exposed control has a test proving it affects the command or validation
- Duplicate test names are removed
- GUI tests run headlessly in CI
- Fixtures are required for tests to pass

---

## 3. Non-goals for Phase 2

Unless explicitly requested, the agent should **not** spend time on:

- adding `upload from-icloud`
- adding `upload from-picasa`
- adding `archive from-google-photos`
- adding `archive from-icloud`
- adding `archive from-picasa`
- full accessibility remediation
- writing end-user documentation
- adding integrated run-history dashboards
- adding dry-run output parsing into a rich UI

These can be future phases.

---

# 4. Workstream A — CLI completeness and schema hardening

This is the highest-priority technical work in Phase 2.

---

## A1. Audit and finalize `TAB_ALLOWED_FLAGS`

### File
`core/cli_schema.py`

### Requirements
The allowlist must match the real CLI help fixtures for each tab.

### Tasks
1. Keep only flags that are valid for the exact subcommand
2. Ensure all important non-secret flags are present
3. Ensure secret flags are not expected in `argv`
4. Ensure `--no-ui` remains excluded
5. Ensure `--config`, `--save-config`, `--log-file`, and `--log-type` are excluded unless deliberately added later

### Already likely present
The current schema is already much better than before.

### Still verify especially
- `upload-folder`
  - `recursive`
  - `date-from-name`
  - `album-path-joiner`
  - `time-zone`
  - `manage-epson-fastfoto`
- `upload-gp`
  - `include-untitled-albums`
  - `from-album-name`
  - `partner-shared-album`
  - `people-tag`
  - `sync-albums`
  - `takeout-tag`
  - `include-archived`
  - `include-partner`
  - `include-trashed`
  - `include-unmatched`
  - `manage-raw-jpeg`
  - `manage-epson-fastfoto`
- `upload-immich`
  - all `from-*` filters
  - destination `tag`
  - destination `session-tag`
  - destination `overwrite`
  - destination pair handling
  - destination `time-zone`
  - `from-dry-run`
- `archive-folder`
  - `write-to-folder`
  - `recursive`
  - `date-from-name`
  - `folder-as-album`
  - `folder-as-tags`
  - `into-album`
  - `album-path-joiner`
  - `include-type`
  - `include-extensions`
  - `exclude-extensions`
  - `ban-file`
  - `ignore-sidecar-files`
  - `on-errors`
- `archive-immich`
  - `write-to-folder`
  - `from-server`
  - all `from-*` filters
  - `from-dry-run`
  - `from-client-timeout`
  - `from-skip-verify-ssl`
  - `from-api-trace`
  - `from-pause-immich-jobs`
- `stack`
  - `date-range`
  - `time-zone`
  - `manage-epson-fastfoto`
  - `pause-immich-jobs`
  - `api-trace`
  - `device-uuid`

### Acceptance
- `check_fixtures()` reports no missing flags
- no tab allowlist contains a flag that is invalid for that subcommand

---

## A2. Emit `device-uuid` for `stack`

### Why
The CLI supports `--device-uuid` for `stack`, but the builder currently emits it only for upload tabs.

### File
`core/command_builder.py`

### Change
Replace upload-only device UUID emission with:

```python
if tab_key in UPLOAD_TABS or tab_key == "stack":
    if config_state.get("device_uuid"):
        emitter.add_option("device-uuid", config_state["device_uuid"])
```

### Acceptance
- `stack` command includes `--device-uuid=...` when configured
- upload behavior remains unchanged

---

## A3. Add optional source admin API key support for `upload-immich`

### Why
The CLI supports `--from-admin-api-key` for `upload from-immich`.

Even if not commonly needed, Phase 2 should either:
- expose it as an optional advanced secret field, or
- explicitly document that it is intentionally unsupported

Preferred: expose it.

---

### Files
- `app.py`
- `core/command_builder.py`
- `core/cli_schema.py`

### UI change
In `_build_upload_immich_tab()` advanced section, add:

- `from-admin-api-key` password field
- optional / advanced only
- helper text: “Only needed if source server requires admin-level operations.”

### State change
In `_collect_tab_state("upload-immich")`, include:

```python
"from-admin-api-key": get_text("from-admin-api-key"),
```

### Builder change
Extend `build_plan_from_state()`:

```python
from_admin_api_key = tab_state.get("from-admin-api-key", "")
```

Extend `build_environment()` signature:

```python
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
```

Then for `upload-immich`:

```python
if tab_key == "upload-immich":
    if from_server:
        env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER"] = from_server
    if from_api_key:
        env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY"] = from_api_key
    if from_admin_api_key:
        env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY"] = from_admin_api_key
```

### Secret safety
- Do not emit `--from-admin-api-key` in `argv`
- Keep it in environment only
- Ensure `collect_form_state()` continues to exclude it from persisted form state

### Acceptance
- source admin key is passed via environment
- source admin key never appears in command preview
- source admin key is not saved into `form_state`

---

## A4. Make `display_argv` copyable as a full command

### Why
Right now the dialog shows the binary separately, but “Copy Command” may copy only subcommand arguments.

That is confusing.

### File
`core/command_builder.py`

### Recommended change
Change:

```python
plan.display_argv = mask_command_for_display(plan.argv)
```

to:

```python
plan.display_argv = mask_command_for_display([binary_path] + plan.argv)
```

### File
`app.py`

### Also fix command string quoting
In `show_confirm_dialog()`, use safe quoting for the full command.

For POSIX:

```python
cmd_str = " ".join(shlex.quote(p) for p in plan.display_argv)
```

For Windows:

```python
cmd_str = subprocess.list2cmdline(plan.display_argv)
```

### Acceptance
- copied command includes the binary path
- secrets remain masked
- command is shell-safe

---

## A5. Add golden tests for every tab with non-default advanced options

### File
`test_app.py`

### Required tests
Add tests that set non-default values and assert the exact emitted flags.

Examples:

#### upload-folder
- `--recursive=false`
- `--date-from-name=false`
- `--album-path-joiner=...`
- `--time-zone=...`
- `--manage-epson-fastfoto`

#### upload-gp
- `--include-archived=false`
- `--include-partner=false`
- `--sync-albums=false`
- `--takeout-tag=false`
- `--people-tag=false`
- `--include-trashed`
- `--include-unmatched`
- `--include-untitled-albums`
- `--from-album-name=...`
- `--partner-shared-album=...`
- `--include-type=VIDEO`
- `--manage-raw-jpeg=...`
- `--manage-epson-fastfoto`

#### upload-immich
- `--from-include-type=...`
- `--from-include-extensions=...`
- `--from-exclude-extensions=...`
- `--from-partners`
- `--from-no-album`
- `--from-time-zone=...`
- `--from-device-uuid=...`
- `--from-api-trace`
- `--from-pause-immich-jobs=false`
- destination `--tag=...`
- destination `--session-tag`
- destination `--overwrite`
- destination `--time-zone=...`
- destination pair handling flags

#### archive-folder
- `--write-to-folder=...`
- `--recursive=false`
- `--date-from-name=false`
- `--folder-as-album=...`
- `--folder-as-tags`
- `--into-album=...`
- `--album-path-joiner=...`
- `--include-type=...`
- `--include-extensions=...`
- `--exclude-extensions=...`
- `--ban-file=...`
- `--ignore-sidecar-files`
- `--on-errors=continue`

#### archive-immich
- `--from-server=...`
- `--write-to-folder=...`
- `--from-favorite`
- `--from-archived`
- `--from-trash`
- `--from-minimal-rating=...`
- `--from-people=...`
- `--from-tags=...`
- `--from-city=...`
- `--from-state=...`
- `--from-country=...`
- `--from-make=...`
- `--from-model=...`
- `--from-include-type=...`
- `--from-include-extensions=...`
- `--from-exclude-extensions=...`
- `--from-partners`
- `--from-time-zone=...`
- `--from-no-album`
- `--from-device-uuid=...`
- `--from-skip-verify-ssl`
- `--from-api-trace`
- `--from-pause-immich-jobs=false`
- `--from-client-timeout=...`
- `--from-dry-run`

#### stack
- `--date-range=...`
- `--time-zone=...`
- `--manage-epson-fastfoto`
- `--pause-immich-jobs=false`
- `--api-trace`
- `--device-uuid=...`

### Acceptance
- every visible advanced control has at least one test proving it affects output or validation

---

# 5. Workstream B — UI completeness and Simple/Advanced finalization

Phase 2 must make the GUI feel complete without making Simple mode overwhelming.

---

## B1. Enforce a clear Simple vs Advanced policy

### Simple mode should show
- required fields
- source / destination
- common workflow choices
- high-impact safe options

### Advanced mode should show
- filtering
- tagging
- debug/trace
- timeouts
- CLI behavior overrides
- rare but valid flags
- dangerous options that are not needed in basic workflows

---

## B2. Finalize tab layouts

### `upload-folder`
#### Simple
- source path
- album organization
- into album
- burst handling
- RAW+JPEG handling
- HEIC+JPEG handling

#### Advanced
- media type
- date range
- include/exclude extensions
- ban-file
- recursive
- ignore sidecar
- date-from-name
- album-path-joiner
- tags
- session tag
- folder as tags
- on-errors
- overwrite
- pause jobs
- time zone
- Epson FastFoto
- log level
- API trace

---

### `upload-gp`
#### Simple
- takeout source
- include partner
- sync albums
- include archived
- burst handling
- HEIC+JPEG handling

#### Advanced
- media type
- into album
- include unmatched
- include trashed
- include untitled albums
- from album name
- partner shared album
- takeout tag
- people tag
- RAW+JPEG
- Epson FastFoto
- date range
- include/exclude extensions
- ban-file
- tags
- session tag
- overwrite
- on-errors
- pause jobs
- time zone
- log level
- API trace

---

### `upload-immich`
#### Simple
- source server
- source API key
- date range
- albums
- favorites only

#### Advanced
- source archived/trashed/partners/no-album
- minimum rating
- people/tags
- city/state/country/make/model
- source media type
- source include/exclude extensions
- source time zone
- source device UUID
- source client timeout
- source SSL skip
- source API trace
- source pause jobs
- optional source admin API key
- destination tags/session tag/overwrite/time zone
- destination pair handling
- destination Epson FastFoto
- on-errors
- log level
- destination API trace

---

### `archive-folder`
#### Simple
- source path
- destination folder

#### Advanced
- date range
- media type
- include/exclude extensions
- ban-file
- recursive
- ignore sidecar
- date-from-name
- folder-as-album
- folder-as-tags
- into-album
- album-path-joiner
- on-errors
- log level

---

### `archive-immich`
#### Simple
- destination folder
- date range
- albums

#### Advanced
- favorite/archived/trash/no-album/partners
- minimum rating
- people/tags
- city/state/country/make/model
- source media type
- source include/exclude extensions
- source time zone
- source device UUID
- source client timeout
- source SSL skip
- source API trace
- source pause jobs
- log level

---

### `stack`
#### Simple
- burst handling
- RAW+JPEG handling
- HEIC+JPEG handling

#### Advanced
- date range
- time zone
- Epson FastFoto
- pause jobs
- log level
- API trace

---

## B3. Persist advanced mode

### File
`app.py`

### Requirements
- `toggle_advanced()` must update `app_config.advanced_mode`
- `load_configuration()` must restore advanced mode
- `save_configuration()` must persist it

### Acceptance
- restart preserves Simple/Advanced state

---

## B4. Remove all remaining false affordances

### Rule
If a widget exists, it must either:
1. affect command generation, or
2. affect validation, or
3. affect persistence/settings

Otherwise remove it.

### Special checks
- no archive tab pair-handling controls unless valid
- no per-tab SSL skip if global SSL skip is the source of truth
- no controls that are collected but never emitted
- no emitted flags that are not allowed for that tab

---

# 6. Workstream C — Validation and safety improvements

---

## C1. Validate server URL format

### File
`core/validation.py`

### Add helper

```python
def validate_server_url(url: str) -> tuple[bool, str | None]:
    clean = normalize_server_url(url)
    if not clean:
        return False, "Server URL is empty"
    if not re.match(r"^https?://[^/\s]+", clean):
        return False, "Server URL must start with http:// or https://"
    return True, None
```

### File
`core/command_builder.py`

### Use in `validate_state()`
For server-required tabs:

```python
ok, err = validate_server_url(srv)
if not ok:
    res.errors.append(err)
```

### Acceptance
- invalid URLs are caught before execution

---

## C2. Add path warnings for Google Photos source

### File
`core/command_builder.py`

### Change
In `validate_state()` for `upload-gp`, do not only check non-empty.

Use:

```python
elif tab_key == "upload-gp":
    p = tab_state.get("path", "").strip()
    if not p:
        res.errors.append("Google Photos takeout source path is required.")
    else:
        _, path_warns = expand_source_paths(p)
        res.warnings.extend(path_warns)
```

### Acceptance
- nonexistent takeout paths produce warnings
- glob patterns that match nothing produce warnings

---

## C3. Keep and verify archive destination warnings

### Required behavior
For `archive-folder`:
- warn if destination is inside source
- warn if destination exists but is not a directory
- warn if destination exists but is not writable

For `archive-immich`:
- warn if destination exists but is not a directory
- warn if destination exists but is not writable

### Acceptance
- archive workflows show meaningful destination warnings before run

---

## C4. Strengthen destructive-option warnings

### Required warnings
Show warnings for:
- `KeepRaw`
- `KeepJPG`
- `KeepHeic`
- `StackKeepRaw`
- `StackKeepJPEG`
- overwrite mode
- SSL skip

### Tabs to check
- `upload-folder`
- `upload-gp`
- `upload-immich`
- `stack`

### Acceptance
- user sees clear warning before running a potentially destructive command

---

## C5. Surface `plan.errors` everywhere

### Already partly done
Keep this behavior and make it unconditional.

### Required
- `show_confirm_dialog()` blocks on `plan.errors`
- `run_command()` blocks on `plan.errors`
- tests prove this behavior

### Optional but recommended
Disable Run/Preview if a built plan would contain schema errors.

---

# 7. Workstream D — Persistence, profiles, and secret safety

---

## D1. Ensure form state persistence is complete

### File
`app.py`

### Requirements
- `collect_form_state()` collects all non-secret widget state
- `apply_form_state()` restores it
- `save_configuration()` stores it in `AppConfig.form_state`
- `load_configuration()` applies it

### Acceptance
- restart restores paths, filters, checkboxes, combos, and spinboxes
- secrets are not stored in `form_state`

---

## D2. Persist advanced settings that affect behavior

### Required settings
- `advanced_mode`
- `allow_untested_updates`
- `preferred_terminal`

### Acceptance
- these survive restart
- tests prove roundtrip persistence

---

## D3. Make secret copy operations verify success

### File
`core/config_manager.py`

### Change `SecretStore.copy_secrets()`
Return a boolean and verify readback.

```python
@staticmethod
def copy_secrets(src_profile: str, dst_profile: str) -> bool:
    ok = True
    for k in ("api_key", "admin_api_key"):
        val = SecretStore.get_secret(src_profile, k)
        if not val:
            continue
        if not SecretStore.set_secret(dst_profile, k, val):
            ok = False
            continue
        if SecretStore.get_secret(dst_profile, k) != val:
            ok = False
    return ok
```

---

## D4. Make profile rename/duplicate safe

### File
`core/profile_manager.py`

### Required behavior
Do not clear old secrets unless copy succeeded.

Example for rename:

```python
if not SecretStore.copy_secrets(clean_old, clean_new):
    raise RuntimeError("Failed to copy secrets to renamed profile.")

SecretStore.clear_secret(clean_old, "api_key")
SecretStore.clear_secret(clean_old, "admin_api_key")
```

### Also apply to duplicate where relevant
If duplicate copies secrets and later operations clear source, verify first.

### Acceptance
- failed keyring copy does not cause secret loss
- profile operations raise meaningful errors

---

## D5. Replace placeholder QSettings identity if still present

### File
`app.py`

### Required
Use a real organization name.

Example:

```python
self.settings = QSettings("Shitan198u", "ImmichGoGUI")
```

### Acceptance
- no placeholder organization remains

---

## D6. Avoid encoding-sensitive UI strings in logic

### Why
Strings like `custom…` can become fragile if encoding is mishandled.

### Recommendation
Use constants.

Example:

```python
ON_ERRORS_CUSTOM_LABEL = "Custom…"
ON_ERRORS_CUSTOM_VALUE = "custom"
```

Then compare against the constant, not a literal scattered through the code.

### Acceptance
- custom error handling works regardless of encoding artifacts

---

# 8. Workstream E — Binary update safety

This is one of the most important Phase 2 areas.

---

## E1. Prevent accidental downgrades

### File
`core/binary_manager.py`

### Required behavior
In `evaluate_update()`:

- if `current_version` is newer than `latest_version`, do not prompt update
- return a clear “already newer” decision

### Example

```python
try:
    if Version(current_clean) > Version(latest_clean):
        return UpdateDecision(
            allowed=False,
            requires_confirmation=False,
            severity=UpdateSeverity.INFO,
            message=f"You are already using a newer version ({current_clean}) than the latest checked release ({latest_clean}).",
            latest_version=latest_clean,
            current_version=current_clean,
        )
except InvalidVersion:
    pass
```

### Acceptance
- no downgrade prompt when current is newer

---

## E2. Use real release asset discovery instead of guessed URLs

### File
`core/binary_manager.py`

### Required
Fetch release metadata from GitHub and select the correct asset by OS/arch.

### Recommended method
Add:

```python
def get_release_asset_url(self, version: str) -> str | None:
    clean_v = clean_version(version)
    urls = [
        f"https://api.github.com/repos/simulot/immich-go/releases/tags/v{clean_v}",
        f"https://api.github.com/repos/simulot/immich-go/releases/tags/{clean_v}",
    ]
    ...
```

Then inspect:

```python
data.get("assets", [])
```

Match asset name by:
- OS
- architecture
- extension

Fallback to guessed URL only if asset lookup fails.

### Acceptance
- update flow uses real asset URLs when available
- fallback behavior is explicit and logged

---

## E3. Replace `QThread.terminate()` with cooperative cancellation

### File
`app.py`

### Required
Do not use:

```python
download_thread.terminate()
```

Use a cancellation flag.

### Pattern

```python
class DownloadThread(QThread):
    download_progress = Signal(int)
    download_complete = Signal(str)
    download_error = Signal(str)

    def __init__(self, url, dest_path):
        super().__init__()
        self.url = url
        self.dest_path = dest_path
        self.cancelled = False

    def run(self):
        try:
            with requests.get(self.url, stream=True, timeout=60) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                with open(self.dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if self.cancelled:
                            self.download_error.emit("Download cancelled")
                            return
                        downloaded += len(chunk)
                        f.write(chunk)
                        if total:
                            self.download_progress.emit(int(downloaded * 100 / total))
            self.download_complete.emit(self.dest_path)
        except Exception as e:
            self.download_error.emit(str(e))
```

Cancel button:

```python
def cancel_download():
    download_thread.cancelled = True
```

### Acceptance
- cancel stops download without `terminate()`
- partial downloads do not corrupt installed binary

---

## E4. Make `update_binary()` return truthful results

### Required
`update_binary()` must return `False` when:
- download fails
- user cancels
- extraction fails
- post-install verification fails

It must return `True` only on full success.

### Acceptance
- callers can rely on the return value

---

## E5. Download to temporary file, then extract

### Required
Do not extract directly from an in-memory blob if cancellation and robustness matter.

Use:
- temporary download file
- extract after download completes
- replace existing binary only after successful extraction

### Acceptance
- failed download does not destroy existing working binary

---

## E6. Verify binary after extraction

### Required
After extraction:
1. chmod if POSIX
2. run `immich-go version`
3. verify version output is not empty
4. optionally compare to expected version

### Acceptance
- corrupted or wrong binary is detected before selection

---

## E7. Add checksum support if available

### Preferred
If upstream release provides checksums:
- download checksum file
- verify SHA256

### If no checksums exist
- compute SHA256 after download
- store it in metadata
- warn that upstream checksum verification was unavailable

### Acceptance
- binary integrity is at least recorded, preferably verified

---

# 9. Workstream F — Compatibility fixtures and CLI contract truthfulness

---

## F1. Ensure CLI help fixtures exist and are committed

### Required files
At minimum:

```text
tests/fixtures/cli_help/0.32.0/upload_from-folder.txt
tests/fixtures/cli_help/0.32.0/upload_from-google-photos.txt
tests/fixtures/cli_help/0.32.0/upload_from-immich.txt
tests/fixtures/cli_help/0.32.0/archive_from-folder.txt
tests/fixtures/cli_help/0.32.0/archive_from-immich.txt
tests/fixtures/cli_help/0.32.0/stack.txt
```

### Script
Use:

```bash
python scripts/capture_cli_help.py --version 0.32.0
```

### Acceptance
- fixtures are present in repo
- tests fail if fixtures are missing

---

## F2. Make missing fixtures fail loudly

### File
`core/cli_contract.py`

### Required
`check_fixtures()` must mark report unsupported if fixture directory or fixture file is missing.

### Already likely improved
Verify that:

```python
report.supported = False
```

is set when fixtures are missing.

### Acceptance
- missing fixtures cannot be interpreted as full compatibility

---

## F3. Make compatibility dialog merge fixture + live results

### File
`app.py`

### Required
The dialog must show:
- fixture compatibility
- live binary compatibility
- merged missing flags
- merged unknown flags
- notes from both sources

### Acceptance
- live binary incompatibility is not hidden by fixture compatibility

---

## F4. Add compatibility regression tests

### File
`test_app.py`

### Required tests
- allowed flags exist in fixtures
- missing fixtures produce unsupported report
- live report merging works
- dialog does not claim full compatibility when fixtures are missing

---

# 10. Workstream G — Process execution and terminal hardening

Phase 1 improved this; Phase 2 should finish it.

---

## G1. Verify preferred terminal handling

### File
`core/terminal_launcher.py`

### Required
- if preferred terminal is set but missing, fall back gracefully
- if no terminal is found, return a clear error
- cleanup lock/temp files on launch failure

### Acceptance
- bad terminal preference does not hang the app or leave stale state

---

## G2. Add stale temporary directory cleanup

### Why
If a machine reboots or a terminal is killed, temporary run directories may remain.

### Recommendation
Add a startup cleanup routine for old `immich-go-run-*` temp directories.

### Safety rules
Only delete directories that:
- match the known prefix
- are older than a safe threshold (e.g. 24 hours)
- are not associated with an active lock

### Acceptance
- old temp directories do not accumulate indefinitely

---

## G3. Keep heartbeat-based lock detection robust

### Required behavior
A lock should be considered active if any of these are true:
- shell PID is alive
- terminal PID is alive
- heartbeat file is fresh
- lock is within grace period

Otherwise stale.

### Acceptance
- stale locks can be cleaned automatically or reset safely

---

# 11. Workstream H — Test hardening and CI readiness

---

## H1. Remove duplicate test names

### File
`test_app.py`

### Required
No duplicated test function names.

### Why
Duplicate names silently override earlier tests.

### Acceptance
- every test function has a unique name

---

## H2. Add widget-to-command tests

### Rule
For every exposed widget:
- set a non-default value
- build command or validation result
- assert expected effect

### Acceptance
- no decorative controls can sneak back in

---

## H3. Add persistence roundtrip tests

### Required tests
- form state save/load
- advanced mode save/load
- preferred terminal save/load
- allow untested updates save/load

---

## H4. Add secret-safety tests

### Required tests
- profile rename does not clear old secrets if copy fails
- profile duplicate verifies secret copy
- keyring fallback still works when keyring is unavailable

---

## H5. Add binary update tests

### Required tests
- downgrade blocked
- asset URL selection chooses correct OS/arch
- cancel returns failure
- extraction failure returns failure
- post-install verification failure returns failure

---

## H6. Make GUI tests headless-friendly

### Required
Use offscreen Qt platform in CI.

Example:

```bash
QT_QPA_PLATFORM=offscreen pytest
```

### Acceptance
- GUI tests run in CI without a real display

---

## H7. Add CI workflow

### Recommended file
`.github/workflows/ci.yml`

### Minimum jobs
- install dependencies
- run pytest headlessly
- verify fixtures exist
- optionally build package artifact

### Acceptance
- pull requests are automatically tested

---

# 12. Workstream I — Release gate and manual QA

Phase 2 is not complete until a human verifies real-world behavior.

---

## I1. Minimum manual smoke test matrix

### Windows
- [ ] app launches
- [ ] managed binary detected
- [ ] external terminal opens
- [ ] dry-run works
- [ ] live run works
- [ ] lock removed after terminal closes
- [ ] stale lock reset works
- [ ] update flow works

### Linux
- [ ] app launches
- [ ] preferred terminal works
- [ ] fallback terminal works
- [ ] dry-run works
- [ ] live run works
- [ ] lock removed after terminal closes
- [ ] stale lock reset works
- [ ] keyring save/load works

### macOS
- [ ] app launches
- [ ] Terminal opens
- [ ] dry-run works
- [ ] live run works
- [ ] lock removed after terminal closes
- [ ] update flow works

---

## I2. Release candidate checklist

Before tagging an RC:

- [ ] all automated tests pass
- [ ] fixtures committed
- [ ] no duplicate tests
- [ ] no known false affordances
- [ ] binary update flow verified
- [ ] profile secret safety verified
- [ ] compatibility dialog verified
- [ ] manual smoke test passed on at least one OS
- [ ] no secrets visible in UI or copied command
- [ ] no invalid CLI flags emitted

---

# 13. Recommended Phase 2 execution order

To reduce regressions, the agent should execute in this order:

---

## Step 1 — Command/schema completeness
1. Finalize `TAB_ALLOWED_FLAGS`
2. Add missing emissions (`stack` device UUID, optional source admin)
3. Add golden tests for all tabs

---

## Step 2 — UI completeness
1. Ensure all existing tabs expose the important flags
2. Enforce Simple/Advanced split
3. Remove false affordances
4. Persist advanced mode and advanced settings

---

## Step 3 — Validation and persistence safety
1. Add server URL validation
2. Add GP path warnings
3. Verify archive destination warnings
4. Make secret/profile operations safe
5. Add persistence roundtrip tests

---

## Step 4 — Binary update safety
1. Prevent downgrades
2. Use release asset discovery
3. Replace `terminate()` with cooperative cancel
4. Make `update_binary()` truthful
5. Add post-install verification

---

## Step 5 — Compatibility and CI
1. Commit CLI fixtures
2. Make missing fixtures fail
3. Merge live + fixture compatibility results
4. Add CI workflow
5. Run headless GUI tests

---

## Step 6 — Manual QA and release candidate
1. Run manual smoke tests
2. Verify terminal behavior
3. Verify update flow
4. Tag RC only after all checks pass

---

# 14. Phase 2 acceptance checklist

The agent should not declare Phase 2 complete until all of these are true:

## CLI correctness
- [ ] no invalid flags in any tab
- [ ] no missing important flags in any existing tab
- [ ] boolean defaults handled correctly
- [ ] repeatable flags handled correctly
- [ ] CSV fields normalized correctly
- [ ] secrets never appear in argv

## UI
- [ ] Simple mode remains clean
- [ ] Advanced mode exposes power-user controls
- [ ] advanced mode persists
- [ ] no decorative controls remain

## Validation
- [ ] required fields validated
- [ ] server URL validated
- [ ] path warnings shown
- [ ] destination warnings shown
- [ ] destructive warnings shown
- [ ] plan errors block execution

## Persistence
- [ ] form state persists
- [ ] advanced settings persist
- [ ] profile secrets copied safely
- [ ] failed secret copy does not delete old secrets

## Binary management
- [ ] no accidental downgrades
- [ ] asset discovery works
- [ ] cancel works safely
- [ ] update_binary returns truthful result
- [ ] extracted binary verified

## Compatibility
- [ ] fixtures committed
- [ ] missing fixtures fail
- [ ] live + fixture results merged
- [ ] compatibility dialog truthful

## Tests
- [ ] unique test names
- [ ] golden tests for all tabs
- [ ] widget-to-command tests
- [ ] persistence tests
- [ ] secret-safety tests
- [ ] binary update tests
- [ ] CI passes headlessly

---

# 15. Final guidance to the agent

When in doubt, prioritize in this order:

1. **Do not generate invalid CLI commands**
2. **Do not lie to the user in the UI**
3. **Do not silently lose secrets or settings**
4. **Do not ship a broken update flow**
5. **Do not rely on tests that can silently pass**

Phase 2 is not about adding more novelty features.

It is about making the existing app:

- complete
- predictable
- safe
- testable
- release-ready

If the agent completes this phase correctly, the app should be ready to move from “strong prototype” to **release candidate** quality.