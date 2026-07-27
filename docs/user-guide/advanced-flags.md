# Advanced Flags

Immich-Go GUI exposes immich-go CLI flags through form controls. The visibility of these controls depends on **Advanced mode**, toggled on the Config tab.

## Simple vs Advanced Mode

| Mode | Behavior |
|------|----------|
| **Simple** | Shows high-frequency inputs only: paths, date filters, dry run, and common options |
| **Advanced** | Dynamically generates additional flag rows from the allowed flag registry for the active tab |

Advanced mode is saved per profile in `config.toml` under `general.advanced_mode`.

## How Flags Are Built

When you click Run, the GUI:

1. Collects form state for the active tab
2. Validates paths, dates, and required fields
3. Builds an argv list with only flags allowed for that tab (`TAB_ALLOWED_FLAGS` in the codebase)
4. Passes secrets through environment variables, not argv
5. Masks secrets in the command preview

If a flag is not in the allowlist for a tab, it cannot be emitted — this prevents invalid cross-tab flag combinations.

## Secret Flags

These flags are never shown with real values in the preview:

- `--api-key`
- `--admin-api-key`
- `--from-api-key`
- `--from-admin-api-key`

They appear as `***` in the command preview.

## Global Flags (Most Server Tabs)

Available on upload tabs, Stack, and server-connected archive tabs:

| Flag | Type | Description |
|------|------|-------------|
| `server` | URL | Immich server (via env var on most tabs) |
| `skip-verify-ssl` | bool | Disable TLS verification |
| `client-timeout` | duration | HTTP timeout |
| `dry-run` | bool | Simulate without changes |
| `concurrent-tasks` | int | Parallelism (0 = auto) |
| `overwrite` | bool | Overwrite existing assets |
| `pause-immich-jobs` | bool | Pause Immich background jobs (**needs Admin API key**; auto-disabled otherwise) |
| `on-errors` | enum | `stop`, `continue`, or custom tolerance |
| `session-tag` / `tag` | string | Add tags to processed assets |
| `device-uuid` | string | Device identifier |
| `log-level` | enum | Logging verbosity |
| `api-trace` | bool | Trace API calls |
| `time-zone` | string | Timezone for date operations |

## Serverless Archive Flags

Serverless archive tabs use a reduced flag set centered on local I/O:

| Flag | Description |
|------|-------------|
| `write-to-folder` | Destination directory (required) |
| `dry-run` | Preview mode |
| `log-level` | Logging |
| `concurrent-tasks` | Parallelism |
| `on-errors` | Error handling |

No `server`, `api-key`, or `client-timeout` flags are available on these tabs.

## Per-Tab Flag Highlights

### Upload / Archive Folder

`recursive`, `date-from-name`, `ignore-sidecar-files`, `include-extensions`, `exclude-extensions`, `include-type`, `ban-file`, `date-range`, `folder-as-album`, `folder-as-tags`, `album-path-joiner`, `into-album`

### Upload / Archive Google Photos

`from-album-name`, `include-archived`, `include-partner`, `include-trashed`, `include-unmatched`, `include-untitled-albums`, `partner-shared-album`, `people-tag`, `sync-albums`, `takeout-tag`

### Upload / Archive iCloud

`memories`, plus folder-style album and filter flags

### Upload / Archive Picasa

`album-picasa`, plus folder-style flags

### Upload / Archive from Immich

`from-server`, `from-api-key`, `from-albums`, `from-tags`, `from-people`, `from-date-range`, `from-favorite`, `from-archived`, `from-trash`, `from-city`, `from-state`, `from-country`, `from-make`, `from-model`, and related `from-*` filters

### Stack

`manage-burst`, `manage-raw-jpeg`, `manage-heic-jpeg`, `manage-epson-fastfoto`, `date-range`, `device-uuid`

## On Errors Behavior

| Value | Description |
|-------|-------------|
| `stop` | Halt on first error |
| `continue` | Keep processing despite errors |
| `custom` | Continue until error count exceeds tolerance (Config tab sets tolerance) |

## Compatibility Notes

The allowed flag set is tied to the tested immich-go version (currently **0.32.0**). New immich-go releases may add, rename, or remove flags. The GUI shows version compatibility warnings when your binary differs from the tested version.

See [immich-go Compatibility](../reference/immich-go-compatibility.md) and [CLI Command Mapping](../reference/cli-command-mapping.md) for the authoritative allowlists.

## Further Reading

- [Configuration](configuration.md) — Toggle advanced mode
- [Developer: Adding Tabs and Flags](../developer-guide/adding-tabs-and-flags.md) — For contributors extending flags
