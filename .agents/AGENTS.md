# Immich-Go GUI — Agent Guide

Authoritative context for AI agents working in this repository. When user-provided docs or specs conflict with this file, prefer the user’s latest instruction — then update this file if the change is permanent.

---

## 1. Workflow & Execution Philosophy

- **Step-by-step, source-first**: Read authoritative files (`core/flags.toml`, `core/command_builder.py`, tests) before editing. Do not guess flag names or CLI behavior.
- **Frequent logical commits**: Small, reviewable commits with Conventional Commit prefixes (`fix:`, `feat:`, `chore:`, `test:`, `docs:`, `ci:`).
- **Minimal scope**: Match existing patterns. Avoid drive-by refactors — especially splitting `app.py` unless explicitly requested.

---

## 2. Environment & Tooling

| Tool | Rule |
|------|------|
| **uv** | Always `uv run …`, `uv sync --dev`. Never system `pip` or bare `python`. |
| **gh** | Use normal user auth locally. Do not pass `GITHUB_TOKEN` / `GH_TOKEN` overrides unless CI context requires it. |
| **pytest** | `uv run pytest` (Linux headless: `QT_QPA_PLATFORM=offscreen xvfb-run uv run pytest`) |
| **Self-test** | `uv run python app.py --self-test` — loads registry, builds a plan, checks config dir |

### Git branching

| Branch | Purpose |
|--------|---------|
| `master` | Production; Release Please merges only |
| `staging` | Active integration |
| Feature/fix branches | Target `staging` via PR |

**Squash merges required** when merging `staging` → `master` so Release Please commit scanning stays clean.

---

## 3. What This Project Is

