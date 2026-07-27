# Scripts

Maintenance scripts in `scripts/` are Qt-free Python utilities. Run them with `uv`:

```bash
uv run scripts/<script>.py
```

## capture_cli_help.py

Captures immich-go `--help` output into versioned test fixtures.

**Purpose:** Keep `TAB_ALLOWED_FLAGS` and CLI contract tests aligned with the installed immich-go binary.

**Usage:**

```bash
uv run scripts/capture_cli_help.py
```

**What it does:**

1. Locates the immich-go binary via `core/binary_manager.get_binary_path()`
2. Runs `--help` for each target subcommand (upload, archive, stack variants)
3. Writes text files to `tests/fixtures/cli_help/{version}/`
4. Generates a manifest JSON with capture metadata

**Target commands** include root, all upload/archive subcommands, and stack — matching the 11 GUI tabs.

**When to run:** After upgrading immich-go or when adding a new tab/subcommand.

## bundle_codebase.py

Bundles Python source files into a single text file for LLM code review.

**Usage:**

```bash
uv run scripts/bundle_codebase.py [output_path]
```

Default output: `immichgo_modules_bundle.txt`

**Bundled files:**

- All `core/*.py` modules
- `tests/test_app.py`
- Other `scripts/*.py` (excluding itself)

## generate_diff_bundle.py

Generates a git diff bundle for code review.

**Usage:**

```bash
uv run scripts/generate_diff_bundle.py
```

Useful for sharing changes with reviewers or AI assistants without exposing the full repository.

## convert_markdown.py

Converts Markdown files to interactive HTML.

**Usage:**

```bash
uv run scripts/convert_markdown.py <input.md> [output.html]
```

Utility for rendering documentation or changelogs as standalone HTML pages.

## Related Documentation

- [Testing](testing.md) — Fixture regeneration workflow
- [Adding Tabs and Flags](adding-tabs-and-flags.md) — When to capture new CLI help
