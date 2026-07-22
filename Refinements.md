# Three-Part Response

---

## Part 1: Native File Dialogs

### The Problem

The current code has two issues:

1. **Double-dialog pattern** in `browse_local_folder()`: it calls `QFileDialog.getOpenFileName()` first (for ZIP), and if the user cancels, falls back to `QFileDialog.getExistingDirectory()`. This forces the user to close two dialogs.

2. **Qt's fallback dialog**: On some Linux desktop environments (or when `QFileDialog.Option.DontUseNativeDialog` is accidentally inherited), Qt renders its own file picker instead of the OS-native one (GTK file chooser, KDE Dolphin dialog, macOS `NSOpenPanel`, Windows `IFileDialog`).

### What To Do

#### A. Replace the double-dialog with a single native dialog + chooser menu

In `browse_local_folder()`, instead of chaining two dialogs:

- Show a small `QMenu` at the cursor position with two options: **"Select Folder…"** and **"Select ZIP Archive…"**
- Each option opens exactly **one** `QFileDialog` call
- This eliminates the double-close problem entirely

Alternatively, use a single `QFileDialog` instance configured to accept both:

```python
dlg = QFileDialog(self, "Select Source")
dlg.setFileMode(QFileDialog.FileMode.AnyFile)
dlg.setOption(QFileDialog.Option.DontUseNativeDialog, False)  # force native
dlg.setNameFilter("All Supported (*.zip *.ZIP);;All Files (*)")
dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
```

But the menu approach is cleaner UX.

#### B. Force native dialogs explicitly

Every `QFileDialog` static call should explicitly **not** pass `DontUseNativeDialog`. The safest pattern:

```python
folder = QFileDialog.getExistingDirectory(
    self,
    "Select Folder",
    "",
    QFileDialog.Option.ShowDirsOnly,  # native folder picker
)
```

For file selection:

```python
files, _ = QFileDialog.getOpenFileNames(
    self,
    "Select Files",
    "",
    "ZIP Archives (*.zip *.ZIP);;All Files (*)",
    options=QFileDialog.Option(0),  # explicitly no DontUseNativeDialog
)
```

#### C. Platform-specific fallback (optional, for Linux)

On Linux, if the native dialog still doesn't appear (headless environments, WSL, etc.), fall back to `zenity` or `kdialog`:

```python
if sys.platform.startswith("linux"):
    try:
        result = subprocess.run(
            ["zenity", "--file-selection", "--directory"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass  # fall back to QFileDialog
```

This is optional but improves Linux compatibility.

#### D. Apply to all browse actions

| Location | Current | Fix |
|---|---|---|
| `browse_local_folder()` | Chains ZIP dialog → folder dialog | Menu chooser: "Folder" / "ZIP" → single dialog each |
| `browse_takeout_source()` | `getOpenFileNames` → fallback `getExistingDirectory` | Menu chooser: "ZIP files" / "Extracted folder" → single dialog each |
| `_add_browse_action()` / `_browse_into()` | `getExistingDirectory` only | Keep as-is (destination is always a folder) but add `ShowDirsOnly` option |
| Archive destination browse | `getExistingDirectory` | Add `QFileDialog.Option.ShowDirsOnly` explicitly |

---

## Part 2: Separate Command Builder from UI

### Why

The `immich-go` CLI evolves: flags get added, renamed, deprecated, or change defaults. Right now, all flag logic lives inside `ImmichGoGUI.build_command()` — a 200+ line method tightly coupled to Qt widgets. Every CLI change means editing the GUI class, risking UI regressions.

### Target Architecture

```
project/
├── app.py                  ← UI only: widgets, layout, signals
├── theme.py                ← unchanged
├── cli/
│   ├── __init__.py
│   ├── models.py           ← Pure dataclasses (no Qt imports)
│   ├── builder.py          ← Pure command-building functions
│   ├── env.py              ← Environment variable construction
│   ├── masking.py          ← Secret masking for display
│   └── paths.py            ← collect_paths, glob expansion
├── test_app.py             ← GUI smoke tests
├── test_cli.py             ← Pure logic tests (no Qt needed)
└── config.toml             ← TOML configuration
```

