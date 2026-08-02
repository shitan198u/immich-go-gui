# Changelog

All notable changes to the Immich-Go GUI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0](https://github.com/shitan198u/immich-go-gui/compare/v1.3.0...v1.4.0) (2026-08-02)


### 🚀 Features & UI Completeness

* **ci:** streamline release workflows to bare v&lt;version&gt; tags ([#116](https://github.com/shitan198u/immich-go-gui/issues/116)) ([5447b7c](https://github.com/shitan198u/immich-go-gui/commit/5447b7c97c6afab2194289d10ed02af1d5107d40))
* **ci:** upload release assets per-platform as builds finish ([#118](https://github.com/shitan198u/immich-go-gui/issues/118)) ([b5aeb60](https://github.com/shitan198u/immich-go-gui/commit/b5aeb601bedf5cea62eb0bdd77fd430b0e1b534f))


### 🐛 Bug Fixes & Discrepancy Resolution

* **ci:** fix release-please extra-files to use x-release-please-version markers ([#119](https://github.com/shitan198u/immich-go-gui/issues/119)) ([a7024ef](https://github.com/shitan198u/immich-go-gui/commit/a7024ef5e136c182d87a0f5dc5d7928bbf9164b2))
* **ci:** update workflow tag triggers to match Release Please immich-go-gui-v* format ([#114](https://github.com/shitan198u/immich-go-gui/issues/114)) ([a9994c8](https://github.com/shitan198u/immich-go-gui/commit/a9994c8a6c30c1e71a9a8164575dd28c57788866))

## [1.3.0](https://github.com/shitan198u/immich-go-gui/compare/immich-go-gui-v1.2.0...immich-go-gui-v1.3.0) (2026-08-01)


### 🚀 Features & UI Completeness

* **ci:** tag-based version sync and PR automation ([#102](https://github.com/shitan198u/immich-go-gui/issues/102)) ([bce1b7a](https://github.com/shitan198u/immich-go-gui/commit/bce1b7a152901148660303ae35f6a4149b4a865b))
* **docs:** dynamic GitHub stars/forks and daily docs cron ([#103](https://github.com/shitan198u/immich-go-gui/issues/103)) ([e670a03](https://github.com/shitan198u/immich-go-gui/commit/e670a03720a5a5cea8beb1c203ca89adaf532ea8))
* slim config persistence, app updates, and Configuration UX ([#96](https://github.com/shitan198u/immich-go-gui/issues/96)) ([1c5b1c1](https://github.com/shitan198u/immich-go-gui/commit/1c5b1c148f77a89ae3b925f9a06f41836042dea3))


### 🐛 Bug Fixes & Discrepancy Resolution

* **ci:** make pyproject.toml single source of truth for version check ([d8034d0](https://github.com/shitan198u/immich-go-gui/commit/d8034d0194324763e8028c4822b2e410b21a35db))
* **command_builder:** add safety warning for from-pause-immich-jobs without from-admin-api-key ([#101](https://github.com/shitan198u/immich-go-gui/issues/101)) ([c83241a](https://github.com/shitan198u/immich-go-gui/commit/c83241ad567ff009d8052921ffca5f107593f6df))
* Ruff Formatting ([3358638](https://github.com/shitan198u/immich-go-gui/commit/33586383f49c60323e70f40b6f70c3f1f45b13ba))
* **test:** isolate keyring operations and enforce XDG config dir in test suite ([#107](https://github.com/shitan198u/immich-go-gui/issues/107)) ([1378e4f](https://github.com/shitan198u/immich-go-gui/commit/1378e4fdda3ecb0ada42ebd499f022b2e497c02e))


### ⚡ Performance & Safety

* **test:** eliminate test suite bottlenecks and enable parallel pytest execution ([#109](https://github.com/shitan198u/immich-go-gui/issues/109)) ([0a26c37](https://github.com/shitan198u/immich-go-gui/commit/0a26c37a70f7dbdbd7e06da41013f54f668a19ca))


### 📚 Documentation

* **agents:** streamline AGENTS.md guide and enforce mandatory pre-commit verification ([323fc8f](https://github.com/shitan198u/immich-go-gui/commit/323fc8f1b8230b911ad8048f8487dbcd5907fac9))
* port runbook palette, remove changelog page, and fix live github stats ([#106](https://github.com/shitan198u/immich-go-gui/issues/106)) ([a3c9844](https://github.com/shitan198u/immich-go-gui/commit/a3c98449281bf5b3fbdfee0f550bae5ed9d9eb46))
* replace screenshots with immich-demo.webm video ([345d3d3](https://github.com/shitan198u/immich-go-gui/commit/345d3d3fa62d250478014e9321fabc14b23763f6))
* replace video tag with trimmed full-resolution demo GIF ([d03cb1d](https://github.com/shitan198u/immich-go-gui/commit/d03cb1db8ffb73623795afa1cb50f0b382ef2ac1))


### 🔧 Refactoring & Architecture

* **app:** extract run_self_test and quality improvements ([#104](https://github.com/shitan198u/immich-go-gui/issues/104)) ([3d371d7](https://github.com/shitan198u/immich-go-gui/commit/3d371d7fc453852490705c50fd5bc0d637ebfc1d))

## [1.2.0](https://github.com/shitan198u/immich-go-gui/compare/immich-go-gui-v1.1.2...immich-go-gui-v1.2.0) (2026-07-29)


### 🚀 Features & UI Completeness

* add documentation review template and styled HTML viewer for Immich-Go GUI ([e449248](https://github.com/shitan198u/immich-go-gui/commit/e449248cbb1c83fe8a79c372ed9101ff4f573ae0))
* add macOS .icns support and consolidate icon generation script ([e5b2c5b](https://github.com/shitan198u/immich-go-gui/commit/e5b2c5b3a607172f04fe43b1f3308cf4c2b21ad4))
* add manual version input for pre-releases via workflow_dispatch ([0f2ba6f](https://github.com/shitan198u/immich-go-gui/commit/0f2ba6f68b7fe0511925788bf9b8309e02643e68))
* add portable zip and tar archives and rename binaries to Immich-Go-GUI ([45cb85e](https://github.com/shitan198u/immich-go-gui/commit/45cb85e4e7ba346bd93c95952b5f44d48ce16e30))
* Add Portable ZIP/TAR Archives & Rename Binaries ([6255a0f](https://github.com/shitan198u/immich-go-gui/commit/6255a0f97c30a1924a7e03f659383362d9b9b529))
* **advanced:** add ADVANCED_FLAGS entries for 5 new tabs ([729cb5a](https://github.com/shitan198u/immich-go-gui/commit/729cb5a0c76e1490c2efb43bc9789910d11a1739))
* **builder:** add command builder and validation rules for 5 new tabs ([6b411bc](https://github.com/shitan198u/immich-go-gui/commit/6b411bcd4beb1e4870de597ede42d995099c592f))
* **builder:** integrate advanced state into command builder and surface plan errors ([5e60606](https://github.com/shitan198u/immich-go-gui/commit/5e60606c04bbaa555d736a44d2e626848b2fcded))
* **ci:** configure release-please with custom section titles, emojis, and manifest tracking ([59c09f2](https://github.com/shitan198u/immich-go-gui/commit/59c09f2c7ec39759b1e853987e2b10d6a41bec66))
* **ci:** embed version in all release artifact filenames (e.g. Immich-Go-GUI-1.1.0-Linux.AppImage) ([4d053a3](https://github.com/shitan198u/immich-go-gui/commit/4d053a3feb649753ea0a40681697791620b1414a))
* **ci:** standardize release artifact filenames with version and x86_64 architecture ([73a08d7](https://github.com/shitan198u/immich-go-gui/commit/73a08d7222255509bda536759f23344f93ccf41b))
* **cli:** capture help fixtures for 5 new sub-commands (0.32.0) ([9d3a3c5](https://github.com/shitan198u/immich-go-gui/commit/9d3a3c5d19a66a25bf16b24de8946c248dc29597))
* **cli:** enable native immich-go UI by default ([033574e](https://github.com/shitan198u/immich-go-gui/commit/033574ef67b395f24ecd640e55c51bb6536cbbf2))
* **core:** add schema-driven advanced_flags registry and helpers ([0bc3ebe](https://github.com/shitan198u/immich-go-gui/commit/0bc3ebef7f6225495b5a743a870f2e4b5cc470b0))
* cross-platform automated packaging via Nuitka and GitHub Actions ([4f65503](https://github.com/shitan198u/immich-go-gui/commit/4f655030a193d11ad6081e1ef59651fbfe32e4ed))
* custom dynamic svg icons for theming ([8337003](https://github.com/shitan198u/immich-go-gui/commit/83370032cedc00e5d941fe0e97fbf4bfb9dec8ec))
* Documentation. ([#79](https://github.com/shitan198u/immich-go-gui/issues/79)) ([4fe7622](https://github.com/shitan198u/immich-go-gui/commit/4fe762263228a6bc4f29daab68f7673b5b3d581a))
* implement flatpak packaging using native flatpak-builder ([00b16a6](https://github.com/shitan198u/immich-go-gui/commit/00b16a629a07ecb1c3207d9a561985903423d514))
* inline validation, diagnostics menus, and exception handler ([f7c7e77](https://github.com/shitan198u/immich-go-gui/commit/f7c7e77ebabe017ed96a61f3525ba2c306e1f964))
* **network:** add pre-flight server connectivity check before command execution ([3534f76](https://github.com/shitan198u/immich-go-gui/commit/3534f76fa29e7fd467a908d40f96de8b02905707))
* **persistence:** persist opt-in advanced flag state and add reset action ([420bda4](https://github.com/shitan198u/immich-go-gui/commit/420bda4fa47dd906469c406db38652d18f1f5f69))
* **phase2:** Step 1 — Command generation completeness & golden tests ([9385c19](https://github.com/shitan198u/immich-go-gui/commit/9385c1913e3bb37fbbcf923d7539961fd09c3fb9))
* **phase2:** Step 2 — UI completeness & Simple/Advanced persistence ([7d67abf](https://github.com/shitan198u/immich-go-gui/commit/7d67abfdc081e60a5d1b879cc3c1ab50e49fc1aa))
* **phase2:** Step 3 — Validation and persistence safety ([cbd7720](https://github.com/shitan198u/immich-go-gui/commit/cbd77205893fda0de50f54caa63bb9a572d3e035))
* **phase2:** Step 4 — Binary update safety ([8b01f62](https://github.com/shitan198u/immich-go-gui/commit/8b01f621a238290b2d38d72d0b74e5b3956ceb91))
* **phase2:** Step 5 — Compatibility, terminal hardening & CI readiness ([5b1b85d](https://github.com/shitan198u/immich-go-gui/commit/5b1b85d30388d8066426cd9807f651a846986def))
* robust process tracking using psutil ([6995514](https://github.com/shitan198u/immich-go-gui/commit/69955148e24c614e2da806452fa74d78183312ed))
* **schema:** add tab keys, commands, serverless status, and allowed flags for 5 new sub-commands ([f153d83](https://github.com/shitan198u/immich-go-gui/commit/f153d833b856f3862adfca7f15f358dd4a5392d5))
* structured command preview dialog with copy command button (Milestone 6) ([12aa449](https://github.com/shitan198u/immich-go-gui/commit/12aa449d2d414ef0efd3c9256fe72f69dad8cf6e))
* suppress advanced options and configuration in Simple mode ([54e5b33](https://github.com/shitan198u/immich-go-gui/commit/54e5b3379b96b80915c6ef58fa3f02e7eda8dce7))
* **ui/A9:** restore include-partner, sync-albums, include-archived as GP simple controls ([01ce622](https://github.com/shitan198u/immich-go-gui/commit/01ce62262967a03f8a92b3fc3ebdce5984ee57e3))
* **ui/B8-B9:** add reset_advanced_flags confirmation dialog and stop persisting secret enabled state ([4de37b3](https://github.com/shitan198u/immich-go-gui/commit/4de37b3e34c74f0998fda29528cda2f32f96b07d))
* **ui:** add AdvancedFlagRow widget and dynamic advanced card generation ([24ec63f](https://github.com/shitan198u/immich-go-gui/commit/24ec63f5e5c901f6b4a6163f8802a5701331e294))
* **ui:** implement 5 missing sub-command tabs (upload-icloud, upload-picasa, archive-gp, archive-icloud, archive-picasa) ([276ba82](https://github.com/shitan198u/immich-go-gui/commit/276ba8288bb9e1d32a2448dd572a956fcff9a9d5))
* v1.1.0 release - complete CLI parity (11 sub-commands), security & runtime safety ([2df7b63](https://github.com/shitan198u/immich-go-gui/commit/2df7b63b8420e397b56221ef09bc0f3b8bb78f1f))
* versioned binary management, manual path pinning, and breaking change checks (Milestone 5) ([4af6ae3](https://github.com/shitan198u/immich-go-gui/commit/4af6ae3954a4116b284b3b563bc8317313b57078))


### 🐛 Bug Fixes & Discrepancy Resolution

* absolutize archive destination paths in command builder ([b13b78e](https://github.com/shitan198u/immich-go-gui/commit/b13b78e7b98aa7a627293c19d4d6804732884c40))
* add --unsafe to check-yaml hook and clean up code linter formatting ([27ef15d](https://github.com/shitan198u/immich-go-gui/commit/27ef15d4af9b6cba41fbc8b5313385cc2f7a9ed7))
* **advanced:** restore api-trace for stack tab and fix tuple syntax closing ([94ba6b9](https://github.com/shitan198u/immich-go-gui/commit/94ba6b97c6128591f553b827680a2392243c9375))
* **assets:** add immich-go-gui.ico for Windows Nuitka build compilation ([32b764b](https://github.com/shitan198u/immich-go-gui/commit/32b764b0211f88edac9a985e940dbb845f4364cc))
* **ci:** add explicit /O github.workspace option to ISCC matching master implementation ([65dcb2f](https://github.com/shitan198u/immich-go-gui/commit/65dcb2fc28d70893e11460f8dbd8724482ecab42))
* **ci:** add windows metadata and .exe icon injection ([4234f0d](https://github.com/shitan198u/immich-go-gui/commit/4234f0ddfc494d05426730be52d43e9e05a2910f))
* **ci:** extract appimagetool to run without FUSE on ubuntu-22.04 runner ([173188d](https://github.com/shitan198u/immich-go-gui/commit/173188d9fe60d89ed404cfed9edcd03c4085dd0e))
* **ci:** move Windows setup installer from parent ISCC OutputDir into workspace root ([68c9328](https://github.com/shitan198u/immich-go-gui/commit/68c9328fe9671d9146c86f67f3cf48bedf5bc57c))
* **ci:** remove redundant PIL conversion and add ARCH=x86_64 for AppImageTool in release.yml ([140b513](https://github.com/shitan198u/immich-go-gui/commit/140b513f52b08c071d7271de3c8ebb0bdbfad888))
* **ci:** replace Minionguyjpro/Inno-Setup-Action with native PowerShell ISCC invocation ([5cae6b6](https://github.com/shitan198u/immich-go-gui/commit/5cae6b63f083fee6b2809a58a5586cdcb9352a7e))
* **ci:** revert appimagetool to continuous build matching master branch behaviour ([b7d68f8](https://github.com/shitan198u/immich-go-gui/commit/b7d68f821a3b2988e1aaf23de7570d2f1b5e86fe))
* **ci:** use /O. relative output directory flag for Inno Setup in release.yml ([e0678b7](https://github.com/shitan198u/immich-go-gui/commit/e0678b77580c0224c92c7738fc7843c6b5493269))
* **cleanup:** derive ADVANCED_KEYS programmatically and fix from-admin-api-key flag name ([1f97bca](https://github.com/shitan198u/immich-go-gui/commit/1f97bca2877d6d1cc7aa815315523d69e6a0df48))
* **cli:** correct command argument ordering and --no-ui flag handling ([e472e77](https://github.com/shitan198u/immich-go-gui/commit/e472e775c99cd127ec01491ec13346603ea5e5d2))
* convert _build_config_tab to new native component structure ([9b516d7](https://github.com/shitan198u/immich-go-gui/commit/9b516d7619bca3e43f042879d926005fab98a64e))
* **deps:** resolve pip-audit vulnerabilities in requests/urllib3/idna ([#95](https://github.com/shitan198u/immich-go-gui/issues/95)) ([3e0695b](https://github.com/shitan198u/immich-go-gui/commit/3e0695bc100432299746ee710d019faa0750aa60))
* ensure inno setup outputs to github workspace ([3f7fd6c](https://github.com/shitan198u/immich-go-gui/commit/3f7fd6c6fd9b8619d84734f787ace335d3911521))
* ensure Nuitka packages assets directory containing SVG icons ([56e823c](https://github.com/shitan198u/immich-go-gui/commit/56e823c3c18fd347f7bf5e91f6b489cbac466442))
* ensure Nuitka packages SVG icons ([37e0883](https://github.com/shitan198u/immich-go-gui/commit/37e08837cd2e4a234076ca90f0356a460ac86fe2))
* explicitly specify flatpak sources to bypass gitignore exclusion of app.dist ([049801d](https://github.com/shitan198u/immich-go-gui/commit/049801d42ced1d174df1303da3eaa466e139896e))
* flatpak sandbox issues (mkdir bin, patch desktop Exec, update runtime) ([b94bb3c](https://github.com/shitan198u/immich-go-gui/commit/b94bb3cfe9b1094611c91d7ababb20d7045cc009))
* Folder & Zip Uploads ([ee3edc7](https://github.com/shitan198u/immich-go-gui/commit/ee3edc7bab2e05bca21a01a5f243e60350f80f4d))
* gutter spaces in UI ([cc1474e](https://github.com/shitan198u/immich-go-gui/commit/cc1474efe077c69fd148a74dc277a3286a887fb3))
* gutter spaces in UI ([fcc129c](https://github.com/shitan198u/immich-go-gui/commit/fcc129ce0ec2d45908762c572da3c09c980cb96c))
* harden GUI emission, launcher env, and regression tests ([4ffcd14](https://github.com/shitan198u/immich-go-gui/commit/4ffcd14eb47fd63211051de1dfc50c36504512db))
* Icon mismatch build fail ([2704432](https://github.com/shitan198u/immich-go-gui/commit/27044328bfcdab216f473dc61b69ecec86e0f2ae))
* **launcher/Fix 1.4:** harden Windows lock lifecycle with heartbeat background loop in bat files ([becb81b](https://github.com/shitan198u/immich-go-gui/commit/becb81bb8421631e5b6e192007c66bba96932000))
* multi-resolution Windows icon and high-DPI SVG icons ([8ac46db](https://github.com/shitan198u/immich-go-gui/commit/8ac46dbbd3819f1d263f7807254d390a5f85dd85))
* only prompt to save when configuration actually changed ([c37f69d](https://github.com/shitan198u/immich-go-gui/commit/c37f69de6535d1b5082f24ede3183b13d6dcc098))
* **packaging:** indent Nuitka project conditional directives in app.py ([4833c30](https://github.com/shitan198u/immich-go-gui/commit/4833c30383a0809f00cd08b22c99645a4ac65a9a))
* **paths/A5:** unify glob expansion to recursive=True in collect_paths ([a0828b4](https://github.com/shitan198u/immich-go-gui/commit/a0828b4bc969a6bbe662b910cbc13e51995e0474))
* pin setup-nfpm version to fix broken latest tag resolution ([2d29e1e](https://github.com/shitan198u/immich-go-gui/commit/2d29e1e97b03234bec016d33b01be634cf35877c))
* pre-release hardening for pause-jobs, SHA256, and CLI defaults ([1a45d76](https://github.com/shitan198u/immich-go-gui/commit/1a45d761ed30dabbefdab4a57371b25a29b3d996))
* Project Documentation ([#81](https://github.com/shitan198u/immich-go-gui/issues/81)) ([be69fae](https://github.com/shitan198u/immich-go-gui/commit/be69fae95ac2210989a4c68a1681d255c838551a))
* propagate global skip-ssl to upload-immich source ([e2269ef](https://github.com/shitan198u/immich-go-gui/commit/e2269efc9dd2247c0c0f31923a4011c67c33a610))
* repair Windows profile config migration and save feedback ([9c19cfe](https://github.com/shitan198u/immich-go-gui/commit/9c19cfeff046bdf97fdff2084e3f35a556e2a70d))
* replace broken nfpm action with native bash installation ([b2e6e0a](https://github.com/shitan198u/immich-go-gui/commit/b2e6e0a64fd8bf7b2ec30a650ee1cd581aaee5e7))
* resize flatpak icon to 512x512 and patch desktop file Icon ([587922d](https://github.com/shitan198u/immich-go-gui/commit/587922d067bdb6b721edddd588687353fc7cf409))
* resolve permission denied error for installer builds by downloading binary to user home directory ([45ee1f1](https://github.com/shitan198u/immich-go-gui/commit/45ee1f1e398c47e3480e11337543d8db6d8ecfa9))
* resolve permission denied error for installer builds by downloading binary to user home directory ([4369e57](https://github.com/shitan198u/immich-go-gui/commit/4369e57e53c6dc27185ff40ddd908be492917f62))
* resolve permission denied error on installer builds ([1ec5068](https://github.com/shitan198u/immich-go-gui/commit/1ec5068da9ba18d9d9d5eca897279a72d7da75aa))
* run terminal in safe working directory to prevent POSIX cwd deletion errors ([1ebc627](https://github.com/shitan198u/immich-go-gui/commit/1ebc62744bc5613cb48ce4d82a0daa410dd90330))
* **security:** mask API keys in preview, pass via env, store in OS keychain ([#46](https://github.com/shitan198u/immich-go-gui/issues/46), [#47](https://github.com/shitan198u/immich-go-gui/issues/47), [#48](https://github.com/shitan198u/immich-go-gui/issues/48)) ([979ee21](https://github.com/shitan198u/immich-go-gui/commit/979ee2123a9a79db8e00ed2caa3d09a951752c0e))
* **security:** pass env dictionary in memory to terminal process and eliminate env.sh cleartext file ([f83a2df](https://github.com/shitan198u/immich-go-gui/commit/f83a2df1b8db03d4fed67c1912ac905dae91beb6))
* **security:** prevent secret advanced values from being persisted in form_state and remove dead GP checkboxes ([c45a851](https://github.com/shitan198u/immich-go-gui/commit/c45a851e220ae97c1e3ba07b418a230ef6971cca))
* skip save prompt when configuration is unchanged ([29b7137](https://github.com/shitan198u/immich-go-gui/commit/29b7137091df1ad1f3ac21bd30906a186e7dd4df))
* specify windows release to use bash shell ([063df55](https://github.com/shitan198u/immich-go-gui/commit/063df5535dab21d624c83d9543aa82a360209041))
* **test:** add _norm_argv helper for cross-platform path assertions on Windows ([b913c68](https://github.com/shitan198u/immich-go-gui/commit/b913c68dd43ffaeed335c15ef1cb82fb05d044b1))
* **test:** normalize Windows drive letters in test assertions for 100% cross-platform pass ([bafb30f](https://github.com/shitan198u/immich-go-gui/commit/bafb30f178502e3f23bab884272d5c086d39e302))
* **test:** use string split normalization in _norm_argv to handle drive letters on Windows ([b31140e](https://github.com/shitan198u/immich-go-gui/commit/b31140e4b9ed9b509e72b169e419c6dca2bf46a9))
* **test:** wrap test_gp_multi_path options in _norm_argv for Windows path normalization ([04eefcf](https://github.com/shitan198u/immich-go-gui/commit/04eefcf17226a8b8fb2c123508f4f9ef3a38be64))
* UI changes before qwen plan ([1d98bb7](https://github.com/shitan198u/immich-go-gui/commit/1d98bb79732c0f79d44077bc5aa523a4a95b54a1))
* **ui/A1:** fix dead simple-mode controls for upload-immich and archive-immich ([f415f34](https://github.com/shitan198u/immich-go-gui/commit/f415f3442c92f8a781544ed86a169bf3a36c7a42))
* **ui/A4:** surface plan.errors in update_status() before Run dialog ([4b0649d](https://github.com/shitan198u/immich-go-gui/commit/4b0649dfeba5a668d1902041e5d44301be363948))
* **ui:** add inline warning and dialog banner for --skip-verify-ssl ([#50](https://github.com/shitan198u/immich-go-gui/issues/50)) ([9fd37d0](https://github.com/shitan198u/immich-go-gui/commit/9fd37d0c11749cf50e66e1ef56f9832844a2656b))
* **ui:** correct binary status checks for eliding labels ([50974ff](https://github.com/shitan198u/immich-go-gui/commit/50974ffaa2d15b9df570667699d31a3105e3a4b8))
* **ui:** correct folder icon assignment in Archive Server tab ([ed68ac9](https://github.com/shitan198u/immich-go-gui/commit/ed68ac9d30ea01fb5eb38914dce36e8de036d90a))
* **ui:** expand BasePage container for uniform tab widths ([50cd140](https://github.com/shitan198u/immich-go-gui/commit/50cd1408306787d8d8d2f0b82e9cba19f28ede08))
* **ui:** improve path, file, and takeout handling ([415c624](https://github.com/shitan198u/immich-go-gui/commit/415c6240d022731fae4fad0d99c56cb737c2859b))
* **ui:** prevent TypeError on QListView.update() in theme engine ([df917dc](https://github.com/shitan198u/immich-go-gui/commit/df917dc11567cf050e418b29026ae6424a799900))
* **ui:** Track 1 - UI sizing & right-edge clipping ([6a3ec41](https://github.com/shitan198u/immich-go-gui/commit/6a3ec41274de367d49fb24f678e2313ecfae90ec))
* **ui:** Track 2 - Icons and Status Indicators (No Emoji) ([f3577b6](https://github.com/shitan198u/immich-go-gui/commit/f3577b6a38afb0d997d8308464ef9d0a7b27eb94))
* update Nuitka directives to include assets and remove gui data dir ([d37bc81](https://github.com/shitan198u/immich-go-gui/commit/d37bc819cbe52ac893eb2fbe12bd9d63b1450a48))
* use official goreleaser-action to install nfpm dynamically ([98ace6f](https://github.com/shitan198u/immich-go-gui/commit/98ace6f42a00fc8fff16047c5afc62b43f5cf848))
* use powershell for windows portable archive since zip is not in path ([4aacaba](https://github.com/shitan198u/immich-go-gui/commit/4aacaba30d2a5d79d9db78ecf2fbb4f301e359aa))
* use test- prefix for manual build tags so release-please ignores them ([ea9aa59](https://github.com/shitan198u/immich-go-gui/commit/ea9aa59f4242e8b47bfbe96bfd2c759a1bb579d5))
* **validation/A3:** use validate_date_range in validate_advanced_state for semantic date checking ([24dabfc](https://github.com/shitan198u/immich-go-gui/commit/24dabfc8e621c9065a2b515d94b7a7bfa78cc885))
* **windows:** 4 runtime bugs — pause-jobs 403, bat self-deletion, lock stale after cmd close ([#70](https://github.com/shitan198u/immich-go-gui/issues/70)) ([c2d9e76](https://github.com/shitan198u/immich-go-gui/commit/c2d9e76329941ade26d1f26168de2f186deb99c3)), closes [#69](https://github.com/shitan198u/immich-go-gui/issues/69)


### 📚 Documentation

* add CLI documentation file and update gitignore and dependency lockfile ([6b37790](https://github.com/shitan198u/immich-go-gui/commit/6b37790b499db7925d133c6e88bd8d58298193b1))
* add contribution guidelines and issue/PR templates ([8b68856](https://github.com/shitan198u/immich-go-gui/commit/8b68856e732fd4369bf986e3b8d205de4743c523))
* add refinement specs, documentation notes, and combined immichgo backend bundle ([a0f473a](https://github.com/shitan198u/immich-go-gui/commit/a0f473a1fd0e9ec3162ba20cdd4e04be25edbbe4))
* add workflow_dispatch and GitHub Actions documentation ([9dfaaea](https://github.com/shitan198u/immich-go-gui/commit/9dfaaea1d7f39927262e413af8079bf2a7a4eae9))
* align architecture and scripts guide with gui package layout ([719f704](https://github.com/shitan198u/immich-go-gui/commit/719f7049c408e0cd03e97e4d315938db17e397c0))
* align user and maintainer docs with flags.toml emission model ([d64db49](https://github.com/shitan198u/immich-go-gui/commit/d64db49d1e98f4184e19dbbecda6e77e6299f0ab))
* **changelog:** add detailed CHANGELOG.md for v1.1.0 release notes ([447252c](https://github.com/shitan198u/immich-go-gui/commit/447252ce263d7268d7d486dbcb99f656e876b939))
* **changelog:** refine v1.1.0 release notes for GitHub release ([49e702f](https://github.com/shitan198u/immich-go-gui/commit/49e702f56490876db3d91e1436146e5932e0487f))
* clarify windows defender false positive in README ([eeaca49](https://github.com/shitan198u/immich-go-gui/commit/eeaca499be4c47a73163c9ca82e24a65ae5cce51))
* finalize command_binary_bugs_fix.txt bundle ([f22aed2](https://github.com/shitan198u/immich-go-gui/commit/f22aed2f3ef1f03a8ae56184eabc95152186db1a))
* generate clean diff bundle for changes made during 'A few fixes again. check' ([ce678dc](https://github.com/shitan198u/immich-go-gui/commit/ce678dc880000643c9fa24dd499b4cbf8dff532f))
* **phase2:** Add Phase 2 review diff bundle and update codebase module bundle ([c0e63c6](https://github.com/shitan198u/immich-go-gui/commit/c0e63c626141ea8411c5a655196914fede88858e))
* regenerate diff and codebase bundles for Phase 3 completion ([98cb629](https://github.com/shitan198u/immich-go-gui/commit/98cb62919db46b178ff77aef17be18828e3a0ce0))
* regenerate diff and codebase bundles for Phase 3 Part 1 completion ([0e77108](https://github.com/shitan198u/immich-go-gui/commit/0e77108cf59c5428b95184a6eeec2b0da804349c))
* regenerate diff and codebase bundles for Phase 4 UI completeness ([a234668](https://github.com/shitan198u/immich-go-gui/commit/a234668723c704f3938904ca8a064052bbb8c2d1))
* regenerate immichgo_modules_bundle.txt with latest code ([fd5d58d](https://github.com/shitan198u/immich-go-gui/commit/fd5d58dca07c3d83bbd18d4050b89769c91e082d))
* update and condense agent knowledge guidelines in AGENTS.md ([c917d63](https://github.com/shitan198u/immich-go-gui/commit/c917d630ae15a822747cd3622d57b506c0a7bb2e))
* update command_binary_bugs_fix.txt bundle with final polish commits ([cbadc2b](https://github.com/shitan198u/immich-go-gui/commit/cbadc2b717fcdf4814d8eec8f63ac820d1902304))
* update command_binary_bugs_fix.txt diff bundle with cleanup commit ([cf6da31](https://github.com/shitan198u/immich-go-gui/commit/cf6da3157c850607ab6af8957830035b08c40214))
* update command_binary_bugs_fix.txt diff review bundle ([375cbfa](https://github.com/shitan198u/immich-go-gui/commit/375cbfa36d9d5a13b79a2c9139c92d9a9c55f4fa))
* update command_binary_bugs_fix.txt to show dump starting from before 'A few fixes again. check' ([d3ca800](https://github.com/shitan198u/immich-go-gui/commit/d3ca8004533c4b65dafb67ff9d00bb4eeae7aa73))
* update command_binary_bugs_fix.txt with secret masking and GP cleanup diff ([bcd0c8b](https://github.com/shitan198u/immich-go-gui/commit/bcd0c8b24f2fb0267e366bdbded5777fdf98a2dc))
* update contributing guide with improved relative path links and usage instructions ([3cdfd09](https://github.com/shitan198u/immich-go-gui/commit/3cdfd09951f731009dd61c152e2f0224159524ec))
* update UI screenshots in README ([3bf32ab](https://github.com/shitan198u/immich-go-gui/commit/3bf32ab8074de5fef8e3a87e5d8180e924c9f8ff))


### 🔧 Refactoring & Architecture

* add explicit QWidget casts and standard button to QMessageBox calls in persistence mixin ([cad6fb1](https://github.com/shitan198u/immich-go-gui/commit/cad6fb19300f0aef52ad5f94e065a67a2b226275))
* **advanced/A10:** route apply_advanced_flags_to_plan through FlagEmitter ([5549887](https://github.com/shitan198u/immich-go-gui/commit/554988733d302f7f35b7bd6c588258d6cd9ba12b))
* align bundle scripts, release workflow, and dev docs ([eb568a8](https://github.com/shitan198u/immich-go-gui/commit/eb568a82836c0b18cf4fb6793cf0ac7bdd6bc8db))
* **binary/Fix 1.3:** centralize binary download and installation in BinaryManager ([ffe8c8d](https://github.com/shitan198u/immich-go-gui/commit/ffe8c8df8a2c9d924628112140c4a784398e9175))
* centralize Nuitka build configuration within app.py pragmas ([f9c0e99](https://github.com/shitan198u/immich-go-gui/commit/f9c0e99f5e29674bc4de6c05983f6f12be22f9fb))
* **ci:** relocate release-please config files into .github directory ([166f75e](https://github.com/shitan198u/immich-go-gui/commit/166f75e6025766ffeb98adb056478c2f4f54a4d3))
* cleanup temporary migration scripts and update UI stylesheet for improved consistency ([eb58b69](https://github.com/shitan198u/immich-go-gui/commit/eb58b69cad61adc8478a091f1a0105d4f16868ee))
* **cleanup:** add explicit operator precedence parentheses and test_gp_simple_card_has_no_dead_checkboxes ([bfd62d3](https://github.com/shitan198u/immich-go-gui/commit/bfd62d38cd4ada764f27f120fb15b3862e412a72))
* **cleanup:** remove obsolete app2.py legacy file, empty package directories, and root config.toml ([112622c](https://github.com/shitan198u/immich-go-gui/commit/112622c493b9e716e4e0219511d79f60f77da8a2))
* **cleanup:** remove Refinement specs and temporary documentation from clean branch ([14a68b5](https://github.com/shitan198u/immich-go-gui/commit/14a68b5a1ffd70ab10de0af625d06f73dfd98ce2))
* command plan builder and secret isolation (Milestone 2) ([33a234b](https://github.com/shitan198u/immich-go-gui/commit/33a234b302dc7109e298779be9825d3ff381659b))
* consolidate environment builder and add defense-in-depth comments (Milestone 8.2) ([efce31b](https://github.com/shitan198u/immich-go-gui/commit/efce31b438727be805a17dbbf00bf7cf7b0b37a9))
* create immichgo_binary.py with BinaryManager and version policies (Milestone 6) ([9292647](https://github.com/shitan198u/immich-go-gui/commit/9292647848068bcc11225cf53590b2f45f98d389))
* create immichgo_commands.py for pure command building and state validation (Milestone 4) ([a2199ed](https://github.com/shitan198u/immich-go-gui/commit/a2199ed11af47d273053fa007cae7c31a4bb2053))
* create immichgo_config.py for TOML configuration and secret management (Milestone 7) ([bc5c65b](https://github.com/shitan198u/immich-go-gui/commit/bc5c65b497e855039d6aaff8fd16de557e088f12))
* create immichgo_models.py with pure dataclasses (Milestone 2) ([1ccfb4e](https://github.com/shitan198u/immich-go-gui/commit/1ccfb4ef23405417fb42b55ecdc73e688ce34ea6))
* create immichgo_schema.py with command and tab constants (Milestone 3) ([5977963](https://github.com/shitan198u/immich-go-gui/commit/59779630c41589b2a5c03f4405278d6576eb09f5))
* DRY browse dialogs and slim app.py entry point ([42315e2](https://github.com/shitan198u/immich-go-gui/commit/42315e2245915b9733e482ae2602a3c5a64277d4))
* explicit validation feedback architecture (Milestone 3) ([fb42ecf](https://github.com/shitan198u/immich-go-gui/commit/fb42ecf9b91d931e124248143387d10b61b54749))
* extract 11 tab builders to gui/tabs/ ([de0c974](https://github.com/shitan198u/immich-go-gui/commit/de0c9748774fd6de0d0b336e85c67377e6243c9e))
* extract behavior mixins to gui/mixins/ and assemble ImmichGoGUI in gui/main_window.py ([352fe97](https://github.com/shitan198u/immich-go-gui/commit/352fe976ebcc39dea377b35c219e2e9a44023774))
* extract browse dialogs mixin to gui/browse_dialogs.py ([409c83d](https://github.com/shitan198u/immich-go-gui/commit/409c83d225e43646065ed9d0da3c4b91f31a09b8))
* extract custom widgets to gui/widgets/ ([36a10c7](https://github.com/shitan198u/immich-go-gui/commit/36a10c71e67df1949deb90fd1d128b227a6f6a8e))
* extract stylesheet to assets/theme.qss ([86f31a9](https://github.com/shitan198u/immich-go-gui/commit/86f31a9ed8201c51646150079799f5d2f5d3f541))
* migrate app.py to new architecture and expand test suite ([f47355b](https://github.com/shitan198u/immich-go-gui/commit/f47355bc9546188a22d6d48aeaee88c455c9cc4b))
* modularize GUI into gui/ package and harden CLI parity ([bd5c64d](https://github.com/shitan198u/immich-go-gui/commit/bd5c64d400315329038351dcd1f9f15a70d132f6))
* modularize GUI into gui/ package and harden CLI parity ([#88](https://github.com/shitan198u/immich-go-gui/issues/88)) ([bd5c64d](https://github.com/shitan198u/immich-go-gui/commit/bd5c64d400315329038351dcd1f9f15a70d132f6))
* modularize theme engine and fix syntax errors ([584d9b2](https://github.com/shitan198u/immich-go-gui/commit/584d9b2b6f5bad4ff76f04a5f1eac0d6bb03afc0))
* Phase 0 - Critical Bug Fixes for layout striping ([66c55c4](https://github.com/shitan198u/immich-go-gui/commit/66c55c45d9170b2c599e45e25fb976dda13a2834))
* Phase 1 - Core Architecture ([7f2e4d6](https://github.com/shitan198u/immich-go-gui/commit/7f2e4d6cbc8a91ea5f61792555d5eb1096c34e87))
* Phase 2 - Refinement and Validation ([466b94b](https://github.com/shitan198u/immich-go-gui/commit/466b94be1dfd11ad0595f2dfc69d5135d0093f5a))
* process tracking via lock-file mechanism (Milestone 4) ([0c4fb17](https://github.com/shitan198u/immich-go-gui/commit/0c4fb179af5b0bad0a5f1384506827151c0dcfa4))
* pure data structures and utilities (Milestone 1) ([4a019ac](https://github.com/shitan198u/immich-go-gui/commit/4a019ac95b1cbce79ac62bdb79ca332ba9110cd0))
* rename icon generator script to generate_build_icons.py ([c9de51e](https://github.com/shitan198u/immich-go-gui/commit/c9de51e469003db3c82e4787856f15f07d270a81))
* restructure backend into core package and add developer scripts ([c7aaef8](https://github.com/shitan198u/immich-go-gui/commit/c7aaef85b1003f68dbe028273777ede46dbaa73c))
* split form and dialog helpers out of large mixins ([dcbf076](https://github.com/shitan198u/immich-go-gui/commit/dcbf076f3dd842d458467d12e0f99ee851edfa83))
* streamline Nuitka build commands and add macOS .icns icon support ([403783c](https://github.com/shitan198u/immich-go-gui/commit/403783cac7af76ec00ba5fab8528090de4f40d21))
* **structure:** move test_app.py into tests/ directory and update project configs ([b52787a](https://github.com/shitan198u/immich-go-gui/commit/b52787a9fda18eb18e9e3049406be293ca81af24))
* **test:** integrate pure utility functions and decoupled test suite ([84b724a](https://github.com/shitan198u/immich-go-gui/commit/84b724a9fb9490bc4013dbf8883ae85b236e418d))
* **ui:** move --skip-verify-ssl to global Configuration tab ([#52](https://github.com/shitan198u/immich-go-gui/issues/52)) ([92b5cbf](https://github.com/shitan198u/immich-go-gui/commit/92b5cbf07509934333b9faf6c0d9e3710232f0c3))
* **ui:** transition to dynamic semantic token theme engine (Fusion) ([c4eb2e4](https://github.com/shitan198u/immich-go-gui/commit/c4eb2e465affde30ecf4db4a114c978d40d219d3))
* unify CLI flags in flags.toml single source of truth ([7228a92](https://github.com/shitan198u/immich-go-gui/commit/7228a92c1a69da1564107d849c8428361690c425))
* update app.py to use state collectors and delegate to immichgo_commands (Milestone 5) ([934271a](https://github.com/shitan198u/immich-go-gui/commit/934271ae8f2d2cbba1dc79bceeb782a3e2e662db))
* update packaging, Pyright config, and test monkeypatch targets ([9556bde](https://github.com/shitan198u/immich-go-gui/commit/9556bde188ace41342c74293cef72529a3ac4c6f))

## [1.4.0] - Unreleased

### Changed
- **Flag system simplification:** removed `emission` field from `flags.toml`; each flag is either `mode = "simple"` (emit when value ≠ default) or `mode = "advanced"` (emit when row enabled)
- Moved `client-timeout`, `concurrent-tasks`, `device-uuid`, `on-errors`, and `pause-immich-jobs` from Config tab to per-tab Advanced Flags rows
- `on-errors` advanced row is now free text: `stop`, `continue`, or a numeric max-error count
- Eliminated `mode = "both"`; Picasa album flags are simple-mode only
- `command_builder` uses a generic simple-flag loop plus positional-owned flag handler (no dedup, no config-tab emission path)

### Removed
- Config tab widgets: Client Timeout, Concurrent Tasks, Device UUID, On Errors, Pause Jobs
- `AppConfig` persisted fields for the above (legacy keys ignored on load)
- `ON_ERRORS_CUSTOM_LABEL` / tolerance spinbox UI

### Added
- `on-errors` validation in `validate_advanced_state()`
- Per-value `warn_values` on `manage-burst` / `manage-raw-jpeg` in `flags.toml`

### Note
- Upgrading from older configs: global `on_errors` / `pause_immich_jobs` preferences are **not** auto-migrated to per-tab advanced rows. Re-enable them on each tab if needed.

---

## [1.3.0] - Unreleased

### Changed
- Replaced `config_emitted` boolean with four-value `emission` field in `flags.toml` (`always`, `config`, `advanced`, `config+advanced`)
- Unified `config+advanced` resolution via `_resolve_config_advanced()` for `log-level`, `on-errors`, and `pause-jobs`
- Simple vs advanced mode distinguished by `advanced_state=None` vs `dict`
- Config-tab preferences now flow through in Simple mode

### Added
- `CommandPlan.emission_log` with per-flag source tracking
- Flag Sources panel in run confirmation dialog
- `tests/test_emission_model.py` integration tests

### Fixed
- `REPEAT_FLAGS` no longer includes boolean `takeout-tag` / `people-tag`
- Archive registry key aligned: `target-folder` → `write-to`
- Removed dead `upload-icloud` album-flag emission; added `upload-folder` `--into-album` emission
- Pause-jobs admin-key safety pass when no flag otherwise emitted

---

## [1.2.0] - Unreleased

### Changed
- Unified CLI flag registry: `core/flags.toml` is now the single source of truth (via `flag_registry.py`); `cli_schema` / `advanced_flags` are delegation shims
- About dialog reads the package version dynamically from metadata
- Stylesheet extracted to `assets/theme.qss`
- `check_binary_help` covers all 11 tabs

### Fixed
- Picasa simple-mode album flags no longer stripped (`mode=both`)
- Duplicate config/advanced flag emission guarded (`config_emitted` + FlagEmitter dedup)
- `upload-folder` `log-level` correctly marked `config_emitted`

### Added
- Keyring availability probe and Config-tab secret storage status indicator
- Rotating GUI log at `{config_dir}/logs/immich-go-gui.log` (argv masked)
- Debounced silent connection test and coalesced status updates
- Close confirmation with Save / Discard / Cancel
- Periodic stale temp-dir cleanup timer

### Docs
- Developer guides updated for `flags.toml`; POSIX env inheritance and Python pin rationale documented

---

## [1.1.2](https://github.com/shitan198u/immich-go-gui/compare/v1.1.0...v1.1.2) - 2026-07-25

### 🐛 Bug Fixes (Windows Runtime)

* **command_builder**: auto-disable `--pause-immich-jobs` when no Admin API Key is configured — previously caused an immediate `403 Forbidden` that aborted every upload ([#64](https://github.com/shitan198u/immich-go-gui/issues/64))
* **terminal_launcher**: remove bat file self-deletion — the script deleting itself under `cmd /k` caused `The batch file cannot be found` to be printed after every run ([#68](https://github.com/shitan198u/immich-go-gui/issues/68))
* **terminal_launcher**: revert `shell=True` which caused the CMD window to be invisible — the list-form `Popen` with `CREATE_NEW_CONSOLE` correctly shows the terminal window
* **process_tracker**: lock now clears immediately when the CMD window is closed — previously the orphan heartbeat subprocess kept the lock "active" indefinitely, blocking re-uploads ([#69](https://github.com/shitan198u/immich-go-gui/issues/69))
* **binary_manager**: resolve binary path via `Path.resolve()` before `subprocess.run` to fix `Error running binary` in Binary Management on Windows ([#66](https://github.com/shitan198u/immich-go-gui/issues/66))

### 🧹 Maintenance

* Pin Python to 3.13 in CI for Nuitka build compatibility
* Add `pyfakefs>=5.5.0` as dev dependency for Windows simulation tests

---

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

## [1.0.1] - 2026-07-21

### Fixed
- Fixed PySide6 theme resolution and fusion style application.
- Improved terminal launcher error messages on Linux and macOS.

## [1.0.0] - 2026-07-21

### Added
- Initial release of Immich-Go GUI with PySide6 interface.
