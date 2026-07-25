# Glossary

Terms used throughout Immich-Go GUI documentation and the immich-go ecosystem.

| Term | Meaning |
|------|---------|
| **Immich** | Self-hosted photo and video backup platform. The server this GUI talks to. |
| **immich-go** | Community CLI that bulk-uploads, archives, and stacks media for Immich. The GUI launches this binary. |
| **Immich-Go GUI** | This project — a PySide6 desktop front-end for immich-go. |
| **Upload** | Workflow that **sends** media **to** an Immich server. |
| **Archive** | Workflow that **writes** media **to a local folder** (or downloads from Immich to disk). |
| **Stack** | Group related assets on Immich (burst sequences, RAW+JPEG pairs, HEIC+JPEG, etc.). |
| **Serverless tab** | Archive tab that never contacts Immich and never emits server/API flags. |
| **Server-required tab** | Tab that needs Immich credentials (all upload tabs, Stack, Archive from Immich). |
| **Profile** | Named set of settings + secrets (server URL, theme, form state, API keys). |
| **form_state** | Per-tab saved field values inside `config.toml`. |
| **Advanced mode** | Config toggle that reveals extra immich-go flags on workflow tabs. |
| **Command preview** | Read-only view of the argv that will run, with secrets masked. |
| **CommandPlan** | Internal object: argv + env + display argv + validation errors/warnings. |
| **Dry run** | immich-go mode that simulates actions without applying changes. |
| **Pre-flight check** | GUI HTTP check to `{server}/api/server/about` before launching server jobs. |
| **API key** | Immich user access token used for normal library operations. |
| **Admin API key** | Elevated Immich key needed for job-pausing and some admin operations. |
| **Keyring** | OS secret store (Keychain / Credential Manager / Secret Service). |
| **Takeout** | Google account export archive (often used for Google Photos migrations). |
| **iCloud export** | Local export of an iCloud Photos library used as an import source. |
| **Picasa** | Legacy Google Photos / Picasa Web Albums export layout. |
| **TAB key** | Stable internal id such as `upload-folder` or `archive-gp` (not the keyboard key). |
| **Allowlist** | Per-tab set of CLI flags the GUI is allowed to emit (`TAB_ALLOWED_FLAGS`). |
| **Golden fixture** | Checked-in expected command state used by tests. |
| **Process lock** | File under `{config_dir}/locks/` preventing concurrent GUI-launched jobs. |
| **Nuitka** | Python compiler used to produce standalone release binaries. |
| **Release Please** | Automation that versions the project and updates `CHANGELOG.md` from conventional commits. |
| **staging / master** | Development vs production branches; PRs target `staging`. |
| **SHA256 verification** | Checksum validation when downloading immich-go releases. |
| **Skip SSL verification** | Disables TLS certificate validation — lab/self-signed only. |

## Related

- [Choose Your Workflow](choose-your-workflow.md)
- [CLI Command Mapping](../reference/cli-command-mapping.md)
- [Architecture](../developer-guide/architecture.md)
