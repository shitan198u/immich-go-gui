# Detailed Implementation Guide — Immich-Go GUI Refactoring

This guide is scoped to the changes you want to make **right now**, organized into six workstreams. Each section references the architectural sections from the earlier improvement guide and maps them to concrete locations in your current codebase (`app.py`, `test_app.py`, `theme.py`, `immich_go_gui_config.toml`, and `Immich-go_cli_doc.md`).

---

## 0. Scope Summary & Phase Mapping

| Workstream | Source Sections | Priority (per §33) | Status |
|---|---|---|---|
| Core refactoring & §27 fixes | §33 P1/P2, §27.1–27.6, §27.8 | **Priority 1 + 2** | Implement now |
| External terminal execution | §14, §19, §27.7 | — | **Intentionally excluded** |
| Command preview enhancements | §18.1, §18.3 | Priority 5 (pulled forward) | Implement now |
| Testing (backend + golden) | §22.1, §22.2 | Priority 1 | Implement now |
| Validation architecture guide | §17 | Priority 5 | **Reference doc only** |
| Binary management & pinning | §15 | Priority 4 | Implement now |

**Explicitly excluded from this phase:**
- §14 (embedded `QProcess` console)
- §19 (embedded dry-run output viewer)
- §27.7 (`--no-ui` flag injection)
- §18.2 (effective defaults display)
- §22.3 (version adapter tests), §22.4 (runner tests), §22.5 (GUI tests beyond existing)
- Versioned CLI adapters / capability profiles (deferred)

---

## 1. Refactoring Priority & Core Improvements (§33 + §27)

### 1.1 Foundational Roadmap (§33)

Follow the priority ordering from §33, but scoped to what you are doing now:

**Priority 1 — Critical Maintainability (do first):**
1. Extract pure logic out of `ImmichGoGUI` into module-level functions or a small backend namespace.
2. Introduce a `CommandPlan` data structure.
3. Remove secrets from `argv` (§27.2).
4. Add backend unit tests for all tabs (§22.1).
5. Add golden command tests (§22.2).

**Priority 2 — Reliability (do second):**
6. Replace `psutil` process-name scanning with direct process tracking (§27.6).
7. Add binary readiness check before execution (§27.5).
8. Harden binary version check with timeout and error handling (§27.8).
9. Add explicit validation feedback (§27.4).

**Priority 4 — Binary Management (do third):**
10. Versioned binary directories (§15).
11. Manual binary path (§15.4).
12. Release-notes-based upgrade gating (§15 custom).

---

### 1.2 §27.1 — Fix Secret Masking for Space-Separated Flags

**Current problem in `app.py`:**

```python
def mask_command_for_display(command_parts: list[str]) -> list[str]:
    masked = []
    # BUG: trailing spaces in flag names
    secret_flags = { "--api-key ",  "--from-api-key ",  "--admin-api-key "}
    for part in command_parts:
        hidden = False
        for flag in secret_flags:
            # BUG: f"{flag}= " has trailing space, will never match "--api-key=secret"
            if part.startswith(f"{flag}= "):
                masked.append(f"{flag}=******** ")
                hidden = True
                break
        if not hidden:
            masked.append(part)
    return masked
```

This has two bugs:
1. Trailing spaces in the flag set mean `part.startswith(f"{flag}= ")` checks for `"--api-key = "` which never matches `"--api-key=secret"`.
2. It does not handle the space-separated form `--api-key secret` (two list elements).

**Target implementation:**

```python
def mask_command_for_display(command_parts: list[str]) -> list[str]:
    """Obfuscates secrets in command previews.

    Handles both forms:
      --api-key=secret   (single element)
      --api-key secret   (two elements)
    """
    masked = []
    secret_flags = {"--api-key", "--from-api-key", "--admin-api-key"}

    skip_next = False
    for part in command_parts:
        if skip_next:
            # This element is the value following a bare secret flag
            masked.append("********")
            skip_next = False
            continue

        # Case 1: bare flag, value is next element
        if part in secret_flags:
            masked.append(part)
            skip_next = True
            continue

        # Case 2: --flag=value in a single element
        hidden = False
        for flag in secret_flags:
            if part.startswith(f"{flag}="):
                masked.append(f"{flag}=********")
                hidden = True
                break

        if not hidden:
            masked.append(part)

    return masked
```

**Test updates in `test_app.py`:**

The existing tests use trailing-space strings (e.g., `"--api-key=super_secret_123 "`). These need to be cleaned up to match real command output:

```python
def test_mask_command_for_display():
    cmd = [
        "immich-go", "upload", "from-folder",
        "--server=http://local", "--api-key=super_secret_123", "/photos"
    ]
    masked = mask_command_for_display(cmd)
    assert "--api-key=super_secret_123" not in masked
    assert "--api-key=********" in masked
    assert "--server=http://local" in masked


def test_mask_command_space_separated():
    """NEW: handle --api-key secret as two elements."""
    cmd = ["immich-go", "upload", "from-folder", "--api-key", "super_secret", "/photos"]
    masked = mask_command_for_display(cmd)
    assert "super_secret" not in masked
    assert "********" in masked
    assert "--api-key" in masked


def test_mask_command_from_api_key():
    cmd = ["immich-go", "upload", "from-immich", "--from-api-key=old_secret"]
    masked = mask_command_for_display(cmd)
    assert "--from-api-key=********" in masked


def test_mask_command_admin_api_key():
    cmd = ["immich-go", "stack", "--admin-api-key=ADMIN_SECRET"]
    masked = mask_command_for_display(cmd)
    assert "ADMIN_SECRET" not in masked
    assert "--admin-api-key=********" in masked
```

---

### 1.3 §27.2 — Pass Secrets via Environment Variables, Not `argv`

**Current problem in `app.py` `build_command()`:**

```python
if tab_key != "archive-folder":
    srv = self.inputs["config"]["server"].text()
    api = self.inputs["config"]["api_key"].text()
    if srv:
        cmd_opts.append(f"--server={srv}")
    if api:
        cmd_opts.append(f"--api-key={api}")       # ← secret in argv
```

And for `upload-immich`:

```python
if c["from-api-key"].text():
    cmd_opts.append(f"--from-api-key={c['from-api-key'].text()}")  # ← secret in argv
```

Then `run_command()` strips them after the fact:

```python
# Strip --api-key / --from-api-key from CLI args (they go via env)
clean_parts = []
skip_next = False
for part in command_parts:
    ...
```

This is fragile: the secret is in the list, gets masked for preview, then stripped for execution. If any code path forgets to strip, the secret leaks.

**Target approach:**

Introduce a `CommandPlan` dataclass. The builder never puts secrets into `argv`. Secrets go into `env` from the start.

```python
from dataclasses import dataclass, field


@dataclass
class CommandPlan:
    """Represents a fully resolved immich-go execution plan."""
    argv: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    display_argv: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tab_key: str = ""
    dry_run: bool = False
    binary_path: str = ""
```

**Refactored `build_command` → `build_plan`:**

The key change: `--server` stays in `argv` (it is not a secret), but `--api-key` and `--from-api-key` are **never added to `argv`**. They go into `env` only.

