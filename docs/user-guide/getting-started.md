# Getting Started

## What Is Immich-Go GUI?

Immich-Go GUI is a graphical front-end for [immich-go](https://github.com/simulot/immich-go), a command-line tool for bulk media operations with [Immich](https://github.com/immich-app/immich). The GUI lets you:

- Configure server credentials and paths through forms instead of memorizing CLI flags
- Preview the constructed command before running it
- Launch immich-go in an external terminal window
- Save and reload settings across sessions using profiles

The application does not run immich-go inside the GUI window. It builds the command, opens your system terminal, and tracks the process until it finishes.

## Installation Options

### Pre-built Binaries (Recommended)

1. Go to the [Releases page](https://github.com/shitan198u/immich-go-gui/releases/latest).
2. Download the package for your operating system:
   - **Windows**: `Immich-Go-GUI-{VERSION}-Windows-x86_64-Setup.exe` or `…-Portable.zip`
   - **macOS**: `Immich-Go-GUI-{VERSION}-macOS-x86_64.dmg`
   - **Linux**: AppImage, `.deb`, `.rpm`, or portable `.tar.gz`
3. Run the executable. No Python installation is required.

OS-specific tips (Gatekeeper, AppImage permissions, Defender): **[Platform Notes](platform-notes.md)**.

!!! warning "Windows Antivirus Note"
    Windows Defender or VirusTotal may flag the Nuitka-compiled executable as suspicious (`Trojan:Win32/Wacatac.B!ml`). This is a common false positive for unsigned standalone apps. See [Troubleshooting](troubleshooting.md#windows-antivirus-false-positives) for details.

### Running from Source

Use this method if you prefer to run from source or need to develop the application.

**Prerequisites:**

- Python **3.13** (`>=3.13.0, <3.14`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager

**Steps:**

```bash
git clone https://github.com/shitan198u/immich-go-gui.git
cd immich-go-gui
uv sync --dev
uv run app.py
```

On first launch, the GUI can automatically download a compatible `immich-go` binary for your platform. See [Configuration](configuration.md#immich-go-binary-management).

## Five-Minute First Run

1. **Open the Config tab** (sidebar, gear icon).
2. **Enter your Immich server URL** (e.g. `https://photos.example.com`).
3. **Enter your API key** — stored in your OS keychain, not in plain config files.
4. Click **Test Connection** — fix URL/key/SSL issues before a long job.
5. (Optional) Enter an **Admin API key** if you want Immich background jobs paused during uploads. Without it, the GUI auto-disables job pausing. See [Configuration](configuration.md#admin-api-key-and-job-pausing).
6. Confirm an immich-go binary is installed (Config tab can download **0.32.0**).
7. **Pick a workflow** — if unsure, open [Choose Your Workflow](choose-your-workflow.md).
8. **Fill required fields** (source path, write folder, etc.). Drag-and-drop works on path inputs.
9. **Review the command preview** (secrets appear as `***`).
10. **Click Run** — immich-go opens in a new terminal window.

While a command is running, the Run button is disabled and the GUI shows a status indicator. Close the terminal window when the job completes before starting another run.

!!! tip "Pro Tip"
    Use **Dry run** the first time you try a new source or advanced stacking option.

## User Interface Overview

The main window has three areas:

### Sidebar Navigation

- **Config** — Server settings, profiles, theme, binary management
- **Upload** — Five sub-tabs for uploading to Immich from different sources
- **Archive** — Five sub-tabs for exporting media to local folders
- **Stack** — Deduplicate/stack assets on the Immich server
- **Monitor** — Background monitoring of local folders (real-time watching, scheduled scans, tray) — see [Backup Monitor](monitoring.md)

### Stacked Pages

Each sidebar section opens a page with its own sub-tabs and form fields. Simple mode shows the most common options; advanced mode exposes additional immich-go flags.

### Command Preview

Every workflow tab shows a read-only preview of the constructed CLI command. API keys and other secrets are masked in the preview.

## Themes

The Config tab lets you choose **System**, **Light**, or **Dark** theme. The choice is saved per profile and applied on next launch.

## Next Steps

- [Platform Notes](platform-notes.md) — OS-specific install and paths
- [Choose Your Workflow](choose-your-workflow.md) — Decision tree and recipes
- [Configuration](configuration.md) — Server, API keys, and binary setup
- [Backup Monitor](monitoring.md) — Automated background uploads
- [Security & Privacy](security-and-privacy.md) — How credentials are handled
- [Profiles](profiles.md) — Multiple Immich servers or environments
- [FAQ](faq.md) — Short answers
- [Troubleshooting](troubleshooting.md) — Common issues
