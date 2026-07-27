# Adding Tabs and Flags

This guide covers extending the GUI when immich-go adds new subcommands or flags.

## Adding a New Tab

Adding a tab requires changes across schema, UI, tests, and fixtures. Follow this checklist:

### 1. Define the tab key in `core/cli_schema.py`

```python
TAB_KEYS.append("upload-newsource")  # Add to TAB_KEYS list

TAB_COMMANDS["upload-newsource"] = ["upload", "from-newsource"]

UPLOAD_TABS.add("upload-newsource")  # Or ARCHIVE_TABS

# If server credentials required:
SERVER_REQUIRED_TABS.add("upload-newsource")
# If serverless archive:
SERVERLESS_TABS.add("upload-newsource")
```

### 2. Add allowed flags

Capture CLI help for the new subcommand (see [Scripts](scripts.md)), then add the flag set:

```python
TAB_ALLOWED_FLAGS["upload-newsource"] = frozenset({
    "server", "dry-run", "log-level",
    # ... all flags from immich-go --help
})
```

### 3. Add environment variable mapping (if secrets involved)

```python
ENV_KEY_MAP["upload-newsource"] = {
    "server": "IMMICH_GO_UPLOAD_SERVER",
    "api_key": "IMMICH_GO_UPLOAD_API_KEY",
}
```

### 4. Define advanced flags in `core/advanced_flags.py`

Add entries to `ADVANCED_FLAGS` for the new tab with correct `FlagDef` kinds and scopes.

### 5. Build the UI tab in `app.py`

- Add sidebar entry and stacked page
- Create form widgets for simple-mode fields
- Wire save/load to `form_state` under the tab key
- Connect Run button to `run_command()` with the tab key

### 6. Add tests and fixtures

In `tests/test_app.py`:

- Add golden JSON state fixture in `tests/fixtures/command_states/`
- Add test asserting `build_plan_from_state()` produces expected argv
- Use `_norm_argv()` for cross-platform path comparisons

### 7. Capture CLI help fixture

```bash
uv run scripts/capture_cli_help.py
```

Run `check_fixtures()` tests to verify allowlist parity.

## Adding a Flag to an Existing Tab

### 1. Verify the flag exists in immich-go

Run the binary's `--help` for the relevant subcommand.

### 2. Add to `TAB_ALLOWED_FLAGS`

```python
TAB_ALLOWED_FLAGS["upload-folder"] = frozenset({
    # existing flags...
    "new-flag-name",
})
```

### 3. Add to `ADVANCED_FLAGS` in `core/advanced_flags.py`

```python
FlagDef(
    name="new-flag-name",
    kind="bool",  # or str, int, enum, etc.
    scope="subcommand",
    default=False,
)
```

Associate the flag with the correct tab in the `ADVANCED_FLAGS` registry structure.

### 4. Add UI widget (if simple mode)

For high-frequency flags, add a control in simple mode section of the tab builder in `app.py`. Advanced-only flags are auto-generated from `ADVANCED_FLAGS`.

### 5. Update tests

- Extend golden fixture JSON if the flag affects command output
- Add validation test if the flag has constraints

## Serverless Tab Rule

For tabs in `SERVERLESS_TABS`, the command builder must never emit:

- `--server`
- `--api-key`
- `--client-timeout`

Add a test asserting these flags are absent from the built plan.

## Secret Flag Handling

If a new flag carries a secret value:

1. Mark `secret=True` in `FlagDef`
2. Add to `SECRET_FLAGS` if it appears in argv (prefer env delivery instead)
3. Map to an env var in `ENV_KEY_MAP`
4. Verify `mask_command_for_display()` redacts it

**Never** pass secrets via argv. Use `build_environment()` to inject env vars.

## Version Compatibility

When immich-go releases a new version:

1. Capture new CLI help fixtures
2. Update `TAB_ALLOWED_FLAGS` for any flag changes
3. Update `COMPATIBILITY_MATRIX` and `VERSION_NOTES` in `cli_schema.py` / `binary_manager.py`
4. Update `TESTED_IMMICH_GO_VERSIONS` after full test pass
5. Document changes in `CHANGELOG.md`

See [immich-go Compatibility](../reference/immich-go-compatibility.md).

## Validation Checklist

Before opening a PR:

- [ ] Tab appears in sidebar and saves form state
- [ ] Command preview shows correct masked output
- [ ] Run launches immich-go with expected argv/env
- [ ] Serverless tabs omit server flags
- [ ] Tests pass: `uv run pytest`
- [ ] CLI fixtures updated if immich-go version changed
