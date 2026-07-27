# Platform Notes

Install and runtime quirks by operating system. For a general first-run walkthrough, see [Getting Started](getting-started.md).

## Artifact Names

Release assets follow:

```text
Immich-Go-GUI-{VERSION}-{OS}-x86_64.{ext}
```

| Platform | Files |
|----------|-------|
| Windows | `…-Windows-x86_64-Setup.exe`, `…-Windows-x86_64-Portable.zip` |
| macOS | `…-macOS-x86_64.dmg` |
| Linux | `…-Linux-x86_64.AppImage`, `…-Linux-x86_64.deb`, `…-Linux-x86_64.rpm`, `…-Linux-x86_64-Portable.tar.gz` |

Download only from the official [Releases page](https://github.com/shitan198u/immich-go-gui/releases/latest).

---

## Windows

### Installer vs portable

| Package | Best for |
|---------|----------|
| **Setup.exe** | Normal desktop install with Start Menu entry |
| **Portable.zip** | USB / no-admin / side-by-side versions |

Extract the portable zip and run `Immich-Go-GUI.exe` inside.

### SmartScreen / antivirus

Unsigned Nuitka builds often trigger SmartScreen or Defender heuristics (`Wacatac`, etc.). This is a known false-positive class for many Python-to-native apps.

**Safer workflow:**

1. Confirm the release tag and publisher on GitHub
2. Unblock the file if Windows marked it (Properties > Unblock)
3. Or run from source with `uv` if your environment blocks unsigned binaries

See [Troubleshooting](troubleshooting.md#windows-antivirus-false-positives).

### Terminals and locks

- Jobs launch in a `cmd.exe` window
- Closing the window should release the GUI run lock quickly
- If Run stays disabled, wait a few seconds, then restart the GUI; only delete `locks/` files when nothing is running

### Paths

Config: `%APPDATA%\immich-go-gui\`  
immich-go binary: `%USERPROFILE%\.immich-go-gui\bin\`

---

## macOS

### Opening the DMG

1. Open the `.dmg`
2. Drag the app to Applications (or run in place)
3. On first launch, if Gatekeeper blocks it: **System Settings > Privacy & Security > Open Anyway**, or right-click and select **Open**

### Terminal

Uses Terminal.app (or another terminal available on PATH). Keep Terminal permissions intact if macOS prompts for Automation access.

### Paths

Config: `~/Library/Application Support/immich-go-gui/`  
immich-go binary: `~/.immich-go-gui/bin/`

### Architecture note

Current release builds target **x86_64**. On Apple Silicon, the app runs under Rosetta if available. If you prefer native arm64, run from source until arm64 release artifacts are published.

---

## Linux

### AppImage (recommended for most desktops)

```bash
chmod +x Immich-Go-GUI-*-Linux-x86_64.AppImage
./Immich-Go-GUI-*-Linux-x86_64.AppImage
```

If your system mounts AppImages via FUSE and launch fails, install FUSE support for your distro, or extract with:

```bash
./Immich-Go-GUI-*-Linux-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

### DEB / RPM

```bash
# Debian / Ubuntu
sudo apt install ./Immich-Go-GUI-*-Linux-x86_64.deb

# Fedora / RHEL-like
sudo rpm -i Immich-Go-GUI-*-Linux-x86_64.rpm
```

A desktop entry is included via packaging metadata (`immich-go-gui.desktop`).

### Portable tarball

```bash
tar -xzf Immich-Go-GUI-*-Linux-x86_64-Portable.tar.gz
cd <extracted-dir>
./Immich-Go-GUI
```

### Terminal emulator required

The GUI launches an external terminal. Install at least one of:

- `gnome-terminal`
- `konsole`
- `xfce4-terminal`
- `xterm`
- `alacritty` / `kitty` (if detected by your preferred-terminal setting)

Set **Preferred terminal** on the Config tab if Auto fails.

### Keyring on headless / minimal desktops

API keys need a Secret Service provider for keyring mode:

- GNOME Keyring
- KWallet
- Other `libsecret` backends

If none is available, the GUI may fall back to `secrets.toml`. See [Security & Privacy](security-and-privacy.md).

### Wayland drag-and-drop

Some compositors restrict DnD into Qt apps. Use the file picker buttons if drops do not populate path fields.

### Paths

Config: `~/.config/immich-go-gui/` (or `$XDG_CONFIG_HOME/immich-go-gui/`)  
immich-go binary: `~/.immich-go-gui/bin/`

---

## Running from Source (All Platforms)

```bash
git clone https://github.com/shitan198u/immich-go-gui.git
cd immich-go-gui
uv sync --dev
uv run app.py
```

Requires **Python 3.13** and [uv](https://docs.astral.sh/uv/).

## Environment Overrides

| Variable | Effect |
|----------|--------|
| `IMMICH_GO_GUI_CONFIG` | Absolute path to a specific `config.toml` |

Useful for portable setups or parallel profiles outside the default OS path.

## Related

- [Getting Started](getting-started.md)
- [Configuration](configuration.md)
- [Troubleshooting](troubleshooting.md)
- [FAQ](faq.md)