```python
def build_plan(self, dry_run: bool) -> CommandPlan:
    tab_key = self._get_active_tab_key()
    if tab_key == "config":
        return CommandPlan(errors=["No executable tab selected."], tab_key=tab_key)

    c = self.inputs[tab_key]
    plan = CommandPlan(tab_key=tab_key, dry_run=dry_run,
                       binary_path=getattr(self, "binary_path", "./immich-go"))

    global_opts = []
    cmd = []
    cmd_opts = []
    path_opt = []
    env = os.environ.copy()

    # --- Log level (global, before command) ---
    if "log-level" in c and c["log-level"].currentText() != "INFO":
        global_opts.append(f"--log-level={c['log-level'].currentText()}")

    # --- Command name ---
    cmd = self._resolve_command_name(tab_key)

    # --- Server connection (non-secret parts in argv, secrets in env) ---
    if tab_key != "archive-folder":
        srv = normalize_server_url(self.inputs["config"]["server"].text())
        api = self.inputs["config"]["api_key"].text().strip()

        if srv:
            cmd_opts.append(f"--server={srv}")

        # Secret → env only, never argv
        if api:
            env_key = self._env_key_for_tab(tab_key, "api_key")
            if env_key:
                env[env_key] = api

        if self.inputs["config"]["skip-ssl"].isChecked():
            cmd_opts.append("--skip-verify-ssl")
            plan.warnings.append(
                "SSL verification is disabled. "
                "Use only on trusted networks or self-hosted test servers."
            )

    # --- upload-immich source secrets → env only ---
    if tab_key == "upload-immich":
        from_srv = normalize_server_url(c["from-server"].text())
        from_api = c["from-api-key"].text().strip()
        if from_srv:
            cmd_opts.append(f"--from-server={from_srv}")
            env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_SERVER"] = from_srv
        if from_api:
            # Secret → env only
            env["IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY"] = from_api

    # ... (rest of flag building stays the same, minus any --api-key lines) ...

    if dry_run and "--dry-run" not in cmd_opts:
        cmd_opts.append("--dry-run")

    plan.argv = global_opts + cmd + cmd_opts + path_opt
    plan.env = env
    plan.display_argv = mask_command_for_display(
        [plan.binary_path] + plan.argv
    )
    return plan
```

**Helper for env key mapping:**

```python
_ENV_KEY_MAP = {
    "upload-folder":   {"server": "IMMICH_GO_UPLOAD_SERVER",
                        "api_key": "IMMICH_GO_UPLOAD_API_KEY"},
    "upload-gp":       {"server": "IMMICH_GO_UPLOAD_SERVER",
                        "api_key": "IMMICH_GO_UPLOAD_API_KEY"},
    "upload-immich":   {"server": "IMMICH_GO_UPLOAD_SERVER",
                        "api_key": "IMMICH_GO_UPLOAD_API_KEY"},
    "archive-immich":  {"server": "IMMICH_GO_ARCHIVE_SERVER",
                        "api_key": "IMMICH_GO_ARCHIVE_API_KEY"},
    "stack":           {"server": "IMMICH_GO_STACK_SERVER",
                        "api_key": "IMMICH_GO_STACK_API_KEY"},
}

def _env_key_for_tab(self, tab_key: str, kind: str) -> str | None:
    return _ENV_KEY_MAP.get(tab_key, {}).get(kind)
```

> **Reference:** `Immich-go_cli_doc.md` §10 confirms the environment variable naming pattern:
> `IMMICH_GO_<COMMAND>[_<SUBCOMMAND>]_<OPTION_NAME>`
> e.g., `IMMICH_GO_UPLOAD_API_KEY`, `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY`, `IMMICH_GO_ARCHIVE_SERVER`, `IMMICH_GO_STACK_API_KEY`.

**`run_command` simplification:**

Since secrets are never in `argv`, the stripping loop is no longer needed:

```python
def run_command(self, plan: CommandPlan):
    # No stripping needed — plan.argv never contained secrets
    command = [plan.binary_path] + plan.argv
    env = plan.env
    # ... launch external terminal with env ...
```

**New test (§22.1):**

```python
def test_api_key_never_in_argv(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("super_secret_key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(dry_run=False)

    # Secret must NOT appear anywhere in argv
    for part in plan.argv:
        assert "super_secret_key" not in part
        assert "--api-key" not in part

    # Secret MUST appear in env
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "super_secret_key"


def test_from_api_key_never_in_argv(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new_key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old_secret")

    plan = gui.build_plan(dry_run=False)

    for part in plan.argv:
        assert "old_secret" not in part
        assert "--from-api-key" not in part

    assert plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY") == "old_secret"
```

---

### 1.4 §27.3 — Normalize Server URLs

**Current problem:** Users may type `localhost:2283`, `http://localhost:2283/`, or `https://photos.example.com/`. The current code passes whatever the user typed directly into `--server=`.

**Add a pure utility function:**

```python
def normalize_server_url(url: str) -> str:
    """Normalize a server URL for CLI consumption.

    - Strips leading/trailing whitespace
    - Adds http:// if no scheme is present
    - Strips trailing slashes
    - Returns empty string for empty input
    """
    url = url.strip()
    if not url:
        return ""

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    return url.rstrip("/")
```

**Where to apply it:**

In `build_plan()`, every place that reads a server URL:

```python
srv = normalize_server_url(self.inputs["config"]["server"].text())
# ...
from_srv = normalize_server_url(c["from-server"].text())
```

Also in `build_environment()` (the standalone function) and `validate_inputs()`.

**Tests (§22.1):**

```python
def test_normalize_server_url_adds_scheme():
    assert normalize_server_url("localhost:2283") == "http://localhost:2283"

def test_normalize_server_url_strips_trailing_slash():
    assert normalize_server_url("http://localhost:2283/") == "http://localhost:2283"

def test_normalize_server_url_preserves_https():
    assert normalize_server_url("https://photos.example.com/") == "https://photos.example.com"

def test_normalize_server_url_empty():
    assert normalize_server_url("") == ""
    assert normalize_server_url("   ") == ""
```

---

### 1.5 §27.4 — Explicit Validation Feedback

**Current problem in `app.py`:**

```python
def validate_inputs(self):
    srv_edit = self.inputs.get("config", {}).get("server")
    api_edit = self.inputs.get("config", {}).get("api_key")
    srv = srv_edit.text() if srv_edit else ""
    api = api_edit.text() if api_edit else ""
    if not re.match(r"^https?://.+", srv) or not api:
        return False
    return True
```

And in `update_status()`:

```python
if self.validate_inputs():
    self.status_card.set_server("ok", "Server: Ready")
    if not is_running:
        self.btn_run.setEnabled(True)
        self.btn_dry_run.setEnabled(True)
else:
    self.status_card.set_server("err", "Server: Not Set")
    if not is_running:
        self.btn_run.setEnabled(False)
        self.btn_dry_run.setEnabled(False)
```

The user gets no indication of **why** the button is disabled.

**Target: return structured validation results.**

```python
@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
```

**Refactored `validate_inputs`:**

```python
def validate_inputs(self) -> ValidationResult:
    result = ValidationResult()
    tab_key = self._get_active_tab_key()

    # --- Global checks (all tabs except config) ---
    if tab_key != "config":
        srv = self.inputs.get("config", {}).get("server")
        api = self.inputs.get("config", {}).get("api_key")
        srv_text = normalize_server_url(srv.text()) if srv else ""
        api_text = api.text().strip() if api else ""

        if not srv_text:
            result.errors.append("Server URL is required.")
        elif not re.match(r"^https?://.+", srv_text):
            result.errors.append("Server URL must start with http:// or https://.")

        # archive-folder does not need server/api
        if tab_key != "archive-folder" and not api_text:
            result.errors.append("API key is required.")

        if self.inputs["config"]["skip-ssl"].isChecked():
            result.warnings.append(
                "SSL verification is disabled. "
                "Use only on trusted networks."
            )

    # --- Per-tab checks (see §5 for full spec) ---
    if tab_key == "upload-folder":
        if not self.inputs["upload-folder"]["path"].text().strip():
            result.errors.append("Source folder or ZIP path is required.")

    elif tab_key == "upload-gp":
        if not self.inputs["upload-gp"]["path"].toPlainText().strip():
            result.errors.append("Google Takeout source is required.")

    elif tab_key == "upload-immich":
        if not self.inputs["upload-immich"]["from-server"].text().strip():
            result.errors.append("Source server URL is required.")
        if not self.inputs["upload-immich"]["from-api-key"].text().strip():
            result.errors.append("Source API key is required.")

    elif tab_key == "archive-folder":
        if not self.inputs["archive-folder"]["path"].text().strip():
            result.errors.append("Source path is required.")
        if not self.inputs["archive-folder"]["write-to"].text().strip():
            result.errors.append("Destination folder is required.")

    elif tab_key == "archive-immich":
        if not self.inputs["archive-immich"]["write-to"].text().strip():
            result.errors.append("Destination folder is required.")

    return result
```