### `cli/models.py` — Pure State Dataclasses

One dataclass per tab. No Qt imports. No widget references. Just data.

```python
from dataclasses import dataclass, field

@dataclass
class ServerConfig:
    server: str = ""
    api_key: str = ""
    skip_ssl: bool = False
    log_level: str = "INFO"
    log_file: str = ""
    log_type: str = "text"
    concurrent_tasks: int = 0       # 0 = auto (CPU count)
    client_timeout: int = 20        # minutes
    device_uuid: str = ""
    on_errors: str = "stop"         # "stop" | "continue" | int-as-string
    pause_jobs: bool = True

@dataclass
class UploadFolderState:
    path: str = ""
    include_type: str = "all"
    folder_album: str = "NONE"
    into_album: str = ""
    manage_burst: str = "NoStack"
    manage_raw_jpeg: str = "NoStack"
    manage_heic_jpeg: str = "NoStack"
    date_range: str = ""
    include_ext: str = ""
    exclude_ext: str = ""
    ban_file: str = ""              # newline-separated
    ignore_sidecar: bool = False
    date_from_name: bool = True
    tags: str = ""
    session_tag: bool = False
    folder_tags: bool = False
    on_errors: str = ""             # per-tab override, empty = use config
    overwrite: bool = False
    pause_jobs: bool | None = None  # None = use config
    api_trace: bool = False

@dataclass
class UploadGooglePhotosState:
    paths: list[str] = field(default_factory=list)  # already expanded
    include_type: str = "all"
    into_album: str = ""
    include_unmatched: bool = False
    include_partner: bool = True
    sync_albums: bool = True
    manage_burst: str = "NoStack"
    manage_heic_jpeg: str = "NoStack"
    from_album_name: str = ""
    include_archived: bool = True
    include_trashed: bool = False
    partner_album: str = ""
    takeout_tag: bool = True
    people_tag: bool = True
    tags: str = ""
    session_tag: bool = False
    on_errors: str = ""
    pause_jobs: bool | None = None
    api_trace: bool = False

@dataclass
class UploadImmichState:
    from_server: str = ""
    from_api_key: str = ""
    from_client_timeout: int = 20
    from_favorite: bool = False
    from_archived: bool = False
    from_trash: bool = False
    from_date_range: str = ""
    from_albums: str = ""
    from_minimal_rating: int = 0
    from_people: str = ""
    from_tags: str = ""
    from_city: str = ""
    from_state: str = ""
    from_country: str = ""
    from_make: str = ""
    from_model: str = ""
    from_skip_ssl: bool = False
    on_errors: str = ""
    api_trace: bool = False

@dataclass
class ArchiveFolderState:
    path: str = ""
    write_to: str = ""
    manage_raw_jpeg: str = "NoStack"
    date_range: str = ""
    log_level: str = "INFO"

@dataclass
class ArchiveImmichState:
    write_to: str = ""
    manage_burst: str = "NoStack"
    manage_raw_jpeg: str = "NoStack"
    from_date_range: str = ""
    from_albums: str = ""
    log_level: str = "INFO"

@dataclass
class StackState:
    manage_burst: str = "NoStack"
    manage_raw_jpeg: str = "NoStack"
    manage_heic_jpeg: str = "NoStack"
    time_zone: str = ""
    manage_epson: bool = False
    api_trace: bool = False
    log_level: str = "INFO"
```

### `cli/builder.py` — Pure Functions

Each function takes a state dataclass + `ServerConfig` and returns `list[str]`. No Qt. No side effects. Fully testable.

