Below is a **detailed, handoff-ready guide** for an AI agent to fix the **critical issues** and, at the same time, make the GUI **functionally complete for the existing tabs**.

I’m assuming:

- `review.md` sections **10, 15, 17 remain out of scope**
- we **do not add `--no-ui`**
- external terminal execution remains the primary run model
- “complete” means:
  - all currently exposed controls actually work
  - all important CLI flags for the existing tabs are exposed
  - simple/advanced mode is respected
  - invalid flags are removed
  - command generation is trustworthy

---

# 1. Objective for the AI agent

You are fixing two things at once:

## A. Critical correctness issues
These are blockers:

1. wrong archive flag: `--write-to` must become `--write-to-folder`
2. wrong `archive from-immich` server/auth model
3. silent command-builder/schema errors
4. UI controls that do not affect the generated command
5. invalid flags / invalid tab options still present in schema or UI
6. broken running-state / stale-lock handling
7. incomplete secret forwarding to external terminal
8. incomplete CLI coverage for existing tabs

## B. Functional completeness
For the **existing tabs only**, make the app expose the important CLI options correctly:

- `upload from-folder`
- `upload from-google-photos`
- `upload from-immich`
- `archive from-folder`
- `archive from-immich`
- `stack`

Do **not** merely add widgets. Every widget must map to:

- state collection
- command emission
- validation
- persistence
- tests

---

# 2. Non-negotiable constraints

The agent must respect all of the following:

## 2.1 No secrets in `argv`
Never emit:

- `--api-key`
- `--from-api-key`
- `--admin-api-key`
- `--from-admin-api-key`

Secrets must be passed only through:

- environment variables, or
- a future secure config-file mechanism if environment support is proven unreliable

For now, keep the environment-variable approach, but make it complete and consistent.

## 2.2 No `--no-ui`
Do not introduce `--no-ui` anywhere.

## 2.3 Preserve external terminal model
Do not replace external terminal execution with an embedded runner in this pass.

## 2.4 Simple mode must remain simple
Advanced mode is for:

- less-common flags
- filtering
- debug/trace
- dangerous or power-user options
- compatibility/version/terminal preferences

Simple mode must show only:

- required fields
- common workflow choices
- high-impact safe options

## 2.5 Do not keep false affordances
If a flag is not valid for a tab, remove it from:

- UI
- state collection
- schema
- command builder
- tests

Do not leave controls that “look useful” but do nothing.

---

# 3. Definition of done

The work is complete only when:

## 3.1 CLI correctness
- Every emitted flag is valid for that exact subcommand
- Every visible control affects the generated command or is intentionally disabled/hidden
- No invalid flags remain in `TAB_ALLOWED_FLAGS`
- No invalid controls remain in the UI
- `plan.errors` are surfaced and block execution

## 3.2 Functional completeness
For the existing tabs:

- all important missing flags are exposed
- defaults are handled correctly
- boolean flags with default `true` emit `--flag=false` when disabled
- repeatable flags are emitted correctly
- CSV flags are normalized correctly
- paths are made absolute before execution

## 3.3 Process safety
- running state cannot get permanently stuck because of a boolean bug
- stale locks can be detected and cleaned where reasonably possible
- reset run state actually clears UI state

## 3.4 Secret handling
- terminal launcher forwards all required `IMMICH_GO_*` variables
- archive secrets are included
- no secret is shown in command preview
- secret migration/copy operations do not silently lose data

## 3.5 Tests
- wrong golden tests are fixed
- duplicate test names are removed
- new tests prove each newly added control changes the command
- compatibility fixtures are present and exercised

---

# 4. Critical fixes: exact implementation guide

---

## Critical Fix 1 — Establish a single source of CLI truth

### Problem
The current schema is partly hand-maintained and has drifted from the CLI help.

### Required changes

#### 4.1.1 Add real CLI help fixtures
Create fixtures for `0.32.0` from the provided CLI documentation:

- `tests/fixtures/cli_help/0.32.0/root.txt`
- `tests/fixtures/cli_help/0.32.0/upload.txt`
- `tests/fixtures/cli_help/0.32.0/upload_from-folder.txt`
- `tests/fixtures/cli_help/0.32.0/upload_from-google-photos.txt`
- `tests/fixtures/cli_help/0.32.0/upload_from-immich.txt`
- `tests/fixtures/cli_help/0.32.0/archive.txt`
- `tests/fixtures/cli_help/0.32.0/archive_from-folder.txt`
- `tests/fixtures/cli_help/0.32.0/archive_from-immich.txt`
- `tests/fixtures/cli_help/0.32.0/stack.txt`

