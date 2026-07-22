Yes — I checked the updated `app.py` and `immichgo_modules_bundle.txt`.

## Short verdict

**Phase 1 is mostly done correctly.**  
The major critical blockers have been addressed:

- `--write-to-folder` is now used for archive tabs
- `archive from-immich` now uses the correct source-server model
- `plan.errors` are now surfaced in the GUI
- the running-state boolean bug is fixed
- stale-lock detection is now meaningfully implemented
- terminal launching now forwards all `IMMICH_GO_*` environment variables
- invalid archive-tab pair-handling controls have been removed
- `album-picasa` has been removed from `upload-folder`
- the CLI allowlist is now much closer to the real CLI help

However, if we are being strict about **“Phase 1 is fully complete”**, then **not quite**.  
There are still a few remaining functional gaps and test gaps that should be cleaned up before calling it fully closed.

---

# What is now correctly done

## 1. Archive destination flag is fixed

### Verified
`core/cli_schema.py` now uses:

- `archive-folder`: `write-to-folder`
- `archive-immich`: `write-to-folder`

`core/command_builder.py` emits:

```python
emitter.add_option("write-to-folder", tab_state["write-to"])
```

Tests also expect:

```python
"--write-to-folder=/dest/folder"
```

### Status
**Done correctly.**

---

## 2. `archive from-immich` source model is fixed

### Verified
`ENV_KEY_MAP["archive-immich"]` now uses:

- `from_server`
- `from_api_key`
- `from_admin_api_key`

`command_builder.py` now emits:

```python
--from-server=...
```

and no longer emits global `--server` for `archive-immich`.

`app.py` also now labels the archive-immich server section as **Source Server**, which is conceptually correct.

### Status
**Done correctly.**

### Minor note
Validation still says generic:

- “Server URL is required. Configure it in the Configuration tab.”

For `archive-immich`, it would be clearer to say:

- “Source server URL is required. Configure it in the Configuration tab.”

This is minor, not a blocker.

---

## 3. `plan.errors` are now surfaced

### Verified
In `app.py`:

- `show_confirm_dialog()` now checks `plan.errors`
- `run_command()` now checks `plan.errors`

This was a major previous issue, and it is now fixed.

### Status
**Done correctly.**

---

## 4. Running-state boolean bug is fixed

### Verified
`app.py` now initializes:

```python
self.running_process = bool(self.active_lock_path)
```

and `update_status()` now uses:

```python
is_running = (
    (active_lock is not None and is_lock_active(active_lock))
    or (getattr(self, "running_process", False) is True)
)
```

This avoids the old bug where `False is not None` evaluated to `True`.

`on_reset_run_state_clicked()` also correctly clears:

- `active_lock_path`
- `running_process`
- timer state

### Status
**Done correctly.**

---

## 5. Stale-lock detection is now real

### Verified
`core/process_tracker.py` now supports:

- `shell_pid`
- `terminal_pid`
- `last_seen`
- sidecar `.pid`
- sidecar `.heartbeat`
- process liveness checks
- grace period for freshly created locks

`core/terminal_launcher.py` now:

- writes a PID file on POSIX
- starts a heartbeat loop
- updates lock with terminal PID where possible
- cleans up lock and sidecars on exit

### Status
**Done correctly enough for Phase 1.**

### Minor edge-case notes
These are not blockers, but worth knowing:

1. On some Linux terminal emulators, the recorded terminal PID may be a short-lived launcher process.  
   The heartbeat mechanism compensates for this.

2. If the script is killed with `SIGKILL`, stale files may remain, but the new stale-detection logic should eventually classify the lock as inactive.

3. The POSIX script removes the temp directory before `exec bash`, which is fine, but the final shell may end up with a deleted current working directory. Cosmetic only.

Overall, this is now a real improvement and not just theoretical.

---

## 6. Terminal secret forwarding is fixed

### Verified
`core/terminal_launcher.py` now exports all environment variables beginning with:

```python
IMMICH_GO_
```

instead of using the old brittle hardcoded list.

This fixes the previous missing archive-secret forwarding issue.

### Status
**Done correctly.**

### Minor test note
The test `test_forward_all_immich_go_env_vars()` only asserts that `Popen` was called.  
It does not yet strongly verify that the generated `env.sh` contains the expected variables.

The implementation is correct, but the test is weak.

---

## 7. Invalid archive-tab controls were removed

### Verified
`app.py` no longer exposes:

- `manage-raw-jpeg` on `archive-folder`
- `manage-burst` on `archive-immich`
- `manage-raw-jpeg` on `archive-immich`

`_collect_tab_state()` also no longer collects those fields for archive tabs.

### Status
**Done correctly.**

---

## 8. `upload-folder` `album-picasa` removed

### Verified
- `cli_schema.py` no longer includes `album-picasa` for `upload-folder`
- `command_builder.py` no longer emits it
- `app.py` has no UI for it

### Status
**Done correctly.**

---

## 9. CLI allowlist is now much more correct

### Verified
The updated `TAB_ALLOWED_FLAGS` now includes many previously missing flags and removes invalid ones.

Examples:

#### `upload-gp`
Now includes:
- `include-archived`
- `include-partner`
- `include-trashed`
- `include-unmatched`
- `include-untitled-albums`
- `from-album-name`
- `partner-shared-album`
- `people-tag`
- `sync-albums`
- `takeout-tag`
- `include-type`
- `manage-raw-jpeg`
- `manage-epson-fastfoto`

#### `stack`
Now includes:
- `api-trace`
- `date-range`
- `time-zone`
- `manage-epson-fastfoto`
- `pause-immich-jobs`

#### `archive-folder`
Now includes:
- `write-to-folder`
- `recursive`
- `folder-as-album`
- `folder-as-tags`
- `album-path-joiner`
- `into-album`
- `include-type`
- `include-extensions`
- `exclude-extensions`
- `ban-file`
- `ignore-sidecar-files`
- `date-from-name`

#### `archive-immich`
Now includes the correct `from-*` filter set and no global `server`.

### Status
**Mostly done correctly.**

There are still a few “UI exists but command builder does not emit” gaps below.

---

# Remaining issues that prevent Phase 1 from being 100% closed

These are not as severe as the original blockers, but they still matter.

---

## Remaining issue 1 — `from-dry-run` is not emitted for `from-immich` tabs

### Observed
For both:

- `upload-immich`
- `archive-immich`

the builder currently emits only:

```bash
--dry-run
```

It does **not** emit:

```bash
--from-dry-run
```

### Why this matters
The CLI help shows that `from-immich` subcommands have both:

- global `--dry-run`
- subcommand-specific `--from-dry-run`

For source-server operations, it is safer to emit both when doing a dry run.

### Impact
Dry-run behavior may be incomplete or ambiguous for Immich-to-Immich and Immich-archive workflows.

### Recommended fix
In `core/command_builder.py`, change dry-run handling to:

```python
if dry_run:
    emitter.add_flag("dry-run")
    if tab_key in ("upload-immich", "archive-immich"):
        emitter.add_flag("from-dry-run")
```

### Status
**Not done yet.**

---

## Remaining issue 2 — Stack “Pause background jobs” is exposed but not emitted

### Observed
In `app.py`, the Stack tab now has:

```python
self.inputs["stack"]["pause-jobs"]
```

and `_collect_tab_state("stack")` includes:

```python
"pause-jobs": get_bool("pause-jobs", True)
```

But `command_builder.py` does **not** emit `--pause-immich-jobs` for `stack`.

### Why this matters
This is a false affordance: the user can change the checkbox, but the generated command does not reflect it.

### Recommended fix
In `command_builder.py`, broaden the pause-jobs block from:

```python
if tab_key in UPLOAD_TABS:
```

to:

```python
if tab_key in UPLOAD_TABS or tab_key == "stack":
```

or add a dedicated stack branch:

```python
elif tab_key == "stack":
    if "pause-jobs" in tab_state and not tab_state["pause-jobs"]:
        emitter.add_bool_val("pause-immich-jobs", False)
    elif not config_state.get("pause_jobs", True):
        emitter.add_bool_val("pause-immich-jobs", False)
```

### Status
**Not done yet.**

---

## Remaining issue 3 — Archive-folder “If a file fails” (`on-errors`) is exposed but not emitted

### Observed
`app.py` now adds an `on-errors` combo to `archive-folder`:

```python
self.inputs["archive-folder"]["on-errors"]
```

and `_collect_tab_state("archive-folder")` includes:

```python
"on-errors": get_combo("on-errors", "stop")
```

But `command_builder.py` still only emits `on-errors` for upload tabs:

```python
if tab_key in UPLOAD_TABS:
    ...
```

### Why this matters
This is another false affordance.

The CLI supports `--on-errors` for archive operations, and your schema already allows it for `archive-folder`.

