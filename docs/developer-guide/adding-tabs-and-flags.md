# Adding Tabs and Flags

This guide covers extending the GUI when immich-go adds new subcommands or flags.

**Source of truth:** `core/flags.toml`, loaded by `core/flag_registry.py`.
`core/cli_schema.py` and `core/advanced_flags.py` are thin delegation shims — do not hand-maintain flag lists there.

## Adding a New Tab

### 1. Add tab metadata and flags in `core/flags.toml`

```toml
[tabs.upload-newsource]
command = ["upload", "from-newsource"]
section = "upload"            # "upload" | "archive" | "stack"
server_required = true
serverless = false

[secrets.upload-newsource]
server = "IMMICH_GO_UPLOAD_SERVER"
api_key = "IMMICH_GO_UPLOAD_API_KEY"
admin_api_key = "IMMICH_GO_UPLOAD_ADMIN_API_KEY"

[[flags.upload-newsource]]
key = "path"
flag = ""
label = "Source path"
kind = "path"
mode = "simple"

[[flags.upload-newsource]]
key = "recursive"
flag = "recursive"
label = "Scan recursively"
kind = "bool"
default = true
mode = "advanced"
```

Rules:

- `mode = "simple"` → always-visible widget; emitted when value ≠ TOML default
- `mode = "advanced"` → advanced card row; emitted only when the enable checkbox is checked

**Opt-in principle:** a flag reaches the CLI if and only if the user explicitly asked for it — simple widget ≠ default, or advanced row enabled. immich-go applies its own defaults for anything not passed.

For every simple-mode bool, the TOML `default` must match the CLI default and the widget default.

### 2. Build the UI tab in `app.py`

- Add sidebar entry / stacked page / sub-tab as needed
- Create simple-mode widgets for `mode = "simple"` flags
- Advanced rows are generated from the registry automatically
- Wire widgets into `inputs` / `adv_rows`; `collect_form_state()` gathers runtime state for `build_plan_from_state()` (not persisted to `config.toml`)

### 3. Add tests and fixtures

- Golden JSON state fixture in `tests/fixtures/command_states/`
- Assert `build_plan_from_state()` argv with `_norm_argv()`
- Capture CLI help: `uv run scripts/capture_cli_help.py`
- Run registry / fixture compatibility tests

## Adding a Flag to an Existing Tab

1. Confirm the flag exists in immich-go `--help` for that subcommand
2. Add a `[[flags.<tab>]]` entry in `core/flags.toml` with correct `kind` and `mode`
3. If the flag needs a simple-mode control, add the widget in `app.py`
4. Update / add tests and refresh help fixtures if the CLI changed

## Related

- [Core Modules](core-modules.md)
- [CLI Command Mapping](../reference/cli-command-mapping.md)
- [Testing](testing.md)