If needed, add a script that splits the master CLI help markdown into these fixtures.

#### 4.1.2 Make missing fixtures fail loudly
Update `core/cli_help.py` / `core/cli_contract.py` so that:

- tests fail if expected fixtures are missing
- compatibility dialog clearly says when fixtures are missing
- missing fixtures are not treated as “compatible”

#### 4.1.3 Rebuild `TAB_ALLOWED_FLAGS` from the fixtures
Do not keep the current list as-is.

Replace it with a corrected set based on actual CLI help.

Use the following as the corrected baseline for **emittable non-secret flags**:

```python
TAB_ALLOWED_FLAGS = {
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
```

#### 4.1.4 Remove invalid flags from current code
Specifically remove:

- `album-picasa` from `upload-folder`
- any idea of `write-to` for archive tabs
- any UI/schema/builder support for pair-handling flags in archive tabs unless the CLI help explicitly supports them

Based on the CLI help you provided:

- `archive from-folder` does **not** support `manage-raw-jpeg`
- `archive from-immich` does **not** support `manage-burst` or `manage-raw-jpeg`

So those controls must be removed from archive UI.

---

## Critical Fix 2 — Fix archive command generation

### Problem
Archive commands are currently wrong in two ways:

1. destination flag is wrong
2. `archive from-immich` uses the wrong server/auth model

---

### 4.2.1 Replace `write-to` with `write-to-folder`

#### In `core/command_builder.py`
For both:

- `archive-folder`
- `archive-immich`

change:

```python
emitter.add_option("write-to", tab_state["write-to"])
```

to:

```python
emitter.add_option("write-to-folder", tab_state["write-to"])
```

You may keep the internal state key as `"write-to"` to reduce migration pain, but the emitted CLI flag must be:

```bash
--write-to-folder=...
```

#### In tests
Update all expectations from:

```python
"--write-to=/dest"
```

to:

```python
"--write-to-folder=/dest"
```

---

### 4.2.2 Fix `archive from-immich` source model

`archive from-immich` is a **source-server** operation.

It must not emit:

```bash
--server=...
```

It should use:

```bash
--from-server=...
```

and source credentials should be supplied via the corresponding secret mechanism.

#### Required behavior
For `archive-immich`:

- use the configured global server as the **source server**
- relabel UI accordingly
- emit `--from-server=...`
- emit `--from-skip-verify-ssl` if SSL skip is enabled
- emit `--from-client-timeout=...` if timeout differs from default
- emit `--from-dry-run` in dry-run mode
- do **not** emit global `--server`
- do **not** emit global `--skip-verify-ssl`
- do **not** emit global `--client-timeout`

#### Command builder change
For `archive-immich`:

```python
if server:
    emitter.add_option("from-server", normalize_server_url(server))

if config_state.get("skip-ssl"):
    emitter.add_flag("from-skip-verify-ssl")

client_timeout = config_state.get("client_timeout", 20)
if client_timeout != 20:
    emitter.add_option("from-client-timeout", f"{client_timeout}m")
```

#### Environment map change
Update `ENV_KEY_MAP["archive-immich"]` to source-style names, for example:

```python
"archive-immich": {
    "from_server": "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER",
    "from_api_key": "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_API_KEY",
    "from_admin_api_key": "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_ADMIN_API_KEY",
},
```

Then update `build_environment()` so that for `archive-immich`:

- config `server` maps to `from_server`
- config `api_key` maps to `from_api_key`
- config `admin_api_key` maps to `from_admin_api_key`

#### UI label change
In `archive-immich` tab:

- change “Target Server” to **“Source Server”**
- explain that it comes from Configuration

Example hint:

> “Archive source server is configured in the Configuration tab.”

---

## Critical Fix 3 — Surface `plan.errors` everywhere

### Problem
`FlagEmitter` can collect errors, but the GUI ignores them.

### Required changes

#### 4.3.1 Block confirm dialog on `plan.errors`
In `show_confirm_dialog()` after building the plan:

```python
plan = self.build_plan(dry_run=is_dry_run)

if plan.errors:
    QMessageBox.critical(
        self,
        "Command Build Errors",
        "\n".join(f"• {e}" for e in plan.errors)
    )
    return
```

#### 4.3.2 Block `run_command()` on `plan.errors`
If `run_command()` builds a plan itself, also check:

```python
if plan.errors:
    QMessageBox.critical(...)
    return
```

#### 4.3.3 Make tests use strict schema enforcement
For pure command-builder tests, prefer:

```python
FlagEmitter(tab_key, strict=True)
```

or assert:

```python
assert plan.errors == []
```

for every valid UI state.

---

## Critical Fix 4 — Fix broken running-state logic

### Problem
`app.py` currently does:

```python
is_running = getattr(self, "running_process", None) is not None
```

but later sets:

```python
self.running_process = False
```

Since `False is not None` is `True`, the GUI can think a process is still running after it has finished.

### Required fix

Prefer using the lock path as the source of truth.

#### In `ImmichGoGUI.__init__`
Initialize:

```python
self.active_lock_path = None
```

#### In `update_status()`
Replace the running check with:

```python
is_running = bool(getattr(self, "active_lock_path", None))
```

or, if you keep `running_process`, use:

```python
is_running = getattr(self, "running_process", False) is True
```

But the lock-path approach is cleaner.

#### In `_check_lock_file()`
When inactive:

```python
self.active_lock_path = None
self.running_process = False
```

When active:

```python
self.running_process = True
```

#### In `on_reset_run_state_clicked()`
After resetting locks:

```python
self.active_lock_path = None
self.running_process = False
```

Then call:

```python
self.update_status()
```

---

## Critical Fix 5 — Make stale-lock detection real

### Problem
`shell_pid` is stored in the model but never written by the launcher.  
As a result, stale-lock detection is mostly ineffective.

### Required improvements

This should be implemented in a pragmatic, best-effort way.

---

### 4.5.1 Extend lock metadata
In `core/process_tracker.py`, add support for:

- `shell_pid`
- `terminal_pid`
- `last_seen`
- optional heartbeat file

Example lock JSON:

```json
{
  "run_id": "abc123",
  "gui_pid": 1234,
  "started_at": "...",
  "tab_key": "upload-folder",
  "command_summary": "...",
  "binary_path": "...",
  "shell_pid": null,
  "terminal_pid": null,
  "last_seen": null
}
```

Add helpers:

```python
def update_lock(lock_path: Path, **fields) -> None: ...
def touch_heartbeat(lock_path: Path) -> None: ...
```

---

### 4.5.2 Make terminal launcher record process info
In `core/terminal_launcher.py`:

#### POSIX
When launching via terminal:

- write a sidecar PID file if possible
- have `run.sh` write its own PID
- add a heartbeat loop while the command runs

Example idea:

```bash
echo $$ > lock_pid_file
(
  while true; do
    touch heartbeat_file
    sleep 30
  done
) &
HEARTBEAT_PID=$!
```

Then cleanup both on exit.

#### Windows
Best-effort:

- capture the launched process PID from `Popen`
- store it in the lock as `terminal_pid`
- if feasible, use a PowerShell wrapper that can maintain a heartbeat or at least record PID

If Windows heartbeat is too fragile, then at minimum:

- store PID
- allow manual reset
- clean locks when PID is provably dead where possible

---

### 4.5.3 Improve `is_lock_active()`
Use this logic:

1. if lock file missing → inactive
2. if `shell_pid` exists and process alive → active
3. if `terminal_pid` exists and process alive → active
4. if heartbeat file exists and is fresh → active
5. if lock is very recent (e.g. < 60 seconds) and no heartbeat yet → active
6. otherwise → stale

This prevents permanent lock stickiness.

---

## Critical Fix 6 — Forward all required secrets to external terminal

### Problem
POSIX terminal launcher uses a hardcoded secret list and misses archive-related variables.

### Required fix

In `core/terminal_launcher.py`, stop maintaining a brittle hardcoded list.

Instead, export all environment variables beginning with:

```python
IMMICH_GO_
```

Example:

```python
for k, v in env.items():
    if k.startswith("IMMICH_GO_"):
        env_lines.append(f"export {k}={_quote_sh_env_val(v)}")
```

This automatically fixes missing:

- archive variables
- future source/admin variables
- other tab-specific secret variables

### Additional requirement
Make sure the confirm dialog continues to mask any variable whose name contains:

- `API_KEY`
- `ADMIN_API_KEY`

---

## Critical Fix 7 — Remove invalid archive UI options

### Problem
Current archive tabs expose pair-handling controls that are not valid for those CLI subcommands.

### Required removals

#### `archive-folder`
Remove:

- `manage-raw-jpeg`

#### `archive-immich`
Remove:

- `manage-burst`
- `manage-raw-jpeg`

These do not belong there according to the CLI help.

### Replacement
Replace those cards with valid archive options:

- destination
- date range
- source filters
- output/organization options where supported

---

