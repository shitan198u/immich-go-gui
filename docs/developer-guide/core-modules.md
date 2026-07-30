# Core Modules

The `core/` package contains all business logic. It is imported by `app.py` and fully testable without Qt.

Public API exports are defined in `core/__init__.py`.

## Module Reference

### `core/models.py`

Pure dataclasses and enums. No I/O.

| Type | Purpose |
|------|---------|
| `AppConfig` | User configuration model (server, theme, client timeout, etc.) |
| `CommandPlan` | Resolved argv, env, display_argv, warnings, errors, `emission_log` |
| `ValidationResult` | Form validation errors and warnings |
| `BinaryStatus` | immich-go binary health display data |
| `UpdateDecision` | Binary update allow/block decision |
| `VersionSupport` | Enum: tested, untested, unsupported, unknown |

### `core/flag_registry.py`

Loads `core/flags.toml` once at import time. **Single source of truth** for tabs, allowlists, advanced flag defs, and secret env routing.

| Export | Purpose |
|--------|---------|
| `REGISTRY` | Module singleton `Registry` |
| `FlagDef` / `TabDef` | Flag and tab dataclasses (`FlagDef.mode`: `simple` \| `advanced`) |
| `Registry.allowed_flags` | Per-tab CLI allowlist (frozenset) |
| `Registry.advanced_defs` / `advanced_keys` | Advanced-card defs and advanced-only keys |

### `core/cli_schema.py`

Thin delegation shim over `flag_registry`. Keeps historical export names for callers. Do not hand-maintain flag data here.

| Export | Purpose |
|--------|---------|
| `TAB_KEYS` | All 12 internal tab keys (including `config`) |
| `TAB_COMMANDS` | Tab key to immich-go command tokens |
| `UPLOAD_TABS`, `ARCHIVE_TABS` | Tab set constants |
| `SERVER_REQUIRED_TABS`, `SERVERLESS_TABS` | Server credential requirements |
| `ENV_KEY_MAP` | Tab key to env var names for secrets |
| `SECRET_FLAGS` | Flags masked in previews |
| `TAB_ALLOWED_FLAGS` | Per-tab flag allowlist (from `flags.toml`) |
| `COMPATIBILITY_MATRIX` | Version-specific flag change notes |
| `flag_allowed_for_tab()` | Runtime allowlist check |

### `core/advanced_flags.py`

Delegation shim: `ADVANCED_FLAGS` is built from `REGISTRY.advanced_defs()`. Contains validation and argv-formatting helpers — flag definitions live in `flags.toml`.

### `core/command_builder.py`

Builds `CommandPlan` from GUI form state.

| Function | Purpose |
|----------|---------|
| `build_plan_from_state()` | Main entry: state dict produces a CommandPlan |
| `_emit_simple_flag()` | Emit simple-mode flags when value ≠ default |
| `_emit_positional_owned_flags()` | Emit write-to, from-server, from-date-range, from-albums |
| `FlagEmitter` | Per-tab allowlist guard with `emission_log` instrumentation |
| `build_environment()` | Construct env dict with secrets |
| `validate_state()` | Validate form before run |
| `mask_command_for_display()` | Redact secrets for preview |
| `normalize_server_url()` | URL normalization |
| `validate_date_range()` | Date range validation |
| `collect_paths()` | Gather filesystem paths from state |

`CommandPlan.emission_log` records why each flag was emitted (`source`: `always`, `simple`, `advanced`, `button`, or `safety`). Shown in the run confirmation dialog.

### `core/logging_config.py`

Rotating file logger writing to `{config_dir}/logs/immich-go-gui.log`.

### `core/config_manager.py`

TOML configuration and secret management.

| Function / Class | Purpose |
|----------------|---------|
| `SecretStore` | Keyring read/write scoped by profile |
| `load_config()` / `save_config()` | TOML persistence |
| `load_secrets()` / `save_secrets()` | Plaintext secrets.toml fallback |
| `default_config_dir()` | OS-specific config directory |
| `default_config_path()` | Active profile config.toml path |

Config paths:

- Linux: `~/.config/immich-go-gui/`
- macOS: `~/Library/Application Support/immich-go-gui/`
- Windows: `%APPDATA%/immich-go-gui/`

### `core/profile_manager.py`

Multi-profile management.

| Function | Purpose |
|----------|---------|
| `list_profiles()` | List all profiles with active flag |
| `create_profile()` | Create (optionally copy from existing) |
| `duplicate_profile()` | Clone profile |
| `rename_profile()` / `delete_profile()` | Profile lifecycle |
| `active_profile_name()` / `set_active_profile_name()` | Active profile tracking |
| `migrate_single_config_to_default()` | Legacy config migration |

### `core/binary_manager.py`

immich-go binary lifecycle.

| Constant / Class | Purpose |
|------------------|---------|
| `RECOMMENDED_IMMICH_GO_VERSION` | Currently `0.32.0` |
| `TESTED_IMMICH_GO_VERSIONS` | Frozenset of tested versions |
| `BinaryManager` | Download, verify, update binary |
| `get_version_support()` | Classify version compatibility |
| `BINARY_BASE_DIR` | `~/.immich-go-gui/bin/` (versioned subdirs: `bin/{version}/immich-go`) |

Downloads from GitHub Releases with SHA256 verification.

### `core/network.py`

Immich server connectivity.

| Function | Purpose |
|----------|---------|
| `test_immich_connection()` | GET `{server}/api/server/about` |
| `check_preflight_server_connection()` | Pre-run validation wrapper |

Uses `x-api-key` header; respects SSL skip setting.

### `core/process_tracker.py`

Run lock files to prevent concurrent immich-go executions.

| Function | Purpose |
|----------|---------|
| `create_lock()` | Create JSON lock in `{config_dir}/locks/` |
| `release_lock()` | Remove lock on completion |
| `is_lock_active()` | Check if lock PID is alive |
| `cleanup_stale_locks()` | Remove orphaned locks |
| `scan_locks()` | List active locks |

### `core/terminal_launcher.py`

Cross-platform external terminal launch.

| Function | Purpose |
|----------|---------|
| `launch_external_terminal()` | Open terminal with immich-go command |

Platform-specific: gnome-terminal/konsole/xterm on Linux, Terminal.app on macOS, cmd.exe batch on Windows with heartbeat cleanup.

### `core/cli_help.py` / `core/cli_contract.py`

CLI help parsing and compatibility checking against versioned fixtures in `core/fixtures/cli_help/`.

| Function | Purpose |
|----------|---------|
| `parse_help_flags()` | Parse `--help` output into flag names |
| `load_help_fixture()` | Load captured help for a tab |
| `check_fixtures()` | Verify fixtures match allowlists |
| `check_binary_help()` | Compare live binary help to fixtures |

### `core/validation.py`

Shared validation helpers for dates, paths, and destination folders.

## Dependency Rules

```text
app.py  →  core/*  →  (stdlib, keyring, requests, packaging, psutil, tomli-w)
core/*  ↛  PySide6, Qt
tests/  →  app.py, core/*
```

## Further Reading

- [Adding Tabs and Flags](adding-tabs-and-flags.md)
- [Config Schema](../reference/config-schema.md)
- [CLI Command Mapping](../reference/cli-command-mapping.md)
