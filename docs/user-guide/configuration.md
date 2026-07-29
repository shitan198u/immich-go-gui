# Configuration

The **Config** tab holds global settings shared across workflow tabs: Immich server credentials, theme, terminal preference, and immich-go binary management.

## Immich Server

| Field | Description |
|-------|-------------|
| **Server URL** | Base URL of your Immich instance (e.g. `https://immich.local`). Used by upload tabs, Stack, and Archive from Immich. |
| **Skip SSL verification** | Bypass TLS certificate validation. Shows an inline warning when enabled. Use only for local/self-signed setups. |
| **API Key** | Your Immich user API key. Stored in the OS keychain by default — never written to plain TOML. |
| **Client Timeout** | How long each HTTP call to Immich may run (minutes). Low values may fail long uploads or archives. Applied globally as `--client-timeout` (and `--from-client-timeout` on Immich-to-Immich tabs). |
| **Admin API Key** | Optional elevated key. Required only if you want Immich background jobs paused during upload/stack. Also stored in the keyring. |

### Connection Testing and Saving Server Details

Use **Test Connection** to call `{server}/api/server/about` with your API key. The same endpoint is used as a **pre-flight check** before server-required runs; a failure blocks launch and shows an error.

Use **Save Server Details** to persist **only** the server URL and API key (to `config.toml` and keyring). Other Config settings (theme, timeout, skip SSL, etc.) are saved separately via **File → Save Configuration**.

Server-required tabs: all Upload tabs, Archive from Immich, and Stack. See [CLI Command Mapping](../reference/cli-command-mapping.md).

### Admin API Key and Job Pausing

Immich can pause background jobs while immich-go runs (`pause-immich-jobs`, enabled by default upstream for upload/stack). That API call needs an **admin** key.

**Where to control pausing:** `pause-immich-jobs` is a **per-tab Advanced Flags row** on upload and Stack tabs — not a Config-tab toggle. In simple mode, the flag is not emitted unless you enable it on the tab's Advanced card.

| Admin key set? | Advanced row enabled? | What the GUI does |
|----------------|----------------------|-------------------|
| Yes | Yes (user checked) | Emits `--pause-immich-jobs` (or the value you set) |
| No | Yes | **Auto-disables** pausing via safety pass: emits `--pause-immich-jobs=false` and adds a warning — avoids a hard `403 Forbidden` abort |
| Any | No (default) | Flag not emitted; immich-go applies its own default |

**Recommendation:** create an admin API key in Immich if you upload large libraries and want Immich to stop thumbnail/metadata jobs from competing for I/O. Otherwise leave the admin field empty; the safety pass prevents 403 errors when pausing would otherwise be requested.

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

## Application Updates (GUI)

The **Application** card checks whether a newer **Immich-Go GUI** release is published on GitHub (separate from the immich-go CLI binary below).

| Element | Description |
|---------|-------------|
| **Current Version** | Installed GUI version (or `dev` when running from source) |
| **Status** | Green when up to date, amber when an update is available, muted for development builds |
| **Check for Updates** | Fetches the latest release; always shows a status message and dialog |
| **Releases link** | Opens [GitHub Releases](https://github.com/shitan198u/immich-go-gui/releases) in your browser |

The GUI does **not** download or install itself. When an update is available, use **Open Download Page** in the dialog (or the releases link) and install the new package manually (installer, AppImage, DMG, etc.).

The same check is available from **File → Check for Application Updates…**.

## immich-go Binary Management

```mermaid
flowchart TD
    classDef startEnd fill:#6366f1,stroke:#4338ca,color:#fff,stroke-width:2px
    classDef check fill:#f59e0b,stroke:#b45309,color:#fff,stroke-width:2px
    classDef download fill:#0ea5e9,stroke:#0369a1,color:#fff,stroke-width:2px
    classDef run fill:#8b5cf6,stroke:#6d28d9,color:#fff,stroke-width:2px
    classDef done fill:#10b981,stroke:#047857,color:#fff,stroke-width:2px

    Start([Download / update requested<br/>from Config tab]):::startEnd
    Check{"Binary installed?"}:::check
    Download[Download archive from<br/>GitHub Releases]:::download
    Checksums{"checksums.txt<br/>present?"}:::check
    Verify[Verify archive SHA256]:::download
    Extract[Extract to version subdir]:::download
    PostCheck[Run immich-go version<br/>post-extract check]:::download
    Launch[Prepare argv + env secrets]:::run
    Execute[Open terminal + run immich-go]:::run
    Done([Process running]):::done

    Start --> Check
    Check -->|No or update| Download
    Check -->|Yes, run only| Launch
    Download --> Checksums
    Checksums -->|missing| Abort([Install aborted<br/>fail-closed]):::startEnd
    Checksums -->|found| Verify
    Verify -->|fail| Abort
    Verify -->|OK| Extract
    Extract --> PostCheck
    PostCheck -->|fail| Abort
    PostCheck -->|OK| Launch
    Launch --> Execute
    Execute --> Done
```

The GUI bundles no immich-go binary inside the app. Downloads are triggered from the **Config tab** (or when you confirm a download prompt before run) — not on every application launch.

| Location | Path |
|----------|------|
| Binary base directory | `~/.immich-go-gui/bin/` |
| Versioned binary | `~/.immich-go-gui/bin/{version}/immich-go` (or `immich-go.exe` on Windows) |
| Metadata file | `~/.immich-go-gui/bin/metadata.json` |

`metadata.json` records `selected_version`, per-version paths, and download metadata. Legacy installs may still have a flat `~/.immich-go-gui/bin/immich-go`; the resolver checks version subdirectories first.

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

Configuration is **not** auto-saved. Use explicit save actions:

| Action | What it saves |
|--------|----------------|
| **Save Server Details** (Config tab) | Server URL + API key only |
| **File → Save Configuration** | Theme, client timeout, skip SSL, secret provider, admin API key, advanced card settings, and advanced mode |
| Close / profile switch prompt | Offers to save pending changes before continuing |

Each profile has its own `config.toml` under `profiles/{name}/`. Workflow tab fields (upload paths, archive destinations, per-tab advanced rows) are **session-only** — they reset when you restart the app or switch profiles without saving Config settings.

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