# 5. Completeness guide: make existing tabs fully useful

Now that the critical correctness issues are defined, the agent should complete the existing tabs.

The rule is:

> If a flag is important for real-world use and valid for the subcommand, expose it in the correct mode.

---

# 6. Simple vs Advanced mode policy

Use the following product judgment.

---

## 6.1 Simple mode should show
- required fields
- source / destination
- common content choices
- high-impact safe options
- destructive options only if they are commonly needed and already warned

## 6.2 Advanced mode should show
- filtering
- tagging
- debug/trace
- timeouts
- CLI behavior overrides
- rare but valid flags
- compatibility/power-user settings
- dangerous options that are not needed in basic workflows

---

# 7. Tab-by-tab completeness specification

---

## 7.1 Configuration tab

### Simple mode
Keep visible:

- Server URL
- API Key
- Test Connection
- Binary status / update button
- Theme

### Advanced mode
Move or keep in advanced:

- Skip SSL
- Secret provider
- Admin API key
- Client timeout
- Concurrent tasks
- Device UUID
- On errors
- Error tolerance
- Pause Immich jobs
- **Allow untested updates** *(add this)*
- **Preferred terminal** *(add this)*

### Required additions
Add these missing advanced config widgets:

#### `allow_untested_updates`
Checkbox:

- label: “Allow untested immich-go versions”
- state key: `allow_untested_updates`

#### `preferred_terminal`
Combo:

- `auto`
- `gnome-terminal`
- `konsole`
- `xfce4-terminal`
- `xterm`

State key:

- `preferred_terminal`

### Persistence requirements
- persist `advanced_mode`
- persist `allow_untested_updates`
- persist `preferred_terminal`

---

## 7.2 `upload from-folder`

### Simple mode
Show:

- source path
- album organization (`folder-as-album`)
- put all into album (`into-album`)
- burst handling
- RAW+JPEG handling
- HEIC+JPEG handling

These are common enough to remain simple.

### Advanced mode
Add / expose:

#### Source behavior
- `recursive` checkbox, default **true**
- `date-from-name` checkbox, default **true**
- `ignore-sidecar-files` checkbox
- `album-path-joiner` text field

#### Filtering
- `include-type` combo
- `date-range`
- `include-extensions`
- `exclude-extensions`
- `ban-file`

#### Tagging
- `tag`
- `session-tag`
- `folder-as-tags`

#### Run behavior
- `overwrite`
- `pause-immich-jobs`
- `on-errors`
- `time-zone`

#### Debug
- `log-level`
- `api-trace`
- `manage-epson-fastfoto`

### Command emission rules
- emit `--recursive=false` only when unchecked
- emit `--date-from-name=false` only when unchecked
- emit `--folder-as-album=...` only when not `NONE`
- emit `--include-type=...` only when not `all`
- emit `--album-path-joiner=...` only if non-empty
- emit `--manage-epson-fastfoto` only if checked
- emit `--time-zone=...` only if non-empty

### Removals
- remove `album-picasa` support from this tab entirely

---

## 7.3 `upload from-google-photos`

This tab currently has many false affordances. Fix all of them.

### Simple mode
Show:

- takeout source
- include partner
- sync albums
- include archived
- burst handling
- HEIC+JPEG handling

### Advanced mode
Add / expose:

#### Media / album controls
- `include-type`
- `into-album`
- `include-unmatched`
- `include-trashed`
- `include-untitled-albums`
- `from-album-name`
- `partner-shared-album`
- `takeout-tag`
- `people-tag`

#### Pair handling
- `manage-raw-jpeg` **add this**
- `manage-epson-fastfoto` **add this**

#### Filtering
- `date-range`
- `include-extensions`
- `exclude-extensions`
- `ban-file`

#### Tagging
- `tag`
- `session-tag`

#### Run behavior
- `overwrite`
- `pause-immich-jobs`
- `on-errors`
- `time-zone`

#### Debug
- `log-level`
- `api-trace`

### Critical emission rules for default-true booleans
This is essential.

For these flags:

- `include-archived`
- `include-partner`
- `sync-albums`
- `takeout-tag`
- `people-tag`

If the user **disables** them, emit:

```bash
--include-archived=false
--include-partner=false
--sync-albums=false
--takeout-tag=false
--people-tag=false
```

For default-false flags:

- `include-trashed`
- `include-unmatched`
- `include-untitled-albums`

emit only when enabled:

```bash
--include-trashed
--include-unmatched
--include-untitled-albums
```

