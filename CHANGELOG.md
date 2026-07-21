# Changelog

## [1.1.0](https://github.com/shitan198u/immich-go-gui/compare/v1.0.0...v1.1.0) (2026-07-21)


### Features

* add manual version input for pre-releases via workflow_dispatch ([0f2ba6f](https://github.com/shitan198u/immich-go-gui/commit/0f2ba6f68b7fe0511925788bf9b8309e02643e68))
* add portable zip and tar archives and rename binaries to Immich-Go-GUI ([45cb85e](https://github.com/shitan198u/immich-go-gui/commit/45cb85e4e7ba346bd93c95952b5f44d48ce16e30))
* Add Portable ZIP/TAR Archives & Rename Binaries ([6255a0f](https://github.com/shitan198u/immich-go-gui/commit/6255a0f97c30a1924a7e03f659383362d9b9b529))
* **cli:** enable native immich-go UI by default ([033574e](https://github.com/shitan198u/immich-go-gui/commit/033574ef67b395f24ecd640e55c51bb6536cbbf2))
* cross-platform automated packaging via Nuitka and GitHub Actions ([4f65503](https://github.com/shitan198u/immich-go-gui/commit/4f655030a193d11ad6081e1ef59651fbfe32e4ed))
* custom dynamic svg icons for theming ([8337003](https://github.com/shitan198u/immich-go-gui/commit/83370032cedc00e5d941fe0e97fbf4bfb9dec8ec))
* implement flatpak packaging using native flatpak-builder ([00b16a6](https://github.com/shitan198u/immich-go-gui/commit/00b16a629a07ecb1c3207d9a561985903423d514))
* robust process tracking using psutil ([6995514](https://github.com/shitan198u/immich-go-gui/commit/69955148e24c614e2da806452fa74d78183312ed))


### Bug Fixes

* **ci:** add windows metadata and .exe icon injection ([4234f0d](https://github.com/shitan198u/immich-go-gui/commit/4234f0ddfc494d05426730be52d43e9e05a2910f))
* **cli:** correct command argument ordering and --no-ui flag handling ([e472e77](https://github.com/shitan198u/immich-go-gui/commit/e472e775c99cd127ec01491ec13346603ea5e5d2))
* convert _build_config_tab to new native component structure ([9b516d7](https://github.com/shitan198u/immich-go-gui/commit/9b516d7619bca3e43f042879d926005fab98a64e))
* ensure inno setup outputs to github workspace ([3f7fd6c](https://github.com/shitan198u/immich-go-gui/commit/3f7fd6c6fd9b8619d84734f787ace335d3911521))
* explicitly specify flatpak sources to bypass gitignore exclusion of app.dist ([049801d](https://github.com/shitan198u/immich-go-gui/commit/049801d42ced1d174df1303da3eaa466e139896e))
* flatpak sandbox issues (mkdir bin, patch desktop Exec, update runtime) ([b94bb3c](https://github.com/shitan198u/immich-go-gui/commit/b94bb3cfe9b1094611c91d7ababb20d7045cc009))
* Icon mismatch build fail ([2704432](https://github.com/shitan198u/immich-go-gui/commit/27044328bfcdab216f473dc61b69ecec86e0f2ae))
* pin setup-nfpm version to fix broken latest tag resolution ([2d29e1e](https://github.com/shitan198u/immich-go-gui/commit/2d29e1e97b03234bec016d33b01be634cf35877c))
* replace broken nfpm action with native bash installation ([b2e6e0a](https://github.com/shitan198u/immich-go-gui/commit/b2e6e0a64fd8bf7b2ec30a650ee1cd581aaee5e7))
* resize flatpak icon to 512x512 and patch desktop file Icon ([587922d](https://github.com/shitan198u/immich-go-gui/commit/587922d067bdb6b721edddd588687353fc7cf409))
* resolve permission denied error for installer builds by downloading binary to user home directory ([45ee1f1](https://github.com/shitan198u/immich-go-gui/commit/45ee1f1e398c47e3480e11337543d8db6d8ecfa9))
* resolve permission denied error for installer builds by downloading binary to user home directory ([4369e57](https://github.com/shitan198u/immich-go-gui/commit/4369e57e53c6dc27185ff40ddd908be492917f62))
* resolve permission denied error on installer builds ([1ec5068](https://github.com/shitan198u/immich-go-gui/commit/1ec5068da9ba18d9d9d5eca897279a72d7da75aa))
* specify windows release to use bash shell ([063df55](https://github.com/shitan198u/immich-go-gui/commit/063df5535dab21d624c83d9543aa82a360209041))
* UI changes before qwen plan ([1d98bb7](https://github.com/shitan198u/immich-go-gui/commit/1d98bb79732c0f79d44077bc5aa523a4a95b54a1))
* **ui:** correct binary status checks for eliding labels ([50974ff](https://github.com/shitan198u/immich-go-gui/commit/50974ffaa2d15b9df570667699d31a3105e3a4b8))
* **ui:** correct folder icon assignment in Archive Server tab ([ed68ac9](https://github.com/shitan198u/immich-go-gui/commit/ed68ac9d30ea01fb5eb38914dce36e8de036d90a))
* **ui:** expand BasePage container for uniform tab widths ([50cd140](https://github.com/shitan198u/immich-go-gui/commit/50cd1408306787d8d8d2f0b82e9cba19f28ede08))
* **ui:** prevent TypeError on QListView.update() in theme engine ([df917dc](https://github.com/shitan198u/immich-go-gui/commit/df917dc11567cf050e418b29026ae6424a799900))
* **ui:** Track 1 - UI sizing & right-edge clipping ([6a3ec41](https://github.com/shitan198u/immich-go-gui/commit/6a3ec41274de367d49fb24f678e2313ecfae90ec))
* **ui:** Track 2 - Icons and Status Indicators (No Emoji) ([f3577b6](https://github.com/shitan198u/immich-go-gui/commit/f3577b6a38afb0d997d8308464ef9d0a7b27eb94))
* use official goreleaser-action to install nfpm dynamically ([98ace6f](https://github.com/shitan198u/immich-go-gui/commit/98ace6f42a00fc8fff16047c5afc62b43f5cf848))
* use powershell for windows portable archive since zip is not in path ([4aacaba](https://github.com/shitan198u/immich-go-gui/commit/4aacaba30d2a5d79d9db78ecf2fbb4f301e359aa))
* use test- prefix for manual build tags so release-please ignores them ([ea9aa59](https://github.com/shitan198u/immich-go-gui/commit/ea9aa59f4242e8b47bfbe96bfd2c759a1bb579d5))


### Documentation

* add contribution guidelines and issue/PR templates ([8b68856](https://github.com/shitan198u/immich-go-gui/commit/8b68856e732fd4369bf986e3b8d205de4743c523))
* add workflow_dispatch and GitHub Actions documentation ([9dfaaea](https://github.com/shitan198u/immich-go-gui/commit/9dfaaea1d7f39927262e413af8079bf2a7a4eae9))
* clarify windows defender false positive in README ([eeaca49](https://github.com/shitan198u/immich-go-gui/commit/eeaca499be4c47a73163c9ca82e24a65ae5cce51))

## [1.0.0](https://github.com/shitan198u/immich-go-gui/compare/v0.9.4...v1.0.0) (2026-07-21)


### Features

* **cli:** enable native immich-go UI by default ([033574e](https://github.com/shitan198u/immich-go-gui/commit/033574ef67b395f24ecd640e55c51bb6536cbbf2))
* custom dynamic svg icons for theming ([8337003](https://github.com/shitan198u/immich-go-gui/commit/83370032cedc00e5d941fe0e97fbf4bfb9dec8ec))
* robust process tracking using psutil ([6995514](https://github.com/shitan198u/immich-go-gui/commit/69955148e24c614e2da806452fa74d78183312ed))
* **UI:** migrate app.py to new architecture and expand test suite ([f47355b](https://github.com/shitan198u/immich-go-gui/commit/f47355b))


### Refactoring

* **UI:** modularize theme engine and fix syntax errors ([584d9b2](https://github.com/shitan198u/immich-go-gui/commit/584d9b2))
* **UI:** transition to dynamic semantic token theme engine (Fusion) ([c4eb2e4](https://github.com/shitan198u/immich-go-gui/commit/c4eb2e4))
* **UI:** Phase 2 - Refinement and Validation ([466b94b](https://github.com/shitan198u/immich-go-gui/commit/466b94b))
* **UI:** Phase 1 - Core Architecture ([7f2e4d6](https://github.com/shitan198u/immich-go-gui/commit/7f2e4d6))
* **UI:** Phase 0 - Critical Bug Fixes for layout striping ([66c55c4](https://github.com/shitan198u/immich-go-gui/commit/66c55c4))
* **UI:** cleanup temporary migration scripts and update UI stylesheet ([eb58b69](https://github.com/shitan198u/immich-go-gui/commit/eb58b69))


### Bug Fixes

* **cli:** correct command argument ordering and --no-ui flag handling ([e472e77](https://github.com/shitan198u/immich-go-gui/commit/e472e775c99cd127ec01491ec13346603ea5e5d2))
* resolve permission denied error for installer builds by downloading binary to user home directory ([45ee1f1](https://github.com/shitan198u/immich-go-gui/commit/45ee1f1e398c47e3480e11337543d8db6d8ecfa9))
* **ui:** prevent TypeError on QListView.update() in theme engine ([df917dc](https://github.com/shitan198u/immich-go-gui/commit/df917dc))
* **ui:** correct folder icon assignment in Archive Server tab ([ed68ac9](https://github.com/shitan198u/immich-go-gui/commit/ed68ac9))
* **ui:** expand BasePage container for uniform tab widths ([50cd140](https://github.com/shitan198u/immich-go-gui/commit/50cd140))
* **ui:** correct binary status checks for eliding labels ([50974ff](https://github.com/shitan198u/immich-go-gui/commit/50974ff))
* **ui:** Track 2 - Icons and Status Indicators (No Emoji) ([f3577b6](https://github.com/shitan198u/immich-go-gui/commit/f3577b6))
* **ui:** Track 1 - UI sizing & right-edge clipping ([6a3ec41](https://github.com/shitan198u/immich-go-gui/commit/6a3ec41))
* **ui:** UI changes before qwen plan ([1d98bb7](https://github.com/shitan198u/immich-go-gui/commit/1d98bb7))
* **ui:** convert _build_config_tab to new native component structure ([9b516d7](https://github.com/shitan198u/immich-go-gui/commit/9b516d7))

## [0.9.4](https://github.com/shitan198u/immich-go-gui/compare/v0.9.3...v0.9.4) (2026-07-20)


### Bug Fixes

* resolve permission denied error for installer builds by downloading binary to user home directory ([4369e57](https://github.com/shitan198u/immich-go-gui/commit/4369e57e53c6dc27185ff40ddd908be492917f62))
* resolve permission denied error on installer builds ([1ec5068](https://github.com/shitan198u/immich-go-gui/commit/1ec5068da9ba18d9d9d5eca897279a72d7da75aa))

## [0.9.3](https://github.com/shitan198u/immich-go-gui/compare/v0.9.2...v0.9.3) (2026-07-20)


### Bug Fixes

* **ci:** add windows metadata and .exe icon injection ([4234f0d](https://github.com/shitan198u/immich-go-gui/commit/4234f0ddfc494d05426730be52d43e9e05a2910f))
* ensure inno setup outputs to github workspace ([3f7fd6c](https://github.com/shitan198u/immich-go-gui/commit/3f7fd6c6fd9b8619d84734f787ace335d3911521))
* specify windows release to use bash shell ([063df55](https://github.com/shitan198u/immich-go-gui/commit/063df5535dab21d624c83d9543aa82a360209041))
* use test- prefix for manual build tags so release-please ignores them ([ea9aa59](https://github.com/shitan198u/immich-go-gui/commit/ea9aa59f4242e8b47bfbe96bfd2c759a1bb579d5))


### Documentation

* clarify windows defender false positive in README ([eeaca49](https://github.com/shitan198u/immich-go-gui/commit/eeaca499be4c47a73163c9ca82e24a65ae5cce51))
