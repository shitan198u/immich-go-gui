# Changelog

All notable changes to the Immich-Go GUI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0](https://github.com/shitan198u/immich-go-gui/compare/v1.0.1...v1.1.0) (2026-07-24)


### Features

* add documentation review template and styled HTML viewer for Immich-Go GUI ([e449248](https://github.com/shitan198u/immich-go-gui/commit/e449248cbb1c83fe8a79c372ed9101ff4f573ae0))
* **advanced:** add ADVANCED_FLAGS entries for 5 new tabs ([729cb5a](https://github.com/shitan198u/immich-go-gui/commit/729cb5a0c76e1490c2efb43bc9789910d11a1739))
* **builder:** add command builder and validation rules for 5 new tabs ([6b411bc](https://github.com/shitan198u/immich-go-gui/commit/6b411bcd4beb1e4870de597ede42d995099c592f))
* **builder:** integrate advanced state into command builder and surface plan errors ([5e60606](https://github.com/shitan198u/immich-go-gui/commit/5e60606c04bbaa555d736a44d2e626848b2fcded))
* **ci:** embed version in all release artifact filenames (e.g. Immich-Go-GUI-1.1.0-Linux.AppImage) ([4d053a3](https://github.com/shitan198u/immich-go-gui/commit/4d053a3feb649753ea0a40681697791620b1414a))
* **ci:** standardize release artifact filenames with version and x86_64 architecture ([73a08d7](https://github.com/shitan198u/immich-go-gui/commit/73a08d7222255509bda536759f23344f93ccf41b))
* **cli:** capture help fixtures for 5 new sub-commands (0.32.0) ([9d3a3c5](https://github.com/shitan198u/immich-go-gui/commit/9d3a3c5d19a66a25bf16b24de8946c248dc29597))
* **core:** add schema-driven advanced_flags registry and helpers ([0bc3ebe](https://github.com/shitan198u/immich-go-gui/commit/0bc3ebef7f6225495b5a743a870f2e4b5cc470b0))
* **network:** add pre-flight server connectivity check before command execution ([3534f76](https://github.com/shitan198u/immich-go-gui/commit/3534f76fa29e7fd467a908d40f96de8b02905707))
* **persistence:** persist opt-in advanced flag state and add reset action ([420bda4](https://github.com/shitan198u/immich-go-gui/commit/420bda4fa47dd906469c406db38652d18f1f5f69))
* **phase2:** Step 1 — Command generation completeness & golden tests ([9385c19](https://github.com/shitan198u/immich-go-gui/commit/9385c1913e3bb37fbbcf923d7539961fd09c3fb9))
* **phase2:** Step 2 — UI completeness & Simple/Advanced persistence ([7d67abf](https://github.com/shitan198u/immich-go-gui/commit/7d67abfdc081e60a5d1b879cc3c1ab50e49fc1aa))
* **phase2:** Step 3 — Validation and persistence safety ([cbd7720](https://github.com/shitan198u/immich-go-gui/commit/cbd77205893fda0de50f54caa63bb9a572d3e035))
* **phase2:** Step 4 — Binary update safety ([8b01f62](https://github.com/shitan198u/immich-go-gui/commit/8b01f621a238290b2d38d72d0b74e5b3956ceb91))
* **phase2:** Step 5 — Compatibility, terminal hardening & CI readiness ([5b1b85d](https://github.com/shitan198u/immich-go-gui/commit/5b1b85d30388d8066426cd9807f651a846986def))
* **schema:** add tab keys, commands, serverless status, and allowed flags for 5 new sub-commands ([f153d83](https://github.com/shitan198u/immich-go-gui/commit/f153d833b856f3862adfca7f15f358dd4a5392d5))
* structured command preview dialog with copy command button (Milestone 6) ([12aa449](https://github.com/shitan198u/immich-go-gui/commit/12aa449d2d414ef0efd3c9256fe72f69dad8cf6e))
* suppress advanced options and configuration in Simple mode ([54e5b33](https://github.com/shitan198u/immich-go-gui/commit/54e5b3379b96b80915c6ef58fa3f02e7eda8dce7))
* **ui/A9:** restore include-partner, sync-albums, include-archived as GP simple controls ([01ce622](https://github.com/shitan198u/immich-go-gui/commit/01ce62262967a03f8a92b3fc3ebdce5984ee57e3))
* **ui/B8-B9:** add reset_advanced_flags confirmation dialog and stop persisting secret enabled state ([4de37b3](https://github.com/shitan198u/immich-go-gui/commit/4de37b3e34c74f0998fda29528cda2f32f96b07d))
* **ui:** add AdvancedFlagRow widget and dynamic advanced card generation ([24ec63f](https://github.com/shitan198u/immich-go-gui/commit/24ec63f5e5c901f6b4a6163f8802a5701331e294))
* **ui:** implement 5 missing sub-command tabs (upload-icloud, upload-picasa, archive-gp, archive-icloud, archive-picasa) ([276ba82](https://github.com/shitan198u/immich-go-gui/commit/276ba8288bb9e1d32a2448dd572a956fcff9a9d5))
* v1.1.0 release - complete CLI parity (11 sub-commands), security & runtime safety ([2df7b63](https://github.com/shitan198u/immich-go-gui/commit/2df7b63b8420e397b56221ef09bc0f3b8bb78f1f))
* versioned binary management, manual path pinning, and breaking change checks (Milestone 5) ([4af6ae3](https://github.com/shitan198u/immich-go-gui/commit/4af6ae3954a4116b284b3b563bc8317313b57078))


### Bug Fixes

* absolutize archive destination paths in command builder ([b13b78e](https://github.com/shitan198u/immich-go-gui/commit/b13b78e7b98aa7a627293c19d4d6804732884c40))
* **advanced:** restore api-trace for stack tab and fix tuple syntax closing ([94ba6b9](https://github.com/shitan198u/immich-go-gui/commit/94ba6b97c6128591f553b827680a2392243c9375))
* **assets:** add immich-go-gui.ico for Windows Nuitka build compilation ([32b764b](https://github.com/shitan198u/immich-go-gui/commit/32b764b0211f88edac9a985e940dbb845f4364cc))
* **ci:** add explicit /O github.workspace option to ISCC matching master implementation ([65dcb2f](https://github.com/shitan198u/immich-go-gui/commit/65dcb2fc28d70893e11460f8dbd8724482ecab42))
* **ci:** extract appimagetool to run without FUSE on ubuntu-22.04 runner ([173188d](https://github.com/shitan198u/immich-go-gui/commit/173188d9fe60d89ed404cfed9edcd03c4085dd0e))
* **ci:** move Windows setup installer from parent ISCC OutputDir into workspace root ([68c9328](https://github.com/shitan198u/immich-go-gui/commit/68c9328fe9671d9146c86f67f3cf48bedf5bc57c))
* **ci:** remove redundant PIL conversion and add ARCH=x86_64 for AppImageTool in release.yml ([140b513](https://github.com/shitan198u/immich-go-gui/commit/140b513f52b08c071d7271de3c8ebb0bdbfad888))
* **ci:** replace Minionguyjpro/Inno-Setup-Action with native PowerShell ISCC invocation ([5cae6b6](https://github.com/shitan198u/immich-go-gui/commit/5cae6b63f083fee6b2809a58a5586cdcb9352a7e))
* **ci:** revert appimagetool to continuous build matching master branch behaviour ([b7d68f8](https://github.com/shitan198u/immich-go-gui/commit/b7d68f821a3b2988e1aaf23de7570d2f1b5e86fe))
* **ci:** use /O. relative output directory flag for Inno Setup in release.yml ([e0678b7](https://github.com/shitan198u/immich-go-gui/commit/e0678b77580c0224c92c7738fc7843c6b5493269))
* **cleanup:** derive ADVANCED_KEYS programmatically and fix from-admin-api-key flag name ([1f97bca](https://github.com/shitan198u/immich-go-gui/commit/1f97bca2877d6d1cc7aa815315523d69e6a0df48))
* Folder & Zip Uploads ([ee3edc7](https://github.com/shitan198u/immich-go-gui/commit/ee3edc7bab2e05bca21a01a5f243e60350f80f4d))
* gutter spaces in UI ([cc1474e](https://github.com/shitan198u/immich-go-gui/commit/cc1474efe077c69fd148a74dc277a3286a887fb3))
* gutter spaces in UI ([fcc129c](https://github.com/shitan198u/immich-go-gui/commit/fcc129ce0ec2d45908762c572da3c09c980cb96c))
* **launcher/Fix 1.4:** harden Windows lock lifecycle with heartbeat background loop in bat files ([becb81b](https://github.com/shitan198u/immich-go-gui/commit/becb81bb8421631e5b6e192007c66bba96932000))
* **packaging:** indent Nuitka project conditional directives in app.py ([4833c30](https://github.com/shitan198u/immich-go-gui/commit/4833c30383a0809f00cd08b22c99645a4ac65a9a))
* **paths/A5:** unify glob expansion to recursive=True in collect_paths ([a0828b4](https://github.com/shitan198u/immich-go-gui/commit/a0828b4bc969a6bbe662b910cbc13e51995e0474))
* run terminal in safe working directory to prevent POSIX cwd deletion errors ([1ebc627](https://github.com/shitan198u/immich-go-gui/commit/1ebc62744bc5613cb48ce4d82a0daa410dd90330))
* **security:** mask API keys in preview, pass via env, store in OS keychain ([#46](https://github.com/shitan198u/immich-go-gui/issues/46), [#47](https://github.com/shitan198u/immich-go-gui/issues/47), [#48](https://github.com/shitan198u/immich-go-gui/issues/48)) ([979ee21](https://github.com/shitan198u/immich-go-gui/commit/979ee2123a9a79db8e00ed2caa3d09a951752c0e))
* **security:** pass env dictionary in memory to terminal process and eliminate env.sh cleartext file ([f83a2df](https://github.com/shitan198u/immich-go-gui/commit/f83a2df1b8db03d4fed67c1912ac905dae91beb6))
* **security:** prevent secret advanced values from being persisted in form_state and remove dead GP checkboxes ([c45a851](https://github.com/shitan198u/immich-go-gui/commit/c45a851e220ae97c1e3ba07b418a230ef6971cca))
* **test:** add _norm_argv helper for cross-platform path assertions on Windows ([b913c68](https://github.com/shitan198u/immich-go-gui/commit/b913c68dd43ffaeed335c15ef1cb82fb05d044b1))
* **test:** normalize Windows drive letters in test assertions for 100% cross-platform pass ([bafb30f](https://github.com/shitan198u/immich-go-gui/commit/bafb30f178502e3f23bab884272d5c086d39e302))
* **test:** use string split normalization in _norm_argv to handle drive letters on Windows ([b31140e](https://github.com/shitan198u/immich-go-gui/commit/b31140e4b9ed9b509e72b169e419c6dca2bf46a9))
* **test:** wrap test_gp_multi_path options in _norm_argv for Windows path normalization ([04eefcf](https://github.com/shitan198u/immich-go-gui/commit/04eefcf17226a8b8fb2c123508f4f9ef3a38be64))
* **ui/A1:** fix dead simple-mode controls for upload-immich and archive-immich ([f415f34](https://github.com/shitan198u/immich-go-gui/commit/f415f3442c92f8a781544ed86a169bf3a36c7a42))
* **ui/A4:** surface plan.errors in update_status() before Run dialog ([4b0649d](https://github.com/shitan198u/immich-go-gui/commit/4b0649dfeba5a668d1902041e5d44301be363948))
* **ui:** add inline warning and dialog banner for --skip-verify-ssl ([#50](https://github.com/shitan198u/immich-go-gui/issues/50)) ([9fd37d0](https://github.com/shitan198u/immich-go-gui/commit/9fd37d0c11749cf50e66e1ef56f9832844a2656b))
* **ui:** improve path, file, and takeout handling ([415c624](https://github.com/shitan198u/immich-go-gui/commit/415c6240d022731fae4fad0d99c56cb737c2859b))
* **validation/A3:** use validate_date_range in validate_advanced_state for semantic date checking ([24dabfc](https://github.com/shitan198u/immich-go-gui/commit/24dabfc8e621c9065a2b515d94b7a7bfa78cc885))


### Documentation

* add CLI documentation file and update gitignore and dependency lockfile ([6b37790](https://github.com/shitan198u/immich-go-gui/commit/6b37790b499db7925d133c6e88bd8d58298193b1))
* add refinement specs, documentation notes, and combined immichgo backend bundle ([a0f473a](https://github.com/shitan198u/immich-go-gui/commit/a0f473a1fd0e9ec3162ba20cdd4e04be25edbbe4))
* **changelog:** add detailed CHANGELOG.md for v1.1.0 release notes ([447252c](https://github.com/shitan198u/immich-go-gui/commit/447252ce263d7268d7d486dbcb99f656e876b939))
* finalize command_binary_bugs_fix.txt bundle ([f22aed2](https://github.com/shitan198u/immich-go-gui/commit/f22aed2f3ef1f03a8ae56184eabc95152186db1a))
* generate clean diff bundle for changes made during 'A few fixes again. check' ([ce678dc](https://github.com/shitan198u/immich-go-gui/commit/ce678dc880000643c9fa24dd499b4cbf8dff532f))
* **phase2:** Add Phase 2 review diff bundle and update codebase module bundle ([c0e63c6](https://github.com/shitan198u/immich-go-gui/commit/c0e63c626141ea8411c5a655196914fede88858e))
* regenerate diff and codebase bundles for Phase 3 completion ([98cb629](https://github.com/shitan198u/immich-go-gui/commit/98cb62919db46b178ff77aef17be18828e3a0ce0))
* regenerate diff and codebase bundles for Phase 3 Part 1 completion ([0e77108](https://github.com/shitan198u/immich-go-gui/commit/0e77108cf59c5428b95184a6eeec2b0da804349c))
* regenerate diff and codebase bundles for Phase 4 UI completeness ([a234668](https://github.com/shitan198u/immich-go-gui/commit/a234668723c704f3938904ca8a064052bbb8c2d1))
* regenerate immichgo_modules_bundle.txt with latest code ([fd5d58d](https://github.com/shitan198u/immich-go-gui/commit/fd5d58dca07c3d83bbd18d4050b89769c91e082d))
* update command_binary_bugs_fix.txt bundle with final polish commits ([cbadc2b](https://github.com/shitan198u/immich-go-gui/commit/cbadc2b717fcdf4814d8eec8f63ac820d1902304))
* update command_binary_bugs_fix.txt diff bundle with cleanup commit ([cf6da31](https://github.com/shitan198u/immich-go-gui/commit/cf6da3157c850607ab6af8957830035b08c40214))
* update command_binary_bugs_fix.txt diff review bundle ([375cbfa](https://github.com/shitan198u/immich-go-gui/commit/375cbfa36d9d5a13b79a2c9139c92d9a9c55f4fa))
* update command_binary_bugs_fix.txt to show dump starting from before 'A few fixes again. check' ([d3ca800](https://github.com/shitan198u/immich-go-gui/commit/d3ca8004533c4b65dafb67ff9d00bb4eeae7aa73))
* update command_binary_bugs_fix.txt with secret masking and GP cleanup diff ([bcd0c8b](https://github.com/shitan198u/immich-go-gui/commit/bcd0c8b24f2fb0267e366bdbded5777fdf98a2dc))

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