### Other emission rules
- `--from-album-name=...` if non-empty
- `--partner-shared-album=...` if non-empty
- `--include-type=...` if not `all`
- `--manage-raw-jpeg=...` if not `NoStack`
- `--manage-epson-fastfoto` if checked
- `--overwrite` if checked
- `--time-zone=...` if non-empty

---

## 7.4 `upload from-immich`

This tab should become a proper migration tab.

### Simple mode
Show:

- source server
- source API key
- date range
- albums
- only favorites

### Advanced mode
Add / expose:

#### Source filters
- `from-archived`
- `from-trash`
- `from-minimal-rating`
- `from-people`
- `from-tags`
- `from-city`
- `from-state`
- `from-country`
- `from-make`
- `from-model`

#### Missing source options to add
- `from-include-type`
- `from-include-extensions`
- `from-exclude-extensions`
- `from-partners`
- `from-no-album`
- `from-time-zone`
- `from-device-uuid`
- `from-api-trace`
- `from-pause-immich-jobs`

#### Destination behavior
Currently missing; add:

- `tag`
- `session-tag`
- `overwrite`
- `pause-immich-jobs`
- `time-zone`

#### Destination pair handling
Currently missing; add:

- `manage-burst`
- `manage-raw-jpeg`
- `manage-heic-jpeg`
- `manage-epson-fastfoto`

#### Debug
- `log-level`
- `api-trace`

### Emission rules
- global destination server remains `--server=...`
- source server is `--from-server=...`
- source API key remains secret via env
- destination API key remains secret via env
- emit `--from-dry-run` in addition to global `--dry-run` for dry runs
- emit `--from-client-timeout=...` if source timeout changed
- emit global `--client-timeout=...` only if destination timeout changed
- emit `--from-include-type=...` if not `all`
- emit `--from-include-extensions=...` / `--from-exclude-extensions=...` if non-empty
- emit repeatable flags for:
  - `--from-albums`
  - `--from-people`
  - `--from-tags`

### UX requirement
Add a small read-only summary banner:

- **Destination:** from Configuration
- **Source:** from tab fields

This reduces confusion.

---

## 7.5 `archive from-folder`

This tab should become a proper local archiving tab.

### Simple mode
Show only:

- source path
- destination folder

### Advanced mode
Add / expose:

#### Filtering
- `date-range`
- `include-type`
- `include-extensions`
- `exclude-extensions`
- `ban-file`

#### Folder behavior
- `recursive` checkbox, default **true**
- `date-from-name` checkbox, default **true**
- `ignore-sidecar-files`
- `folder-as-album`
- `folder-as-tags`
- `into-album`
- `album-path-joiner`

#### Run behavior
- `on-errors`
- `log-level`

### Removals
Remove:

- `manage-raw-jpeg`

It is not valid for `archive from-folder`.

### Emission rules
- emit `--write-to-folder=...`
- emit `--recursive=false` if unchecked
- emit `--date-from-name=false` if unchecked
- emit `--folder-as-album=...` if not `NONE`
- emit `--folder-as-tags` if checked
- emit `--into-album=...` if non-empty
- emit `--album-path-joiner=...` if non-empty
- emit `--include-type=...` if not `all`
- emit extension flags as normalized CSV
- emit repeatable `--ban-file=...`

### Important scoping rule
Do **not** emit:

- `--server`
- `--skip-verify-ssl`
- `--client-timeout`

for `archive-folder`.

---

## 7.6 `archive from-immich`

This should become a powerful source-filtered backup tab.

### Simple mode
Show:

- destination folder
- date range
- albums

### Advanced mode
Add / expose all important source filters:

#### Asset filters
- `from-favorite`
- `from-archived`
- `from-trash`
- `from-minimal-rating`
- `from-no-album`
- `from-partners`

#### People / tags
- `from-people`
- `from-tags`

#### Location / device
- `from-city`
- `from-state`
- `from-country`
- `from-make`
- `from-model`

#### Media filters
- `from-include-type`
- `from-include-extensions`
- `from-exclude-extensions`

#### Source behavior / debug
- `from-time-zone`
- `from-device-uuid`
- `from-client-timeout`
- `from-skip-verify-ssl`
- `from-api-trace`
- `from-pause-immich-jobs`
- `log-level`

### Removals
Remove:

- `manage-burst`
- `manage-raw-jpeg`

They are not valid for `archive from-immich`.

### Emission rules
- emit `--write-to-folder=...`
- emit `--from-server=...`
- emit `--from-dry-run` on dry run
- emit `--from-skip-verify-ssl` if enabled
- emit `--from-client-timeout=...` if not default
- emit repeatable flags for:
  - `--from-albums`
  - `--from-people`
  - `--from-tags`
