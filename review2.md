Yes — I’ll be blunt.

The project is **structurally strong**, and the refactor into `core/` is a real improvement. But if we’re treating review sections **3–8 as “implemented”**, I do **not** agree that they’re truly done. You have a lot of the right machinery now — schema/allowlists, secret env passing, profiles, locks, validation, binary management — but there are still several places where the GUI either:

1. **shows options that never reach the CLI**,  
2. **emits flags that do not match the documented `immich-go` CLI**, or  
3. **fails silently instead of telling the user something is wrong**.

That is more dangerous than simply missing features, because it can produce **incorrect imports/archives/stacking behavior without obvious error**.

I’m ignoring the `__init__` rendering artifact issue as you asked, and I’m also not treating “no `--no-ui`” as a defect.

---

# Overall verdict

## What is genuinely good
These parts are already strong:

- clean separation between `core` and Qt UI
- secret handling is much better than typical GUI wrappers
- command preview with masked secrets is excellent UX
- profile support is a big usability win
- validation helpers are much better than before
- binary management is ambitious and useful
- theme system is polished
- the app already feels like a real product, not a toy

## The main problem now
The biggest remaining weakness is **operational correctness**:

- CLI flag mapping is still not trustworthy
- some UI controls are decorative rather than functional
- some errors are swallowed or never shown
- process/lock tracking can get stuck
- binary update flow is still not safe enough
- tests enshrine some incorrect CLI assumptions

So: **good architecture, but not yet reliable enough for power users**.

---

# Critical issues

These are the ones I would fix before calling sections 3–8 “done”.

---

## 1. Archive destination flag appears to be wrong: `--write-to` vs `--write-to-folder`

### Evidence
From the CLI help:

- `immich-go archive` uses:
  - `-w, --write-to-folder string`

But your code uses:

- `core/cli_schema.py`: `TAB_ALLOWED_FLAGS` includes `"write-to"`
- `core/command_builder.py`: emits `--write-to=...`
- `app.py` tests expect `--write-to=...`

### Why this matters
If the CLI help you provided is accurate, then archive commands are likely **invalid**:

```bash
archive from-folder --write-to=/dest
```

instead of:

```bash
archive from-folder --write-to-folder=/dest
```

### Impact
This is not a minor naming issue. It can make the entire archive workflow fail or behave unpredictably.

### Fix
Rename the internal flag and emitter to:

- `write-to-folder`

Also update:
- schema
- command builder
- tests
- golden fixtures

This is a showstopper-level mismatch.

---

## 2. `archive from-immich` server/auth model looks fundamentally mismatched

### Evidence
From CLI help, `immich-go archive from-immich` uses source-style flags:

- `--from-server`
- `--from-api-key`
- `--from-admin-api-key`
- `--from-skip-verify-ssl`
- `--from-client-timeout`
- `--from-date-range`
- `--from-albums`
- etc.

But your implementation does this:

- `SERVER_REQUIRED_TABS` includes `archive-immich`
- `command_builder.py` emits global `--server=...`
- `ENV_KEY_MAP` uses:
  - `IMMICH_GO_ARCHIVE_SERVER`
  - `IMMICH_GO_ARCHIVE_API_KEY`
- UI label says **“Target Server”**
- there is no explicit source server/source API key entry for this tab

### Why this matters
For `archive from-immich`, the Immich server is the **source** being archived from, not a “target” in the upload sense.

If the CLI really expects `--from-server` / `--from-api-key`, then your current command shape is likely wrong:

```bash
archive from-immich --server=... --write-to=...
```

when it likely needs something more like:

```bash
archive from-immich --from-server=... --write-to-folder=...
```

with source credentials passed appropriately.

### Impact
This is one of the most serious functional risks in the app.

### Fix
Rework `archive-immich` around the actual CLI contract:

- use `--from-server`
- use source API key mechanism correctly
- use `--from-skip-verify-ssl`
- use `--from-client-timeout`
- relabel UI from **Target Server** to **Source Server**
- decide whether global `--dry-run` is enough or whether `--from-dry-run` is also required
- update `ENV_KEY_MAP` and terminal secret forwarding accordingly

This tab needs a correctness pass, not just polish.

---

## 3. Many Google Photos options are exposed in the UI but ignored by the command builder

This is a classic “false affordance” problem.