A **PySide6 desktop GUI** for [immich-go](https://github.com/simulot/immich-go) (CLI target **v0.32.0**). Users configure upload/archive/stack jobs, preview the exact command (secrets redacted), and launch **immich-go in an external terminal**.

**11 workflow tabs** — one per immich-go subcommand:

| Group | Tab keys |
|-------|----------|
| Upload | `upload-folder`, `upload-gp`, `upload-icloud`, `upload-picasa`, `upload-immich` |
| Archive | `archive-folder`, `archive-gp`, `archive-icloud`, `archive-picasa`, `archive-immich` |
| Stack | `stack` |

---

## 4. Architecture (Non-Negotiable)

```text
app.py (Qt UI)  →  core/* (Qt-free business logic)  →  immich-go (external binary)
```

- **`core/` is Qt-free.** All command building, validation, secrets, binary management, and terminal launch logic must stay testable without PySide6.
- **`core/flags.toml` is the single source of truth** for tab metadata and flag definitions. Loaded at import by `core/flag_registry.py` → `REGISTRY`.
- **`cli_schema.py` and `advanced_flags.py`** are thin shims over the registry — do not duplicate flag lists elsewhere.
- **Secrets never go in argv.** API keys are injected as `IMMICH_GO_*` environment variables via `build_environment()` in `core/command_builder.py`.
- **Serverless archive tabs** (`archive-folder`, `archive-gp`, `archive-icloud`, `archive-picasa`) must **never** emit `--server`, `--api-key`, or `--client-timeout`.

### Key modules

| Module | Role |
|--------|------|
| `app.py` (~4100 lines) | Qt UI: tabs, widgets, status, run/save/load, menus, diagnostics |
| `theme.py` | Palettes, QSS, DPR-aware SVG icons (`load_themed_icon`) |
| `core/flags.toml` (~2600 lines) | All tabs + flags (simple/advanced, secrets, defaults) |
| `core/flag_registry.py` | Parses flags.toml → `REGISTRY` singleton |
| `core/command_builder.py` | `build_plan_from_state()`, `validate_state()`, `validate_state_light()` |
| `core/advanced_flags.py` | Advanced row emission; respects `hidden` flags |
| `core/cli_help.py` | Loads CLI help fixtures from `core/fixtures/cli_help/{version}/` |
| `core/cli_contract.py` | Compatibility checker; `IGNORED_UPSTREAM_FLAGS` for intentional omissions |
| `core/config_manager.py` | TOML config, keyring `SecretStore`, corrupt-file quarantine |
| `core/profile_manager.py` | Multi-profile dirs + transactional rename |
| `core/binary_manager.py` | Download, SHA256 verify, version policy |
| `core/terminal_launcher.py` | Cross-platform external terminal + POSIX `run.sh` |
| `core/process_tracker.py` | Lock files, heartbeat, stale-lock detection |
| `core/network.py` | `normalize_server_url()`, connection preflight |
| `core/logging_config.py` | Rotating log under `{config_dir}/logs/` |

### Runtime data files (must ship in Nuitka builds)

```
core/flags.toml
core/fixtures/cli_help/{version}/*
assets/icons/*
immich-go-gui.png
immich-go-gui.ico          # Windows only; multi-size 16–256px
immich-go-gui.icns         # macOS only; multi-size 16–512px
```

Nuitka directives live at the top of `app.py`. All release workflow invocations must include `--include-data-files=core/flags.toml=core/flags.toml` and `--include-data-dir=core/fixtures=core/fixtures`.

---

## 5. Flag Emission Model (1.4.0+)

> **A flag reaches the CLI if and only if the user explicitly asked for it.** immich-go applies its own defaults for anything not passed.

### Modes

- **`mode = "simple"`** — visible in simple UI; emit when value ≠ TOML/CLI default.
- **`mode = "advanced"`** — row shown in advanced panel; emit **only** when enable checkbox is checked.
- **`hidden = true`** — not shown in UI; used for structural flags like `from-dry-run` (emitted by Dry Run button only).

### Emission order (`build_plan_from_state`)

1. Build `IMMICH_GO_*` env via `build_environment()`
2. Structural flags: server, skip-ssl, positional-owned keys
3. **Global skip-SSL mapping:**
   - Server-required tabs → `--skip-verify-ssl`
   - `upload-immich` / `archive-immich` → also `--from-skip-verify-ssl` (source server)
4. Simple-mode widgets (non-default values)
5. Positional-owned flags (`from-server`, `write-to`, etc.)
6. Advanced rows (enabled only)
7. Dry-run button → `--dry-run` (+ `--from-dry-run` for immich-to-immich tabs)
8. Path positional suffix
9. **Safety:** upload/stack tabs without admin key → force `--pause-immich-jobs=false` + warning (unless user explicitly set false)

### Config persistence

- Simple values: `form_state.{tab}.{key}`
- Advanced: `form_state.advanced.{tab}.{key}.enabled` + `.value`
- Secrets: keyring (preferred) or `profiles/{name}/secrets.toml` — never in `form_state`

### Validation

| Function | When used | Glob expansion |
|----------|-----------|----------------|
| `validate_state()` | Preview / Run | Yes |
| `validate_state_light()` | Status bar updates | No |
| `ValidationResult.field_errors` | Inline red labels under fields | — |

Always **normalize server URL before validating** (`normalize_server_url` → `validate_server_url`).

---

## 6. Security & Secret Handling

| Concern | Mitigation |
|---------|------------|
| Keys in argv / preview | Env vars only; `mask_command_for_display()` |
| Keys in config files | OS keyring default; `0600` secrets.toml fallback |
| Keys in launch scripts | Windows `.bat` has no secrets; POSIX `run.sh` has no secrets in argv |
| POSIX secret delivery | `IMMICH_GO_*` written to `env.sh` (`0600`) in temp dir (`0700`), sourced then deleted at start of `run.sh` — required because Terminal.app / some emulators drop parent env |
| Windows secret delivery | Full `env` dict passed to `subprocess.Popen` on `cmd.exe` |
| SSL bypass | Warning in plan + UI banner; global skip propagates to source flags on immich-to-immich tabs |
| Overlapping runs | Lock files under `{config_dir}/locks/`; GUI tracks `active_lock_paths` set |

**Redaction rule:** Logs and previews show env var **names**, never values.

---

## 7. Terminal Launcher & Process Locks

### POSIX (`core/terminal_launcher.py`)

- Temp dir `immich-go-run-*` with `run.sh`, optional `env.sh`, PID/heartbeat sidecars
- `cd "$HOME"` before executing (prevents CWD-deletion races)
- `trap cleanup EXIT INT TERM HUP`
- Binary path resolved to absolute before launch
- Stale lock: dead shell PID → lock inactive (unless startup grace period)

### Windows

- `.bat` launcher with background heartbeat loop
- `CREATE_NEW_CONSOLE` + `cmd /k` (no `shell=True`)
- Dead terminal PID clears lock immediately

### Connection-test gating

Failed config-tab connection test disables Run **only** on `SERVER_REQUIRED_TABS` — serverless archive tabs remain runnable.

---

## 8. Testing

### Test modules

| File | Focus |
|------|-------|
| `tests/test_app.py` | GUI integration, command building, locks, profiles |
| `tests/test_emission_model.py` | Emission rules / golden fixtures |
| `tests/test_flag_registry.py` | flags.toml schema integrity |
| `tests/test_config_manager.py` | Config load, corrupt-file quarantine |
| `tests/test_terminal_launcher_env.py` | POSIX env.sh, stale-lock, binary resolve |

### Conventions

- **Windows path normalization:** pass argv through `_norm_argv(...)` before comparing paths.
- **Headless launcher mocks:** `patch("shutil.which", return_value="/usr/bin/gnome-terminal")` + platform patches.
- **Golden fixtures:** `tests/fixtures/command_states/*.json`
- **CLI help fixtures (runtime + tests):** `core/fixtures/cli_help/0.32.0/` — regenerate via `uv run python scripts/capture_cli_help.py`
- **Stub binary:** `tests/stub_immich_go.py` for launcher integration tests

Target: **~217 tests**, coverage gate **80%** on `core` + `app` (Linux CI).

---

## 9. CI/CD & Packaging

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push to `master` | Pyright (`core/`), pre-commit, multi-OS pytest + coverage, `--self-test` |
| `pr-fast-feedback.yml` | PR | Tests, pip-audit (fails on vulns), CodeQL |
| `release.yml` | Tag `v*` | **pytest gate** → Nuitka builds → SHA256SUMS → GitHub Release |
| `release-please.yml` | Push to `master` | Version bump PR |

### Build artifacts

Naming: `Immich-Go-GUI-{VERSION}-{OS}-{ARCH}.{ext}`

| Platform | Outputs |
|----------|---------|
| Windows | Setup.exe (Inno Setup), portable zip |
| macOS | DMG (arch detected: arm64 / x86_64) |
| Linux | AppImage, tar.gz, deb, rpm |

### Packaging rules

- **Build icons:** `immich-go-gui.ico` (Windows) and `immich-go-gui.icns` (macOS). Regenerate: `uv run python scripts/generate_build_icons.py` (Pillow is dev-only).
- **Inno Setup:** `packaging/windows/installer.iss` outputs to `..\..\` — release workflow relocates `.exe` before artifact upload.
- **AppImage:** uses `appimagetool` continuous release with `--appimage-extract-and-run` (not pinned — known trade-off).
- **Release Please:** config in `.github/release-please-config.json` + `.github/.release-please-manifest.json` — keep manifest in sync on manual version bumps.

### Code signing

CI builds are **unsigned**. Windows SmartScreen / macOS Gatekeeper warnings are expected for distributed binaries.

---

## 10. UI Features Agents Should Know

- **Status card** — debounced updates use `validate_state_light()` (no `build_plan` on every keystroke).
- **Inline field errors** — `ValidationResult.field_errors` → red `FieldError` labels per tab widget.
- **Help menu** — Open Config Folder, Open Log Folder, Export Diagnostics (secrets redacted).
- **Exception hook** — `_install_exception_hook()` logs tracebacks + shows non-blocking error dialog.
- **Advanced mode toggle** — `SwitchButton` widget; state synced with saved `advanced_mode` config.

---

## 11. Tech Stack

- Python **3.13** (`>=3.13.0, <3.14`)
- PySide6, `keyring`, `requests`, `packaging`, `tomli-w`
- Dev: `pytest`, `pytest-qt`, `pytest-cov`, `pyright`, `ruff`, `pre-commit`, `nuitka`, `pillow` (icon script only), MkDocs Material
- Release builds: Nuitka standalone / app bundle

---

## 12. Common Pitfalls

1. **Adding flags in Python instead of `flags.toml`** — always extend the registry first.
2. **Emitting secrets as CLI flags** — use `secret_env` in flags.toml + `build_environment()`.
3. **Blocking serverless tabs on connection failure** — check `SERVER_REQUIRED_TABS`.
4. **Forgetting Nuitka data files** — `flags.toml` and `core/fixtures/` or packaged app crashes on import.
5. **Assuming POSIX env inheritance** — secrets must go through `env.sh` inside `run.sh`.
6. **Editing `tests/fixtures/cli_help/`** — that path is removed; use `core/fixtures/cli_help/`.
7. **Qt signal arity** — `QTimer.timeout` and `QPlainTextEdit.textChanged` emit no args; `QAction.triggered` emits `bool`.

---

## 13. Useful Commands

```bash
uv sync --dev
uv run pytest
uv run python app.py --self-test
uv run python scripts/capture_cli_help.py          # refresh CLI help fixtures
uv run python scripts/generate_build_icons.py      # regenerate .ico and .icns from .png
uv run pyright core/
uv run pre-commit run --all-files
```

---

## 14. Config Persistence & Test-Isolation Invariants (must-not-break)

Durable rules established by the schema-v3 / slim-persistence work (PR #96 era). Violating these reintroduces real bugs — keep them in mind.

### Persistence & secrets

- **`form_state` is session-only** — it is never persisted under schema v3. Both `save_config()` and `save_server_url()` write `schema_version = 3` **unconditionally** (`save_server_url` uses assignment, not `setdefault`, so a legacy v2 config is upgraded when the public API writes it).
- **`save_secret_with_fallback()` only raises `OSError`.** `SecretStore.set_secret`/`get_secret` swallow all keyring exceptions internally, so the only uncaught raise path is the fallback `secrets.toml` file write. GUI callers (`save_server_details`, `save_configuration` in `gui/mixins/persistence.py`) MUST wrap `save_secret_with_fallback` in `try/except OSError`, matching the adjacent `save_server_url`/`save_config` guards — otherwise a keyring+file write failure crashes `closeEvent`/profile-switch.
- **Profile migration is independent.** In `migrate_single_config_to_default()` (`core/profile_manager.py`), legacy config migration is best-effort (`_migrate_legacy_config_file`) and must NOT `return` out of the whole function — the legacy `secrets.toml` migration on the same call always runs.
- **Save flow bails on first failure.** `_save_pending_configuration` / `_save_from_menu` skip `save_configuration()` when `save_server_details()` fails, to avoid a second redundant "Save Failed" dialog for one disk error.

### Async update check

- **`check_for_application_updates()` never blocks the GUI thread.** It runs the GitHub fetch (`requests.get`, timeout 15s) on a `QThreadPool` worker (`QRunnable` + `Signal`); the result is handled in `_handle_update_check_result` (`gui/mixins/app_update.py`). Tests drain the worker with `QThreadPool.globalInstance().waitForDone()` + `QApplication.processEvents()` (see `_drain_update_check` in `tests/test_app_update.py`).

### Test isolation (CRITICAL — was a real bug)

- **The session `gui` fixture is built BEFORE function-scoped autouse fixtures.** `ImmichGoGUI.__init__` (`gui/main_window.py`) calls `active_profile_name()` (→ `ensure_default_profile()` → `_save_profiles_index()` writes `profiles.toml`) and `load_config()` at construction. Therefore config isolation MUST happen **before** the `gui` fixture builds the window — see `_session_config_root` in `tests/conftest.py`, which `gui` depends on. **Linux isolation:** `_session_config_root` sets `XDG_CONFIG_HOME` to a session tmp dir, protecting the developer's real `~/.config/immich-go-gui/`. **Verify after conftest changes:** `stat -c %y ~/.config/immich-go-gui/profiles.toml` before and after a test run — the mtime must NOT change. **macOS/Windows gap:** `XDG_CONFIG_HOME` is ignored on these platforms (`core/config_manager.py::default_config_dir()` uses native paths: `~/Library/Application Support/immich-go-gui` on macOS, `%APPDATA%\immich-go-gui` on Windows). The session fixture does **not** currently monkeypatch these platform-specific path resolutions, so macOS/Windows developers running the test suite may see writes to their real config directories during session `gui` construction. To fully isolate on all platforms, `_session_config_root` would need to also patch `default_config_dir()` or set the `IMMICH_GO_GUI_CONFIG` env var override (which works cross-platform per lines 144-146 in `config_manager.py`), but the current implementation relies solely on XDG redirection.
- **Platform-specific config path tests must be conditionally skipped.** Tests that assert Linux XDG paths must be guarded with `@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="XDG_CONFIG_HOME is honored only on Linux")` (see `test_linux_xdg_*` in `tests/test_persistence.py`). Use the same pattern for macOS-specific (`sys.platform.startswith("darwin")`) or Windows-specific (`sys.platform.startswith("win")`) config directory assertions if added in the future.
- **Tests that build their own `ImmichGoGUI` and exercise real `secrets.toml` I/O:** force file-backed secrets by stubbing `SecretStore.set_secret` → `False` and `get_secret` → `""` (avoids keyring flakiness/leak), and always close the GUI (`gui._force_close = True; gui.close()`).

### Docs emission model

- Only `client-timeout` / `from-client-timeout` is **unconditionally** emitted (applicable tabs). `server`, `skip-verify-ssl`, and `dry-run` are emitted **only when configured or requested** (`docs/user-guide/advanced-flags.md`).

### PR / branch hygiene

- **#96 (`feat/config-slim-and-updates-ui`) is the single merge path** for the config/UX wave; the focused splits #97–#100 were closed as superseded. Never keep an umbrella PR and its splits open at the same time. Before deleting umbrella branches, recover orphaned commits that live on no split (e.g., the ruff-formatting commit `3cfa2b6` on the wave-2 umbrella).

### CI gating reality

- **PR-gating** (`pr-fast-feedback.yml`) = multi-OS `pytest` + `pip-audit` + CodeQL. **Ruff / Pyright / pre-commit run in `ci.yml` on push to `master` only — they are NOT PR-gating.** CodeRabbit review is informational/non-gating (and frequently rate-limited).
