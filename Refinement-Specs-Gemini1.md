# Verification Report & Next Steps

I have cross-referenced every claim in the walkthrough against the actual uploaded `app.py` and `test_app.py`. Below is the milestone-by-milestone verification, followed by issues found and a prioritized next-steps roadmap.

---

## Part 1: Milestone-by-Milestone Verification

### Milestone 1 — Pure Data Structures & Utilities ✅ VERIFIED

| Claim | Status | Evidence in `app.py` |
|---|---|---|
| `CommandPlan` dataclass | ✅ Present | `argv`, `env`, `display_argv`, `warnings`, `errors`, `tab_key`, `dry_run`, `binary_path` fields all present |
| `ValidationResult` dataclass | ✅ Present | `errors`, `warnings`, `is_valid` property present |
| `normalize_server_url()` | ✅ Present | Adds `http://`, strips trailing `/`, handles empty |
| `validate_date_range()` | ✅ Present | `_DATE_RANGE_RE` regex matches `YYYY`, `YYYY-MM`, `YYYY-MM-DD`, and `start,end` |
| `load_binary_metadata()` | ✅ Present | Reads `~/.immich-go-gui/bin/metadata.json`, returns default dict on failure |
| `save_binary_metadata()` | ✅ Present | Writes JSON with `indent=2` |
| `get_binary_path()` | ✅ Present | Priority: manual → selected version → legacy flat path |
| `check_release_for_breaking_changes()` | ✅ Present | `BREAKING_INDICATORS` regex list, fetches GitHub release body |
| `mask_command_for_display()` space-separated | ✅ Present | `skip_next` logic handles `--api-key secret` as two elements |

**One note:** The `BREAKING_INDICATORS` list in the uploaded file shows trailing spaces inside the regex strings (e.g., `r"\bbreaking\s+change "`). If this is not a formatting artifact from the upload, those trailing spaces would cause the regex to require a trailing space in the release body text, making matches less reliable. **Verify in your actual file that the regex strings have no trailing spaces.**

---

### Milestone 2 — Command Plan Builder & Secret Isolation ✅ VERIFIED (with one nuance)

| Claim | Status | Evidence |
|---|---|---|
| `build_plan()` returns `CommandPlan` | ✅ Present | Full method with all 6 tab branches |
| Secrets never in `plan.argv` | ✅ Verified | `--api-key` and `--from-api-key` go only to `env[env_key]` |
| `_ENV_KEY_MAP` for env key resolution | ✅ Present | Maps all 5 server-connected tabs |
| `_env_key_for_tab()` helper | ✅ Present | |
| Server URLs normalized | ✅ Verified | `normalize_server_url()` called for both config server and `from-server` |
| `build_command()` backward-compatible wrapper | ✅ Present | Returns `self.build_plan(dry_run).argv` |
| `display_argv` masked via `mask_command_for_display()` | ✅ Present | |

**Nuance on "Removed manual secret-stripping loop":** The `run_command()` method **still contains** the secret-stripping loop:

```python
clean_parts = []
skip_next = False
for part in command_parts:
    if skip_next:
        skip_next = False
        continue
    if part.startswith("--api-key=") or ...
```

This is **not a bug** — it acts as defense-in-depth. But the walkthrough claim of "removed" is slightly inaccurate. It is more accurately described as "retained as a safety net but no longer needed for `CommandPlan`-based calls." This is fine to keep.

---

### Milestone 3 — Validation Feedback Architecture ✅ VERIFIED

| Claim | Status | Evidence |
|---|---|---|
| `validate_inputs()` returns `ValidationResult` | ✅ Present | Per-tab checks for all 6 tabs + global checks |
| `update_status()` shows specific errors | ✅ Present | `first_error = validation.errors[0]` displayed in `StatusCard` |
| Per-tab validation: upload-folder path | ✅ Present | |
| Per-tab validation: upload-gp source | ✅ Present | |
| Per-tab validation: upload-immich from-server/from-api-key | ✅ Present | |
| Per-tab validation: archive-folder path + write-to | ✅ Present | |
| Per-tab validation: archive-immich write-to | ✅ Present | |
| SSL warning in `ValidationResult.warnings` | ✅ Present | |
| `archive-folder` exempt from server/api requirement | ✅ Present | `if tab_key != "archive-folder":` guard |

---

### Milestone 4 — Lock-File Process Tracker ✅ VERIFIED