### Recommended fix
Make `on-errors` emission global/tab-aware rather than upload-only.

For example:

```python
if "on-errors" in tab_state:
    if tab_state["on-errors"] != "stop":
        emitter.add_option("on-errors", tab_state["on-errors"])
else:
    oe_config = config_state.get("on_errors", "stop")
    if oe_config == "custom…":
        tol = config_state.get("on_errors_tolerance", 10)
        emitter.add_option("on-errors", tol)
    elif oe_config != "stop":
        emitter.add_option("on-errors", oe_config)
```

This way:

- tabs with explicit `on-errors` use their own value
- tabs without one can inherit the global config value

### Status
**Not done yet.**

---

## Remaining issue 4 — Some tests are still duplicated or weak

This is not a runtime blocker, but it weakens verification.

### 4.1 Duplicate test names still exist
In `test_app.py`, there are still duplicated function names, for example:

- `test_api_trace_on_stack`
- `test_golden_archive_folder`

In Python, the later definition silently overrides the earlier one.

### Impact
You may think you have coverage that is not actually executing.

### Recommended fix
Rename the duplicates uniquely, e.g.:

- `test_api_trace_on_stack_enabled`
- `test_api_trace_on_stack_disabled`
- `test_golden_archive_folder_basic`
- `test_golden_archive_folder_with_options`

---

### 4.2 `test_plan_errors_surfaced_in_gui` may not reliably reach the plan-error path
`show_confirm_dialog()` checks binary readiness before checking `plan.errors`.

If the binary is not ready in the test environment, the flow can branch into the binary-missing dialog before reaching the plan-error assertion.

### Recommended fix
Patch `check_binary_ready` in that test:

```python
with patch.object(gui, "check_binary_ready", return_value=(True, "ready")):
    ...
```

---

### 4.3 `test_forward_all_immich_go_env_vars` is too weak
It only checks that `Popen` was called.

It does not verify that:

- the generated `env.sh` contains the expected variables on POSIX
- or the passed `env` dictionary contains them on Windows

### Recommended fix
Strengthen the test to inspect the created script or the `Popen` env argument.

---

# Minor observations that are not Phase 1 blockers

These are worth noting, but they do not mean Phase 1 failed.

---

## 1. `SECRET_FLAGS` does not include `--from-admin-api-key`
Currently:

```python
SECRET_FLAGS = {
    "--api-key",
    "--from-api-key",
    "--admin-api-key",
}
```

It would be safer to add:

```python
"--from-admin-api-key"
```

even if you are not emitting it in argv today.

This future-proofs masking.

---

## 2. Global config “Skip SSL” vs archive-immich source SSL skip
For `archive-immich`, the command builder uses:

- `from-skip-ssl` from the archive-immich tab

but the global config `skip-ssl` warning still appears because validation checks `config_state["skip-ssl"]`.

This is not broken, but it may confuse users.

### Suggestion
Either:

- make archive-immich inherit global skip-ssl when tab-specific is unset, or
- clarify in UI text that archive-immich uses its own source SSL setting

---

## 3. Relative path normalization is still not implemented
This was more of a Phase 2 item, but worth repeating:

- source/destination paths are still passed largely as typed
- external terminal working directory is isolated
- relative paths can therefore behave unexpectedly

This is not a Phase 1 blocker, but it should still be done soon.

---

# Final assessment

## If Phase 1 means “fix the original critical blockers”
Then **yes, Phase 1 is effectively done**.

The following are all in good shape:

- archive flag correctness
- archive-immich source model
- plan-error surfacing
- running-state bug
- stale-lock detection
- secret forwarding
- removal of invalid controls
- much better CLI allowlisting

That is a very large chunk of the critical risk, and it has been implemented properly.

---

## If Phase 1 means “no false affordances and all critical source-model behavior complete”
Then **not quite**.

To close it fully, I would fix these remaining items:

1. emit `--from-dry-run` for `upload-immich` and `archive-immich`
2. emit stack `--pause-immich-jobs=false` when disabled
3. emit `--on-errors` for `archive-folder` when set
4. clean up duplicated tests
5. strengthen the plan-error and terminal-env tests

---

# Bottom line

**Phase 1 is about 90–95% done.**

The core critical architecture and correctness fixes are in place and look solid.  
The remaining issues are smaller, but they are still important enough that I would not call Phase 1 “fully verified” until they are addressed.

If you want, I can next give you a **very short punch-list of the exact code changes still needed to declare Phase 1 complete**.