### Evidence
In `app.py`, `_build_upload_gp_tab()` exposes:

- include type
- include unmatched
- include partner
- sync albums
- include archived
- include trashed
- from album name
- partner shared album
- takeout tag
- people tag

But in `core/command_builder.py`, the `upload-gp` branch only emits a small subset:

- burst
- raw+jpeg
- heic+jpeg
- include-untitled-albums
- date-range
- include/exclude extensions
- ban-file
- tag
- session-tag
- api-trace

It does **not** emit:

- `--include-type`
- `--include-unmatched`
- `--include-partner`
- `--include-trashed`
- `--include-archived`
- `--sync-albums`
- `--from-album-name`
- `--partner-shared-album`
- `--takeout-tag`
- `--people-tag`

And `TAB_ALLOWED_FLAGS["upload-gp"]` is missing many of these too.

### Why this matters
The user can change these checkboxes/combos, but the generated command does not reflect their choices.

That is worse than not having the controls at all.

### Examples
If the user:

- unchecks **Include Archived**
- unchecks **Include Partner Photos**
- unchecks **Sync Google Albums**
- checks **Include Trashed**
- enters a **From Specific Album**
- sets **Media Type = VIDEO**

your app currently gives the impression that this matters, but the CLI command may remain unchanged.

### Impact
This can lead to:
- importing more than intended
- importing partner/trashed/archived content unexpectedly
- failing to restrict to a chosen album
- user distrust when behavior doesn’t match the UI

### Fix
Either:

1. wire these controls properly to the CLI flags, or  
2. remove/disable them until they are implemented

For boolean flags with defaults, remember you may need explicit false emission, e.g.:

```bash
--include-archived=false
--include-partner=false
--sync-albums=false
--takeout-tag=false
--people-tag=false
```

not just omitting the flag.

---

## 4. Stack tab has exposed options that are ignored or blocked by the allowlist

### Evidence
`app.py` stack tab exposes:

- `time-zone`
- `manage-epson`
- `api-trace`

But:

- `TAB_ALLOWED_FLAGS["stack"]` does **not** include:
  - `api-trace`
  - `time-zone`
  - `manage-epson-fastfoto`
- `command_builder.py` stack branch does not emit:
  - `time-zone`
  - `manage-epson-fastfoto`
- it tries to emit `api-trace`, but the allowlist blocks it

### Why this matters
Because `FlagEmitter` is non-strict in the GUI, blocked flags are dropped and collected in `plan.errors`, but those errors are not shown to the user.

So the user checks **Enable API Trace**, and nothing happens.

### Impact
Silent feature failure.

### Fix
Add the missing flags to the stack allowlist and builder if they are intended:

- `api-trace`
- `time-zone`
- `manage-epson-fastfoto`

Also consider whether these should be exposed:
- `date-range`
- `pause-immich-jobs`
- `device-uuid`
- `concurrent-tasks`

because the CLI supports them for `stack`.

---

## 5. `plan.errors` are generated but never surfaced

This is a systemic issue.

### Evidence
`FlagEmitter` collects errors when a flag is not allowed:

```python
self.errors.append(err)
```

and `build_plan_from_state()` extends:

```python
plan.errors.extend(emitter.errors)
```

But:

- `show_confirm_dialog()` only checks `validation.errors`
- `run_command()` does not check `plan.errors`
- `update_status()` does not consider `plan.errors`

### Why this matters
You can build a plan with invalid/dropped flags and still show a “valid” command preview.

That means the GUI can silently omit options the user thought were enabled.

### Impact
This is one of the biggest correctness gaps in the whole app.

### Fix
Before showing the confirm dialog or running:

- check `plan.errors`
- display them clearly
- block execution if any exist

Better yet:
- make the GUI builder strict enough that schema violations are treated as hard errors during development/testing

---

## 6. Process/lock tracking can get stuck because stale-lock detection is effectively not working

### Evidence
`core/process_tracker.py`:

- `create_lock()` writes `gui_pid`
- `RunLock` has `shell_pid`
- but no code ever writes `shell_pid` into the lock file

Then `is_lock_active()` does:

```python
if lock.shell_pid and os.name == "posix":
    ...
return True
```

So if `shell_pid` is absent, a lock file is treated as active merely because it exists.