| Claim | Status | Evidence |
|---|---|---|
| `ProcessTracker` class | ✅ Present | `create_lock()`, `release_lock()`, `is_running`, `wrap_command_with_lock()` |
| Lock files in `tmp/immich-go-gui/run-<id>.lock` | ✅ Present | Uses `tempfile.gettempdir()` + `uuid.uuid4().hex[:12]` |
| `psutil` removed | ✅ Verified | No `import psutil` in the new `app.py` |
| Lock-file polling via `QTimer` | ✅ Present | `_check_lock_file()` connected to `self.check_process_timer` at 1000ms |
| `check_if_process_running()` backward-compatible alias | ✅ Present | Calls `self._check_lock_file()` |
| Windows `.bat` wrapper for lock cleanup | ✅ Present | `bat_content` with `del /f` |
| Unix `trap` for lock cleanup | ✅ Present | `wrap_command_with_lock()` uses `trap 'rm -f ...' EXIT INT TERM` |

---

### Milestone 5 — Versioned Binary Management ✅ VERIFIED

| Claim | Status | Evidence |
|---|---|---|
| Versioned subdirectories `bin/<version>/` | ✅ Present | `version_dir = os.path.join(BINARY_BASE_DIR, clean_version)` |
| `metadata.json` with `selected_version`, `manual_path`, `versions` | ✅ Present | `_select_version()` writes full metadata |
| Manual Binary Path field in Config tab | ✅ Present | `self.manual_binary_edit` with `_on_manual_binary_changed()` |
| Breaking change check in `check_for_updates()` | ✅ Present | Calls `check_release_for_breaking_changes()`, blocks upgrade if `has_breaking` |
| Hardened `check_binary_version()` | ✅ Present | Handles `TimeoutExpired`, `PermissionError`, `OSError`, non-zero exit code, empty output |
| `TESTED_IMMICH_GO_VERSION = "0.31.0"` | ✅ Present | |
| Untested version warning | ✅ Present | `status_state = "warn"` when version differs from tested |
| `check_binary_ready()` | ✅ Present | Checks existence, is-file, `os.X_OK` on Unix |

---

### Milestone 6 — Rich Command Preview Dialog ✅ VERIFIED

| Claim | Status | Evidence |
|---|---|---|
| Section 1: Binary Path | ✅ Present | `QLineEdit(plan.binary_path)` read-only |
| Section 2: Command (masked) | ✅ Present | `cmd_block` with `plan.display_argv` |
| Section 3: Environment Variables (masked) | ✅ Present | Filters `IMMICH_GO_*`, masks `API_KEY`/`FROM_API_KEY`/`ADMIN_API_KEY` values |
| Section 4: Warnings | ✅ Present | Iterates `plan.warnings` with ⚠️ prefix |
| Copy Command button (command only) | ✅ Present | `QApplication.clipboard().setText(cmd_str)` — copies only the command string |
| Binary readiness gate before dialog | ✅ Present | `check_binary_ready()` called first, offers download if not ready |
| Validation errors block dialog | ✅ Present | `if plan.errors:` shows `QMessageBox.warning` and returns |

---

### Milestone 7 — Golden Command Tests ⚠️ VERIFIED WITH ONE GAP

| Claim | Status | Evidence in `test_app.py` |
|---|---|---|
| `test_golden_upload_folder` | ✅ Present | Asserts exact `plan.argv` vector + env secret check |
| `test_golden_upload_gp` | ✅ Present | Multi-ZIP path, partner/sync defaults |
| `test_golden_stack` | ✅ Present | All stack options including `--manage-epson-fastfoto=true` |
| `test_golden_archive_folder` | ✅ Present | No server, `--dry-run`, date-range |
| `test_golden_upload_immich` | ✅ Present | Filters, `--from-albums` repeatable, secret exclusion verified |
| **`test_golden_archive_immich`** | ❌ **MISSING** | **Not present in test_app.py** |

The walkthrough claims "all 6 tabs" but only 5 golden tests exist. **`archive-immich` has no golden test.** The existing `test_build_command_archive_immich` test uses the old `build_command()` wrapper and does not verify `CommandPlan` structure, env isolation, or exact vector matching.

---

## Part 2: Additional Issues Found During Verification

### Issue 1: Missing `test_golden_archive_immich` (Priority: HIGH)

The `archive-immich` tab is the only tab without a golden `CommandPlan` test. This means:
- No verification that `IMMICH_GO_ARCHIVE_API_KEY` is in `plan.env`
- No verification that `--api-key` is absent from `plan.argv`
- No exact vector assertion for the archive-immich command

**Recommended test:**

