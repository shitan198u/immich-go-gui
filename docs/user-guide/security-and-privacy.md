# Security & Privacy

Immich-Go GUI is designed so credentials never need to live in shell history, process argv listings, or committed config files.

## Threat Model (Practical)

| Risk | How the GUI mitigates it |
|------|--------------------------|
| API keys in config files | Stored in OS keyring by default |
| Keys visible in command preview | Masked as `***` |
| Keys in `ps` / Task Manager argv | Passed via environment variables, not `--api-key` flags |
| Keys written to `.bat` / `.sh` launch scripts | Launch scripts must not embed secrets; env is set in-process |
| Accidental TLS intercept on self-hosted setups | Optional skip-SSL with **visible warning banners** |
| Concurrent overlapping jobs | Process locks prevent double-runs |

This is **not** a formal audit. Treat it as an engineering design summary.

## Credential Lifecycle

```text
You paste API key
        │
        ▼
 OS keyring (preferred)
   or secrets.toml fallback
        │
        ▼
 GUI loads key into memory for the active profile
        │
        ▼
 build_environment() injects IMMICH_GO_* vars
        │
        ▼
 External terminal process inherits env
        │
        ▼
 immich-go authenticates to Immich
```

### Storage backends

1. **OS keyring (default)** — service name `immich-go-gui`, keys like `default:api_key`
2. **File fallback** — `profiles/{name}/secrets.toml` when keyring is missing or fails

Prefer fixing keyring on Linux (GNOME Keyring / KWallet) over leaving keys on disk.

## What Goes Through Environment Variables

Server URLs and API keys for server-required tabs are injected as `IMMICH_GO_*` variables. Full map: [Environment Variables](../reference/environment-variables.md).

**Never** put real keys into issues, screenshots of unmasked previews, or shared logs.

## What Still Appears on the Command Line

Non-secret flags and paths appear in argv (and therefore in the preview), for example:

- Source / destination paths
- `--server` for destination server (URL only — not the API key)
- Filters, dry-run, stacking options

Paths can still be sensitive (home directory layout, album names). Share previews carefully.

## SSL Verification

| Setting | When to use |
|---------|-------------|
| **Skip SSL verification off** (default) | Production, public HTTPS, valid certs |
| **Skip SSL verification on** | Local lab / self-signed only |

!!! danger "SSL Verification Warning"
    When **Skip SSL verification** is enabled:
    
    - The Config tab shows a prominent warning banner.
    - Command plans add a warning indicator before execution.
    - Traffic can be inspected by any device on the network path — only use this in trusted local lab environments.

## Admin API Key

The optional Admin API key is stored like the user key. It is required only for operations that pause Immich background jobs. Without it, the GUI disables job pausing rather than sending a request that would fail with `403`.

## Profiles Isolate Secrets

Each profile has its own keyring entries and config. Switching profiles reloads credentials so you do not accidentally upload home photos to a work server (or the reverse).

## What the App Does *Not* Do

- Does not phone home except for:
  - Immich server checks you initiate
  - GitHub Releases when downloading immich-go
- Does not upload your media itself — immich-go does, to **your** Immich server
- Does not store photo contents in the config directory
- Does not share telemetry

## Hardening Checklist

- [ ] Use HTTPS with a valid certificate on Immich
- [ ] Prefer keyring over `secrets.toml`
- [ ] Use separate profiles for separate servers
- [ ] Leave Skip SSL off outside trusted lab networks
- [ ] Keep immich-go on the tested version from the Config tab
- [ ] Download GUI binaries only from official [GitHub Releases](https://github.com/shitan198u/immich-go-gui/releases)
- [ ] Never paste live API keys into GitHub issues

## Developer Pointers

Security-sensitive code lives in:

| Area | Module |
|------|--------|
| Secret storage | `core/config_manager.py` (`SecretStore`) |
| Env injection | `core/command_builder.py` (`build_environment`) |
| Preview redaction | `mask_command_for_display()` |
| Terminal launch | `core/terminal_launcher.py` |
| Connection checks | `core/network.py` |

Architecture overview: [Architecture — Security Model](../developer-guide/architecture.md#security-model).