### Why this matters
If the terminal/script cleanup fails, or the machine reboots, or the terminal emulator misbehaves, the lock can become stale — but your app will still think a process is running.

### Additional UI bug
In `app.py`:

```python
is_running = getattr(self, "running_process", None) is not None
```

But you later set:

```python
self.running_process = False
```

Since `False is not None` evaluates to `True`, once `running_process` has been set to `False`, `update_status()` can continue behaving as if a process is still running.

### Impact
This can cause:

- Run/Preview buttons staying disabled
- “command still running” warning persisting
- reset run state not visually fixing the state
- a generally broken run lifecycle

### Fix
You need both:

#### A. Fix the boolean logic
Use something like:

```python
is_running = bool(getattr(self, "running_process", False))
```

or initialize and manage a proper state enum.

#### B. Make lock tracking real
Either:

- record a meaningful process identifier and check liveness, or
- implement a more robust heartbeat/cleanup strategy

As it stands, `shell_pid` is dead code and stale-lock recovery is mostly theoretical.

---

## 7. POSIX terminal launcher does not forward all required secret environment variables

### Evidence
`core/terminal_launcher.py` writes only a hardcoded list of secret keys into `env.sh`.

It includes upload/stack keys, but appears to miss:

- `IMMICH_GO_ARCHIVE_SERVER`
- `IMMICH_GO_ARCHIVE_API_KEY`
- `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY`

### Why this matters
On Linux/macOS, if a secret is not in that hardcoded list, it will not be sourced into the launched terminal environment.

So even if `plan.env` contains the value, the actual executed command may never receive it.

### Impact
This can cause authentication failures on POSIX systems that do not occur on Windows, because Windows passes the full `env` directly to `Popen`.

### Fix
Do not maintain a fragile hardcoded list if you can avoid it.

Safer approaches:

- forward all keys beginning with `IMMICH_GO_` from `plan.env`, or
- explicitly generate a complete secret env list from `ENV_KEY_MAP`

The current mismatch between `ENV_KEY_MAP` and `terminal_launcher.secret_keys` is a bug factory.

---

# High-priority issues

These are not always immediate showstoppers, but they still materially weaken the app.

---

## 8. The CLI allowlist/schema is still drifting from the real CLI

The idea behind `TAB_ALLOWED_FLAGS` is excellent. The execution is not there yet.

### Examples of schema problems

#### A. `upload-folder` allows `album-picasa`
But the CLI help for `upload from-folder` does **not** show `--album-picasa`.

That flag belongs to Picasa workflows, not generic folder upload.

#### B. `archive-folder` is missing real archive flags
The CLI supports things like:

- `--folder-as-album`
- `--folder-as-tags`
- `--album-path-joiner`
- `--into-album`

but your `archive-folder` allowlist and UI are much narrower.

That’s fine if intentional, but then the schema should reflect the actual supported subset deliberately, not accidentally.

#### C. `concurrent-tasks` is not allowed for some tabs where the CLI appears to support it
For example:

- `archive-folder`
- `archive-immich`
- `stack`

If the user changes concurrent tasks in config, the emitter may silently drop it for those tabs.

#### D. `client-timeout` scoping is questionable
You emit `client-timeout` broadly, but for local archive operations it may not be meaningful.

### Fix
You need a deliberate matrix of:

- global flags
- command flags
- subcommand flags
- tab-exposed flags
- CLI-supported flags

Right now the schema is partially correct, partially aspirational, and partially outdated.

---

## 9. Some command paths use raw paths/globs inconsistently

### Evidence
- `validation.expand_source_paths()` expands globs recursively for warnings
- `command_builder.collect_paths()` expands globs non-recursively
- `upload-folder` and `archive-folder` often append the raw path instead of expanded paths

### Why this matters
If a user enters a glob pattern, validation may behave differently from the actual command construction.

Also, since you launch via subprocess without a shell, glob expansion is not guaranteed unless `immich-go` itself handles it.

### Impact
Possible mismatches between:
- what validation says
- what the user expects
- what the CLI receives

### Fix
Decide one path-handling contract:

- if the CLI supports globs natively, document and preserve patterns
- if it does not, expand consistently before execution
- make recursive glob behavior consistent

Right now it’s too ambiguous.

---

## 10. Relative paths + external terminal working directory is a latent bug

### Evidence
`terminal_launcher.py` changes the working directory:

- Windows bat: `cd /d "%~dp0"`
- POSIX run script: `cd <temp dir>`

But command building does not force all paths to absolute.

### Why this matters
If the user types a relative source or destination path, the command may be executed from a different working directory than expected.

### Impact
Commands that work when tested from the project directory may fail from the GUI.

### Fix
Normalize user-provided paths to absolute paths before building the command, especially for:

- source paths
- archive destination paths
- takeout paths

This is especially important because you are intentionally isolating the launched terminal environment.

---

## 11. Binary update flow is still not safe enough

This was already called out in the review, and it’s still not where it should be.

### Main problems

#### A. Possible downgrade prompting
`BinaryManager.evaluate_update()` does not robustly handle:

- current version newer than latest tested
- already up to date
- latest older than current

So you can still prompt users to “update” to an older tested version.

#### B. Download URL guessing
`get_download_url()` constructs release asset names by convention:

```python
immich-go_{version}_{os}_{arch}{ext}
```

That is fragile if upstream naming changes.

#### C. No checksum verification
You compute SHA256 after extraction, but you do not verify against a known good checksum.

#### D. `QThread.terminate()` is used for cancel
That is explicitly discouraged in Qt and can leave state inconsistent.

#### E. In-memory download
Fine for small binaries, less ideal for robustness.

#### F. Duplicated update/extraction logic
`BinaryManager` already contains download/extract/select helpers, but `app.py` still has its own parallel flow.

#### G. `update_binary()` return value is misleading
It can return `True` even when the user cancels or extraction fails, depending on how the flow unwinds.

### Fix
Centralize update logic in `BinaryManager` or a controller, and make it:

- version-comparison aware
- asset-discovery based
- checksum-verifying
- cancellation-safe
- temp-file based
- explicit about success/failure

Right now this subsystem is ambitious but still too fragile.

---

## 12. Some model settings exist but are not exposed in the UI

### Examples
`AppConfig` includes:

- `advanced_mode`
- `allow_untested_updates`
- `preferred_terminal`

But the UI does not seem to expose or persist all of them properly.

### Specific issues
- advanced mode is not restored/persisted
- `allow_untested_updates` is checked in update logic but not user-configurable
- `preferred_terminal` exists but has no settings UI

### Why this matters
This creates hidden behavior:

- users cannot enable untested updates even when appropriate
- users cannot choose a terminal emulator
- UI state is lost across restarts

### Fix
Either:
- expose these settings, or
- remove them from the config model until they are real features

Dead config fields create confusion.

---

## 13. Secret/profile operations can still lose data in edge cases

You improved this area a lot, but not completely.

### Problem areas

#### A. `SecretStore.copy_secrets()` silently ignores failures
It returns bool, but callers often ignore it.

#### B. `rename_profile()` copies secrets, then clears old ones
If the copy step fails silently, clearing the old secret can cause loss.

#### C. App-level QSettings migration ignores save result
In `app.py`:

```python
set_api_key(old_key, cfg)
self.settings.remove("api_key")
```

If the save fails, the old key may still be removed.

### Fix
For secret migration/copy/rename:

- verify success before deleting old secrets
- propagate errors
- log failures
- avoid silent `except: pass` in critical secret paths

You are close, but not fully safe yet.

---

## 14. Compatibility checking can give false confidence

### Evidence
`core/cli_contract.check_fixtures()` skips tabs when fixture flags are empty:

```python
if not fixture_flags:
    continue
```

So if fixtures are missing, the report can appear fully compatible by default.

Also, `app.show_cli_compatibility_dialog()` computes a live report, but then mostly displays the fixture report and does not properly merge live missing/unknown flags.

### Why this matters
The compatibility dialog can say “compatible” when:
- fixtures are absent
- live binary mismatch exists but fixture report is clean

### Fix
The compatibility dialog should:

- clearly distinguish fixture compatibility vs live binary compatibility
- warn when fixtures are missing
- merge and display live report details
- not treat missing data as success

This feature is very useful, but currently not trustworthy enough.

---

# Medium-priority issues

These are important, but less urgent than the critical/high items.

---

## 15. Some UI labels are still misleading

### Biggest offender
`archive-immich` still says **Target Server** in the UI.

For an archive-from-Immich operation, that server is conceptually the **source**.