```python
def test_golden_archive_immich(gui):
    """Golden: archive from-immich with options."""
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["skip-ssl"].setChecked(False)
    gui.inputs["config"]["client_timeout"].setValue(20)
    cpu_default = min(max(os.cpu_count() or 2, 1), 20)
    gui.inputs["config"]["concurrent"].setValue(cpu_default)
    gui.inputs["archive-immich"]["write-to"].setText("/backup/photos")
    gui.inputs["archive-immich"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["archive-immich"]["manage-raw-jpeg"].setCurrentText("KeepRaw")
    gui.inputs["archive-immich"]["from-date-range"].setText("2024")
    gui.inputs["archive-immich"]["from-albums"].setText("Family")
    gui.inputs["archive-immich"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "archive", "from-immich",
        "--server=http://localhost:2283",
        "--write-to-folder=/backup/photos",
        "--manage-burst=Stack",
        "--manage-raw-jpeg=KeepRaw",
        "--from-date-range=2024",
        "--from-albums=Family",
    ]
    assert plan.env.get("IMMICH_GO_ARCHIVE_API_KEY") == "test-key"
    assert not any("--api-key" in p for p in plan.argv)
```

### Issue 2: Trailing Spaces in String Literals (Priority: MEDIUM)

Throughout both uploaded files, many string literals contain trailing spaces:

```python
# In test_app.py:
gui.inputs["config "]["server "].setText("http://local:2283 ")
assert "--client-timeout=60m " in opts

# In app.py:
env["IMMICH_GO_UPLOAD_SERVER "] = server
secret_flags = {"--api-key ", "--from-api-key ", "--admin-api-key "}
```

If these are **actual characters in your source files** (not upload formatting artifacts), they would cause:
- Dictionary key mismatches (`"config "` ≠ `"config"`)
- Env variable names with trailing spaces (breaking CLI env var resolution)
- Flag matching failures in `mask_command_for_display()`
- Test assertions that pass incorrectly (matching `"--flag "` instead of `"--flag"`)

**Action:** Run this check in your actual repo:

```bash
grep -n '" ' app.py test_app.py | head -40
```

If trailing spaces exist, strip them. The `test_build_environment_no_trailing_spaces` test should catch the env var issue, but only if the test strings themselves are clean.

### Issue 3: `run_command()` Still Has Secret-Stripping Loop (Priority: LOW)

As noted above, the stripping loop in `run_command()` is retained. This is fine as defense-in-depth, but the walkthrough says it was "removed." Consider adding a comment:

```python
# Defense-in-depth: strip any secret flags that may have leaked
# into argv from legacy code paths. With CommandPlan, this should
# never trigger, but it prevents accidental exposure.
```

### Issue 4: `build_environment()` Standalone Function Still Exists (Priority: LOW)

The module-level `build_environment()` function is still present and still used by `self.build_environment()` (the instance method). This is fine, but note that `build_plan()` now builds its own `env` dict inline. There are now **two code paths** that build environment variables:

1. `build_plan()` → inline env construction
2. `build_environment()` → standalone function (used by `run_command()` fallback path)

If a future flag is added to one but not the other, they could diverge. Consider eventually consolidating to a single source of truth.

### Issue 5: No `test_golden_archive_immich` Means 5/6 Coverage (Priority: HIGH)

Already covered in Issue 1. This is the single most important gap.

---

## Part 3: Verification Summary

| Milestone | Verdict | Notes |
|---|---|---|
| 1 — Pure Data Structures | ✅ **PASS** | All functions present and correct |
| 2 — Command Plan Builder | ✅ **PASS** | Secret isolation verified; stripping loop retained as safety net |
| 3 — Validation Feedback | ✅ **PASS** | All 6 tabs covered, structured errors |
| 4 — Lock-File Tracker | ✅ **PASS** | psutil fully removed, cross-platform lock cleanup |
| 5 — Binary Management | ✅ **PASS** | Versioned dirs, manual path, breaking-change gate |
| 6 — Preview Dialog | ✅ **PASS** | 4 sections, copy button, binary gate |
| 7 — Golden Tests | ⚠️ **PARTIAL** | 5/6 tabs covered; `archive-immich` golden test missing |

**Overall: 6/7 milestones fully verified. 1 milestone has a gap (missing golden test).**

---

## Part 4: Next Steps

Now that the core refactoring is complete and verified, here is a prioritized roadmap for what comes next.

### Immediate (This Week)

#### 4.1 Add the Missing `test_golden_archive_immich`

This is the single highest-priority gap. Write and commit the test from Issue 1 above. This completes the 6/6 golden coverage.

#### 4.2 Audit and Fix Trailing Spaces