**UI integration in `update_status()`:**

```python
def update_status(self):
    is_running = getattr(self, "running_process", None) is not None
    validation = self.validate_inputs()

    if is_running:
        self.lbl_running_warning.setVisible(True)
        self.btn_run.setEnabled(False)
        self.btn_dry_run.setEnabled(False)
    else:
        self.lbl_running_warning.setVisible(False)

    if validation.is_valid:
        self.status_card.set_server("ok", "Server: Ready")
        if not is_running:
            self.btn_run.setEnabled(True)
            self.btn_dry_run.setEnabled(True)
    else:
        # Show the FIRST error as the status message
        first_error = validation.errors[0] if validation.errors else "Server: Not Set"
        self.status_card.set_server("err", f"Server: {first_error}")
        if not is_running:
            self.btn_run.setEnabled(False)
            self.btn_dry_run.setEnabled(False)

    # Update target-server mirrors
    srv_edit = self.inputs.get("config", {}).get("server")
    srv = normalize_server_url(srv_edit.text()) if srv_edit else ""
    for t in ["archive-immich", "stack"]:
        if t in self.inputs and "target-server" in self.inputs[t]:
            self.inputs[t]["target-server"].setText(srv if srv else "Not Configured")
```

> **Note:** Full inline validation labels per field are deferred. For now, the `StatusCard` text and the preview dialog warnings carry the feedback. The full §17 architecture is documented in §5 below as a reference for a later phase.

---

### 1.6 §27.5 — Binary Readiness Check Before Execution

**Current problem in `app.py` `run_command()`:**

```python
if not hasattr(self, "binary_path") or not os.path.exists(self.binary_path):
    if not self.update_binary():
        QMessageBox.critical(...)
        return
```

This checks existence but not executability.

**Add a dedicated check function:**

```python
def check_binary_ready(self) -> tuple[bool, str]:
    """Check that the binary exists and is executable.

    Returns (is_ready, message).
    """
    if not hasattr(self, "binary_path") or not self.binary_path:
        return False, "Binary path is not configured."

    if not os.path.exists(self.binary_path):
        return False, f"Binary not found at: {self.binary_path}"

    if not os.path.isfile(self.binary_path):
        return False, f"Binary path is not a file: {self.binary_path}"

    # On Unix, check executable permission
    if not sys.platform.startswith("win"):
        if not os.access(self.binary_path, os.X_OK):
            return False, (
                f"Binary is not executable: {self.binary_path}\n"
                "Run: chmod +x " + shlex.quote(self.binary_path)
            )

    return True, "Binary ready."
```

**Use it in `run_command()` and `show_confirm_dialog()`:**

```python
def show_confirm_dialog(self, is_dry_run):
    if self.stacked_widget.currentIndex() == 0:
        return

    # Binary readiness gate
    ready, msg = self.check_binary_ready()
    if not ready:
        reply = QMessageBox.question(
            self, "Binary Not Ready",
            f"{msg}\n\nDo you want to download it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.update_binary(force_download=True)
            ready, msg = self.check_binary_ready()
            if not ready:
                QMessageBox.critical(self, "Error", msg)
                return
        else:
            return

    plan = self.build_plan(dry_run=is_dry_run)
    # ... show preview dialog ...
```

---

### 1.7 §27.6 — Replace `psutil` Process-Name Scanning

**Current problem in `app.py`:**

```python
def check_if_process_running(self):
    still_running = False
    if getattr(self, "immich_go_pid", None) is not None:
        if psutil.pid_exists(self.immich_go_pid):
            still_running = True
    else:
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name'].lower()
                if 'immich-go' in name:       # ← matches ANY process with "immich-go" in name
                    still_running = True
                    self.immich_go_pid = proc.pid
                    break
            except ...
```

This can match unrelated processes (e.g., a text editor with `immich-go` in the window title, another GUI instance, a grep command).

**Target: lock-file-based tracking.**

Since you are keeping external terminal execution (§2), you cannot get a direct `QProcess` handle. Instead, use a **lock file** that the launched command creates on start and removes on exit.

**Implementation:**

```python
import tempfile
import uuid

class ProcessTracker:
    """Tracks an externally-launched immich-go process via a lock file."""

    def __init__(self):
        self._lock_dir = os.path.join(
            tempfile.gettempdir(), "immich-go-gui"
        )
        os.makedirs(self._lock_dir, exist_ok=True)
        self._lock_path: str | None = None

    @property
    def is_running(self) -> bool:
        if self._lock_path is None:
            return False
        return os.path.exists(self._lock_path)

    def create_lock(self) -> str:
        """Create a lock file and return its path."""
        run_id = uuid.uuid4().hex[:12]
        self._lock_path = os.path.join(self._lock_dir, f"run-{run_id}.lock")
        with open(self._lock_path, "w") as f:
            f.write(str(os.getpid()))  # GUI PID, for debugging
        return self._lock_path

    def release_lock(self):
        if self._lock_path and os.path.exists(self._lock_path):
            try:
                os.remove(self._lock_path)
            except OSError:
                pass
        self._lock_path = None

    def wrap_command_with_lock(self, command_str: str) -> str:
        """Wrap a shell command so it removes the lock file on exit."""
        if self._lock_path is None:
            return command_str
        lock = self._lock_path
        # The trap ensures cleanup even on Ctrl+C / kill
        return (
            f"trap 'rm -f {shlex.quote(lock)}' EXIT INT TERM; "
            f"{command_str}; "
            f"rm -f {shlex.quote(lock)}"
        )
```

**Integration in `run_command()`:**

