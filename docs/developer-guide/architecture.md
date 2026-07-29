# Architecture

Immich-Go GUI is a desktop application with a deliberate separation between Qt UI code and testable business logic.

## High-Level Overview

```mermaid
flowchart TB
    classDef userStyle fill:#6366f1,stroke:#4338ca,color:#fff,stroke-width:2px
    classDef uiStyle fill:#0ea5e9,stroke:#0369a1,color:#fff,stroke-width:2px
    classDef coreStyle fill:#8b5cf6,stroke:#6d28d9,color:#fff,stroke-width:2px
    classDef runStyle fill:#f59e0b,stroke:#b45309,color:#fff,stroke-width:2px
    classDef extStyle fill:#10b981,stroke:#047857,color:#fff,stroke-width:2px

    User([User]):::userStyle

    subgraph UI["UI Layer — app.py / gui/ / theme.py"]
        direction LR
        AppPy[app.py<br/>Thin entrypoint ~130 LOC]:::uiStyle
        GuiPkg[gui/<br/>MainWindow · Mixins · Tabs · Widgets]:::uiStyle
        ThemePy[theme.py<br/>Palette · Icons]:::uiStyle
    end

    subgraph Core["core/ — Qt-free business logic"]
        direction LR
        Builder[command_builder<br/>CommandPlan]:::coreStyle
        Validator[validation]:::coreStyle
        Config[config_manager<br/>TOML + keyring]:::coreStyle
        BinMgr[binary_manager<br/>GitHub Releases]:::coreStyle
        Tracker[process_tracker<br/>Lock files]:::coreStyle
        Terminal[terminal_launcher]:::runStyle
    end

    subgraph Ext["External"]
        direction LR
        ImmichGo[immich-go CLI]:::extStyle
        ImmichAPI[(Immich Server)]:::extStyle
        GitHub[(GitHub Releases)]:::extStyle
    end

    User -->|interact| GuiPkg
    AppPy --> GuiPkg
    GuiPkg --> ThemePy
    GuiPkg --> Builder
    Builder --> Validator
    GuiPkg --> Config
    GuiPkg --> BinMgr
    GuiPkg --> Tracker
    Builder -->|argv + env| Terminal
    Tracker -->|lock gates launch| Terminal
    Terminal -->|launch subprocess| ImmichGo
    BinMgr -->|download / verify SHA256| GitHub
    Config -->|pre-flight ping| ImmichAPI
    ImmichGo -->|upload / archive / stack| ImmichAPI
```

## High-Level Structure

```text
immich-go-gui/
├── app.py                 # Thin entry point (~130 lines) + --self-test CLI handler
├── theme.py               # Theming: Fusion style, palettes, SVG icons
├── gui/                   # PySide6 desktop GUI package
│   ├── main_window.py     # ImmichGoGUI QMainWindow composition
│   ├── browse_dialogs.py  # File/directory chooser dialog helpers
│   ├── widgets/           # Custom Qt widgets package
│   │   ├── droppable.py   # DroppableLineEdit, DroppablePlainTextEdit
│   │   ├── status_card.py # Live status summary card
│   │   ├── navigation.py  # NavGroup, NavItem sidebar navigation
│   │   └── ...            # cards, base_page, advanced_flag_row, etc.
│   ├── mixins/            # Focused QMainWindow mixins (all ≤300 lines)
│   │   ├── layout.py      # Main layout & tab assembly
│   │   ├── form_helpers.py# Inline field errors & helper controls
│   │   ├── form_state.py  # State collection & restoration
│   │   ├── execution.py   # Command building & terminal execution
│   │   ├── confirm_dialog.py # Run confirmation dialog
│   │   ├── persistence.py # TOML config & secret store persistence
│   │   ├── profiles_ui.py # Profile switcher menu & dialogs
│   │   ├── status.py      # Debounced status updates & light validation
│   │   ├── binary_ui.py   # Binary download & version management UI
│   │   ├── connection.py  # Connection test preflight UI
│   │   ├── diagnostics.py # System diagnostics & log export
│   │   ├── menu.py        # Top bar & context menus
│   │   └── theme_mixin.py # Dynamic theme switching
│   └── tabs/              # Tab builder modules
│       ├── config_tab.py  # Server & credentials configuration tab
│       ├── stack_tab.py   # Photo stacking subcommand tab
│       ├── upload/        # Upload subcommand tabs (folder, GP, icloud, picasa, immich)
│       └── archive/       # Archive subcommand tabs (folder, GP, icloud, picasa, immich)
├── core/                  # Qt-free business logic (testable without GUI)
│   ├── flags.toml         # Single source of truth for tabs + flags
│   ├── flag_registry.py   # Loads flags.toml → REGISTRY singleton
│   ├── models.py          # Dataclasses / enums
│   ├── cli_schema.py      # Thin shim: TAB_COMMANDS, TAB_ALLOWED_FLAGS, etc.
│   ├── advanced_flags.py  # Thin shim over registry advanced defs
│   ├── command_builder.py # state dict produces a CommandPlan
│   ├── config_manager.py  # TOML + keyring secrets
│   ├── profile_manager.py # Multi-profile index
│   ├── binary_manager.py  # immich-go download / versions
│   ├── network.py         # Pre-flight Immich checks
│   ├── process_tracker.py # Run locks
│   ├── terminal_launcher.py
│   ├── validation.py
│   ├── cli_help.py / cli_contract.py
│   └── __init__.py        # Public re-exports
├── tests/                 # Focused Pytest modules (20 modules, ~260 tests)
├── scripts/               # CLI help capture, review bundles, icon generator
├── docs/                  # User + developer + reference docs
├── packaging/             # Linux nfpm + Windows Inno Setup
└── assets/icons/          # Sidebar SVG icons
```

