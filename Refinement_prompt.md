I want you to give me a detailed guide with references to the following points for the changes which I would like to make right now:

---

### 1. Refactoring Priority & Core Improvements (Sections 33 & 27)
Follow **Section 33 (Recommended Priority List)** as the foundational roadmap (focusing on Priority 1 maintainability and Priority 2 reliability), incorporating the following specific improvements from **Section 27**:
- **Section 27.1**: Fix secret masking to handle space-separated flags (e.g., `--api-key secret` in addition to `--api-key=secret`).
- **Section 27.2**: Pass API keys/secrets via environment variables (`IMMICH_GO_UPLOAD_API_KEY`, etc.) rather than command-line `argv` flags wherever possible.
- **Section 27.3**: Normalize server URLs automatically (e.g., adding `http://` default, stripping trailing slashes).
- **Section 27.4**: Provide explicit validation feedback text rather than silently disabling UI buttons.
- **Section 27.5**: Add a binary readiness and executable permission (`os.access`) check prior to process execution.
- **Section 27.6**: Replace process-name scanning (`psutil` matching generic `immich-go`) with direct process handling.
- **Section 27.8**: Add a timeout (e.g., 2 seconds) and error handling to binary version checks.

---

### 2. Execution Strategy & Terminal Behavior (Sections 14, 19, & 27.7 Exceptions)
- **External Terminal Execution (Intentional Choice)**: Do **NOT** implement Section 27.7 (`--no-ui` flag for embedded runs) or Section 14 (replacing the terminal with an embedded `QProcess` console viewer). The GUI must continue launching an external terminal window running `immich-go` so the user gets detailed interactive TUI output and live progress.
- **Dry-Run Output**: Retain the existing dry-run implementation, as it already satisfies functional requirements.

---

### 3. Command Preview Enhancements (Section 18)
Refine the Command Preview Dialog according to Section 18 with these specific constraints:
- **Section 18.1 (Show Sections)**: Include structured preview sections displaying: Binary Path, Executable Command, Environment Variables, and active Warnings.
- **Section 18.3 (Copy Button)**: Add a Copy button, but configure it to copy **ONLY the clean executable command string** (excluding secrets and environment blocks).
- **Section 18.2 (Omit Effective Defaults)**: **Do NOT implement** Section 18.2 (listing implicit default flags), as displaying implicit defaults creates unnecessary flag clutter.

---

### 4. Testing Strategy Scope (Section 22)
Focus testing effort strictly on the following two subsections for now:
- **Section 22.1 (Backend Unit Tests)**: Unit tests for command building across all tabs, secret exclusion from `argv`, environment variable generation, path expansion, and flag ordering.
- **Section 22.2 (Golden Tests)**: Snapshot/golden tests comparing built command vectors against expected command outputs.
- *(Postpone Section 22.3, 22.4, and 22.5 for future phases).*

---

### 5. Validation Architecture Guide (Section 17)
- Provide the structural guide and validation logic specifications from **Section 17** (per-tab validation, inline messages, warning checks) as an architectural reference guide in the codebase, though active UI integration can be completed in a later phase.

---

### 6. Binary Management & Manual Version Pinning (Section 15)
Adopt the binary storage and version management concepts from Section 15 with a custom upgrade strategy:
- **Version Pinning & Manual Control**: Pin the `immich-go` binary version and store binaries in versioned directories (`~/.immich-go-gui/bin/<version>/`). Allow specifying a manual binary path (Section 15.4).
- **Release Notes Upgrade Parsing**: Instead of automated version adapters or automatic upgrades, check GitHub release notes when an update is detected. If the release notes contain terms like `"breaking changes"`, `"breaking"`, or similar indicators, automatically **disallow/block the upgrade** and prompt the user for manual verification.
