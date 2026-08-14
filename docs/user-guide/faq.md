# FAQ

Short answers to questions users and contributors ask most often.

## General

### What is Immich-Go GUI?

A desktop GUI for [immich-go](https://github.com/simulot/immich-go). It builds, previews, and launches immich-go commands for upload, archive, and stack workflows against [Immich](https://immich.app/).

### Does the GUI replace immich-go?

No. The GUI is a front-end. All heavy lifting still happens in the immich-go CLI process that runs in an external terminal.

### Why open an external terminal instead of logging inside the app?

immich-go is interactive and long-running. A real terminal gives you live progress, copy-pasteable errors, and the ability to stop the job by closing the window. The GUI tracks the process and re-enables Run when it finishes.

### Which immich-go version should I use?

The GUI is tested against **0.32.0**. Use the Config tab binary manager to download the recommended version. See [immich-go Compatibility](../reference/immich-go-compatibility.md).

### Is my API key stored in plain text?

By default, no — keys go in the OS keyring (macOS Keychain, Windows Credential Manager, or Linux Secret Service). A `secrets.toml` fallback exists only when keyring is unavailable. See [Security & Privacy](security-and-privacy.md).

## Installation & Platforms

### Which package should I download?

| Platform | Recommended | Alternatives |
|----------|-------------|--------------|
| Windows | `…-Windows-x86_64-Setup.exe` | `…-Portable.zip` |
| macOS | `…-macOS-x86_64.dmg` | — |
| Linux desktop | `…-Linux-x86_64.AppImage` | `.deb`, `.rpm`, portable `.tar.gz` |

Full notes: [Platform Notes](platform-notes.md).

### Windows Defender flags the app. Is it malware?

Almost always a **false positive** on unsigned Nuitka builds. Prefer official GitHub Releases only, or run from source. Details: [Troubleshooting](troubleshooting.md#windows-antivirus-false-positives).

### Can I run it without installing Python?

Yes — use pre-built binaries. Python 3.13 is only required when running from source.

### Why is Python pinned to 3.13?

Release builds use Nuitka with a Python 3.13 pin for compatibility. From-source development uses the same range: `>=3.13.0, <3.14`.

## Configuration & Profiles

### Do I need an Admin API key?

Only if you want Immich background jobs paused during upload/stack. Without it, the GUI auto-disables pausing and warns you. See [Configuration](configuration.md#admin-api-key-and-job-pausing).

### Can I manage multiple Immich servers?

Yes — create a [profile](profiles.md) per server or environment. API keys are scoped per profile in the keyring.

### Where are my settings stored?

| OS | Config directory |
|----|------------------|
| Linux | `~/.config/immich-go-gui/` |
| macOS | `~/Library/Application Support/immich-go-gui/` |
| Windows | `%APPDATA%\immich-go-gui\` |

Override with `IMMICH_GO_GUI_CONFIG`. Schema: [Config Schema](../reference/config-schema.md).

### Why does the command preview show `***`?

Secrets are masked on purpose. Real keys are injected via environment variables at launch. This is expected.

## Workflows

### Which tab do I pick?

See [Choose Your Workflow](choose-your-workflow.md) for a decision tree and recipes.

### What is the difference between Upload and Archive?

- **Upload** puts media **into Immich**
- **Archive** writes media **to a local folder** (except Archive from Immich, which downloads *from* Immich to disk)

### Can I archive without an Immich server?

Yes for Folder, Google Photos, iCloud, and Picasa archive tabs (serverless). Archive from Immich needs source credentials.

### Should I dry-run first?

Yes for large libraries, migrations, and any stacking option that may discard non-cover frames.

### Does drag-and-drop work?

Yes on path fields. Drop onto the input, not empty chrome. Wayland compositors can be finicky — use the browse button if drops fail.

## Runtime Problems

### Run is disabled / "process already running"

Close the immich-go terminal window and wait a few seconds. On Windows, lock cleanup is heartbeat-based. Last resort: remove stale files under `{config_dir}/locks/` only when no job is running. See [Troubleshooting](troubleshooting.md#run-button-disabled-process-already-running).

### Upload fails with 403 when pausing jobs

Provide an **Admin API key**, or turn off job pausing. The GUI tries to auto-disable pausing when the admin key is missing; older versions did not. See [Troubleshooting](troubleshooting.md#403-forbidden-when-pausing-immich-jobs).

### Terminal never opens on Linux

Install a terminal emulator (`gnome-terminal`, `konsole`, `xfce4-terminal`, `xterm`, …) or set Preferred Terminal in Config.

## Backup Monitor

### How do I make the Monitor upload automatically?

Tick **Enable Backup Monitor** on the [Monitor](monitoring.md) tab, add at least one watched folder, and set credentials on the Config tab. Real-time watching, scheduled scans, and tray operation then run in the background.

### Dialog-free monitoring? How do runs happen?

Monitor runs launch immich-go as a **hidden background process** (no terminal window). Progress appears in the Monitor tab's progress card and Activity feed instead of a terminal.

### Why did nothing upload after I added a folder?

The master **Enable Backup Monitor** switch must be on, and only files that pass the folder filters are uploaded. Also confirm the [network policy](monitoring.md#network-policy) isn't pausing uploads and that no [activity pause](monitoring.md#activity-based-auto-pause) is active.

### Where are Monitor settings stored?

Per profile, in `monitor_config.json` (settings) and `monitor_state.json` (last-success timestamps, retries, run results), next to the profile's `config.toml`. See [Backup Monitor — Where Data Is Stored](monitoring.md#where-data-is-stored).

## Contributing & Development

### Where should pull requests target?

Always open PRs against **`master`**. See [CONTRIBUTING](../CONTRIBUTING.md).

### How do I run tests?

```bash
uv sync --dev
uv run pytest
```

On Linux CI-style headless:

```bash
QT_QPA_PLATFORM=offscreen xvfb-run uv run pytest
```

### How do I add support for a new immich-go flag?

Follow [Adding Tabs and Flags](../developer-guide/adding-tabs-and-flags.md). Capture CLI help fixtures after upgrading immich-go.

## Still stuck?

1. [Troubleshooting](troubleshooting.md)
2. [immich-go issues](https://github.com/simulot/immich-go/issues) for CLI errors in the terminal
3. [immich-go-gui issues](https://github.com/shitan198u/immich-go-gui/issues) — include OS, GUI version, immich-go version, **masked** command preview, and terminal output (never paste real API keys)
