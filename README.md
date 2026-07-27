# Immich-Go GUI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![immich-go](https://img.shields.io/badge/immich--go-0.32.0%20tested-blueviolet.svg)](https://github.com/simulot/immich-go)
[![Docs Website](https://img.shields.io/badge/docs-website-e9533f.svg)](https://shitan198u.github.io/immich-go-gui/)

A cross-platform desktop front-end for [immich-go](https://github.com/simulot/immich-go) — configure workflows with forms, preview the exact command, and launch it in a real terminal against your [Immich](https://immich.app/) server.

📖 **Live Documentation Website**: [https://shitan198u.github.io/immich-go-gui/](https://shitan198u.github.io/immich-go-gui/)

<table>
  <tr>
    <td align="center" width="33%">
      <a href="screenshots/1.png">
        <img src="screenshots/1.png" alt="Main window" width="100%"/>
      </a>
      <sub><b>Main Window</b></sub>
    </td>
    <td align="center" width="33%">
      <a href="screenshots/2.png">
        <img src="screenshots/2.png" alt="Workflow tab" width="100%"/>
      </a>
      <sub><b>Workflow Tab</b></sub>
    </td>
    <td align="center" width="33%">
      <a href="screenshots/3.png">
        <img src="screenshots/3.png" alt="Command preview" width="100%"/>
      </a>
      <sub><b>Command Preview</b></sub>
    </td>
  </tr>
</table>


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
flowchart LR
    classDef userStyle fill:#6366f1,stroke:#4338ca,color:#fff,stroke-width:2px
    classDef guiStyle fill:#0ea5e9,stroke:#0369a1,color:#fff,stroke-width:2px
    classDef cliStyle fill:#8b5cf6,stroke:#6d28d9,color:#fff,stroke-width:2px
    classDef serverStyle fill:#10b981,stroke:#047857,color:#fff,stroke-width:2px

    User([👤 You]):::userStyle
    GUI[🖥️ Immich-Go GUI]:::guiStyle
    CLI[⚙️ immich-go CLI]:::cliStyle
    Server[(☁️ Immich Server)]:::serverStyle

    User -->|configure & launch| GUI
    GUI -->|argv + env secrets| CLI
    CLI -->|upload / archive / stack| Server
```

## Download & Installation

### 📥 Download — Releases Page (recommended)

**[⬇️ Download the latest release →](https://github.com/shitan198u/immich-go-gui/releases/latest)**

Pre-built desktop apps are available for all platforms — no Python or dependencies required:

| Platform | Package |
|----------|---------|
| 🪟 Windows | `Immich-Go-GUI-{VERSION}-Windows-x86_64-Setup.exe` (or Portable `.zip`) |
| 🍎 macOS | `Immich-Go-GUI-{VERSION}-macOS-x86_64.dmg` |
| 🐧 Linux | `Immich-Go-GUI-{VERSION}-Linux-x86_64.AppImage` · `.deb` · `.rpm` · `.tar.gz` |

> **Windows antivirus note:** Defender or VirusTotal may flag the unsigned Nuitka build (`Trojan:Win32/Wacatac.B!ml`). This is a common **false positive**. Always download from [official GitHub Releases](https://github.com/shitan198u/immich-go-gui/releases/latest).

See **[Platform Notes](docs/user-guide/platform-notes.md)** for Gatekeeper, AppImage `chmod +x`, and other OS-specific tips.

### 💻 Run from source

For contributors or users who prefer source:

**Prerequisites:** Python **3.13** and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/shitan198u/immich-go-gui.git
cd immich-go-gui
uv sync --dev
uv run app.py
```

On first use, the Config tab can download a compatible immich-go binary for you.

## Documentation

🌐 **Live Documentation Website**: [https://shitan198u.github.io/immich-go-gui/](https://shitan198u.github.io/immich-go-gui/)

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

This project is licensed under the [MIT License](LICENSE.txt).