```python
def run_command(self, plan: CommandPlan):
    ready, msg = self.check_binary_ready()
    if not ready:
        QMessageBox.critical(self, "Error", msg)
        return

    command = [plan.binary_path] + plan.argv
    env = plan.env

    # Create lock file
    self.process_tracker = ProcessTracker()
    lock_path = self.process_tracker.create_lock()

    try:
        self.btn_run.setDisabled(True)
        self.btn_dry_run.setDisabled(True)

        if sys.platform.startswith("win"):
            cmd_string = subprocess.list2cmdline(command)
            # Windows: use a batch wrapper to clean up lock
            bat_content = (
                f"@echo off\n"
                f"{cmd_string}\n"
                f'del /f "{lock_path}" 2>nul\n'
            )
            bat_path = lock_path.replace(".lock", ".bat")
            with open(bat_path, "w") as f:
                f.write(bat_content)
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", bat_path],
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                env=env,
            )
        elif sys.platform.startswith("darwin"):
            cmd_str = shlex.join(command)
            wrapped = self.process_tracker.wrap_command_with_lock(cmd_str)
            apple_script = (
                'tell application "Terminal" to do script '
                f'"{wrapped}; exec bash"'
            )
            subprocess.Popen(["osascript", "-e", apple_script], env=env)
        else:
            cmd_str = shlex.join(command)
            wrapped = self.process_tracker.wrap_command_with_lock(cmd_str)
            terminals = [
                ("gnome-terminal", "--", "bash", "-c", f"{wrapped}; exec bash"),
                ("konsole", "-e", "bash", "-c", f"{wrapped}; exec bash"),
                ("xfce4-terminal", "-e", "bash", "-c", f"{wrapped}; exec bash"),
                ("xterm", "-hold", "-e", "bash", "-c", wrapped),
            ]
            for term in terminals:
                try:
                    subprocess.Popen(term, env=env)
                    break
                except FileNotFoundError:
                    continue
            else:
                self.process_tracker.release_lock()
                QMessageBox.critical(self, "Error", "No suitable terminal emulator found.")
                self.btn_run.setDisabled(False)
                self.btn_dry_run.setDisabled(False)
                return

        # Start polling the lock file instead of scanning process names
        self.check_process_timer = QTimer()
        self.check_process_timer.timeout.connect(self._check_lock_file)
        self.check_process_timer.start(1000)  # poll every 1s
        self.update_status()

    except Exception as e:
        self.process_tracker.release_lock()
        QMessageBox.critical(self, "Error", f"Failed to run command: {e}")
        self.btn_run.setDisabled(False)
        self.btn_dry_run.setDisabled(False)


def _check_lock_file(self):
    if not hasattr(self, "process_tracker"):
        self.check_process_timer.stop()
        return

    if not self.process_tracker.is_running:
        self.check_process_timer.stop()
        self.process_tracker.release_lock()
        self.running_process = None
        self.update_status()
```

**This removes the `psutil` dependency entirely** for process tracking. You can remove `import psutil` from `app.py` if it is not used elsewhere.

---

### 1.8 §27.8 — Binary Version Check Timeout & Error Handling

**Current code in `app.py` `check_binary_version()`:**

```python
try:
    result = subprocess.run(
        [self.binary_path, "version"],
        capture_output=True, text=True, timeout=2
    )
    version_text = result.stdout.strip() if result.stdout else "Unknown version"
    ...
except Exception:
    ...
```

The timeout is already 2 seconds, which is good. But the error handling is too broad and the status messages are misleading (it says "Binary: Ready" even when the version is unknown).

**Improved version:**

```python
def check_binary_version(self):
    user_home = os.path.expanduser("~")
    binary_folder = os.path.abspath(os.path.join(user_home, ".immich-go-gui", "bin"))
    binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
    self.binary_path = os.path.join(binary_folder, binary_filename)

    if not os.path.exists(self.binary_path):
        self._set_binary_status("err", "Binary: Missing", "Not found")
        if hasattr(self, "btn_check_updates"):
            self.btn_check_updates.setText("Download Immich-Go")
        return

    if not sys.platform.startswith("win") and not os.access(self.binary_path, os.X_OK):
        self._set_binary_status("err", "Binary: Not Executable", "Permission denied")
        return

    try:
        result = subprocess.run(
            [self.binary_path, "version"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode != 0:
            stderr_snippet = (result.stderr or "").strip()[:120]
            self._set_binary_status(
                "warn", "Binary: Error",
                f"Exit code {result.returncode}: {stderr_snippet}"
            )
            return

        version_text = (result.stdout or "").strip()
        if not version_text:
            self._set_binary_status("warn", "Binary: Unknown Version", "No output")
            return

        # Parse "immich-go version 0.31.0, ..." → "0.31.0"
        if "," in version_text:
            version_text = version_text.split(",")[0]
        # Strip prefix like "immich-go version " if present
        for prefix in ("immich-go version ", "version "):
            if version_text.lower().startswith(prefix):
                version_text = version_text[len(prefix):]

        self.current_version = version_text.strip()
        self._set_binary_status(
            "ok", f"Binary: {self.current_version}", self.current_version
        )
        if hasattr(self, "btn_check_updates"):
            self.btn_check_updates.setText("Check for Updates")

    except subprocess.TimeoutExpired:
        self._set_binary_status(
            "warn", "Binary: Timeout",
            "Version check timed out (>2s). Binary may be corrupted."
        )
    except PermissionError:
        self._set_binary_status("err", "Binary: Permission Denied", "Permission denied")
    except OSError as e:
        self._set_binary_status(
            "err", "Binary: OS Error", str(e)[:120]
        )
    except Exception as e:
        self._set_binary_status(
            "err", "Binary: Check Failed", str(e)[:120]
        )


def _set_binary_status(self, state: str, card_text: str, version_text: str):
    if hasattr(self, "status_card"):
        self.status_card.set_binary(state, card_text)
    if hasattr(self, "lbl_binary_version"):
        self.lbl_binary_version.setText(f"Current Version: {version_text}")
    if hasattr(self, "lbl_binary_path"):
        self.lbl_binary_path.setText(getattr(self, "binary_path", ""))
```

---

## 2. Execution Strategy & Terminal Behavior (§14, §19, §27.7)

### 2.1 Explicit Exclusions

The following are **intentionally NOT implemented** in this phase:

| Section | What it says | Why excluded |
|---|---|---|
| §14 | Replace external terminal with embedded `QProcess` console | You want the interactive TUI output from `immich-go` in a real terminal |
| §19 | Embedded dry-run output viewer inside the GUI | Current dry-run preview dialog is sufficient |
| §27.7 | Add `--no-ui` flag for embedded runs | Contradicts the external terminal choice; `--no-ui` disables the TUI you want |

### 2.2 What IS retained

- External terminal launch via `cmd /c start` (Windows), `osascript` (macOS), `gnome-terminal`/`konsole`/`xfce4-terminal`/`xterm` (Linux).
- The `immich-go` interactive TUI runs in the terminal with full live progress.
- Dry-run shows the command preview dialog (enhanced per §3 below).

### 2.3 Process tracking change

As detailed in §1.7 above, the `psutil` process-name scan is replaced with a **lock-file mechanism**. The terminal command is wrapped so that:
1. A lock file is created before launch.
2. The lock file is removed when the command exits (via `trap` on Unix, `del` in a `.bat` wrapper on Windows).
3. The GUI polls for lock file existence instead of scanning all system processes.

This is compatible with external terminal execution and avoids false positives from `psutil`.

---

## 3. Command Preview Enhancements (§18)

### 3.1 §18.1 — Structured Preview Sections

**Current `show_confirm_dialog` in `app.py`** shows a single `QPlainTextEdit` with the full command string.

**Target:** Show four labeled sections:

1. **Binary Path**
2. **Command** (masked, no secrets)
3. **Environment Variables** (secrets masked)
4. **Warnings** (if any)

**Implementation:**