Run a project-wide audit:

```bash
# Find suspicious trailing spaces in string literals
grep -Pn '"\s+"' app.py test_app.py
grep -Pn "'\s+'" app.py test_app.py

# Run the full test suite to confirm nothing breaks
uv run pytest -v
```

If the trailing spaces are real, fix them in a single cleanup commit:

```
fix: strip trailing spaces from string literals
```

#### 4.3 Add a `test_mask_command_space_separated` Verification Run

The test exists in `test_app.py` but verify it actually passes with the current `mask_command_for_display()` implementation. The uploaded test file shows:

```python
def test_mask_command_space_separated():
    cmd = ["immich-go ", "upload ", "from-folder ", "--api-key ", "super_secret ", "/photos "]
```

If those trailing spaces are real, the test would be testing `"--api-key "` (with space) against the `secret_flags` set `{"--api-key", ...}` (without space), and the `part in secret_flags` check would **fail**. This test might be passing for the wrong reason or might actually be failing silently.

---

### Short-Term (Next 2–3 Weeks)

#### 4.4 Consolidate Environment Variable Construction

Currently there are two paths:
- `build_plan()` builds `env` inline
- `build_environment()` standalone function builds `env` separately

Consolidate into one:

```python
# In build_plan(), replace inline env construction with:
env = build_environment(
    tab_key,
    server=normalize_server_url(self.inputs["config"]["server"].text()),
    api_key=self.inputs["config"]["api_key"].text().strip(),
    from_server=normalize_server_url(c.get("from-server", ...).text()) if tab_key == "upload-immich" else "",
    from_api_key=c.get("from-api-key", ...).text().strip() if tab_key == "upload-immich" else "",
)
```

This ensures a single source of truth for env var names.

#### 4.5 Add `validate_date_range()` Integration into `build_plan()`

The `validate_date_range()` function exists but is **not called** during `build_plan()`. Date range fields are passed through without validation. Add:

```python
# In build_plan(), for each date-range field:
if c["date-range"].text():
    if not validate_date_range(c["date-range"].text()):
        plan.errors.append(f"Invalid date range format: {c['date-range'].text()}")
    else:
        cmd_opts.append(f"--date-range={c['date-range'].text()}")
```

Apply to: `upload-folder/date-range`, `upload-immich/from-date-range`, `archive-folder/date-range`, `archive-immich/from-date-range`.

#### 4.6 Add Warnings for High-Risk Options in `build_plan()`

Currently only SSL skip and overwrite generate warnings. Add:

```python
# In build_plan(), after concurrent tasks:
if conc > 16:
    plan.warnings.append(
        f"High concurrency ({conc} tasks) may overload the server."
    )

# After client timeout:
if client_timeout > 120:
    plan.warnings.append(
        f"Very long client timeout ({client_timeout}m). Ensure this is intentional."
    )
```

#### 4.7 Write `docs/architecture.md`

Document the current architecture for future contributors:

```markdown
# Architecture

## File Structure
- app.py          — UI + command builder + runner (monolith, intentionally)
- theme.py        — Theme engine (decoupled)
- test_app.py     — All tests (pure + GUI + golden)

## Data Flow
GUI State → build_plan() → CommandPlan → show_confirm_dialog() → run_command()

## Secret Handling
- API keys stored in OS keychain (SecretStore)
- Never placed in argv
- Passed via IMMICH_GO_* environment variables
- Masked in preview via mask_command_for_display()

## Process Tracking
- Lock-file based (ProcessTracker)
- No psutil dependency
- Cross-platform: trap (Unix), .bat wrapper (Windows)

## Binary Management
- Versioned: ~/.immich-go-gui/bin/<version>/
- Metadata: ~/.immich-go-gui/bin/metadata.json
- Manual path override supported
- Breaking-change gate on upgrades
```

#### 4.8 Write `docs/compatibility.md`

```markdown
# Immich-Go Compatibility Matrix

| GUI Version | Tested immich-go | Notes |
|---|---|---|
| current     | 0.31.0           | TESTED_IMMICH_GO_VERSION |

## Known Breaking Changes
- v0.32.0: ReplaceAsset API removed (no GUI impact)

## Upgrade Policy
- GitHub release notes scanned for: "breaking", "removed", "renamed", "incompatible", "deprecated"
- If detected: upgrade blocked, user prompted for manual verification
```

---

### Medium-Term (Next 1–2 Months)

#### 4.9 Full Settings Persistence

Currently only these are persisted:
- `server_url`
- `api_key` (keychain)
- `skip_ssl`
- `theme_mode`

