# Configuration

The **Config** tab holds global settings shared across workflow tabs: Immich server credentials, theme, terminal preference, and immich-go binary management.

## Immich Server

| Field | Description |
|-------|-------------|
| **Server URL** | Base URL of your Immich instance (e.g. `https://immich.local`). Used by upload tabs, Stack, and Archive from Immich. |
| **Skip SSL verification** | Bypass TLS certificate validation. Shows an inline warning when enabled. Use only for local/self-signed setups. |
| **API Key** | Your Immich user API key. Stored in the OS keychain by default — never written to plain TOML. |
| **Admin API Key** | Optional elevated key. Required only if you want Immich background jobs paused during upload/stack. Also stored in the keychain. |

### Connection Testing

Use **Test Connection** on the Config tab to call `{server}/api/server/about` with your API key. The same endpoint is used as a **pre-flight check** before server-required runs; a failure blocks launch and shows an error.

Server-required tabs: all Upload tabs, Archive from Immich, and Stack. See [CLI Command Mapping](../reference/cli-command-mapping.md).

### Admin API Key and Job Pausing

Immich can pause background jobs while immich-go runs (`pause-immich-jobs`, enabled by default for upload/stack). That API call needs an **admin** key.

| Admin key set? | Pause jobs preference | What the GUI does |
|----------------|----------------------|-------------------|
| Yes | On (default) | Jobs can be paused during the run |
| No | On (default) | **Auto-disables** pausing and adds a warning — avoids a hard `403 Forbidden` abort |
| Any | Off | Emits pause disabled; no admin key needed |

**Recommendation:** create an admin API key in Immich if you upload large libraries and want Immich to stop thumbnail/metadata jobs from competing for I/O. Otherwise leave the admin field empty and accept that pausing stays off.

## Configuration Lifecycle

```mermaid
stateDiagram-v2

    [*] --> Default

    Default --> Modified

    Modified --> Saved

    Saved --> Loaded

    Loaded --> Modified

    Saved --> Deleted

    Deleted --> Default
```

## Secret Storage

API keys are handled securely:

1. **OS Keychain (default)** — macOS Keychain, Windows Credential Manager, or Linux Secret Service via the `keyring` library.
2. **Plaintext fallback** — If keyring is unavailable, secrets may be stored in `secrets.toml` inside the profile directory (see [Config Schema](../reference/config-schema.md)).

Secrets are passed to immich-go through **environment variables**, not command-line arguments. The command preview masks all secret values.

## Advanced Settings (Config Tab)

These defaults apply globally and can be overridden per tab in advanced mode:

| Setting | Default | Description |
|---------|---------|-------------|
| Client timeout | 20 minutes | HTTP timeout for Immich API calls |
| Concurrent tasks | 0 (auto) | Parallel upload/task count |
| Device UUID | empty | Device identifier sent to Immich |
| On errors | stop | Behavior when errors occur (`stop`, `continue`, or custom tolerance) |
| Pause Immich jobs | enabled | Pause background Immich jobs during upload |

## immich-go Binary Management

```mermaid
flowchart TD
    classDef startEnd fill:#6366f1,stroke:#4338ca,color:#fff,stroke-width:2px
    classDef check fill:#f59e0b,stroke:#b45309,color:#fff,stroke-width:2px
    classDef download fill:#0ea5e9,stroke:#0369a1,color:#fff,stroke-width:2px
    classDef run fill:#8b5cf6,stroke:#6d28d9,color:#fff,stroke-width:2px
    classDef done fill:#10b981,stroke:#047857,color:#fff,stroke-width:2px

    Start([Launch requested]):::startEnd
    Check{"Binary installed?"}:::check
    Download[Download from<br/>GitHub Releases]:::download
    Verify[Verify SHA256 checksum]:::download
    Launch[Prepare argv + env secrets]:::run
    Execute[Open terminal + run immich-go]:::run
    Done([Process running]):::done

    Start --> Check
    Check -->|Yes| Launch
    Check -->|No| Download
    Download --> Verify
    Verify -->|checksum OK| Launch
    Launch --> Execute
    Execute --> Done
```

The GUI bundles no immich-go binary inside the app. On first use it can download one from [GitHub Releases](https://github.com/simulot/immich-go/releases).

| Location | Path |
|----------|------|
| Binary directory | `~/.immich-go-gui/bin/` |
| Metadata file | `~/.immich-go-gui/bin/metadata.json` |

The Config tab shows:

- Installed version and support status (tested, untested, unsupported)
- Option to download or update the binary
- Compatibility warnings for versions outside the tested range

See [immich-go Compatibility](../reference/immich-go-compatibility.md) for version details.

## Theme and Terminal

| Setting | Options | Description |
|---------|---------|-------------|
| Theme | System / Light / Dark | UI appearance |
| Preferred terminal | Auto or specific emulator | Which terminal opens when you click Run (platform-dependent) |

## Saving Configuration

Configuration is saved automatically when you change settings or switch tabs. Each profile has its own `config.toml`. Form field values for workflow tabs are stored in the `form_state` section of that file.

### Config File Locations

| Platform | Default directory |
|----------|-------------------|
| Linux | `~/.config/immich-go-gui/` |
| macOS | `~/Library/Application Support/immich-go-gui/` |
| Windows | `%APPDATA%\immich-go-gui\` |

Override the config file path with the `IMMICH_GO_GUI_CONFIG` environment variable. See [Config Schema](../reference/config-schema.md).

## Simple vs Advanced Mode

Toggle **Advanced mode** in the Config tab to show additional flag rows on workflow tabs. Simple mode keeps the UI focused on high-frequency options; advanced mode exposes the full immich-go flag surface allowed for each tab. See [Advanced Flags](advanced-flags.md).

## Related

- [Security & Privacy](security-and-privacy.md) — Keyring, env delivery, SSL
- [Profiles](profiles.md) — Multi-server setups
- [Platform Notes](platform-notes.md) — Config paths per OS
- [Choose Your Workflow](choose-your-workflow.md)