```python
from .models import *
from .paths import collect_paths

UPLOAD_TABS = {"upload-folder", "upload-gp", "upload-immich"}

def build_upload_folder(cfg: ServerConfig, state: UploadFolderState, dry_run: bool) -> list[str]:
    global_opts = _global_opts(cfg, state_log_level=None)
    cmd = ["upload", "from-folder"]
    cmd_opts = _server_opts(cfg)
    # ... all flag logic ...
    path_opt = [state.path] if state.path else []
    if dry_run:
        cmd_opts.append("--dry-run")
    return global_opts + cmd + cmd_opts + path_opt

def build_upload_gp(cfg: ServerConfig, state: UploadGooglePhotosState, dry_run: bool) -> list[str]:
    # ...
    pass

# ... one function per tab ...

def _global_opts(cfg: ServerConfig, state_log_level: str | None = None) -> list[str]:
    opts = []
    level = state_log_level or cfg.log_level
    if level and level != "INFO":
        opts.append(f"--log-level={level}")
    if cfg.log_file:
        opts.append(f"--log-file={cfg.log_file}")
    if cfg.log_type and cfg.log_type != "text":
        opts.append(f"--log-type={cfg.log_type}")
    return opts

def _server_opts(cfg: ServerConfig) -> list[str]:
    opts = []
    if cfg.server:
        opts.append(f"--server={cfg.server}")
    if cfg.api_key:
        opts.append(f"--api-key={cfg.api_key}")
    if cfg.skip_ssl:
        opts.append("--skip-verify-ssl")
    if cfg.client_timeout != 20:
        opts.append(f"--client-timeout={cfg.client_timeout}m")
    cpu_default = min(max(os.cpu_count() or 2, 1), 20)
    if cfg.concurrent_tasks and cfg.concurrent_tasks != cpu_default:
        opts.append(f"--concurrent-tasks={cfg.concurrent_tasks}")
    return opts
```

### `cli/env.py` — Environment Variables

```python
def build_environment(tab_key: str, cfg: ServerConfig,
                      from_server: str = "", from_api_key: str = "") -> dict:
    env = os.environ.copy()
    # ... same logic as current build_environment ...
    return env
```

### `cli/masking.py` — Secret Masking

```python
SECRET_FLAGS = {"--api-key", "--from-api-key", "--admin-api-key"}

def mask_command_for_display(parts: list[str]) -> list[str]:
    # ... same logic as current ...
    pass
```

### `cli/paths.py` — Path Utilities

```python
import glob

def collect_paths(raw_text: str) -> list[str]:
    # ... same logic as current ...
    pass
```

### UI Layer Changes in `app.py`

The GUI class gets a thin adapter method that reads widgets → builds dataclass → calls builder:

```python
from cli.models import ServerConfig, UploadFolderState
from cli.builder import build_upload_folder
from cli.env import build_environment
from cli.masking import mask_command_for_display
from cli.paths import collect_paths

class ImmichGoGUI(QMainWindow):
    # ...

    def _read_server_config(self) -> ServerConfig:
        c = self.inputs["config"]
        return ServerConfig(
            server=c["server"].text().strip(),
            api_key=c["api_key"].text().strip(),
            skip_ssl=c["skip-ssl"].isChecked(),
            log_level=c.get("log-level", ...).currentText() if ... else "INFO",
            client_timeout=c["client_timeout"].value(),
            device_uuid=c["device_uuid"].text().strip(),
            concurrent_tasks=c["concurrent"].value(),
            on_errors=self._resolve_on_errors(),
            pause_jobs=c["pause_jobs"].isChecked(),
        )

    def _read_upload_folder_state(self) -> UploadFolderState:
        c = self.inputs["upload-folder"]
        return UploadFolderState(
            path=c["path"].text().strip(),
            include_type=c["include-type"].currentText(),
            folder_album=c["folder-album"].currentText(),
            # ... map every widget to a field ...
        )

    def build_command(self, dry_run: bool) -> list[str]:
        idx = self.stacked_widget.currentIndex()
        tab_key = self.TAB_KEYS[idx]
        if tab_key == "config":
            return []
        cfg = self._read_server_config()
        if tab_key == "upload-folder":
            state = self._read_upload_folder_state()
            return build_upload_folder(cfg, state, dry_run)
        elif tab_key == "upload-gp":
            state = self._read_upload_gp_state()
            return build_upload_gp(cfg, state, dry_run)
        # ... etc ...
```

