# CI/CD and Releases

## Branching Policy

| Branch | Purpose |
|--------|---------|
| `master` | Production; updated via Release Please PR merges only |
| `staging` | Active development and integration |
| Feature branches | Target `staging` via pull request |

Pull requests to `master` come from `staging`. Merges from `staging` into `master` **must use squash merge** to keep Release Please commit history clean.

## GitHub Actions Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI Checks | `.github/workflows/ci.yml` | Push to `master` | Multi-OS pytest |
| PR Fast Feedback | `.github/workflows/pr-fast-feedback.yml` | PR to `master`/`staging` | Tests, CodeQL, Nuitka smoke, PR comments |
| CodeQL | `.github/workflows/codeql.yml` | Push/PR/schedule | Python security scanning |
| Release Please | `.github/workflows/release-please.yml` | Push to `master` | Automated version bump PR |
| Release Build | `.github/workflows/release.yml` | Tag `v*` or manual | Build and publish release artifacts |
| Manual Prerelease | `.github/workflows/manual-prerelease.yml` | Manual dispatch | Pre-release builds |

## Release Please

Configuration files:

- `.github/release-please-config.json`
- `.github/.release-please-manifest.json`

When merging to `master`, Release Please opens a version bump PR. On merge, it creates a GitHub Release and triggers the release build workflow.

**Important:** Update `.github/.release-please-manifest.json` when performing manual version bumps so Release Please tracks the correct baseline.

Current version is defined in `pyproject.toml` (e.g. `1.2.0`).

## Release Artifacts

Built with Nuitka (directives embedded at top of `app.py`):

| Platform | Formats |
|----------|---------|
| Windows | Setup `.exe`, portable `.exe` |
| macOS | `.dmg` app bundle |
| Linux | AppImage, `.deb`, `.rpm`, `.tar.gz` |

### Artifact Naming Convention

All packages include version and architecture:

```text
Immich-Go-GUI-{VERSION}-{OS}-{ARCH}.{ext}
```

Examples:

- `Immich-Go-GUI-1.1.0-Windows-x86_64-Setup.exe`
- `Immich-Go-GUI-1.1.0-Linux-x86_64.AppImage`

## Packaging Configs

| Platform | Config |
|----------|--------|
| Windows | `packaging/windows/installer.iss` (Inno Setup) |
| Linux DEB/RPM | `packaging/linux/nfpm.yaml` |
| Linux desktop entry | `packaging/linux/immich-go-gui.desktop` |

### Build Rules

- **App icons:** `immich-go-gui.ico` (Windows) and `immich-go-gui.icns` (macOS) in the repo root. Regenerate from `immich-go-gui.png` with `uv run python scripts/generate_build_icons.py` (requires Pillow; dev-only, not a runtime dependency).
- **Inno Setup output:** `OutputDir=..\..\` — release workflow moves `.exe` files back to workspace root before artifact upload.
- **AppImageTool:** Uses continuous release from AppImageKit with `--appimage-extract-and-run`.

## Local Nuitka Builds

See [CONTRIBUTING](../CONTRIBUTING.md) for per-OS Nuitka commands.

### Python version pin

`requires-python = ">=3.13.0, <3.14"` is intentional. Release builds
use Nuitka, which must be validated against each new CPython minor
version before the pin can be widened. Do not widen this range without
a full Nuitka smoke-build pass on all three platforms.

## Tooling Conventions

- **Package manager:** Always use `uv` (`uv sync`, `uv run pytest`, `uv run app.py`)
- **GitHub CLI:** Use standard user auth for `gh` commands locally; do not pass `GITHUB_TOKEN`/`GH_TOKEN` overrides
- **Lint/format:** Ruff via pre-commit

## Dependabot

Configured in `.github/dependabot.yml` for dependency update PRs (open PR limit currently 15).

## Conventional commits

Release Please groups commits by type. Prefer:

```text
feat: …    fix: …    docs: …    sec: …    refactor: …
test: …    ci: …     chore: …
```

See [CONTRIBUTING](../CONTRIBUTING.md) for the full contributor workflow.
