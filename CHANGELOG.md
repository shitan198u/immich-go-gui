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

### 🐛 Bug Fixes & Discrepancy Resolution
- **Sidebar Server Status Indicator**: Fixed UI status card discrepancy so failed connection tests display `🔴 Server: Connection Failed` rather than falsely displaying green `Server: Configured`.
- **Automatic Test State Reset**: Reset connection test status automatically when Server URL or API Key input text is edited.
- **Simple-Mode Control Emission**: Fixed simple-mode date range and album inputs for `upload-immich` and `archive-immich` to prevent options from being silently omitted.
- **Google Takeout Checkboxes**: Restored `include-partner`, `sync-albums`, and `include-archived` default-true checkboxes in simple mode cards, emitting `--flag=false` when unchecked.
- **Path Collection Unification**: Standardized glob expansion with `recursive=True` across single and multi-path collection handlers.

### 🛡️ Security & Secret Management
- **Environment Variable Secret Delivery**: Migrated sensitive API keys (`IMMICH_GO_UPLOAD_API_KEY`, `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY`, etc.) away from CLI command arguments (`argv`) to process environment variables.
- **OS Keyring Integration**: Supported OS Keyring (Keychain, KWallet, Credential Manager) for secure API key storage.
- **Redacted Confirmation & Logs**: Sanitized command confirmation dialogs and log files to prevent credential leakage.

### 🔧 Release & Runtime Safety
- **Binary Manager**: Centralized release version fetching, binary downloads, SHA256 checksum verification, and graceful cancellation cleanup.
- **Windows Terminal Heartbeat**: Hardened Windows external terminal execution using temporary `.bat` launcher scripts and background heartbeat loops (`.heartbeat`) for clean lock lifecycle tracking.
- **Validation Engine**: Standardized date range validation (`YYYY-MM-DD,YYYY-MM-DD` and single dates) with full calendar semantic checks.

### 🧪 Test Infrastructure & Codebase Reorganization
- **Reorganized Test Suite**: Moved test suite to `tests/test_app.py` with dynamic `Path(__file__)` resolution.
- **Contract Lint Guards**: Enforced duplicate test name checks (`test_no_duplicate_test_names`) and flag subset validation (`test_advanced_flags_subset_of_tab_allowed_flags`).
- **Golden State Fixtures**: Added JSON fixture files and golden test cases for all 11 sub-commands.
- **Pytest Suite**: 149 test cases passing cleanly across Linux, macOS, and Windows.

---

## [1.0.1] - 2026-02-18

### Fixed
- Fixed PySide6 theme resolution and fusion style application.
- Improved terminal launcher error messages on Linux and macOS.

## [1.0.0] - 2025-02-18

### Added
- Initial release of Immich-Go GUI with PySide6 interface.
