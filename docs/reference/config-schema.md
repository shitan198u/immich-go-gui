# Config Schema

Immich-Go GUI stores configuration in TOML files. API keys are stored in the OS keyring by default, not in these files.

## Directory Layout

```text
{config_dir}/
├── profiles.toml              # Profile index
├── locks/                     # Run lock files (runtime)
├── logs/                      # Rotating GUI log (immich-go-gui.log)
└── profiles/
    └── {profile_name}/
        ├── config.toml        # Configuration-page settings only
        └── secrets.toml       # Plaintext secrets (fallback only)
```

## Config Directory Paths

| Platform | Default path |
|----------|--------------|
| Linux | `~/.config/immich-go-gui/` |
| Linux (XDG) | `$XDG_CONFIG_HOME/immich-go-gui/` |
| macOS | `~/Library/Application Support/immich-go-gui/` |
| Windows | `%APPDATA%\immich-go-gui\` |

### Environment Override

| Variable | Effect |
|----------|--------|
| `IMMICH_GO_GUI_CONFIG` | Path to a specific `config.toml` file. Config directory is derived from the file's parent. |

## profiles.toml

Profile index file at `{config_dir}/profiles.toml`:

```toml
schema_version = 1
active_profile = "default"

[[profiles]]
name = "default"
created_at = "2026-01-01T00:00:00+00:00"
```

## config.toml Schema

Current schema version: **3**

```toml
schema_version = 3

[general]
theme = "system"                    # "system" | "light" | "dark"
advanced_mode = false
allow_untested_updates = false
preferred_terminal = "auto"

[server]
url = "https://immich.example.com"
skip_ssl = false
client_timeout_minutes = 60

[secrets]
provider = "keyring"                # "keyring" | "config"
```

Workflow tab field values are **session-only** and are not written to `config.toml`.

### Section Reference

| Section | Field | Type | Default | Description |
|---------|-------|------|---------|-------------|
| `general` | `theme` | string | `"system"` | UI theme |
| `general` | `advanced_mode` | bool | `false` | Show advanced flag rows |
| `general` | `allow_untested_updates` | bool | `false` | Allow immich-go versions outside tested range |
| `general` | `preferred_terminal` | string | `"auto"` | Terminal emulator preference |
| `server` | `url` | string | `""` | Immich server base URL |
| `server` | `skip_ssl` | bool | `false` | Skip TLS verification |
| `server` | `client_timeout_minutes` | int | `60` | Global HTTP timeout (minutes) for server-connected commands |
| `secrets` | `provider` | string | `"keyring"` | Secret storage backend |

### Schema v2 → v3 migration

On load, legacy `form_state` is discarded. If a v2 config had an **enabled** per-tab `client-timeout` advanced flag, that value is migrated into `server.client_timeout_minutes`.

## secrets.toml (Fallback)

Used when keyring is unavailable and `secrets.provider = "config"`:

```toml
api_key = "your-api-key"
admin_api_key = "optional-admin-key"
```

Prefer keyring storage. Plaintext secrets are a fallback only.

## Keyring Storage

Service name: `immich-go-gui`

User key format: `{profile_name}:{key}` (e.g. `default:api_key`)

Legacy key `immich_api_key` is migrated non-destructively to `default:api_key`.

## Binary Storage

Separate from config directory:

| Path | Contents |
|------|----------|
| `~/.immich-go-gui/bin/` | Downloaded immich-go binary |
| `~/.immich-go-gui/bin/metadata.json` | Version and download metadata |

## Qt Settings (Legacy)

Theme and legacy API key may exist in `QSettings("Shitan198u", "ImmichGoGUI")`. API keys are migrated to keyring on first read.

## Lock Files

Runtime lock files in `{config_dir}/locks/run_{id}.lock`:

```json
{
  "run_id": "abc12345",
  "gui_pid": 12345,
  "started_at": "2026-01-01T00:00:00+00:00",
  "tab_key": "upload-folder",
  "command_summary": "upload from-folder /photos",
  "binary_path": "/home/user/.immich-go-gui/bin/immich-go"
}
```

## Related

- [Profiles](../user-guide/profiles.md)
- [Environment Variables](environment-variables.md)