```python
def show_confirm_dialog(self, is_dry_run):
    if self.stacked_widget.currentIndex() == 0:
        return

    ready, msg = self.check_binary_ready()
    if not ready:
        # ... binary download prompt (see §1.6) ...
        pass

    plan = self.build_plan(dry_run=is_dry_run)

    if plan.errors:
        QMessageBox.warning(
            self, "Validation Errors",
            "\n".join(f"• {e}" for e in plan.errors)
        )
        return

    dlg = QDialog(self)
    dlg.setWindowTitle("Confirm Execution")
    dlg.setModal(True)
    dlg.resize(680, 520)
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(22, 22, 22, 22)
    layout.setSpacing(12)

    # --- Kicker + Title ---
    kicker = QLabel("Dry run" if is_dry_run else "Live execution")
    kicker.setObjectName("DlgKicker")
    layout.addWidget(kicker)

    title = QLabel("This is what will run")
    title.setObjectName("DlgTitle")
    layout.addWidget(title)

    desc = QLabel(
        "A dry run simulates the action. No files are changed."
        if is_dry_run
        else "This executes the real command in an external terminal."
    )
    desc.setObjectName("DlgDesc")
    desc.setWordWrap(True)
    layout.addWidget(desc)

    # --- Section 1: Binary Path ---
    layout.addSpacing(8)
    lbl_binary = QLabel("Binary")
    lbl_binary.setObjectName("Subhead")
    layout.addWidget(lbl_binary)

    binary_edit = QLineEdit(plan.binary_path)
    binary_edit.setReadOnly(True)
    layout.addWidget(binary_edit)

    # --- Section 2: Command ---
    lbl_cmd = QLabel("Command")
    lbl_cmd.setObjectName("Subhead")
    layout.addWidget(lbl_cmd)

    # Build the display string from masked argv
    if sys.platform.startswith("win"):
        cmd_str = subprocess.list2cmdline(plan.display_argv)
    else:
        cmd_str = (
            plan.display_argv[0] + " "
            + " ".join(shlex.quote(p) for p in plan.display_argv[1:])
        )

    cmd_block = QPlainTextEdit()
    cmd_block.setObjectName("CmdBlock")
    cmd_block.setPlainText(cmd_str)
    cmd_block.setReadOnly(True)
    cmd_block.setMaximumHeight(120)
    layout.addWidget(cmd_block)

    # --- Section 3: Environment Variables ---
    # Only show IMMICH_GO_* vars (not the entire os.environ)
    immich_env = {
        k: v for k, v in plan.env.items()
        if k.startswith("IMMICH_GO_")
    }
    if immich_env:
        lbl_env = QLabel("Environment Variables")
        lbl_env.setObjectName("Subhead")
        layout.addWidget(lbl_env)

        env_lines = []
        secret_env_keys = {"API_KEY", "FROM_API_KEY", "ADMIN_API_KEY"}
        for k, v in sorted(immich_env.items()):
            # Mask secret values
            is_secret = any(s in k for s in secret_env_keys)
            display_v = "********" if is_secret else v
            env_lines.append(f"{k}={display_v}")

        env_block = QPlainTextEdit()
        env_block.setObjectName("CmdBlock")
        env_block.setPlainText("\n".join(env_lines))
        env_block.setReadOnly(True)
        env_block.setMaximumHeight(80)
        layout.addWidget(env_block)

    # --- Section 4: Warnings ---
    if plan.warnings:
        lbl_warn = QLabel("Warnings")
        lbl_warn.setObjectName("Subhead")
        layout.addWidget(lbl_warn)

        for w in plan.warnings:
            warn_lbl = QLabel(f"⚠️ {w}")
            warn_lbl.setObjectName("WarningHint")
            warn_lbl.setWordWrap(True)
            layout.addWidget(warn_lbl)

    layout.addStretch()

    # --- Buttons ---
    btn_row = QHBoxLayout()
    btn_row.addStretch()

    # Copy button (§18.3) — copies ONLY the clean command string
    btn_copy = QPushButton("Copy Command")
    btn_copy.setObjectName("BtnPreview")
    btn_copy.clicked.connect(
        lambda: QApplication.clipboard().setText(cmd_str)
    )
    btn_row.addWidget(btn_copy)

    btn_cancel = QPushButton("Cancel")
    btn_cancel.setObjectName("BtnPreview")
    btn_cancel.clicked.connect(dlg.reject)
    btn_row.addWidget(btn_cancel)

    btn_confirm = QPushButton("Run preview" if is_dry_run else "Start execution")
    btn_confirm.setObjectName("BtnRun")
    btn_confirm.clicked.connect(dlg.accept)
    btn_row.addWidget(btn_confirm)

    layout.addLayout(btn_row)

    if dlg.exec():
        self.run_command(plan)
```

### 3.2 §18.3 — Copy Button Behavior

The Copy button copies **only the clean executable command string** (`cmd_str`), which is:
- Built from `plan.display_argv` (already masked)
- Does NOT include environment variables
- Does NOT include the binary path as a separate section (it is part of `display_argv[0]`)

This is intentional per your requirement: **copy only the command, not the env block**.

### 3.3 §18.2 — Explicitly Excluded

Effective defaults display is **not implemented**. The preview shows only explicitly-passed flags. This avoids clutter.

---

## 4. Testing Strategy (§22.1 + §22.2)

### 4.1 §22.1 — Backend Unit Tests

These test pure logic, decoupled from the GUI. They should live in `test_app.py` (or a future `test_backend.py` if you split later).

**Test inventory:**

| Test | What it verifies |
|---|---|
| `test_collect_paths_single_file` | Single path passthrough |
| `test_collect_paths_multiline` | Multi-line splitting |
| `test_collect_paths_glob_expansion` | Glob expansion with tmp_path |
| `test_mask_command_for_display` | `--api-key=secret` masking |
| `test_mask_command_space_separated` | `--api-key secret` masking (NEW) |
| `test_mask_command_from_api_key` | `--from-api-key` masking |
| `test_mask_command_admin_api_key` | `--admin-api-key` masking |
| `test_normalize_server_url_*` | URL normalization (NEW, 4 tests) |
| `test_build_environment_no_trailing_spaces` | Env key hygiene |
| `test_api_key_never_in_argv` | Secret exclusion from argv (NEW) |
| `test_from_api_key_never_in_argv` | Source secret exclusion (NEW) |
| `test_build_environment_upload` | Env vars for upload tabs |
| `test_build_environment_upload_immich` | Env vars for upload-immich |
| `test_global_flag_ordering` | `--log-level` before `upload` |
| `test_pause_jobs_not_on_archive` | Flag scoping |
| `test_pause_jobs_not_on_stack` | Flag scoping |
| `test_on_errors_not_on_archive` | Flag scoping |
| `test_client_timeout_emitted` | `--client-timeout=60m` |
| `test_device_uuid_emitted` | `--device-uuid=...` |
| `test_api_trace_on_upload_gp` | `--api-trace` on GP tab |
| `test_api_trace_on_stack` | `--api-trace` on stack tab |
| `test_from_client_timeout` | `--from-client-timeout=60m` |
| `test_gp_multi_path` | Multi-ZIP path expansion |
| `test_global_skip_ssl_option` | `--skip-verify-ssl` |
| `test_secret_store_save_load` | Keychain mock |
| `test_secret_store_migration` | QSettings → keychain migration |
| `test_build_command_upload_folder` | Full upload-folder command (NEW golden) |
| `test_build_command_upload_gp` | Full upload-gp command (NEW golden) |
| `test_build_command_upload_immich` | Full upload-immich command |
| `test_build_command_archive_folder` | Full archive-folder command |
| `test_build_command_archive_immich` | Full archive-immich command |
| `test_build_command_stack` | Full stack command |

**Key new tests for §27.2 (secret exclusion):**

```python
def test_api_key_never_in_argv(gui):
    """Secrets must not appear in plan.argv for any tab."""
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("super_secret_key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(dry_run=False)

    for part in plan.argv:
        assert "super_secret_key" not in part
        assert "--api-key" not in part

    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "super_secret_key"


def test_from_api_key_never_in_argv(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new_key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old_secret")

    plan = gui.build_plan(dry_run=False)

    for part in plan.argv:
        assert "old_secret" not in part
        assert "--from-api-key" not in part

    assert plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY") == "old_secret"


def test_archive_folder_no_server_in_argv(gui):
    """archive-folder should not have --server or --api-key."""
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://local:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("/dst")

    plan = gui.build_plan(dry_run=False)

    assert not any("--server" in p for p in plan.argv)
    assert not any("--api-key" in p for p in plan.argv)
```