### Benefits

| Concern | Before | After |
|---|---|---|
| CLI flag change | Edit 200-line GUI method | Edit one pure function in `cli/builder.py` |
| Testing | Need Qt, qtbot, full GUI | `pytest test_cli.py` — no Qt, instant |
| New tab (e.g. iCloud) | Add widgets + edit build_command | Add dataclass + builder function + widgets |
| Flag deprecation | Hunt through GUI code | Grep one file |
| Reuse (CLI wrapper, scripts) | Not possible | Import `cli.builder` directly |

### Migration Strategy

1. Create `cli/` package with `models.py`, `builder.py`, `env.py`, `masking.py`, `paths.py`
2. Move existing logic from `build_command()` into the appropriate builder functions
3. Move `collect_paths`, `mask_command_for_display`, `build_environment` into `cli/`
4. Add `_read_*_state()` adapter methods to `ImmichGoGUI`
5. Replace `build_command()` body with dispatcher that calls `cli.builder`
6. Move existing pure-logic tests to `test_cli.py`
7. Keep GUI smoke tests in `test_app.py` but they now test the adapter layer
8. Delete the old inline logic from `app.py`

---

## Part 3: What's Still Missing (Refinements.md Audit)

### ✅ Already Implemented

| Refinements § | Item | Status |
|---|---|---|
| 1.1 | Global flag ordering | ✅ Fixed |
| 1.2 | `--pause-immich-jobs` scoping | ✅ Fixed |
| 1.3 | `--on-errors` scoping | ✅ Fixed |
| 1.4 | `--client-timeout` emitted | ✅ Fixed |
| 1.5 | `--device-uuid` emitted | ✅ Fixed |
| 1.6 | `--api-trace` on all upload + stack | ✅ Fixed |
| 1.8 | Concurrent tasks = CPU count | ✅ Fixed |
| 1.9 | Numeric `--on-errors` | ✅ Fixed |
| 3.1 | Multi-ZIP Takeout | ✅ Fixed |
| 3.2 | Multi-file drag-drop | ✅ Fixed |
| 3.3 | ZIP for upload from-folder | ✅ Fixed |
| 3.4 | Destination browse buttons | ✅ Fixed |
| 4.1 | API key masking in preview | ✅ Fixed |
| 4.2 | Env vars for secrets | ✅ Fixed |
| 4.3 | OS keychain storage | ✅ Fixed |
| 4.4 | SSL warning (inline + dialog) | ✅ Fixed |

### ❌ Still Missing — High Priority

| Refinements § | Item | What's Needed |
|---|---|---|
| **2.6** | `archive from-folder` missing options | Add: `--include-type`, `--include-extensions`, `--exclude-extensions`, `--ban-file`, `--ignore-sidecar-files`, `--date-from-name`, `--manage-burst`, `--manage-heic-jpeg`, `--recursive`. The CLI doc confirms archive shares the same source options as upload. |
| **2.7** | `archive from-immich` missing options | Add: `--from-favorite`, `--from-archived`, `--from-trash`, `--from-minimal-rating`, `--from-people`, `--from-tags`, `--from-city`, `--from-state`, `--from-country`, `--from-make`, `--from-model`, `--from-no-album`, `--from-client-timeout`, `--from-skip-verify-ssl`. |
| **2.8** | `--include-untitled-albums` | Add checkbox to upload-gp tab. CLI doc: `--include-untitled-albums` (default false). |
| **2.9** | `--recursive` | Add checkbox to upload-folder (default true, emit `--recursive=false` when unchecked). |
| **2.10** | `--album-path-joiner` | Add text field to upload-folder advanced (default `/`). |
| **2.11** | `--album-picasa` | Add checkbox to upload-folder advanced. |
| **2.12** | Global `--log-file` and `--log-type` | Add to Configuration tab. Emit in `global_opts`. Add "Open Log Folder" button. |
| **1.10** | `--from-albums` vs `--from-album` | Verify with `immich-go upload from-immich --help`. CLI doc uses both forms inconsistently. |
| **4.5** | Binary checksum verification | Add SHA-256 verification after download. Atomic replacement via temp file. |
| **7.1** | Per-tab validation | Validate source path, destination, from-server per tab before enabling Run/Preview. |
| **10.1** | Decouple command builder | **This is Part 2 above.** |

