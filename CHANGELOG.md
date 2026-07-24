# Changelog

All notable changes to the Immich-Go GUI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-24

### 🚀 Features & UI Completeness (11/11 CLI Sub-Commands)
- **5 New GUI Sub-Tabs**: Added full GUI coverage for all 11 `immich-go` CLI sub-commands:
  - `upload-icloud` (`upload from-icloud`): Support for iCloud photo library imports with `--memories` flag and HEIC/JPEG pair handling.
  - `upload-picasa` (`upload from-picasa`): Support for Picasa album exports and `--album-picasa` metadata detection.
  - `archive-gp` (`archive from-google-photos`): Serverless archive tab for Google Takeout photo libraries with takeout filters.
  - `archive-icloud` (`archive from-icloud`): Serverless archive tab for iCloud photo libraries with `--memories` support.
  - `archive-picasa` (`archive from-picasa`): Serverless archive tab for Picasa photo libraries with `--album-picasa` support.
- **Serverless Tab Isolation**: Explicitly classified `archive-folder`, `archive-gp`, `archive-icloud`, and `archive-picasa` as `SERVERLESS_TABS`, guaranteeing they never emit `--server`, `--api-key`, or `--client-timeout` flags.
- **Pre-Flight Server Connectivity Check**: Added fast pre-flight connection check (`/api/server/about`) before launching server-required commands, warning users if the Immich server is unreachable (`connection refused` / `timeout`).
- **Help Menu Links**: Added direct links to Immich-Go CLI (`simulot/immich-go`) and Immich-Go GUI (`shitan198u/immich-go-gui`) GitHub repositories alongside an interactive About dialog.

### 🛡️ Security & Secret Management
- **Environment Variable Secret Delivery**: Migrated sensitive API keys (`IMMICH_GO_UPLOAD_API_KEY`, `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY`, etc.) away from CLI command arguments (`argv`) to process environment variables.
- **Zero Plaintext Disk Files**: Completely eliminated disk shell files (`env.sh`) in favor of direct process launching via Python `subprocess.Popen`.
- **OS Keyring Integration**: Supported OS Keyring (Keychain, KWallet, Credential Manager) for secure API key storage.
- **Redacted Previews & Logs**: Sanitized command confirmation dialogs and log files to prevent credential leakage.
- **SSL Bypass Warning Banners**: Displayed clear inline safety warnings when `--skip-verify-ssl` is activated.

### 🔧 Release & Runtime Safety
- **Binary Manager**: Centralized release version fetching, binary downloads, SHA256 checksum verification, and graceful cancellation cleanup.
- **Safe Working Directory Isolation**: POSIX launchers execute inside isolated temporary directories with safe `$HOME` fallback directory changes, avoiding working directory deletion crashes.
- **Windows Terminal Heartbeat**: Hardened Windows external terminal execution using temporary `.bat` launcher scripts and background heartbeat loops (`.heartbeat`) for clean lock lifecycle tracking.
- **Validation Engine**: Standardized date range validation (`YYYY-MM-DD,YYYY-MM-DD` and single dates) with full calendar semantic checks.

### 📦 Multi-Platform Packaging & CI
- **Automated Standalone Builds**: Compiled standalone distributions for Windows (Installer & Portable), macOS (DMG), and Linux (AppImage, DEB, RPM, Portable Tarball).
- **Version & Architecture Tagging**: Standardized output package names to include version and architecture (e.g., `Immich-Go-GUI-1.1.0-Windows-x86_64-Setup.exe`, `Immich-Go-GUI-1.1.0-Linux-x86_64.AppImage`).

### 🧪 Test Infrastructure
- **Cross-Platform Test Suite**: Added `_norm_argv` path normalization helper ensuring 100% test suite pass rate (149/149 tests) across Linux, macOS, and Windows.
- **Golden State Fixtures**: Added JSON fixture files and golden test cases for all 11 sub-commands.

---

## [1.0.1] - 2026-02-18

### Fixed
- Fixed PySide6 theme resolution and fusion style application.
- Improved terminal launcher error messages on Linux and macOS.

## [1.0.0] - 2025-02-18

### Added
- Initial release of Immich-Go GUI with PySide6 interface.
