# Immich-Go GUI — Agent Guide

Authoritative context for AI agents working in this repository. When user-provided docs or specs conflict with this file, prefer the user’s latest instruction — then update this file if the change is permanent.

---

## 1. Workflow & Execution Philosophy

- **Step-by-step, source-first**: Read authoritative files (`core/flags.toml`, `core/command_builder.py`, tests) before editing. Do not guess flag names or CLI behavior.
- **Frequent logical commits**: Small, reviewable commits with Conventional Commit prefixes (`fix:`, `feat:`, `chore:`, `test:`, `docs:`, `ci:`).
- **Pre-Commit Verification**: The `.githooks/pre-commit` hook runs `pre-commit` (staged files only) automatically on every commit. Before **opening PRs**, run the full local pre-PR gate: `uv run pre-commit run --all-files`, `uv run ty check core/`, `uv run python app.py --self-test`, `uv run python scripts/sync_version.py --check`. Note that `pr-fast-feedback.yml` additionally runs multi-OS pytest, test-count synchronization, and security checks (pip-audit, CodeQL).
- **Mandatory Pre-Commit Verification**: Run local checks (`uv run pre-commit run --all-files`, `uv run ty check core/`, `uv run python app.py --self-test`, `uv run python scripts/sync_version.py --check`) **before committing or opening PRs**. This guarantees `pr-fast-feedback.yml` passes on first attempt.
- **Pre-Commit Verification**: The `.githooks/pre-commit` hook runs `pre-commit` (staged files only) automatically on every commit. Before **opening PRs**, run the full gate: `uv run pre-commit run --all-files`, `uv run ty check core/`, `uv run python app.py --self-test`, `uv run python scripts/sync_version.py --check`. This guarantees `pr-fast-feedback.yml` passes on first attempt.
- **Minimal scope**: Match existing patterns. Avoid drive-by refactors — especially splitting `app.py` unless explicitly requested.

---

## 2. Environment & Tooling

| Tool | Rule |
|------|------|
| **uv** | Always `uv run …`, `uv sync --dev`. Never system `pip` or bare `python`. |
| **gh** | Use normal user auth locally. Do not pass `GITHUB_TOKEN` / `GH_TOKEN` overrides unless CI context requires it. |
| **pytest** | `uv run pytest` (Linux headless requires `libegl1 libgl1 libxkbcommon-x11-0`: `QT_QPA_PLATFORM=offscreen xvfb-run uv run pytest`) |
| **Self-test** | `uv run python app.py --self-test` — loads registry, builds a plan, checks config dir |
| **pre-commit** | `uv run pre-commit run --all-files` — mandatory check before committing or creating PRs |
| **githooks** | Native git hooks in `.githooks/` configured via `git config core.hooksPath .githooks` |
| **subshell/env** | On first command, initialize a persistent terminal (`RunPersistent: true`) with `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"; unset GITHUB_TOKEN GH_TOKEN; export GH_PROMPT_DISABLED=1 NO_COLOR=1` and reuse `TerminalID` across commands to avoid repetitive prefixes and token bloat. |

### Git Branching

| Branch | Purpose |
|--------|---------|
| `master` | Main integration & production; PR target |
| Feature/fix branches | Target `master` via PR |

**Squash merges or Conventional Commits required** when merging PRs → `master` so Release Please commit scanning stays clean.

---

## 3. Architecture & Key Modules

```text
app.py (Qt UI)  →  core/* (Qt-free business logic)  →  immich-go (external binary)
```

- **`core/` is Qt-free.** All command building, validation, secrets, binary management, and terminal launch logic must stay testable without PySide6.
- **`core/flags.toml` is the single source of truth** for tab metadata and flag definitions. Loaded at import by `core/flag_registry.py` → `REGISTRY`.
- **Secrets never go in argv.** API keys are injected as `IMMICH_GO_*` environment variables via `build_environment()` in `core/command_builder.py`.
- **Serverless archive tabs** (`archive-folder`, `archive-gp`, `archive-icloud`, `archive-picasa`) must **never** emit `--server`, `--api-key`, or `--client-timeout`.

### Key Modules

| Module | Role |
|--------|------|
| `app.py` (~4100 lines) | Qt UI: tabs, widgets, status, run/save/load, menus, diagnostics |
| `theme.py` | Palettes, QSS, DPR-aware SVG icons (`load_themed_icon`) |
| `core/flags.toml` (~2600 lines) | All tabs + flags (simple/advanced, secrets, defaults) |
| `core/flag_registry.py` | Parses flags.toml → `REGISTRY` singleton |
| `core/command_builder.py` | `build_plan_from_state()`, `validate_state()`, `validate_state_light()` |
| `core/advanced_flags.py` | Advanced row emission; respects `hidden` flags |
| `core/config_manager.py` | TOML config, keyring `SecretStore`, corrupt-file quarantine |
| `core/profile_manager.py` | Multi-profile dirs + transactional rename |
| `core/app_update.py` | Asynchronous GitHub release update check (`QThreadPool` worker) |
| `gui/mixins/app_update.py` | Update check dialog & UI integration mixin |
| `core/binary_manager.py` | Download, SHA256 verify, version policy |
| `core/terminal_launcher.py` | Cross-platform external terminal + POSIX `run.sh` |
| `core/process_tracker.py` | Lock files, heartbeat, stale-lock detection |
| `core/network.py` | `normalize_server_url()`, connection preflight |
| `core/logging_config.py` | Rotating log under `{config_dir}/logs/` |