## Layer Responsibilities

| Layer | Files | Responsibility |
|-------|-------|----------------|
| **Entrypoint** | `app.py` | App startup, exception hook, CLI flags (`--self-test`) |
| **UI** | `gui/`, `theme.py` | Window management, tab builders, mixins, widgets, visual feedback |
| **Core** | `core/*.py` | CLI schema, command building, config, binary mgmt, process locks |
| **External** | immich-go CLI, Immich API, GitHub Releases | Runtime dependencies |

The `core/` package MUST NOT import PySide6 or Qt. All network, file I/O, subprocess, and keyring operations live here so unit tests can run headlessly.

## Data Flow

```mermaid
flowchart LR
    State[form_state dict] --> Build[build_plan_from_state<br/>validates + builds]
    Build --> Plan[CommandPlan<br/>argv · env · warnings]
    Plan --> Mask[mask_command_for_display]
    Mask --> Preview[Preview pane]
    Plan --> Launch[terminal_launcher]
    Launch --> Terminal[External terminal<br/>argv + env]
```

### Typical Run Sequence

```mermaid
sequenceDiagram

participant User
participant GUI
participant Builder
participant Process
participant Immich

User->>GUI: Configure Import

GUI->>Builder: Build Command

Builder-->>GUI: Generated Command

User->>GUI: Start

GUI->>Process: Launch Process

Process->>Immich: Execute immich-go

Immich-->>Process: Progress

Process-->>GUI: Live Logs

GUI-->>User: Status Updates
```

1. User fills form fields on a workflow tab in `app.py`.
2. `build_plan_from_state()` in `core/command_builder.py` validates input and produces a `CommandPlan` (argv + env + masked display).
3. Pre-flight check calls `core/network.py` for server-required tabs.
4. `core/process_tracker.py` creates a lock file to prevent concurrent runs.
5. `core/terminal_launcher.py` opens an external terminal running immich-go with the constructed argv and env.
6. Lock is released when the process exits (Windows uses a heartbeat helper for cleanup).

## CLI Parity Model

The GUI maintains **11/11 parity** with immich-go subcommands:

- 5 upload tabs
- 5 archive tabs
- 1 stack tab

Each tab maps to a fixed command token list in `core/cli_schema.py` (`TAB_COMMANDS`). Allowed flags per tab are defined in `core/flags.toml` and loaded via `core/flag_registry.py` (`TAB_ALLOWED_FLAGS` is a shim export). Validated at build time.

### Serverless Tab Rule

These archive tabs are classified as `SERVERLESS_TABS`:

- `archive-folder`, `archive-gp`, `archive-icloud`, `archive-picasa`

They must **never** emit `--server`, `--api-key`, or `--client-timeout` flags.

## Security Model

| Concern | Implementation |
|---------|----------------|
| Secret storage | OS keyring via `keyring` library; scoped per profile |
| Secret delivery | Environment variables in `subprocess.Popen` env dict — never argv |
| Disk scripts | Launch scripts must NOT write secrets to shell files |
| Preview redaction | `mask_command_for_display()` masks `--api-key`, `--from-api-key`, etc. |
| SSL bypass | Inline warning banner when `--skip-verify-ssl` is enabled |

See [Environment Variables](../reference/environment-variables.md) for the env var map.

## Configuration Persistence

- Per-profile TOML files via `core/config_manager.py` and `core/profile_manager.py`
- Form field values stored in `form_state` dict within config
- Legacy QSettings migration for API keys handled once on startup

## Process Lock Lifecycle

Lock files live in `{config_dir}/locks/run_{id}.lock` as JSON documents tracking GUI PID, tab key, and command summary.

- **POSIX:** Launcher uses a temporary run directory with safe `$HOME` fallback to avoid CWD deletion errors.
- **Windows:** `.bat` launcher runs a background `.heartbeat` process to clean `.lock` files if the terminal is killed abruptly.

## Entry Point

```python
# app.py
if __name__ == "__main__":
    app = QApplication(sys.argv)
    set_fusion_style()
    window = ImmichGoGUI()
    window.show()
    sys.exit(app.exec())
```

Run with: `uv run app.py`

## Further Reading

- [Core Modules](core-modules.md) — Detailed module reference
- [Adding Tabs and Flags](adding-tabs-and-flags.md) — Extension guide
- [Testing](testing.md) — Test infrastructure
