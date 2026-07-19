# Changelog

## [1.1.0-test](https://github.com/shitan198u/immich-go-gui/compare/v1.0.0-test...v1.1.0-test) (2026-07-19)


### Features

* add manual version input for pre-releases via workflow_dispatch ([0f2ba6f](https://github.com/shitan198u/immich-go-gui/commit/0f2ba6f68b7fe0511925788bf9b8309e02643e68))
* add portable zip and tar archives and rename binaries to Immich-Go-GUI ([45cb85e](https://github.com/shitan198u/immich-go-gui/commit/45cb85e4e7ba346bd93c95952b5f44d48ce16e30))
* Add Portable ZIP/TAR Archives & Rename Binaries ([6255a0f](https://github.com/shitan198u/immich-go-gui/commit/6255a0f97c30a1924a7e03f659383362d9b9b529))
* implement flatpak packaging using native flatpak-builder ([00b16a6](https://github.com/shitan198u/immich-go-gui/commit/00b16a629a07ecb1c3207d9a561985903423d514))


### Bug Fixes

* explicitly specify flatpak sources to bypass gitignore exclusion of app.dist ([049801d](https://github.com/shitan198u/immich-go-gui/commit/049801d42ced1d174df1303da3eaa466e139896e))
* flatpak sandbox issues (mkdir bin, patch desktop Exec, update runtime) ([b94bb3c](https://github.com/shitan198u/immich-go-gui/commit/b94bb3cfe9b1094611c91d7ababb20d7045cc009))
* pin setup-nfpm version to fix broken latest tag resolution ([2d29e1e](https://github.com/shitan198u/immich-go-gui/commit/2d29e1e97b03234bec016d33b01be634cf35877c))
* replace broken nfpm action with native bash installation ([b2e6e0a](https://github.com/shitan198u/immich-go-gui/commit/b2e6e0a64fd8bf7b2ec30a650ee1cd581aaee5e7))
* resize flatpak icon to 512x512 and patch desktop file Icon ([587922d](https://github.com/shitan198u/immich-go-gui/commit/587922d067bdb6b721edddd588687353fc7cf409))
* use official goreleaser-action to install nfpm dynamically ([98ace6f](https://github.com/shitan198u/immich-go-gui/commit/98ace6f42a00fc8fff16047c5afc62b43f5cf848))
* use powershell for windows portable archive since zip is not in path ([4aacaba](https://github.com/shitan198u/immich-go-gui/commit/4aacaba30d2a5d79d9db78ecf2fbb4f301e359aa))