### Fix
Use labels like:

- **Source Server**
- **Destination Folder**
- **Immich Server** for stack/upload destination where appropriate

This matters more than it seems because migration/backup workflows are easy to misunderstand.

---

## 16. Warnings are not visible early enough

You do generate useful warnings:

- SSL skip
- overwrite
- destructive RAW/JPEG/HEIC modes
- destination inside source

But many warnings only appear in the confirm dialog.

### Better UX
Show important warnings closer to the input field, or in a persistent inline area, especially for:

- skip SSL
- overwrite
- destructive pair handling
- destination inside source

This would reduce accidental misconfiguration.

---

## 17. `update_status()` is doing too much work on every keystroke

### Evidence
You connect many widgets directly to `update_status()`, which calls `validate_inputs()`, which can expand globs and inspect paths.

### Why this matters
For path fields, this can become expensive if the user types:
- large globs
- slow network paths
- recursive patterns

### Fix
Debounce validation for text inputs, especially:
- source paths
- manual binary path
- destination paths

Also, manual binary path checking on every keystroke can spawn subprocesses too often. Use `editingFinished` or a timer.

---

## 18. The running warning is hidden on the Configuration page

### Evidence
The running warning lives in the footer, and the footer is hidden on the config tab.

### Why this matters
If a job is running and the user switches to Configuration, the warning disappears.

### Fix
Use a more global indicator:
- status card
- header badge
- always-visible banner when a lock is active

---

## 19. Theme/icon state handling is not complete

### Issue
Sidebar icons are recolored by theme, but not by checked state.

So a selected nav item may have highlighted text but still use the muted icon color.

### Fix
Generate or cache icon variants for:
- normal
- hovered
- checked

or use proper `QIcon` state/mode pixmaps.

This is polish, but it makes the app feel much more finished.

---

## 20. Some combo state persistence is text-based and fragile

### Evidence
`collect_form_state()` stores `QComboBox.currentText()`.

That is okay for simple cases, but fragile for:
- secret provider
- on-errors custom mode
- future localized labels

### Fix
Use item data instead of display text wherever the value is semantic.

This avoids encoding/label mismatch problems and makes state persistence more robust.

---

## 21. `Card.layout` shadows Qt’s `layout()` method

You assign:

```python
self.layout = QVBoxLayout(self)
```

This shadows the QWidget `layout()` method.

It may work, but it is risky and can cause confusing behavior later.

### Fix
Use:
- `self._layout`
- or `setLayout(...)` and access via `layout()`

This is a code-quality issue, but worth fixing before the codebase grows further.

---

# Testing critique

You have made real progress on tests, but there are important weaknesses.

---

## 22. Some golden tests enshrine incorrect CLI assumptions

For example, tests currently expect:

- `--write-to=...`
- `archive from-immich --server=...`

If the CLI help is correct, those tests are protecting the wrong behavior.

### Fix
Audit golden tests against the actual CLI contract, not against the current builder.

Tests should prevent regressions, not cement bugs.

---

## 23. Duplicate test names silently disable tests

In `test_app.py`, there are duplicated function names, e.g.:

- `test_api_trace_on_stack`
- `test_golden_archive_folder`

In Python, the later definition silently overrides the earlier one.

### Impact
You may think you have coverage that is not actually running.

### Fix
Rename tests uniquely and add a lint rule for duplicate test names.

---

## 24. Missing tests for “UI option actually affects command”

You have tests for many happy paths, but not enough tests that say:

- if I toggle this GP checkbox, the emitted command changes
- if I choose VIDEO include type, `--include-type=VIDEO` appears
- if I disable archived/partner/sync, the correct false flags appear
- if I set stack time zone, it appears in argv

Right now, many UI controls are untested against actual command emission.

### Fix
Add widget-to-plan tests for every exposed control.

If a control exists, a test should prove it matters.

---

## 25. Compatibility fixtures need to be first-class artifacts

The fixture approach is good, but the fixtures need to be:

- committed
- versioned
- exercised in CI
- checked for absence (fail loudly if missing)

Otherwise the compatibility system can silently become decorative.

---

# Security critique

You are already above average here, but a few things remain.

---

## 26. Environment-variable secret passing is still an unverified contract

The whole secret strategy depends on `immich-go` honoring variables like:

- `IMMICH_GO_UPLOAD_SERVER`
- `IMMICH_GO_UPLOAD_API_KEY`
- `IMMICH_GO_ARCHIVE_API_KEY`
- etc.

But the CLI help you provided does not document those env vars.

### Why this matters
If upstream does not actually support these variables, your app may fail authentication while showing a “secure” command preview.

### Fix
Verify the env-var contract explicitly.

If it is not stable, consider:
- temporary config file generation with restrictive permissions
- or another non-argv secret mechanism

Do not build the whole security model on an undocumented interface unless you control it or have verified it.

---

## 27. POSIX temp secret files can remain after abnormal termination

You do set `0600` and clean up on exit, which is good.

But if the process is killed abruptly, `env.sh` may remain in a temp directory.

### Fix
Consider:
- shorter-lived temp paths
- best-effort startup cleanup of old immich-go-run temp dirs
- or avoiding secret files entirely where possible

Not catastrophic, but worth noting.

---

# Architecture / code-quality critique

---

## 28. `app.py` is still doing too much

This was already true before, and it still is.

`app.py` contains:
- main window
- custom widgets
- page construction
- process launching glue
- update flow
- profile menu logic
- theme handling
- persistence glue

It is manageable for now, but if you add the missing CLI options and workflows, this file will become a liability.

### Fix
When you do the next pass, split into:

- `widgets/`
- `pages/`
- `controllers/`
- `dialogs/`

Especially separate:
- update controller
- run controller
- profile controller
- compatibility controller

---

## 29. Too many magic strings remain

You still have many repeated string keys:

- tab keys
- field names
- flag names
- provider names
- status states

This increases the chance of subtle bugs.

### Fix
Introduce constants/enums for:
- tab identifiers
- form field keys
- secret provider values
- support states

This will make refactoring much safer.

---

## 30. Silent exception handling is still too common in backend helpers

There are still many places where exceptions are swallowed or reduced to empty results.

That may be acceptable for optional UI conveniences, but not for:
- secret migration
- metadata corruption
- config save/load
- binary extraction
- compatibility fixtures

### Fix
Add structured logging and differentiate:
- expected recoverable cases
- unexpected failures that should be surfaced

Right now the app is sometimes too quiet when something goes wrong.

---

# What I would prioritize next

If this were my project, I would do this in order:

---

## Phase 1 — Correctness first
1. Fix archive flag:
   - `write-to` → `write-to-folder`
2. Fix `archive-immich` source-server/auth model
3. Surface `plan.errors` everywhere
4. Wire or remove all non-functional GP controls
5. Fix stack flag allowlist/builder mismatches
6. Fix `running_process` boolean bug
7. Make stale-lock detection real

---

## Phase 2 — CLI contract hardening
8. Rebuild `TAB_ALLOWED_FLAGS` directly from captured CLI help
9. Add missing flags where appropriate:
   - concurrent tasks
   - stack time zone / epson / api-trace
   - GP album/partner/trash/archived/sync controls
10. Verify env-var secret contract or replace it with temporary config generation
11. Normalize all paths to absolute before execution

---

## Phase 3 — Safety and reliability
12. Make binary updates:
   - comparison-aware
   - asset-discovery based
   - checksum-verifying
   - cancel-safe
13. Make secret copy/rename/migration verify success before deleting old data
14. Add debouncing for path/manual-binary validation
15. Add real run-state recovery/reset behavior

---

## Phase 4 — Test repair
16. Fix duplicate test names
17. Replace incorrect golden expectations
18. Add tests proving every visible widget changes the generated command
19. Make missing compatibility fixtures a hard failure
20. Add stale-lock and terminal-env tests

---

# Bottom line

The app is already **well above average** for a GUI wrapper.

But if I’m being a critic, the honest assessment is:

- **architecture: strong**
- **UX: strong**
- **security direction: strong**
- **CLI correctness: not yet trustworthy**
- **process lifecycle: still fragile**
- **tests: useful, but partly protecting the wrong behavior**

The most important thing to understand is this:

> The biggest remaining risk is not missing features.  
> It is that the GUI can look correct while generating an incorrect command.

Once you eliminate silent flag mismatches and non-functional controls, this will be in much better shape.

If you want, I can next turn this critique into a **prioritized GitHub issue list** or a **concrete patch plan for the critical fixes only**.