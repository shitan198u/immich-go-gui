# Immich-Go GUI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![immich-go](https://img.shields.io/badge/immich--go-0.32.0%20tested-blueviolet.svg)](https://github.com/simulot/immich-go)
[![Docs](https://img.shields.io/badge/docs-user%20%26%20dev%20guides-0A66C2.svg)](docs/README.md)

A cross-platform desktop front-end for [immich-go](https://github.com/simulot/immich-go) — configure workflows with forms, preview the exact command, and launch it in a real terminal against your [Immich](https://immich.app/) server.

![Screenshot 1](screenshots/1.png)
![Screenshot 2](screenshots/2.png)
![Screenshot 3](screenshots/3.png)

## Why this exists

immich-go is powerful but flag-heavy. Immich-Go GUI gives you:

- **11 workflow tabs** covering every current immich-go upload / archive / stack subcommand
- **Safe defaults** — API keys in the OS keyring, secrets via environment variables, masked previews
- **Profiles** for home vs work (or staging vs production) Immich servers
- **Pre-flight checks** so you discover connection problems before a long job starts
- **Automatic immich-go downloads** with SHA256 verification

New here? Start with **[docs/](docs/README.md)** — especially [Choose Your Workflow](docs/user-guide/choose-your-workflow.md) and [Getting Started](docs/user-guide/getting-started.md).

## Features

| Area | Highlights |
|------|------------|
| **Workflows** | Upload & archive from folder, Google Photos, iCloud, Picasa, Immich; plus Stack |
| **Config** | Multi-profile settings, themes (system/light/dark), preferred terminal |
| **Safety** | Keyring secrets, env delivery, SSL warnings, process locks, dry-run |
| **CLI parity** | Simple mode for common fields; advanced mode for full flag surface |
| **Ops** | Binary manager, connection test, command preview, drag-and-drop paths |
| **Platforms** | Windows installer/portable, macOS DMG, Linux AppImage/DEB/RPM/tarball |

## Architecture Overview

```mermaid
flowchart TB
    classDef user fill:#6366f1,stroke:#4338ca,color:#ffffff,stroke-width:2px,rx:10px;
    classDef gui fill:#0ea5e9,stroke:#0284c7,color:#ffffff,stroke-width:2px,rx:8px;
    classDef core fill:#8b5cf6,stroke:#6d28d9,color:#ffffff,stroke-width:2px,rx:8px;
    classDef process fill:#f59e0b,stroke:#d97706,color:#ffffff,stroke-width:2px,rx:8px;
    classDef external fill:#ec4899,stroke:#be185d,color:#ffffff,stroke-width:2px,rx:8px;
    classDef storage fill:#10b981,stroke:#047857,color:#ffffff,stroke-width:2px,rx:8px;

    User([User]):::user
    GUI[Immich-Go GUI]:::gui
    Config[Configuration Manager]:::core
    Validator[Input Validator]:::core
    Builder[Command Builder]:::core
    Downloader[Binary Manager]:::core
    Process[Process Runner]:::process
    Binary[immich-go Binary]:::external
    Server[(Immich Server)]:::external
    Log[Live Log Output]:::storage
    Settings[(Saved Configuration)]:::storage

    User --> GUI
    GUI --> Config
    GUI --> Validator
    GUI --> Builder
    GUI --> Downloader
    Builder --> Process
    Downloader --> Binary
    Process --> Binary
    Binary --> Server
    Process --> Log
    Config --> Settings
```

## Download & Installation

### Pre-built binaries (recommended)

Grab the latest build from the [Releases page](https://github.com/shitan198u/immich-go-gui/releases/latest):

| Platform | Recommended package |
|----------|---------------------|
| Windows | `Immich-Go-GUI-{VERSION}-Windows-x86_64-Setup.exe` (or `…-Portable.zip`) |
| macOS | `Immich-Go-GUI-{VERSION}-macOS-x86_64.dmg` |
| Linux | `Immich-Go-GUI-{VERSION}-Linux-x86_64.AppImage` (also `.deb` / `.rpm` / `.tar.gz`) |

Platform-specific tips (Gatekeeper, AppImage `chmod`, Defender false positives): **[Platform Notes](docs/user-guide/platform-notes.md)**.

> **Windows antivirus note:** Defender or VirusTotal may flag the unsigned Nuitka build (e.g. `Trojan:Win32/Wacatac.B!ml`). This is a common **false positive**. Prefer official GitHub Releases, or run from source below.

### Run from source

**Prerequisites:** Python **3.13** (`>=3.13.0, <3.14`) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/shitan198u/immich-go-gui.git
cd immich-go-gui
uv sync --dev
uv run app.py
```

On first use, the Config tab can download a compatible immich-go binary for you.

## Documentation

Full guides live under **[docs/](docs/README.md)**:

| Audience | Start here |
|----------|------------|
| **Users** | [Getting Started](docs/user-guide/getting-started.md) · [Choose Your Workflow](docs/user-guide/choose-your-workflow.md) · [FAQ](docs/user-guide/faq.md) |
| **Operators** | [Configuration](docs/user-guide/configuration.md) · [Security](docs/user-guide/security-and-privacy.md) · [Troubleshooting](docs/user-guide/troubleshooting.md) |
| **Developers** | [Architecture](docs/developer-guide/architecture.md) · [Testing](docs/developer-guide/testing.md) · [CONTRIBUTING](CONTRIBUTING.md) |
| **Reference** | [CLI mapping](docs/reference/cli-command-mapping.md) · [Config schema](docs/reference/config-schema.md) · [Env vars](docs/reference/environment-variables.md) |

Version history: [CHANGELOG.md](CHANGELOG.md).

## Immich-Go Integration

This GUI targets immich-go **0.32.0** (tested). CLI behavior, edge cases, and flag semantics are defined upstream:

https://github.com/simulot/immich-go/

Compatibility policy: [docs/reference/immich-go-compatibility.md](docs/reference/immich-go-compatibility.md).

## Contributing

Contributions are welcome. Please:

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Skim the [Developer Guide](docs/developer-guide/architecture.md)
3. Open PRs against **`staging`** (not `master`)
4. Prefer [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, …) so Release Please can version cleanly

```bash
uv sync --dev
uv run pytest
```

## Support

If Immich-Go GUI saves you time, you can support development:

### GitHub Sponsors

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-%E2%9D%A4-red?style=for-the-badge&logo=github)](https://github.com/sponsors/shitan198u)

### Buy Me a Coffee

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-%F0%9F%8D%BA-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/shivashitan)

## License


