# Environment Variables

Immich-Go GUI passes server URLs and API keys to immich-go through environment variables rather than command-line arguments. This prevents secrets from appearing in process listings and shell history.

## GUI Configuration Override

| Variable | Purpose |
|----------|---------|
| `IMMICH_GO_GUI_CONFIG` | Absolute path to a specific `config.toml` file, overriding the default config location |

## immich-go Secret Variables

Mapped in `core/cli_schema.py` (`ENV_KEY_MAP`). Each tab uses a distinct prefix to avoid collisions when multiple credential sets are needed.

### Upload Tabs (folder, gp, icloud, picasa)

| State key | Environment variable |
|-----------|---------------------|
| `server` | `IMMICH_GO_UPLOAD_SERVER` |
| `api_key` | `IMMICH_GO_UPLOAD_API_KEY` |
| `admin_api_key` | `IMMICH_GO_UPLOAD_ADMIN_API_KEY` |

Applies to: `upload-folder`, `upload-gp`, `upload-icloud`, `upload-picasa`

### Upload from Immich

Uses upload destination vars plus source ("from") vars:

| State key | Environment variable |
|-----------|---------------------|
| `server` | `IMMICH_GO_UPLOAD_SERVER` |
| `api_key` | `IMMICH_GO_UPLOAD_API_KEY` |
| `admin_api_key` | `IMMICH_GO_UPLOAD_ADMIN_API_KEY` |
| `from_server` | `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER` |
| `from_api_key` | `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY` |
| `from_admin_api_key` | `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY` |

### Archive from Immich

Source-only credentials (no destination server env vars):

| State key | Environment variable |
|-----------|---------------------|
| `from_server` | `IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER` |
| `from_api_key` | `IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_API_KEY` |
| `from_admin_api_key` | `IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_ADMIN_API_KEY` |

### Stack

| State key | Environment variable |
|-----------|---------------------|
| `server` | `IMMICH_GO_STACK_SERVER` |
| `api_key` | `IMMICH_GO_STACK_API_KEY` |
| `admin_api_key` | `IMMICH_GO_STACK_ADMIN_API_KEY` |

### Serverless Archive Tabs

No environment variables for server credentials. These tabs do not use `ENV_KEY_MAP` entries:

- `archive-folder`
- `archive-gp`
- `archive-icloud`
- `archive-picasa`

## Secret Delivery Rules

1. Secrets are injected into the subprocess environment dict at launch time
2. Secrets are **never** written to disk shell scripts (`.bat`, `.sh`)
3. Command preview masks all secret values as `***`
4. Secret CLI flags (`--api-key`, `--from-api-key`, etc.) are excluded from argv when env delivery is used

## Masked Preview Flags

These flag names are always redacted in the command preview (`SECRET_FLAGS`):

- `--api-key`
- `--admin-api-key`
- `--from-api-key`
- `--from-admin-api-key`

## Related

- [Configuration](../user-guide/configuration.md)
- [Architecture](../developer-guide/architecture.md) — Security model
- [CLI Command Mapping](cli-command-mapping.md)