### ❌ Still Missing — Medium Priority

| Refinements § | Item | What's Needed |
|---|---|---|
| **5.2.2** | `Card.layout` shadows `QWidget.layout()` | Rename to `card_layout` or `_layout`. |
| **5.2.3** | `SwitchButton` → `QAbstractButton` | Inherit properly, add keyboard support, accessible name. |
| **5.2.4** | HiDPI icons | Render at 2x, set `devicePixelRatio`. |
| **5.2.5** | Sidebar icons checked state | Use accent color for checked nav items. |
| **5.2.6** | Icon caching | Cache rendered icons in a dict. |
| **5.2.7** | `QThread.terminate()` | Replace with cooperative cancellation (`_cancelled` flag). |
| **5.2.8** | Network on UI thread | Move `get_latest_release_info()` to a `QThread` worker. |
| **5.2.9** | `QSettings` placeholder org | Set proper `app.setOrganizationName("immich-go-gui")`. |
| **5.2.10** | Window icon not set | `app.setWindowIcon(QIcon("immich-go-gui.png"))`. |
| **5.2.13** | Drag-drop monkeypatching | Replace `_enable_folder_drop` with `DroppableLineEdit` / `DroppablePlainTextEdit` subclasses. |
| **6.1** | Terminal launching safety | Use temp `.bat`/`.command` scripts instead of `shell=True` / AppleScript string interpolation. |
| **8.1** | TOML config | Migrate to `config.toml` via `platformdirs` + `tomli_w`. |
| **9.4** | API key permissions helper | Show required scopes in Configuration tab. |
| **9.5** | Connection test button | `GET /api/server/about` in worker thread. |

### ❌ Still Missing — Low Priority / Deferred

| Refinements § | Item | Note |
|---|---|---|
| 2.1–2.5 | Missing tabs (iCloud, Picasa, archive-GP) | User deferred |
| 1.7 | `--no-ui` | User wants external terminal — intentional |
| 5.2.11 | QSS font-family emoji | Low impact |
| 5.2.12 | QComboBox arrow | Cosmetic |
| 6.2 | Embedded QProcess runner | User wants external terminal |
| 9.1–9.3, 9.6 | UI/UX polish | User deferred |

### Summary: Immediate Next Steps (in order)

1. **Create `cli/` package** — extract builder, models, env, masking, paths (Part 2)
2. **Fix native file dialogs** — menu chooser pattern, eliminate double-dialog (Part 1)
3. **Expand `archive from-folder`** — add the ~10 missing filtering/management options (§2.6)
4. **Expand `archive from-immich`** — add the ~14 missing source-filtering options (§2.7)
5. **Add missing upload-folder flags** — `--recursive`, `--album-path-joiner`, `--album-picasa`, `--include-untitled-albums` on GP (§2.8–2.11)
6. **Add global logging** — `--log-file`, `--log-type` to Configuration tab (§2.12)
7. **Per-tab validation** (§7.1)
8. **Replace drag-drop monkeypatching** with proper subclasses (§5.2.13)
9. **Fix `QThread.terminate()`** + move network to worker (§5.2.7, §5.2.8)
10. **TOML config migration** (§8.1)