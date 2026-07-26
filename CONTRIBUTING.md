# Contributing to Immich-Go GUI

Thank you for helping improve Immich-Go GUI. Clear PRs and docs keep the project healthy for users and maintainers alike.

## Where do I go from here?

If you've noticed a bug or have a feature request, check for an existing [issue](https://github.com/shitan198u/immich-go-gui/issues) first. If none exists, open one with the provided templates.

Documentation-only fixes are very welcome — start from the [docs hub](README.md).

## Documentation map

| Audience | Read first |
|----------|------------|
| Architecture | [Architecture](developer-guide/architecture.md) |
| Core package | [Core Modules](developer-guide/core-modules.md) |
| Tests | [Testing](developer-guide/testing.md) |
| Releases / CI | [CI/CD and Releases](developer-guide/ci-cd-and-releases.md) |
| Extending CLI parity | [Adding Tabs and Flags](developer-guide/adding-tabs-and-flags.md) |
| CLI / config lookup | [Reference](reference/cli-command-mapping.md) |
| Security model | [Security & Privacy](user-guide/security-and-privacy.md) |

Agent-oriented project notes also live in [`AGENTS.md`](https://github.com/shitan198u/immich-go-gui/blob/master/.agents/AGENTS.md); keep them aligned when you change architecture or CI conventions.

## Setting up for local development

1. **Install prerequisites**
   - Python **3.13** (`>=3.13.0, <3.14`)
   - [`uv`](https://docs.astral.sh/uv/getting-started/installation/) package manager

2. **Fork & clone**

   ```bash
   git clone https://github.com/YOUR_USERNAME/immich-go-gui.git
   cd immich-go-gui
   ```

3. **Install dependencies**

   ```bash
   uv sync --dev
   ```

   This installs PySide6, pytest, pre-commit, Nuitka (dev), and related tools.

4. **Run the application**

   ```bash
   uv run app.py
   ```

5. **(Optional) Enable pre-commit hooks**

   ```bash
   uv run pre-commit install
   uv run pre-commit run --all-files
   ```

## Testing your changes

```bash
uv run pytest
```

Linux headless (matches CI):

```bash
QT_QPA_PLATFORM=offscreen xvfb-run uv run pytest
```

When adding behavior:

- Prefer tests in `tests/test_app.py`
- Use `_norm_argv()` for path comparisons
- Update golden fixtures under `tests/fixtures/` when command output changes
- After upgrading immich-go, run `uv run scripts/capture_cli_help.py`

Details: [Testing guide](developer-guide/testing.md).

## Making a pull request

1. Branch from **`staging`**: `git checkout -b feature-or-bugfix-name`
2. Make focused commits (see commit style below)
3. Push and open a PR **targeting `staging`**
4. Fill out the PR template (platforms tested, docs updated, tests run)

### Commit message style

This repo uses [Release Please](https://github.com/googleapis/release-please) with [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Changelog section |
|--------|-------------------|
| `feat:` | Features |
| `fix:` | Bug fixes |
| `docs:` | Documentation |
| `sec:` | Security |
| `refactor:` | Refactoring |
| `test:` / `ci:` / `chore:` | Usually hidden from user-facing notes |

Examples:

```text
feat: add preferred terminal override for Linux
fix: auto-disable pause-immich-jobs without admin key
docs: document admin API key and job pausing
```

## Branching policy

| Branch | Role |
|--------|------|
| `staging` | Active development; **all contributor PRs land here** |
| `master` | Production; advanced by Release Please after squash merge from `staging` |

Do not open routine feature PRs directly against `master`.

## Design rules worth knowing early

- **`core/` is Qt-free.** Business logic stays testable without a display server.
- **Secrets never go in argv.** Use env delivery via `build_environment()`.
- **Serverless archive tabs** must never emit `--server`, `--api-key`, or `--client-timeout`.
- **Flag allowlists** in `TAB_ALLOWED_FLAGS` are the source of truth for what each tab may emit.
- Prefer small PRs with tests over large unscoped rewrites.

## Building executables (optional)

Local Nuitka smoke builds:

**Windows:**

```bash
uv run python -m nuitka --assume-yes-for-downloads --onefile --windows-console-mode=disable --enable-plugin=pyside6 --include-data-files=immich-go-gui.png=immich-go-gui.png app.py
```

**macOS:**

```bash
uv run python -m nuitka --assume-yes-for-downloads --macos-create-app-bundle --enable-plugin=pyside6 --include-data-files=immich-go-gui.png=immich-go-gui.png app.py
```

**Linux:**

```bash
uv run python -m nuitka --assume-yes-for-downloads --standalone --enable-plugin=pyside6 --include-data-files=immich-go-gui.png=immich-go-gui.png app.py
```

Official multi-format packages are produced by `.github/workflows/release.yml`. See [CI/CD and Releases](developer-guide/ci-cd-and-releases.md).

## Documentation contributions

When you change user-visible behavior, update the matching page under `docs/`:

| Change type | Update |
|-------------|--------|
| New tab / flag | User workflow page + CLI mapping + advanced flags + tests |
| Config field | `configuration.md` + `config-schema.md` |
| Secret / env handling | `security-and-privacy.md` + `environment-variables.md` |
| Install artifact names | `platform-notes.md` + README + getting-started |
| CI / branching | `ci-cd-and-releases.md` + CONTRIBUTING |

Keep the [docs hub](README.md) table of contents in sync when adding new pages.

Thank you for contributing!
