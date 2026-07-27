# Stack

The **Stack** tab runs immich-go's `stack` command against your Immich server. Stacking groups related assets (burst photos, RAW+JPEG pairs, HEIC+JPEG, Epson FastFoto sequences) into a single stack on the server.

**Command:** `immich-go stack`

## Requirements

Stack requires a configured Immich server and API key on the Config tab. The GUI performs a pre-flight connection check before launch.

| Credential | Purpose |
|------------|---------|
| Server URL | Target Immich instance |
| API key | Authentication for stack operations |
| Admin API key | Optional; required only if you want Immich background jobs paused during stacking |

Secrets are passed via environment variables (`IMMICH_GO_STACK_SERVER`, `IMMICH_GO_STACK_API_KEY`, etc.). See [Environment Variables](../reference/environment-variables.md).

Without an admin key, the GUI auto-disables job pausing and warns instead of failing with `403`. See [Configuration](configuration.md#admin-api-key-and-job-pausing).

## Common Fields

| Field | Description |
|-------|-------------|
| **Dry run** | Preview stacking actions without modifying the server |
| **Date range** | Limit stacking to assets within a date window |
| **Device UUID** | Filter or tag by device identifier |

## Stack Management Options (Advanced)

These flags control how immich-go detects and groups assets:

| Flag | Description |
|------|-------------|
| `manage-burst` | Stack burst/sequence photos |
| `manage-raw-jpeg` | Pair RAW files with JPEG previews |
| `manage-heic-jpeg` | Pair HEIC with JPEG counterparts |
| `manage-epson-fastfoto` | Handle Epson FastFoto scan sequences |

Enable the options matching your library content. See [Advanced Flags](advanced-flags.md) for the full list.

## Other Advanced Options

- `concurrent-tasks` — Parallel processing count
- `pause-immich-jobs` — Pause background Immich jobs during stacking
- `on-errors` — Error handling behavior
- `log-level`, `api-trace` — Logging verbosity
- `time-zone` — Timezone for date-based filtering
- `skip-verify-ssl` — Bypass TLS verification (shows warning)

## Running Stack

1. Configure server and API key on the Config tab.
2. Open the Stack tab.
3. Set date range or management options as needed.
4. Review the command preview.
5. Click **Run**.

Stack operations can take considerable time on large libraries. Monitor progress in the terminal window.

## Further Reading

- [Configuration](configuration.md) — Server and API key setup
- [Troubleshooting](troubleshooting.md) — Connection and lock issues
- [immich-go stack documentation](https://github.com/simulot/immich-go/)