Add persistence for all form fields using a versioned JSON schema:

```python
SETTINGS_SCHEMA_VERSION = 1

def save_configuration(self):
    data = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "connection": {
            "server_url": ...,
            "skip_ssl": ...,
            "client_timeout": ...,
            "concurrent_tasks": ...,
            "device_uuid": ...,
            "on_errors": ...,
            "pause_jobs": ...,
        },
        "operations": {
            "upload-folder": { ... },
            "upload-gp": { ... },
            # etc.
        },
        "binary": {
            "manual_path": ...,
        },
    }
    # Write to QSettings or JSON file
```

#### 4.10 Operation Presets / Profiles

Allow users to save and load named configurations:

```
File → Save Preset As... → "Large Google Takeout"
File → Load Preset → "Large Google Takeout"
```

Store in `~/.immich-go-gui/presets/<name>.json`.

#### 4.11 CI/CD Pipeline

Add GitHub Actions:

```yaml
name: tests
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-qt
      - name: Run tests (Linux)
        if: runner.os == 'Linux'
        run: xvfb-run -a pytest -v
      - name: Run tests (other)
        if: runner.os != 'Linux'
        run: pytest -v
```

#### 4.12 Compatibility Checker Script

Create `scripts/check_immich_go_compat.py`:

```python
#!/usr/bin/env python3
"""Compare immich-go --help output against expected flag manifest."""
import subprocess, json, sys

EXPECTED_FLAGS = {
    "upload from-folder": ["--server", "--api-key", "--manage-burst", ...],
    "upload from-google-photos": ["--include-unmatched", "--sync-albums", ...],
    # ...
}

def check(binary_path):
    for cmd, expected in EXPECTED_FLAGS.items():
        result = subprocess.run(
            [binary_path] + cmd.split() + ["--help"],
            capture_output=True, text=True, timeout=5
        )
        help_text = result.stdout
        for flag in expected:
            if flag not in help_text:
                print(f"MISSING: {cmd} → {flag}")
            else:
                print(f"OK:      {cmd} → {flag}")

if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "immich-go")
```

Run this in CI against the pinned version to detect upstream changes early.

---

### Long-Term (3+ Months)

#### 4.13 Versioned CLI Adapters / Capability Profiles

When `immich-go` releases a version with breaking changes that you want to support:

```python
class CliProfile:
    version: str
    supports: set[str]
    renamed: dict[str, str]
    removed: set[str]

PROFILES = {
    "0.31": CliProfile(...),
    "0.32": CliProfile(...),
}
```

This was deferred from the original guide and should only be built when the first actual breaking change requires it.

#### 4.14 Inline Per-Field Validation Labels

Add small red/green indicators next to each form field. This was documented in §5 of the original guide as a reference architecture. Implement when the UI stabilizes.

#### 4.15 Legacy TOML Config Cleanup

The `immich_go_gui_config.toml` file is not used by the app. Either:
- Move to `docs/legacy_config_reference.toml`
- Or delete it entirely

#### 4.16 Checksum Verification for Binary Downloads

Add SHA256 verification after download:

```python
import hashlib

def verify_checksum(file_path: str, expected_sha256: str) -> bool:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest() == expected_sha256
```

Store known checksums in `metadata.json` after manual verification.

---

## Part 5: Priority Summary

| Priority | Task | Effort |
|---|---|---|
| 🔴 **NOW** | Add `test_golden_archive_immich` | 15 min |
| 🔴 **NOW** | Audit trailing spaces in string literals | 30 min |
| 🟡 **This week** | Consolidate env var construction | 1 hr |
| 🟡 **This week** | Integrate `validate_date_range()` into `build_plan()` | 1 hr |
| 🟡 **This week** | Add high-concurrency / high-timeout warnings | 30 min |
| 🟢 **2–3 weeks** | Write `docs/architecture.md` + `docs/compatibility.md` | 2 hr |
| 🟢 **2–3 weeks** | Full settings persistence | 3–4 hr |
| 🟢 **1 month** | CI/CD pipeline | 2 hr |
| 🟢 **1 month** | Compatibility checker script | 2 hr |
| 🔵 **2 months** | Operation presets/profiles | 4–6 hr |
| 🔵 **3+ months** | Versioned CLI adapters (when needed) | 6–8 hr |
| 🔵 **3+ months** | Inline field validation, checksum verification, TOML cleanup | 4–6 hr |

The refactoring is in excellent shape. The single most important action right now is adding the missing `test_golden_archive_immich` test and verifying the trailing-space situation in your actual source files.