- emit `--from-minimal-rating=...` only if > 0
- emit `--from-include-type=...` only if not `all`

### UX requirement
Rename the server section to:

- **Source Server**

and explain that it comes from Configuration.

---

## 7.7 `stack`

### Simple mode
Show:

- manage burst
- manage RAW+JPEG
- manage HEIC+JPEG

### Advanced mode
Add / expose:

- `date-range`
- `time-zone`
- `manage-epson-fastfoto`
- `pause-immich-jobs`
- `api-trace`
- `log-level`

### Emission rules
- emit `--date-range=...` if non-empty
- emit `--time-zone=...` if non-empty
- emit `--manage-epson-fastfoto` if checked
- emit `--api-trace` if checked
- emit `--pause-immich-jobs=false` if disabled
- emit global `--client-timeout=...`, `--concurrent-tasks=...`, `--on-errors=...`, `--log-level=...` under the same rules as other tabs

---

# 8. Command-builder implementation rules

The agent should refactor `core/command_builder.py` so it is no longer a pile of ad hoc branches.

---

## 8.1 Add helper emission functions

Add helpers like:

```python
def emit_bool_flag(emitter, flag_name, value, default=False):
    if value != default:
        emitter.add_bool_val(flag_name, value)
```

and:

```python
def emit_if_not_default(emitter, flag_name, value, default):
    if value != default and value not in ("", None):
        emitter.add_option(flag_name, value)
```

Use these consistently.

---

## 8.2 Boolean default handling

### Default true
For flags whose CLI default is `true`:

- `recursive`
- `date-from-name`
- `include-archived`
- `include-partner`
- `sync-albums`
- `takeout-tag`
- `people-tag`
- `pause-immich-jobs`

emit only when the GUI value is **false**:

```bash
--flag=false
```

### Default false
For flags whose CLI default is `false`:

- `include-trashed`
- `include-unmatched`
- `include-untitled-albums`
- `overwrite`
- `session-tag`
- `folder-as-tags`
- `api-trace`
- `from-favorite`
- `from-archived`
- `from-trash`
- `from-partners`
- `from-no-album`

emit only when enabled:

```bash
--flag
```

---

## 8.3 Repeatable flags

Use repeatable emission for:

- `tag`
- `ban-file`
- `from-albums`
- `from-people`
- `from-tags`

Example:

```python
for item in split_csv(value):
    emitter.add_option("from-albums", item)
```

---

## 8.4 CSV flags

Use normalized CSV for:

- `include-extensions`
- `exclude-extensions`
- `from-include-extensions`
- `from-exclude-extensions`

Example:

```python
value = normalize_extensions_csv(raw)
if value:
    emitter.add_option("include-extensions", value)
```

---

## 8.5 Absolute path normalization

All path inputs must be converted to absolute paths before command construction.

Add a helper in `core/validation.py` or `core/command_builder.py`:

```python
def normalize_command_paths(raw_text: str) -> list[str]:
    ...
```

Requirements:

- split lines
- strip whitespace
- expand user (`~`)
- convert relative paths to absolute using GUI working directory
- expand globs where appropriate
- return absolute paths
- preserve non-existent paths as absolute patterns if needed

Then use this for:

- `upload-folder`
- `upload-gp`
- `archive-folder`

This fixes the external-terminal working-directory mismatch.

---

## 8.6 Dry-run handling for `from-immich`

For both:

- `upload-immich`
- `archive-immich`

when `dry_run=True`, emit:

```bash
--dry-run
--from-dry-run
```

unless real-world testing proves one is redundant.

This is the safer interpretation because source and destination actions may both need simulation.

---

# 9. State collection and persistence rules

The agent must update `app.py` state collection whenever adding widgets.

---

## 9.1 Add new state keys for every new widget

Examples:

- `recursive`
- `album-path-joiner`
- `manage-epson-fastfoto`
- `time-zone`
- `include-untitled-albums`
- `from-include-type`
- `from-include-ext`
- `from-exclude-ext`
- `from-partners`
- `from-no-album`
- `from-time-zone`
- `from-device-uuid`
- `from-api-trace`
- `from-pause-jobs`

Do not add a widget without also updating:

- `_collect_tab_state()`
- `collect_form_state()`
- `apply_form_state()`
- command builder
- tests

---

## 9.2 Use combo data where appropriate
For combos like:

- secret provider
- on-errors
- folder-as-album
- include-type

prefer storing semantic values in item data rather than relying on display text.