### 4.2 §22.2 — Golden Tests

Golden tests capture the **exact expected command vector** for a known input state. If any flag logic changes, the golden test breaks and forces a conscious review.

**Approach:** Use plain `assert plan.argv == [...]` with the full expected list. No external snapshot library needed for now.

```python
def test_golden_upload_folder(gui):
    """Golden: upload-folder with typical options."""
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["config"]["skip-ssl"].setChecked(False)
    gui.inputs["config"]["client_timeout"].setValue(20)  # default, not emitted
    gui.inputs["config"]["concurrent"].setValue(
        min(max(os.cpu_count() or 2, 1), 20)
    )  # default, not emitted
    gui.inputs["upload-folder"]["path"].setText("/photos")
    gui.inputs["upload-folder"]["include-type"].setCurrentText("IMAGE")
    gui.inputs["upload-folder"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["upload-folder"]["manage-raw-jpeg"].setCurrentText("NoStack")
    gui.inputs["upload-folder"]["manage-heic-jpeg"].setCurrentText("NoStack")
    gui.inputs["upload-folder"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "upload", "from-folder",
        "--server=http://localhost:2283",
        "--include-type=IMAGE",
        "--manage-burst=Stack",
        "/photos",
    ]
    # Secret in env, not argv
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "test-key"
    assert not any("--api-key" in p for p in plan.argv)


def test_golden_upload_gp(gui):
    """Golden: upload from-google-photos with partner + sync."""
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout-001.zip\n/takeout-002.zip")
    gui.inputs["upload-gp"]["include-type"].setCurrentText("all")
    gui.inputs["upload-gp"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["upload-gp"]["include-partner"].setChecked(True)
    gui.inputs["upload-gp"]["sync-albums"].setChecked(True)
    gui.inputs["upload-gp"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "upload", "from-google-photos",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "/takeout-001.zip",
        "/takeout-002.zip",
    ]


def test_golden_stack(gui):
    """Golden: stack with all options."""
    gui.stacked_widget.setCurrentIndex(3)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("test-key")
    gui.inputs["stack"]["manage-burst"].setCurrentText("Stack")
    gui.inputs["stack"]["manage-raw-jpeg"].setCurrentText("StackCoverRaw")
    gui.inputs["stack"]["manage-heic-jpeg"].setCurrentText("StackCoverJPG")
    gui.inputs["stack"]["manage-epson"].setChecked(True)
    gui.inputs["stack"]["time-zone"].setText("UTC")
    gui.inputs["stack"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "stack",
        "--server=http://localhost:2283",
        "--manage-burst=Stack",
        "--manage-raw-jpeg=StackCoverRaw",
        "--manage-heic-jpeg=StackCoverJPG",
        "--time-zone=UTC",
        "--manage-epson-fastfoto=true",
    ]


def test_golden_archive_folder(gui):
    """Golden: archive from-folder (no server)."""
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["archive-folder"]["path"].setText("/messy/photos")
    gui.inputs["archive-folder"]["write-to"].setText("/organized")
    gui.inputs["archive-folder"]["manage-raw-jpeg"].setCurrentText("KeepRaw")
    gui.inputs["archive-folder"]["date-range"].setText("2024")
    gui.inputs["archive-folder"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=True)

    assert plan.argv == [
        "archive", "from-folder",
        "--write-to-folder=/organized",
        "--manage-raw-jpeg=KeepRaw",
        "--date-range=2024",
        "--dry-run",
        "/messy/photos",
    ]
    # No server for archive-folder
    assert not any("--server" in p for p in plan.argv)


def test_golden_upload_immich(gui):
    """Golden: upload from-immich with filters."""
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)
    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new-key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")
    gui.inputs["upload-immich"]["from-favorite"].setChecked(True)
    gui.inputs["upload-immich"]["from-date-range"].setText("2023")
    gui.inputs["upload-immich"]["from-albums"].setText("Family, Travel")
    gui.inputs["upload-immich"]["log-level"].setCurrentText("INFO")

    plan = gui.build_plan(dry_run=False)

    assert plan.argv == [
        "upload", "from-immich",
        "--server=http://new:2283",
        "--from-server=http://old:2283",
        "--from-favorite=true",
        "--from-date-range=2023",
        "--from-albums=Family",
        "--from-albums=Travel",
    ]
    # Secrets in env only
    assert plan.env.get("IMMICH_GO_UPLOAD_API_KEY") == "new-key"
    assert plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY") == "old-key"
    assert not any("--api-key" in p for p in plan.argv)
    assert not any("--from-api-key" in p for p in plan.argv)
```

> **Maintenance note:** When `immich-go` changes flags, these golden tests will break. That is the intended behavior — it forces a conscious review of what changed. Update the expected vectors deliberately, and note the change in your compatibility docs.

---

## 5. Validation Architecture Guide (§17) — Reference Document

This section is an **architectural reference** to be included in the codebase (e.g., as a docstring block in `app.py` or a `docs/validation.md` file). Active UI integration of inline per-field validation labels is deferred to a later phase.

### 5.1 Validation Result Structure

```python
@dataclass
class ValidationResult:
    """Structured validation output.

    errors:   Block execution. Shown in status bar and preview dialog.
    warnings: Do not block execution. Shown in preview dialog.
    """
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
```

### 5.2 Per-Tab Validation Specification

| Tab | Field | Rule | Severity |
|---|---|---|---|
| **All except config** | Server URL | Required, must match `^https?://.+` after normalization | Error |
| **All except config, archive-folder** | API Key | Required, non-empty | Error |
| **All** | Skip SSL | If checked | Warning |
| **upload-folder** | Source path | Required, non-empty | Error |
| **upload-folder** | Date range | If provided, must match `YYYY[-MM[-DD]]` or `start,end` | Error |
| **upload-folder** | Extensions | If provided, must be comma-separated `.ext` | Warning |
| **upload-gp** | Takeout source | Required, non-empty | Error |
| **upload-gp** | Date range | Same as upload-folder | Error |
| **upload-immich** | Source server | Required, valid URL | Error |
| **upload-immich** | Source API key | Required, non-empty | Error |
| **upload-immich** | Date range | Same format | Error |
| **archive-folder** | Source path | Required, non-empty | Error |
| **archive-folder** | Destination | Required, non-empty | Error |
| **archive-immich** | Destination | Required, non-empty | Error |
| **archive-immich** | Date range | Same format | Error |
| **stack** | *(no tab-specific required fields)* | — | — |
| **All** | Concurrent tasks | If > 16 | Warning: "High concurrency may overload the server." |
| **All** | Client timeout | If > 120m | Warning: "Very long timeout." |

### 5.3 Date Range Validation Helper

```python
import re

_DATE_RANGE_RE = re.compile(
    r"^\d{4}(-\d{2}(-\d{2})?)?"          # single: YYYY, YYYY-MM, YYYY-MM-DD
    r"(,\d{4}(-\d{2}(-\d{2})?)?)?$"      # optional ,end
)

def validate_date_range(text: str) -> bool:
    """Validate immich-go date range format.

    Accepts: 2023, 2023-07, 2023-07-15, 2023-01-01,2023-12-31
    """
    text = text.strip()
    if not text:
        return True  # empty is valid (means no filter)
    return bool(_DATE_RANGE_RE.match(text))
```

> **Reference:** `Immich-go_cli_doc.md` §11.3 "Date Range Formats" confirms:
> - `2023` → Jan 1 – Dec 31, 2023
> - `2023-07` → July 1–31, 2023
> - `2023-07-15` → Single day
> - `2023-01-15,2023-03-15` → Explicit start,end range

### 5.4 Warning Generation Rules

