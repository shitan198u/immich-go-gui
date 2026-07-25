# Testing

The test suite lives in `tests/test_app.py` (~100 tests) using pytest and pytest-qt.

## Running Tests

```bash
uv sync --dev
uv run pytest
```

### Headless Linux

CI runs Linux tests with offscreen Qt and xvfb:

```bash
QT_QPA_PLATFORM=offscreen xvfb-run uv run pytest
```

Required system packages on Ubuntu (see `.github/workflows/ci.yml`):

- `xvfb`, `libxkbcommon-x11-0`, `libxcb-cursor0`, and related XCB libraries

macOS and Windows run `uv run pytest` directly without xvfb.

## Test Categories

### Golden Command Tests

Verify that form state produces the expected `CommandPlan` argv and env for each tab. Fixtures live in `tests/fixtures/command_states/`.

Example pattern:

```python
def test_golden_upload_folder(gui):
    gui.toggle_advanced(False)
    gui.inputs["upload-folder"]["path"].setText("/photos")
    plan = gui.build_plan(dry_run=False)
    assert _norm_argv(plan.argv) == _norm_argv([...])
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert not any("--api-key" in p for p in plan.argv)
```

Key assertions:

- Correct command tokens for the tab
- Secrets in env, not argv
- Serverless tabs omit server flags

### Cross-Platform Path Normalization

All argv comparisons MUST use `_norm_argv()`:

```python
def _norm_argv(argv):
    # Strips Windows drive letters (C:, D:)
    # Normalizes backslashes to forward slashes
    ...
```

This ensures tests pass on Linux, macOS, and Windows CI runners.

### Headless Terminal Mocks

Launcher tests mock platform and terminal detection:

```python
with patch("sys.platform", "linux"):
    with patch("shutil.which", return_value="/usr/bin/gnome-terminal"):
        result = launch_external_terminal(...)
```

This prevents CI failures when no terminal emulator is installed.

### CLI Contract Tests

`core/cli_contract.py` compares:

- `TAB_ALLOWED_FLAGS` against captured CLI help fixtures
- Live binary `--help` output (when binary present)

Fixtures are stored in `tests/fixtures/cli_help/{version}/`.

## Fixtures

| Directory | Contents |
|-----------|----------|
| `tests/fixtures/cli_help/` | Captured `--help` text per immich-go version |
| `tests/fixtures/command_states/` | Golden JSON form states per tab |

## Regenerating CLI Help Fixtures

When immich-go releases a new version:

1. Install or download the new binary to `~/.immich-go-gui/bin/`
2. Run the capture script:

```bash
uv run scripts/capture_cli_help.py
```

3. Update `TAB_ALLOWED_FLAGS` in `core/cli_schema.py` if flags changed
4. Run tests and fix any golden fixture drift

See [Scripts](scripts.md) for script details.

## Writing New Tests

1. Use the `gui` pytest fixture (pytest-qt) for widget interaction
2. Call `gui.build_plan()` rather than clicking Run (avoids subprocess)
3. Always `_norm_argv()` when comparing paths in argv
4. Mock network, subprocess, and keyring for unit tests
5. Use `pyfakefs` for filesystem tests where applicable

## Pre-commit

Local lint/format checks via pre-commit:

```bash
uv run pre-commit run --all-files
```

Configured in `.pre-commit-config.yaml`: trailing whitespace, YAML check, Ruff lint/format.

## CI Matrix

| Workflow | Trigger | Platforms |
|----------|---------|-----------|
| `ci.yml` | Push to `master` | ubuntu-22.04, macos-latest, windows-latest |
| `pr-fast-feedback.yml` | PR to `master`/`staging` | Same + Nuitka smoke build, CodeQL |

See [CI/CD and Releases](ci-cd-and-releases.md).