### Runtime Data Files (must ship in Nuitka builds)

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

## 4. Flag Emission & Validation

> **A flag reaches the CLI if and only if the user explicitly asked for it.** immich-go applies its own defaults for anything not passed.

- **`mode = "simple"`** — visible in simple UI; emit when value ≠ TOML/CLI default.
- **`mode = "advanced"`** — row shown in advanced panel; emit **only** when enable checkbox is checked.
- **`hidden = true`** — not shown in UI; used for structural flags like `from-dry-run`.
- **Config persistence**: Simple values in `form_state.{tab}.{key}`; Advanced in `form_state.advanced.{tab}.{key}`; Secrets in OS keyring or fallback `secrets.toml` — never in `form_state`.
- **Validation**:
  - `validate_state()` (Preview/Run - with glob expansion)
  - `validate_state_light()` (Debounced status card - light check)
  - Always normalize server URL before validating (`normalize_server_url` → `validate_server_url`).

---

## 5. Security & Secret Handling

| Concern | Mitigation |
|---------|------------|
| Keys in argv / preview | Env vars only; `mask_command_for_display()` |
| Keys in config files | OS keyring default; `0600` secrets.toml fallback |
| POSIX / Windows secret delivery | POSIX: `IMMICH_GO_*` in `env.sh` (`0600`) in temp dir, sourced then deleted. Windows: `Popen` env dict. |
| SSL bypass | Warning in plan + UI banner; global skip propagates to source flags on immich-to-immich tabs |
| Overlapping runs | Lock files under `{config_dir}/locks/`; GUI tracks `active_lock_paths` set |

**Redaction rule:** Logs and previews show env var **names**, never values.

---

## 6. Testing

- **Suite Metrics**: **487 tests across 30 modules**, coverage gate **75%** on `core` (Linux CI).
- **Conventions**:
  - Windows path normalization: pass argv through `_norm_argv(...)` before comparing paths.
  - Golden fixtures: `tests/fixtures/command_states/*.json`
  - CLI help fixtures: `core/fixtures/cli_help/0.32.0/` — regenerate via `uv run python scripts/capture_cli_help.py`

---

## 7. CI/CD, Packaging & Versioning

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push to `master` | `ty` type checker (`core/`), pre-commit, multi-OS pytest + coverage, `--self-test` |
| `pr-fast-feedback.yml` | PR | Multi-OS tests, `ty` type checker, pre-commit, version sync check, pip-audit, CodeQL |
| `docs.yml` | Tag `v*` / manual | Test count sync, MkDocs build, lychee link check, GitHub Pages deploy |
| `release.yml` | Tag `v*` | **pytest gate** → Nuitka builds → SHA256SUMS → GitHub Release |
| `release-please.yml` | Push to `master` | Version bump PR (updates pyproject.toml, manifest, docs via `extra-files`) |

### Packaging & Version Rules

- **Version Sync**: `pyproject.toml` is the single source of truth (`uv run python scripts/sync_version.py`).
- **Release Please**: Config in `.github/release-please-config.json` uses `extra-files` to sync `docs/README.md` and `docs/developer-guide/ci-cd-and-releases.md`.
- **Build icons**: `immich-go-gui.ico` (Windows) and `immich-go-gui.icns` (macOS). Regenerate: `uv run python scripts/generate_build_icons.py`.
- **Code signing**: CI builds are **unsigned**. Windows SmartScreen / macOS Gatekeeper warnings are expected.

---

## 8. Common Pitfalls

1. **Adding flags in Python instead of `flags.toml`** — always extend the registry first.
2. **Emitting secrets as CLI flags** — use `secret_env` in flags.toml + `build_environment()`.
3. **Blocking serverless tabs on connection failure** — check `SERVER_REQUIRED_TABS`.
4. **Forgetting Nuitka data files** — `flags.toml` and `core/fixtures/` or packaged app crashes on import.
5. **Qt signal arity** — `QTimer.timeout` and `QPlainTextEdit.textChanged` emit no args; `QAction.triggered` emits `bool`.

---

## 9. Useful Commands

```bash
uv sync --dev
uv run pytest
uv run python app.py --self-test
uv run python scripts/sync_version.py --check        # verify pyproject.toml matches docs
uv run python scripts/sync_test_count.py --sync       # sync pytest count to documentation
uv run python scripts/capture_cli_help.py            # refresh CLI help fixtures
uv run python scripts/generate_build_icons.py        # regenerate .ico and .icns from .png
uv run ty check core/
uv run ty check core/
uv run pre-commit run --all-files                     # MANDATORY before commit/PR
```

---

## 10. Persistence & Async Invariants

- **`form_state` is session-only** — never persisted under schema v3.
- **`save_secret_with_fallback()` only raises `OSError`** — callers MUST wrap in `try/except OSError`.
- **`check_for_application_updates()` never blocks the GUI thread** — runs on `QThreadPool` worker (`QRunnable` + `Signal`).