Warnings are collected during `build_plan()` and `validate_inputs()`:

| Condition | Warning text |
|---|---|
| `--skip-verify-ssl` active | "SSL verification is disabled. Use only on trusted networks." |
| Concurrent tasks > 16 | "High concurrency (>16) may overload the server." |
| Client timeout > 120m | "Very long client timeout. Ensure this is intentional." |
| Binary version newer than tested | "immich-go version X is newer than the tested version Y. Some options may behave differently." |
| `--overwrite` active | "Overwrite mode will replace existing files on the server." |

### 5.5 Future Inline Validation (Deferred)

In a later phase, each form field can get a small red/green indicator:

```python
def _set_field_error(self, widget: QWidget, message: str | None):
    """Set or clear an inline error on a field."""
    # Find or create a QLabel sibling below the widget
    # Show/hide based on message
    pass
```

This is **not implemented now**. The `StatusCard` text and preview dialog warnings carry the feedback for this phase.

---

## 6. Binary Management & Manual Version Pinning (§15)

### 6.1 Versioned Binary Directories

**Current structure:**

```
~/.immich-go-gui/bin/immich-go
```

**Target structure:**

```
~/.immich-go-gui/
├── bin/
│   ├── 0.31.0/
│   │   └── immich-go          (or immich-go.exe on Windows)
│   ├── 0.32.0/
│   │   └── immich-go
│   └── metadata.json
└── config.json                (future: full settings)
```

**`metadata.json` schema:**

```json
{
  "schema_version": 1,
  "selected_version": "0.31.0",
  "manual_path": "",
  "versions": {
    "0.31.0": {
      "path": "/home/user/.immich-go-gui/bin/0.31.0/immich-go",
      "download_url": "https://github.com/simulot/immich-go/releases/download/0.31.0/immich-go_Linux_x86_64.tar.gz",
      "downloaded_at": "2026-07-22T00:00:00Z",
      "gui_tested": true
    },
    "0.32.0": {
      "path": "/home/user/.immich-go-gui/bin/0.32.0/immich-go",
      "download_url": "https://github.com/simulot/immich-go/releases/download/0.32.0/immich-go_Linux_x86_64.tar.gz",
      "downloaded_at": "2026-07-22T00:00:00Z",
      "gui_tested": false
    }
  }
}
```

**Implementation:**

```python
import json
from datetime import datetime, timezone

BINARY_BASE_DIR = os.path.join(os.path.expanduser("~"), ".immich-go-gui", "bin")
METADATA_PATH = os.path.join(BINARY_BASE_DIR, "metadata.json")

# The version this GUI was tested against
TESTED_IMMICH_GO_VERSION = "0.31.0"


def load_binary_metadata() -> dict:
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "schema_version": 1,
        "selected_version": "",
        "manual_path": "",
        "versions": {},
    }


def save_binary_metadata(meta: dict):
    os.makedirs(BINARY_BASE_DIR, exist_ok=True)
    with open(METADATA_PATH, "w") as f:
        json.dump(meta, f, indent=2)


def get_binary_path(meta: dict) -> str:
    """Resolve the effective binary path from metadata."""
    # 1. Manual path takes priority
    manual = meta.get("manual_path", "").strip()
    if manual and os.path.exists(manual):
        return manual

    # 2. Selected versioned binary
    selected = meta.get("selected_version", "")
    if selected and selected in meta.get("versions", {}):
        path = meta["versions"][selected]["path"]
        if os.path.exists(path):
            return path

    # 3. Fallback: legacy flat path
    binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
    legacy = os.path.join(BINARY_BASE_DIR, binary_filename)
    if os.path.exists(legacy):
        return legacy

    return ""
```

### 6.2 Manual Binary Path (§15.4)

Add a UI field in the Configuration tab's "Binary Management" card:

```python
# In _build_config_tab(), inside card2 (Binary Management):
manual_form = FormSection()
self.manual_binary_edit = QLineEdit()
self.manual_binary_edit.setPlaceholderText(
    "/usr/local/bin/immich-go  (leave empty to use managed binary)"
)
self.manual_binary_edit.textChanged.connect(self._on_manual_binary_changed)
manual_form.add_row(
    "Manual Binary Path",
    self.manual_binary_edit,
    "If set, this path is used instead of the managed binary."
)
card2.layout.addLayout(manual_form)
```

```python
def _on_manual_binary_changed(self, text: str):
    meta = load_binary_metadata()
    meta["manual_path"] = text.strip()
    save_binary_metadata(meta)
    self.binary_path = get_binary_path(meta)
    self.check_binary_version()
```

### 6.3 Release Notes Upgrade Parsing (Custom §15 Strategy)

Instead of automatic upgrades or versioned adapters, you check GitHub release notes for breaking-change indicators.

**Implementation:**

```python
import re

BREAKING_INDICATORS = [
    r"\bbreaking\s+change",
    r"\bbreaking\b",
    r"\bBREAKING\b",
    r"\bremoved\b.*\bflag\b",
    r"\brenamed\b.*\bflag\b",
    r"\bincompatible\b",
    r"\bdeprecat(ed|ion)\b",
]

_BREAKING_RE = re.compile(
    "|".join(BREAKING_INDICATORS),
    re.IGNORECASE
)


def check_release_for_breaking_changes(version: str) -> tuple[bool, str]:
    """Fetch release notes from GitHub and check for breaking change indicators.

    Returns (has_breaking, release_body_text).
    """
    try:
        api_url = f"https://api.github.com/repos/simulot/immich-go/releases/tags/{version}"
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        data = response.json()
        body = data.get("body", "") or ""

        has_breaking = bool(_BREAKING_RE.search(body))
        return has_breaking, body
    except Exception as e:
        # If we can't check, treat as potentially breaking (safe default)
        return True, f"Could not fetch release notes: {e}"
```

**Integration in `check_for_updates()`:**

```python
def check_for_updates(self):
    self.check_binary_version()
    latest_version = self.get_latest_release_info()
    if not latest_version:
        QMessageBox.warning(
            self, "Update Check",
            "Failed to fetch the latest version information from GitHub."
        )
        return

    current_version = getattr(self, "current_version", "Unknown")

    if current_version == latest_version:
        QMessageBox.information(
            self, "Update Check",
            f"You are already on the latest version ({current_version})."
        )
        return

    # Check release notes for breaking changes
    has_breaking, release_body = check_release_for_breaking_changes(latest_version)

    if has_breaking:
        # BLOCK the upgrade
        QMessageBox.warning(
            self,
            "Update Blocked — Breaking Changes Detected",
            f"Latest version: {latest_version}\n"
            f"Current version: {current_version}\n\n"
            f"⚠️ The release notes for {latest_version} contain breaking change "
            f"indicators. Automatic upgrade is blocked.\n\n"
            f"Please review the release notes manually:\n"
            f"https://github.com/simulot/immich-go/releases/tag/{latest_version}\n\n"
            f"If you have verified compatibility, you can download the binary "
            f"manually and set the path in Configuration → Manual Binary Path."
        )
        return

    # No breaking changes detected — offer upgrade
    reply = QMessageBox.question(
        self, "Update Available",
        f"Latest version: {latest_version}\n"
        f"Current version: {current_version}\n\n"
        f"No breaking changes detected in release notes.\n"
        f"Do you want to download and install {latest_version}?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.Yes:
        self.update_binary(version=latest_version, force_download=True)
```

### 6.4 Versioned Download & Install

Modify `update_binary()` to accept a version and install into a versioned directory:

```python
def update_binary(self, version: str | None = None, force_download: bool = False):
    if version is None:
        version = self.get_latest_release_info()
        if not version:
            QMessageBox.critical(self, "Error", "Could not determine latest version.")
            return False

    # Strip leading 'v' if present (GitHub tags may be "v0.31.0")
    clean_version = version.lstrip("v")

    version_dir = os.path.join(BINARY_BASE_DIR, clean_version)
    os.makedirs(version_dir, exist_ok=True)

    binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
    binary_path = os.path.join(version_dir, binary_filename)

    if os.path.exists(binary_path) and not force_download:
        # Already downloaded, just select it
        self._select_version(clean_version, binary_path)
        return True

    # Download into versioned directory
    download_url = self.get_download_url(version=clean_version)
    if not download_url:
        QMessageBox.critical(
            self, "Error",
            f"Could not determine download URL for version {clean_version} "
            f"on this platform."
        )
        return False

    # ... (existing DownloadThread logic, but extract to binary_path) ...
    # After successful extraction:

    meta = load_binary_metadata()
    meta["versions"][clean_version] = {
        "path": binary_path,
        "download_url": download_url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "gui_tested": clean_version == TESTED_IMMICH_GO_VERSION,
    }
    meta["selected_version"] = clean_version
    save_binary_metadata(meta)

    self.binary_path = binary_path
    self.check_binary_version()
    return True


def _select_version(self, version: str, binary_path: str):
    meta = load_binary_metadata()
    meta["selected_version"] = version
    save_binary_metadata(meta)
    self.binary_path = binary_path
    self.check_binary_version()
```

### 6.5 Startup Binary Resolution

In `__init__`, resolve the binary path from metadata:

```python
def __init__(self):
    super().__init__()
    # ... existing init ...

    # Resolve binary from metadata
    meta = load_binary_metadata()
    self.binary_path = get_binary_path(meta)
    if not self.binary_path:
        # Fall back to legacy default
        binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        self.binary_path = os.path.join(BINARY_BASE_DIR, binary_filename)

    self.check_binary_version()
    # ... rest of init ...
```

### 6.6 Compatibility Warning

In `check_binary_version()`, after successfully parsing the version, compare against `TESTED_IMMICH_GO_VERSION`:

```python
# After self.current_version is set:
if self.current_version != TESTED_IMMICH_GO_VERSION:
    # Check if it's newer
    try:
        from packaging.version import Version
        is_newer = Version(self.current_version) > Version(TESTED_IMMICH_GO_VERSION)
    except Exception:
        is_newer = self.current_version != TESTED_IMMICH_GO_VERSION

    if is_newer and hasattr(self, "status_card"):
        self.status_card.set_binary(
            "warn",
            f"Binary: {self.current_version} (untested)"
        )
```

> **Note:** If you do not want to add a `packaging` dependency, a simple string comparison or manual semver parse is sufficient for now.

---

## 7. Implementation Order Checklist

Execute in this order to minimize breakage:

### Step 1: Pure utility functions (no UI changes)
- [ ] Add `normalize_server_url()`
- [ ] Fix `mask_command_for_display()` (§27.1)
- [ ] Add `validate_date_range()`
- [ ] Add `CommandPlan` dataclass
- [ ] Add `ValidationResult` dataclass
- [ ] Add `ProcessTracker` class
- [ ] Add binary metadata functions (`load_binary_metadata`, `save_binary_metadata`, `get_binary_path`)
- [ ] Add `check_release_for_breaking_changes()`
- [ ] Add `check_binary_ready()`
- [ ] Write unit tests for all new pure functions (§22.1)

### Step 2: Refactor `build_command` → `build_plan`
- [ ] Rename `build_command()` to `build_plan()`, return `CommandPlan`
- [ ] Remove `--api-key` and `--from-api-key` from `argv` (§27.2)
- [ ] Apply `normalize_server_url()` to all server URL reads (§27.3)
- [ ] Populate `plan.env` with secrets
- [ ] Populate `plan.warnings`
- [ ] Update `show_confirm_dialog()` to use `plan`
- [ ] Update `run_command()` to accept `plan`
- [ ] Remove the secret-stripping loop from `run_command()`
- [ ] Write golden tests for all 6 tabs (§22.2)

### Step 3: Validation feedback (§27.4)
- [ ] Refactor `validate_inputs()` to return `ValidationResult`
- [ ] Update `update_status()` to show first error in `StatusCard`
- [ ] Show all errors in preview dialog if any

### Step 4: Process tracking (§27.6)
- [ ] Integrate `ProcessTracker` into `run_command()`
- [ ] Replace `check_if_process_running()` with `_check_lock_file()`
- [ ] Remove `psutil` import if no longer needed
- [ ] Test on Linux, macOS, Windows

### Step 5: Binary management (§15)
- [ ] Migrate to versioned directories
- [ ] Add `metadata.json` read/write
- [ ] Add manual binary path field in Configuration tab
- [ ] Add release-notes breaking-change check in `check_for_updates()`
- [ ] Add compatibility warning for untested versions
- [ ] Harden `check_binary_version()` (§27.8)

### Step 6: Command preview dialog (§18)
- [ ] Rebuild `show_confirm_dialog()` with 4 sections
- [ ] Add Copy Command button (command only)
- [ ] Show warnings section
- [ ] Show environment variables section (masked)

### Step 7: Final test pass
- [ ] Run full test suite
- [ ] Verify all golden tests pass
- [ ] Manual smoke test on all 6 tabs
- [ ] Manual test: dry run, live run, cancel, binary download, manual path

---

## 8. Files Changed Summary

| File | Changes |
|---|---|
| `app.py` | All refactoring: `CommandPlan`, `build_plan()`, `normalize_server_url()`, fixed `mask_command_for_display()`, `ValidationResult`, `ProcessTracker`, binary metadata, release-notes check, preview dialog rebuild, `check_binary_ready()`, hardened `check_binary_version()` |
| `test_app.py` | New tests: secret exclusion, URL normalization, space-separated masking, golden tests for all 6 tabs, updated existing tests to remove trailing-space artifacts |
| `theme.py` | No changes needed |
| `immich_go_gui_config.toml` | No changes needed (legacy reference; consider moving to `docs/` later) |

---

## 9. Key References to `Immich-go_cli_doc.md`

| Topic | Doc Section | Relevance |
|---|---|---|
| Environment variable naming pattern | §10 | Confirms `IMMICH_GO_<COMMAND>[_<SUBCOMMAND>]_<OPTION_NAME>` for §27.2 |
| `--api-key`, `--server` flags | §6.1 | Confirms these are required for upload commands |
| `archive from-folder` needs no server | §7.2 | Confirms archive-folder is local-only |
| Date range formats | §11.3 | Validates the regex in §5.3 |
| `--no-ui` flag | §6.1 | Explicitly NOT used per §2 exclusion |
| `--dry-run` flag | §5, §6.1 | Confirms dry-run is a global/command flag |
| Release compatibility notes | §1, §11.12 | Supports the release-notes parsing strategy in §6.3 |
| `ReplaceAsset` removal in v0.32.0 | §1 | Example of a breaking change that the release-notes parser should catch |
| Config file structure (TOML/YAML/JSON) | §9 | Reference for future config import/export; not used now |
| `--concurrent-tasks` default = CPU cores | §6.1, §11.10 | Confirms the current CPU-count default logic |
| `--pause-immich-jobs` default = true | §6.1 | Confirms only emit `=false` when unchecked |
| `--on-errors` accepts `stop`, `continue`, or N | §5, §6.1 | Confirms the numeric tolerance support |

---

This guide gives you a complete, ordered, and testable path for the changes you want to make right now, while keeping the external terminal workflow, deferring embedded console features, and building a solid foundation for future `immich-go` compatibility management.