This avoids fragile text comparisons.

---

## 9.3 Persist advanced mode
In `load_configuration()`:

```python
self.switch_advanced.setChecked(self.app_config.advanced_mode)
```

In `save_configuration()`:

```python
self.app_config.advanced_mode = self.switch_advanced.isChecked()
```

---

# 10. Validation updates

Update `validate_state()` to reflect the corrected model.

---

## 10.1 Server/API requirements

### Require server + API key for:
- `upload-folder`
- `upload-gp`
- `upload-immich`
- `stack`
- `archive-immich`

But use wording that matches the tab meaning:

- for `archive-immich`: “Source server URL is required.”
- for `upload-immich`: also require source server/source API key
- for `stack`: “Immich server URL is required.”

### Do not require server for:
- `archive-folder`

---

## 10.2 Add URL validation for source fields
For:

- `upload-immich.from-server`

validate URL format similarly to global server.

---

## 10.3 Keep date-range validation
Continue validating:

- `date-range`
- `from-date-range`

---

## 10.4 Keep destination warnings
Continue warning when:

- destination is inside source
- destination exists but is not writable
- destination exists but is not a directory

---

# 11. Compatibility checking fixes

The compatibility dialog must become trustworthy.

---

## 11.1 Merge live report and fixture report
Currently the live binary report is computed but not properly used.

Fix it so the dialog shows:

- fixture compatibility
- live binary compatibility
- missing flags from live binary
- unknown flags from live binary

Do not let a clean fixture report hide live binary incompatibility.

---

## 11.2 Warn when fixtures are missing
If fixtures are missing, show:

- “CLI help fixtures missing for version X”
- not “Fully Compatible”

---

# 12. Binary manager safety improvements

These are not strictly CLI-flag issues, but they are still critical for a reliable app.

---

## 12.1 Prevent downgrade prompts
In `BinaryManager.evaluate_update()`:

- if `current_version` is newer than `latest_version`, return:
  - `allowed=False`
  - message: already newer than latest tested/available

Do not prompt downgrades.

---

## 12.2 Use GitHub release assets instead of guessed URLs
Replace guessed asset URLs with release-asset discovery:

- query release metadata
- select asset by OS/arch
- only fall back to guessed URL if absolutely necessary

---

## 12.3 Centralize download/extract logic
Stop duplicating download/extraction logic in `app.py`.

Use `BinaryManager` methods instead.

---

## 12.4 Make cancellation safe
Do not use `QThread.terminate()`.

Use a cooperative cancellation flag:

```python
self.cancelled = False
```

and stop the download loop when cancelled.

---

## 12.5 Return correct success/failure
`update_binary()` must return:

- `False` on cancel
- `False` on download error
- `False` on extraction error
- `True` only on real success

---

# 13. Secret-management safety fixes

---

## 13.1 Do not delete old secrets unless copy/save succeeded
In profile rename / duplicate / migration flows:

- copy secrets
- verify success
- only then clear old secrets

If copy fails, raise or return an error.

---

## 13.2 Fix QSettings migration
In `_migrate_legacy_qsettings_to_config()`:

- only remove old QSettings API key if `set_api_key()` succeeded

Do not delete the old secret unconditionally.

---

# 14. UI polish required for completeness

These are not optional if the goal is a complete app.

---

## 14.1 Fix misleading labels

### `archive-immich`
Change:

- “Target Server” → **“Source Server”**

### `upload-immich`
Add a small banner:

- Destination server comes from Configuration
- Source server is entered in this tab

---

## 14.2 Debounce manual binary path checking
Do not check binary version on every keystroke.

Use:

- `editingFinished`, or
- a debounce timer

---

## 14.3 Replace placeholder QSettings identity
Replace:

```python
QSettings("YourOrganization", "ImmichGoGUI")
```

with a real identity, for example:

```python
QSettings("Shitan198u", "ImmichGoGUI")
```

---

## 14.4 Add missing advanced settings UI
Add UI for:

- `allow_untested_updates`
- `preferred_terminal`

These already exist in the model but are not user-controllable.

---

# 15. Test plan

The agent must update and add tests.

---

## 15.1 Remove duplicate test names
Search for duplicated function names in `test_app.py` and rename them.

Duplicate Python test functions silently override earlier ones.

---

## 15.2 Fix wrong golden tests
Update all golden tests that currently expect:

- `--write-to=...`
- `--server=...` for `archive-immich`
- missing GP flags
- missing stack flags

---

## 15.3 Add command emission tests for every new control

At minimum, add tests for:

### upload-folder
- `--recursive=false`
- `--date-from-name=false`
- `--album-path-joiner=...`
- `--manage-epson-fastfoto`
- `--time-zone=...`

### upload-gp
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
- `--overwrite`

### upload-immich
- `--from-include-type=...`
- `--from-include-extensions=...`
- `--from-exclude-extensions=...`
- `--from-partners`
- `--from-no-album`
- `--from-time-zone=...`
- `--from-device-uuid=...`
- `--from-api-trace`
- `--from-dry-run`
- destination `--tag=...`
- destination `--session-tag`
- destination `--overwrite`

### archive-folder
- `--write-to-folder=...`
- `--recursive=false`
- `--folder-as-album=FOLDER`
- `--folder-as-tags`
- `--into-album=...`
- `--album-path-joiner=...`
- `--include-type=IMAGE`
- `--include-extensions=...`
- `--exclude-extensions=...`
- `--ban-file=...`

### archive-immich
- no `--server`
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
- `--from-no-album`
- `--from-time-zone=...`
- `--from-dry-run`

### stack
- `--date-range=...`
- `--time-zone=...`
- `--manage-epson-fastfoto`
- `--api-trace`
- `--pause-immich-jobs=false`

---

## 15.4 Add error-surfacing tests
Add tests that verify:

- `plan.errors` blocks confirm dialog
- invalid flag emission is caught in tests
- schema violations do not pass silently

---

## 15.5 Add process/lock tests
Add tests for:

- active lock with live PID
- stale lock with dead PID
- stale lock with old heartbeat
- reset clears UI running state
- terminal launcher exports archive-related `IMMICH_GO_*` variables

---

## 15.6 Add compatibility fixture tests
Add tests that verify:

- fixtures exist
- allowed flags are present in fixtures
- missing fixtures are treated as failure/warning, not silent success

---

# 16. Suggested implementation order for the agent

To reduce regressions, do the work in this order:

---

## Phase 1 — Correctness blockers
1. fix `write-to-folder`
2. fix `archive-immich` source model
3. fix `plan.errors` surfacing
4. fix running-state boolean bug
5. remove invalid archive controls
6. remove invalid `upload-folder` `album-picasa`
7. fix terminal secret forwarding

---

## Phase 2 — Schema and builder completeness
1. replace `TAB_ALLOWED_FLAGS`
2. add missing flags to builder
3. add default-aware boolean emission
4. normalize paths to absolute
5. add `from-dry-run` handling
6. update validation messages

---

## Phase 3 — UI completeness
1. add missing widgets per tab
2. wire state collection
3. wire persistence
4. respect simple/advanced mode
5. fix labels and banners
6. add missing config advanced settings

---

## Phase 4 — Safety hardening
1. improve stale-lock detection
2. improve binary update logic
3. fix secret copy/migration safety
4. debounce manual binary checks
5. centralize update flow

---

## Phase 5 — Tests
1. fix golden tests
2. remove duplicate tests
3. add new command tests
4. add lock/terminal tests
5. add fixture/contract tests

---

# 17. Practical acceptance checklist

Before declaring success, the agent must verify:

## Command correctness
- [ ] `archive from-folder` uses `--write-to-folder`
- [ ] `archive from-immich` does not emit `--server`
- [ ] `archive from-immich` emits `--from-server`
- [ ] no invalid flags remain
- [ ] all visible controls affect command output

## UI completeness
- [ ] GP tab includes missing flags
- [ ] stack tab includes missing flags
- [ ] archive tabs include valid filters
- [ ] invalid archive pair-handling controls removed
- [ ] advanced mode exposes power-user flags
- [ ] simple mode remains clean

## Safety
- [ ] running state cannot get stuck due to boolean bug
- [ ] stale locks can be cleaned
- [ ] terminal launcher exports all `IMMICH_GO_*` variables
- [ ] secrets are not in argv
- [ ] secret migration cannot lose data silently

## Tests
- [ ] all tests pass
- [ ] no duplicate test names
- [ ] golden tests reflect real CLI
- [ ] new controls have explicit tests

---

# 18. Final guidance to the agent

When in doubt, follow this priority order:

1. **Correct CLI behavior**
2. **No silent failures**
3. **No false controls**
4. **Complete existing tabs**
5. **Better UX polish**

Do not add new source tabs like iCloud/Picasa yet unless all existing tabs are already correct and complete.

The goal is not “more widgets”.  
The goal is:

> a trustworthy GUI where every visible option is real, every generated command is valid, and the app feels complete for the workflows it already supports.