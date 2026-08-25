# CLI Command Mapping

The GUI exposes 11 immich-go subcommands across Upload, Archive, and Stack sections. Each tab has a stable internal key used in code, config, and tests.

## Tab Key to Command Mapping

| Internal tab key | GUI section | immich-go command | Server required |
|------------------|-------------|-------------------|-----------------|
| `upload-folder` | Upload | `upload from-folder` | Yes |
| `upload-gp` | Upload | `upload from-google-photos` | Yes |
| `upload-icloud` | Upload | `upload from-icloud` | Yes |
| `upload-picasa` | Upload | `upload from-picasa` | Yes |
| `upload-immich` | Upload | `upload from-immich` | Yes (source + destination) |
| `archive-folder` | Archive | `archive from-folder` | No (serverless) |
| `archive-gp` | Archive | `archive from-google-photos` | No (serverless) |
| `archive-icloud` | Archive | `archive from-icloud` | No (serverless) |
| `archive-picasa` | Archive | `archive from-picasa` | No (serverless) |
| `archive-immich` | Archive | `archive from-immich` | Yes (source only) |
| `stack` | Stack | `stack` | Yes |

Defined in `core/cli_schema.py` as `TAB_COMMANDS`.

## Tab Sets

| Set | Tab keys |
|-----|----------|
| `UPLOAD_TABS` | `upload-folder`, `upload-gp`, `upload-icloud`, `upload-picasa`, `upload-immich` |
| `ARCHIVE_TABS` | `archive-folder`, `archive-gp`, `archive-icloud`, `archive-picasa`, `archive-immich` |
| `SERVER_REQUIRED_TABS` | All upload tabs + `archive-immich` + `stack` |
| `SERVERLESS_TABS` | `archive-folder`, `archive-gp`, `archive-icloud`, `archive-picasa` |

## Serverless Rule

Tabs in `SERVERLESS_TABS` must never emit these flags:

- `--server`
- `--api-key`
- `--client-timeout`

## Example Constructed Commands

Server URL may appear on argv as `--server=…`. **API keys never do** — they are injected via environment variables.

### Upload from Folder (simple)

```text
immich-go upload from-folder --server=https://immich.example.com /path/to/photos
```

Also set in the process environment:

- `IMMICH_GO_UPLOAD_SERVER`
- `IMMICH_GO_UPLOAD_API_KEY` (never shown in argv / preview)

### Archive from Folder (serverless)

```text
immich-go archive from-folder /source/path --write-to-folder /dest/path
```

No server or API env vars.

### Upload from Immich

```text
immich-go upload from-immich --server=https://dest.example.com --from-server=https://source.example.com
```

Source secrets via `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_*` env vars; destination via `IMMICH_GO_UPLOAD_*`.

### Stack

```text
immich-go stack --server=https://immich.example.com --manage-burst=Stack
```

API key via `IMMICH_GO_STACK_API_KEY`.

## Allowed Flags Per Tab

Each tab has an allowlist derived from `core/flags.toml` (exposed as `TAB_ALLOWED_FLAGS` via `flag_registry`). The command builder rejects flags not in the set for the active tab.

Flag counts against the **0.32.0** fixture set (exact; regenerate after CLI upgrades):

| Tab | Allowed flags |
|-----|---------------|
| `upload-folder` | 31 |
| `upload-gp` | 33 |
| `upload-icloud` | 31 |
| `upload-picasa` | 31 |
| `upload-immich` | 45 |
| `archive-folder` | 17 |
| `archive-gp` | 20 |
| `archive-icloud` | 18 |
| `archive-picasa` | 18 |
| `archive-immich` | 31 |
| `stack` | 16 |

See [Advanced Flags](../user-guide/advanced-flags.md) for user-facing flag descriptions.

## Config Tab

The `config` tab key is used internally for the settings page. It does not map to an immich-go subcommand.

## Source Reference

Authoritative definitions: `core/flags.toml` (loaded by `core/flag_registry.py`)

Historical re-exports in `core/cli_schema.py`:

- `TAB_KEYS` — all tab identifiers
- `TAB_COMMANDS` — command token mapping
- `TAB_ALLOWED_FLAGS` — per-tab flag allowlists (generated from `flags.toml`)
- `ENV_KEY_MAP` — secret environment variable mapping

## Related

- [Upload Workflows](../user-guide/upload-workflows.md)
- [Archive Workflows](../user-guide/archive-workflows.md)
- [Environment Variables](environment-variables.md)
