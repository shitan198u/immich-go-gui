# Troubleshooting

Common issues and how to resolve them. For short Q&A, see the [FAQ](faq.md). For install quirks, see [Platform Notes](platform-notes.md).

## Quick triage

| Symptom | Jump to |
|---------|---------|
| Defender / VirusTotal flag | [Windows antivirus](#windows-antivirus-false-positives) |
| Run button grayed out | [Process already running](#run-button-disabled--process-already-running) |
| No terminal window | [Terminal does not open](#terminal-does-not-open) |
| Cannot reach Immich | [Server connection failed](#server-connection-failed) |
| `403` during upload | [403 when pausing jobs](#403-forbidden-when-pausing-immich-jobs) |
| Version warning on Config | [immich-go version warnings](#immich-go-version-warnings) |
| API key empty after restart | [API key not saved](#api-key-not-saved) |
| TLS errors | [SSL / certificate errors](#ssl--certificate-errors) |

## Windows Antivirus False Positives

**Symptom:** Windows Defender or VirusTotal flags the executable (e.g. `Trojan:Win32/Wacatac.B!ml`).

**Cause:** The app is compiled with Nuitka into a standalone executable without a paid code-signing certificate. This triggers heuristic detections.

**Solutions:**

- Run from source: `uv sync --dev && uv run app.py`
- Add an exclusion in Windows Defender for the install directory
- Verify the download came from the official [GitHub Releases](https://github.com/shitan198u/immich-go-gui/releases) page

## Run Button Disabled / Process Already Running

**Symptom:** The Run button stays grayed out with a message about an active process.

**Cause:** The GUI tracks running immich-go jobs via lock files in `{config_dir}/locks/`. A lock remains while the terminal job is active or if a previous run did not clean up.

**Solutions:**

1. Close the terminal window running immich-go and wait a few seconds for lock cleanup.
2. On Windows, the launcher uses a heartbeat process to clean locks when the terminal is killed abruptly — wait briefly and retry.
3. Restart the GUI application.
4. As a last resort, delete stale lock files in your config directory's `locks/` folder (only when no immich-go process is running).

## Terminal Does Not Open

**Symptom:** Clicking Run does nothing or shows a terminal launch error.

**Solutions:**

- **Linux:** Ensure a terminal emulator is installed (`gnome-terminal`, `konsole`, `xterm`, etc.). Set preferred terminal in Config if Auto detection fails.
- **macOS:** Terminal.app or iTerm should be available on PATH.
- **Windows:** cmd.exe is used by default; verify it is accessible.
- Check file permissions on the immich-go binary in `~/.immich-go-gui/bin/`.

## Server Connection Failed

**Symptom:** Pre-flight check fails or immich-go cannot reach Immich.

**Checklist:**

- Verify server URL includes scheme (`https://` or `http://`) and has no trailing junk path
- Confirm API key is valid and has required permissions
- Click **Test Connection** on the Config tab
- Test the server in a browser: `{server}/api/server/about`
- For self-signed certificates, enable **Skip SSL verification** (shows a warning banner)
- Check firewall/proxy settings between your machine and the Immich server
- Confirm you are on the correct [profile](profiles.md) (home vs work server)

## 403 Forbidden When Pausing Immich Jobs

**Symptom:** Terminal shows `403 Forbidden` related to pausing jobs, or uploads abort immediately after start.

**Cause:** `pause-immich-jobs` requires an **Admin API key**. A normal user key cannot pause Immich background jobs.

**Solutions:**

1. Add an **Admin API Key** on the Config tab, or
2. Disable job pausing (advanced / config advanced settings), or
3. Upgrade to GUI **≥ 1.1.2**, which auto-disables pausing when no admin key is present and warns instead of failing hard

See [Configuration — Admin API Key and Job Pausing](configuration.md#admin-api-key-and-job-pausing).

## immich-go Version Warnings

**Symptom:** Config tab shows untested or unsupported version warnings.

**Details:**

- **Tested:** v0.32.0 (recommended)
- **Unsupported old:** Versions below 0.32.0
- **Untested new:** Versions above 0.32.0

**Solutions:**

- Download the recommended version from the Config tab binary manager
- Enable "allow untested updates" in advanced settings if you intentionally use a newer binary
- See [immich-go Compatibility](../reference/immich-go-compatibility.md)

## API Key Not Saved

**Symptom:** API key field is empty after restart.

**Cause:** Keyring backend unavailable on Linux (no Secret Service), or permission denied.

**Solutions:**

- Install and unlock a Secret Service provider (GNOME Keyring, KWallet)
- Check `secrets.toml` in your profile directory for plaintext fallback storage
- Re-enter the API key on the Config tab

## SSL / Certificate Errors

**Symptom:** Connection fails with TLS or certificate errors.

**Solutions:**

- Use a valid certificate on your Immich server (Let's Encrypt recommended)
- For local development only: enable **Skip SSL verification** — an inline warning is displayed
- Do not disable SSL verification on production servers

## Command Preview Shows `***` for Secrets

**This is expected behavior.** API keys are masked in the preview for security. The real values are passed to immich-go via environment variables at runtime.

## Config Not Found or Wrong Profile

**Symptom:** Settings reset or wrong server appears.

**Check:**

- Active profile on the Config tab
- Whether `IMMICH_GO_GUI_CONFIG` environment variable overrides the default path
- Config directory for your OS (see [Config Schema](../reference/config-schema.md))

## Drag and Drop Not Working

**Symptom:** Dropped files do not populate path fields.

**Solutions:**

- Drop folders onto path input fields (not empty areas)
- On Linux Wayland, some compositors restrict drag-and-drop — try selecting via the file picker button

## Getting Help

1. Skim the [FAQ](faq.md) and [Choose Your Workflow](choose-your-workflow.md)
2. Check [immich-go issues](https://github.com/simulot/immich-go/issues) for CLI-specific errors shown in the terminal
3. Open a [GUI issue](https://github.com/shitan198u/immich-go-gui/issues) with:
   - OS and GUI version
   - immich-go version (from Config tab)
   - Active profile name (if relevant)
   - Masked command preview (never paste real API keys)
   - Terminal error output
