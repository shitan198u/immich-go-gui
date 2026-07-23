Yes — that is the better model.

Your instinct is correct:

> Do **not** special-case “default-false” vs “default-true” booleans in the UI.
> Make every advanced flag an explicit opt-in row:
>
> ```text
> [ ]  --flag-name  [flag options]
> ```
>
> If the checkbox is unchecked, the flag is **never passed**.
> If the checkbox is checked, the flag is passed with the chosen option/value.

That removes the maintenance burden and makes the GUI much more predictable.

Below is a detailed implementation guide you can hand to an AI agent.

---

# AI Agent Implementation Guide
## Unified “Opt-In Advanced Flag Rows” for Immich-Go GUI

## 1. Goal

Replace the current advanced-options implementation with a single unified model:

```text
[enable checkbox]  [flag]  [flag options]
```

### Core rule
For every advanced flag:

- the row is **disabled by default**
- if the enable checkbox is **unchecked**:
  - the flag is ignored
  - nothing is added to `argv`
  - nothing is added to secret env
- if the enable checkbox is **checked**:
  - the flag value widget is enabled
  - the flag is emitted according to its value/type

This applies to **all advanced flags**, including boolean flags.

---

## 2. Desired UX

### Example layout

```text
Advanced Flags

[ ] --recursive              [ false ▼ ]
[ ] --date-from-name         [ true  ▼ ]
[ ] --time-zone              [ UTC     ]
[ ] --log-level              [ DEBUG ▼ ]
[ ] --include-trashed        [ true  ▼ ]
[ ] --include-archived       [ false ▼ ]
[ ] --ban-file               [ @eaDir/ ... ]
[ ] --include-extensions     [ .jpg,.png ]
```

### Behavior
- unchecked → flag not passed
- checked → flag passed according to selected option/value

### Examples

#### Boolean flag enabled as true
```text
[x] --include-trashed   [ true ▼ ]
```

produces:

```bash
--include-trashed
```

#### Boolean flag enabled as false
```text
[x] --recursive   [ false ▼ ]
```

produces:

```bash
--recursive=false
```

#### Text flag enabled
```text
[x] --time-zone   [ UTC ]
```

produces:

```bash
--time-zone=UTC
```

#### Enum flag enabled
```text
[x] --log-level   [ DEBUG ▼ ]
```

produces:

```bash
--log-level=DEBUG
```

---

## 3. Product rules

### Rule 1 — Everything advanced is disabled by default
On first load, all advanced flag rows are unchecked.

### Rule 2 — Disabled means ignored
A disabled advanced flag must not affect:

- command generation
- validation
- warnings
- run button state

### Rule 3 — No default-true/default-false special casing in UI
The UI should not know or care whether the CLI default is true or false.

The row simply represents:

- enable this flag or not
- choose the flag value/options if enabled

### Rule 4 — Boolean flags still have explicit options
For boolean flags, use a value selector:

```text
[ true ▼ ]
[ false ▼ ]
```

This lets the user pass either:

- `--flag`
- `--flag=false`

without creating separate UI logic for default-true/default-false flags.

### Rule 5 — Simple mode hides and ignores advanced rows
If Simple mode is active:

- advanced rows are hidden
- advanced rows are ignored completely

### Rule 6 — Advanced mode shows rows but still requires opt-in
Advanced mode only makes the rows visible.

It does **not** enable the flags automatically.

### Rule 7 — Persist values, but do not auto-enable
When restoring saved state:

- restore the option values
- restore the enabled checkbox state only if explicitly saved
- if migrating from the old UI, set all advanced rows to disabled by default

---

## 4. Recommended architecture

Create a schema-driven advanced-flag system.

Do **not** implement this by manually adding one checkbox per flag in every tab.

Instead:

1. define advanced flags in a registry
2. generate the UI rows from that registry
3. collect row state generically
4. emit flags generically in the command builder

This is the key to reducing maintenance.

---

# 5. Core data model

Create a new pure-Python module:

```text
core/advanced_flags.py
```

This module must not import Qt.

## 5.1 Flag definition model

```python
from dataclasses import dataclass, field
from typing import Any, Literal

AdvancedFlagKind = Literal[
    "bool",
    "text",
    "enum",
    "int",
    "duration_minutes",
    "extensions",
    "csv_repeat",
    "lines_repeat",
    "date_range",
]

@dataclass(frozen=True)
class AdvancedFlagDef:
    key: str                      # internal state key
    flag: str                     # CLI flag name without --
    label: str                    # human-readable label / tooltip
    kind: AdvancedFlagKind
    default: Any = None
    options: tuple[str, ...] = ()
    placeholder: str = ""
    hint: str = ""
    secret_env: str | None = None
    allow_empty: bool = True
    warn_values: dict[Any, str] = field(default_factory=dict)
```

---

## 5.2 Kind meanings

### `bool`
- UI: checkbox + true/false combo
- output:
  - true → `--flag`
  - false → `--flag=false`

### `text`
- UI: line edit
- output:
  - `--flag=value`

### `enum`
- UI: combo box
- output:
  - `--flag=value`

### `int`
- UI: spinbox
- output:
  - `--flag=123`

### `duration_minutes`
- UI: spinbox with “minutes”
- output:
  - `--flag=60m`

### `extensions`
- UI: line edit
- normalization:
  - lowercase
  - ensure leading dot
  - comma-separated
- output:
  - `--flag=.jpg,.png`

### `csv_repeat`
- UI: line edit
- split on commas
- output:
  - `--flag=item1 --flag=item2`

### `lines_repeat`
- UI: multiline text edit
- split by lines
- output:
  - `--flag=line1 --flag=line2`

### `date_range`
- UI: line edit
- validate with existing date-range helper
- output:
  - `--flag=cleaned_value`

---

# 6. Registry design

Define advanced flags per tab.

Example:

```python
ADVANCED_FLAGS: dict[str, tuple[AdvancedFlagDef, ...]] = {
    "upload-folder": (
        AdvancedFlagDef(
            key="recursive",
            flag="recursive",
            label="Scan subdirectories recursively",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="date-from-name",
            flag="date-from-name",
            label="Use date from filename",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="ignore-sidecar",
            flag="ignore-sidecar-files",
            label="Ignore sidecar files",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="time-zone",
            flag="time-zone",
            label="Time zone override",
            kind="text",
            placeholder="UTC or America/New_York",
        ),
        AdvancedFlagDef(
            key="album-path-joiner",
            flag="album-path-joiner",
            label="Album path joiner",
            kind="text",
            placeholder=" / ",
        ),
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
            placeholder=".jpg,.heic,.mp4",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
            placeholder=".thm,.xmp",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
            placeholder="@eaDir/\n.DS_Store",
        ),
        AdvancedFlagDef(
            key="tag",
            flag="tag",
            label="Custom tags",
            kind="csv_repeat",
            placeholder="vacation, family/reunion",
        ),
        AdvancedFlagDef(
            key="session-tag",
            flag="session-tag",
            label="Session tag",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="folder-tags",
            flag="folder-as-tags",
            label="Folder as tags",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="overwrite",
            flag="overwrite",
            label="Overwrite existing",
            kind="bool",
            default=False,
            warn_values={
                True: "Overwrite mode will replace existing files on the server."
            },
        ),
        AdvancedFlagDef(
            key="pause-jobs",
            flag="pause-immich-jobs",
            label="Pause Immich background jobs",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="manage-epson",
            flag="manage-epson-fastfoto",
            label="Manage Epson FastFoto photos",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
        AdvancedFlagDef(
            key="api-trace",
            flag="api-trace",
            label="Enable API trace",
            kind="bool",
            default=False,
        ),
    ),
}
```

Do the same for:

- `upload-gp`
- `upload-immich`
- `archive-folder`
- `archive-immich`
- `stack`

---

# 7. Important flag cleanup before implementation

Before generating the new advanced UI, the agent must clean up known contract problems.

## 7.1 Remove unsupported GP `into-album`
Current code exposes `into-album` for Google Photos, but the CLI documentation does not list it for `upload from-google-photos`.

Unless live binary help proves otherwise:

- remove `into-album` from `upload-gp`
- remove it from UI
- remove it from state
- remove it from tests

## 7.2 Verify stack `date-range`
The supplied CLI guide does not clearly document `--date-range` for `stack`.

The agent must run:

```bash
/home/shsrra/.immich-go-gui/bin/immich-go stack --help
```

Then:

- if `date-range` exists, keep it
- if not, remove it from stack advanced flags and schema

## 7.3 Use live binary help as the authority
The agent should verify every advanced flag against:

```bash
immich-go <command> <subcommand> --help
```

Do not preserve flags just because the old GUI had them.

---

# 8. UI implementation

## 8.1 Create a reusable Qt row widget

Add a custom widget in `app.py` or a new `widgets/advanced_flag_row.py`.

### Recommended widget structure

```python
class AdvancedFlagRow(QWidget):
    def __init__(self, def_: AdvancedFlagDef, parent=None):
        super().__init__(parent)
        self.def_ = def_

        self.enable = QCheckBox(f"--{def_.flag}")
        self.enable.setObjectName("AdvancedFlagEnable")
        self.enable.setChecked(False)
        self.enable.setToolTip(def_.label)

        self.value_widget = self._create_value_widget()
        self.value_widget.setEnabled(False)

        self.enable.toggled.connect(self.value_widget.setEnabled)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.enable)
        layout.addWidget(self.value_widget, 1)
```

---

## 8.2 Value widget creation

```python
def _create_value_widget(self):
    kind = self.def_.kind

    if kind == "bool":
        w = QComboBox()
        w.addItems(["true", "false"])
        w.setCurrentText("true")
        return w

    if kind == "enum":
        w = QComboBox()
        w.addItems(list(self.def_.options))
        if self.def_.default is not None:
            w.setCurrentText(str(self.def_.default))
        return w

    if kind == "int":
        w = QSpinBox()
        w.setRange(0, 999999)
        if isinstance(self.def_.default, int):
            w.setValue(self.def_.default)
        return w

    if kind == "duration_minutes":
        w = QSpinBox()
        w.setRange(1, 1440)
        w.setSuffix(" minutes")
        if isinstance(self.def_.default, int):
            w.setValue(self.def_.default)
        else:
            w.setValue(20)
        return w

    if kind == "lines_repeat":
        w = QPlainTextEdit()
        w.setPlaceholderText(self.def_.placeholder)
        w.setMaximumHeight(80)
        return w

    # text, extensions, csv_repeat, date_range
    w = QLineEdit()
    w.setPlaceholderText(self.def_.placeholder)
    return w
```

---

## 8.3 State getters/setters

```python
def get_value(self):
    kind = self.def_.kind

    if kind == "bool":
        return self.value_widget.currentText() == "true"

    if kind in ("int", "duration_minutes"):
        return self.value_widget.value()

    if kind == "lines_repeat":
        return self.value_widget.toPlainText()

    return self.value_widget.text()

def set_value(self, value):
    kind = self.def_.kind

    if kind == "bool":
        self.value_widget.setCurrentText("true" if value else "false")

    elif kind in ("int", "duration_minutes"):
        try:
            self.value_widget.setValue(int(value))
        except Exception:
            pass

    elif kind == "lines_repeat":
        self.value_widget.setPlainText(str(value or ""))

    else:
        self.value_widget.setText(str(value or ""))

def state(self) -> dict:
    return {
        "enabled": self.enable.isChecked(),
        "value": self.get_value(),
    }

def set_state(self, state: dict):
    self.enable.blockSignals(True)
    self.value_widget.blockSignals(True)
    try:
        self.enable.setChecked(bool(state.get("enabled", False)))
        self.set_value(state.get("value", self.def_.default))
        self.value_widget.setEnabled(self.enable.isChecked())
    finally:
        self.enable.blockSignals(False)
        self.value_widget.blockSignals(False)
```

---

# 9. Replace advanced cards with generated rows

## 9.1 Add row storage in main window

In `ImmichGoGUI.__init__`:

```python
self.adv_rows: dict[str, dict[str, AdvancedFlagRow]] = {}
```

---

## 9.2 Add a generic advanced card builder

```python
def _build_advanced_flags_card(self, tab_key: str):
    from core.advanced_flags import ADVANCED_FLAGS

    card = Card("Advanced Flags")
    form = FormSection()

    hint = QLabel(
        "Advanced flags are disabled by default. "
        "Disabled flags are not passed to immich-go."
    )
    hint.setObjectName("Hint")
    hint.setWordWrap(True)
    form.addRow("", hint)

    self.adv_rows[tab_key] = {}

    for def_ in ADVANCED_FLAGS.get(tab_key, ()): 
        row = AdvancedFlagRow(def_)
        self.adv_rows[tab_key][def_.key] = row
        form.addRow("", row)

    card.layout.addLayout(form)
    card.setVisible(False)
    self.adv_frames.append(card)
    return card
```

---

## 9.3 Use it in each tab builder

Replace the existing manually built “Advanced Options” cards with:

```python
adv_card = self._build_advanced_flags_card("upload-folder")
lay.addWidget(adv_card)
```

Do this for:

- `upload-folder`
- `upload-gp`
- `upload-immich`
- `archive-folder`
- `archive-immich`
- `stack`

Then delete the old advanced widget creation code for migrated flags.

---

# 10. State collection

## 10.1 Collect advanced state

Add:

```python
def _collect_advanced_state(self, tab_key: str | None = None) -> dict:
    if tab_key is not None:
        rows = self.adv_rows.get(tab_key, {})
        return {key: row.state() for key, row in rows.items()}

    return {
        tab: {key: row.state() for key, row in rows.items()}
        for tab, rows in self.adv_rows.items()
    }
```

---

## 10.2 Apply advanced state

```python
def _apply_advanced_state(self, state: dict):
    if not isinstance(state, dict):
        return

    for tab_key, flags in state.items():
        rows = self.adv_rows.get(tab_key, {})
        if not isinstance(flags, dict):
            continue

        for key, row_state in flags.items():
            row = rows.get(key)
            if row is not None and isinstance(row_state, dict):
                row.set_state(row_state)
```

---

# 11. Command builder integration

The builder should receive advanced state explicitly.

## 11.1 Update `build_plan_from_state`

Add a new optional argument:

```python
def build_plan_from_state(
    tab_key: str,
    config_state: dict,
    tab_state: dict,
    binary_path: str = "./immich-go",
    dry_run: bool = False,
    base_env: dict[str, str] | None = None,
    strict_schema: bool = False,
    advanced_state: dict | None = None,
) -> CommandPlan:
```

---

## 11.2 Remove migrated advanced flags from old hardcoded logic

For every flag moved into `ADVANCED_FLAGS`, remove the old manual emission code from `command_builder.py`.

Examples:

- `time-zone`
- `log-level`
- `api-trace`
- `recursive`
- `date-from-name`
- `include-type`
- `include-ext`
- `exclude-ext`
- `ban-file`
- `tag`
- `session-tag`
- `folder-tags`
- `overwrite`
- `pause-jobs`
- `manage-epson`
- `include-archived`
- `include-partner`
- `sync-albums`
- `takeout-tag`
- `people-tag`
- `include-trashed`
- `include-unmatched`
- `include-untitled-albums`
- `from-album-name`
- `partner-album`
- etc.

Do not keep both old and new emission paths for the same flag.

---

## 11.3 Add generic advanced-flag emission

In `core/advanced_flags.py`, add pure helpers.

### Value-to-argv helper

```python
def advanced_flag_args(def_: AdvancedFlagDef, value: Any) -> list[str]:
    flag = def_.flag

    if def_.kind == "bool":
        if value:
            return [f"--{flag}"]
        return [f"--{flag}=false"]

    if value is None:
        return []

    if def_.kind == "text":
        text = str(value).strip()
        if not text:
            return []
        return [f"--{flag}={text}"]

    if def_.kind == "enum":
        text = str(value).strip()
        if not text:
            return []
        return [f"--{flag}={text}"]

    if def_.kind == "int":
        return [f"--{flag}={int(value)}"]

    if def_.kind == "duration_minutes":
        return [f"--{flag}={int(value)}m"]

    if def_.kind == "date_range":
        cleaned = clean_date_range(str(value))
        if not cleaned:
            return []
        return [f"--{flag}={cleaned}"]

    if def_.kind == "extensions":
        normalized = normalize_extensions_csv(str(value))
        if not normalized:
            return []
        return [f"--{flag}={normalized}"]

    if def_.kind == "csv_repeat":
        items = normalize_list_csv(str(value))
        return [f"--{flag}={item}" for item in items if item]

    if def_.kind == "lines_repeat":
        args = []
        for line in str(value).splitlines():
            line = line.strip()
            if line:
                args.append(f"--{flag}={line}")
        return args

    return []
```

---

### Apply advanced flags to plan

```python
def apply_advanced_flags_to_plan(
    plan: CommandPlan,
    emitter: FlagEmitter,
    tab_key: str,
    advanced_state: dict,
):
    from .cli_schema import flag_allowed_for_tab

    for def_ in ADVANCED_FLAGS.get(tab_key, ()): 
        entry = advanced_state.get(def_.key)
        if not entry or not entry.get("enabled"):
            continue

        value = entry.get("value", def_.default)

        # Secret advanced flags go to env, not argv
        if def_.secret_env:
            if value:
                plan.env[def_.secret_env] = str(value)
            continue

        args = advanced_flag_args(def_, value)
        if not args:
            continue

        if not flag_allowed_for_tab(tab_key, def_.flag):
            emitter.errors.append(
                f"Flag '--{def_.flag}' is not allowed for tab '{tab_key}'"
            )
            continue

        emitter.opts.extend(args)

        warning = def_.warn_values.get(value)
        if warning:
            plan.warnings.append(warning)
```

---

## 11.4 Call it from `build_plan_from_state`

Near the end of `build_plan_from_state`, before finalizing `plan.argv`:

```python
if advanced_state:
    apply_advanced_flags_to_plan(
        plan=plan,
        emitter=emitter,
        tab_key=tab_key,
        advanced_state=advanced_state,
    )
```

---

# 12. GUI plan building update

Update `build_plan()` in `app.py`:

```python
def build_plan(self, dry_run: bool) -> CommandPlan:
    tab_key = self._get_active_tab_key()
    if tab_key == "config":
        return CommandPlan(errors=["No executable tab selected."], tab_key=tab_key)

    config_state = self._collect_config_state()
    tab_state = self._collect_tab_state(tab_key)
    advanced_state = self._collect_advanced_state(tab_key)

    binary_path = getattr(self, "binary_path", "")
    if not binary_path:
        binary_path = get_binary_path(load_binary_metadata()) or "./immich-go"

    return build_plan_from_state(
        tab_key=tab_key,
        config_state=config_state,
        tab_state=tab_state,
        binary_path=binary_path,
        dry_run=dry_run,
        advanced_state=advanced_state,
    )
```

---

# 13. Validation integration

Only validate enabled advanced flags.

Add a pure validator in `core/advanced_flags.py`:

```python
def validate_advanced_state(tab_key: str, advanced_state: dict) -> ValidationResult:
    res = ValidationResult()

    for def_ in ADVANCED_FLAGS.get(tab_key, ()): 
        entry = advanced_state.get(def_.key)
        if not entry or not entry.get("enabled"):
            continue

        value = entry.get("value", def_.default)

        if def_.kind == "date_range":
            text = str(value or "").strip()
            if text:
                ok, err = validate_date_range(text)
                if not ok:
                    res.errors.append(f"Invalid {def_.label}: {err}")

        elif def_.kind in ("text", "extensions", "csv_repeat", "lines_repeat"):
            text = str(value or "").strip()
            if not text and not def_.allow_empty:
                res.errors.append(f"{def_.label} is enabled but empty.")

    return res
```

Then merge this into GUI validation:

```python
def validate_inputs(self) -> ValidationResult:
    tab_key = self._get_active_tab_key()
    if tab_key == "config":
        return ValidationResult()

    config_state = self._collect_config_state()
    tab_state = self._collect_tab_state(tab_key)
    advanced_state = self._collect_advanced_state(tab_key)

    base = validate_state(
        tab_key=tab_key,
        config_state=config_state,
        tab_state=tab_state,
    )

    adv = validate_advanced_state(tab_key, advanced_state)

    base.errors.extend(adv.errors)
    base.warnings.extend(adv.warnings)
    return base
```

---

# 14. Persistence integration

## 14.1 Save advanced state

Update `collect_form_state()` or `save_configuration()` so the saved form state includes advanced row state.

Recommended structure:

```python
{
    "fields": {
        "upload-folder": { ... simple fields only ... },
        "upload-gp": { ... },
    },
    "advanced": {
        "upload-folder": {
            "time-zone": {"enabled": True, "value": "UTC"},
            "recursive": {"enabled": True, "value": False},
        },
        "upload-gp": {
            "include-trashed": {"enabled": True, "value": True},
        },
    },
}
```

If you need backward compatibility with the old flat format, detect it:

```python
if "fields" in state or "advanced" in state:
    fields_state = state.get("fields", {})
    advanced_state = state.get("advanced", {})
else:
    fields_state = state
    advanced_state = {}
```

---

## 14.2 Load advanced state

After applying simple field state:

```python
self._apply_advanced_state(advanced_state)
```

---

## 14.3 Migration rule
When migrating from the old advanced widgets:

- preserve old values if possible
- set all advanced enable checkboxes to **false**

Do **not** auto-enable old advanced values.

---

# 15. Simple/Advanced mode behavior

Keep the existing Simple/Advanced switch, but update its meaning:

## Simple mode
- hides advanced flag rows
- ignores advanced flag state completely

## Advanced mode
- shows advanced flag rows
- still does not enable anything automatically

Implementation:

```python
def toggle_advanced(self, checked):
    self.is_advanced = checked
    if hasattr(self, "app_config"):
        self.app_config.advanced_mode = checked

    if hasattr(self, "lbl_mode"):
        self.lbl_mode.setText("Advanced" if checked else "Simple")

    for w in getattr(self, "adv_frames", []):
        w.setVisible(checked)

    self.update_status()
```

No extra logic is needed if command building already ignores advanced rows in Simple mode.

But to be extra safe, you can also do:

```python
def _collect_advanced_state(self, tab_key: str | None = None) -> dict:
    if not getattr(self, "is_advanced", False):
        return {}
    ...
```

This guarantees Simple mode never leaks advanced flags.

---

# 16. Reset advanced flags

Add a UI action:

- menu item: **Reset Advanced Flags**
- or button inside each Advanced card

Implementation:

```python
def reset_advanced_flags(self, tab_key: str | None = None):
    tabs = [tab_key] if tab_key else list(self.adv_rows.keys())

    for t in tabs:
        for row in self.adv_rows.get(t, {}).values():
            row.set_state({
                "enabled": False,
                "value": row.def_.default,
            })

    self.update_status()
```

Recommended default:
- reset current tab if invoked from a tab
- reset all tabs if invoked from menu

---

# 17. Surface `plan.errors`

This is mandatory.

The current app can still hide schema/emitter errors too easily.

Update:

- `show_confirm_dialog()`
- `run_command()`
- preferably `update_status()`

to check `plan.errors`.

Minimum requirement:

```python
plan = self.build_plan(dry_run=is_dry_run)
if plan.errors:
    QMessageBox.critical(
        self,
        "Command Build Errors",
        "\n".join(f"• {e}" for e in plan.errors)
    )
    return
```

Better:
- disable Run/Preview if `plan.errors` exists
- show first error in status card

---

# 18. Secret advanced flags

Some optional flags are secrets, for example:

- `from-admin-api-key`

Do not pass these in argv.

Use `secret_env` in the flag definition:

```python
AdvancedFlagDef(
    key="from-admin-api-key",
    flag="from-admin-api-key",
    label="Source admin API key",
    kind="text",
    secret_env="IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY",
)
```

Then the generic emitter puts the value into `plan.env`, not `plan.argv`.

### Important
Secret advanced rows should use password-style input if they remain visible in the UI.

If possible, do not persist secret values in `form_state`.

---

# 19. Flags to move into the advanced registry

Below is the recommended split.

## 19.1 `upload-folder`

### Keep as simple/curated
- source path
- folder-as-album
- into-album
- manage-burst
- manage-raw-jpeg
- manage-heic-jpeg

### Move to advanced opt-in
- include-type
- date-range
- include-extensions
- exclude-extensions
- ban-file
- recursive
- date-from-name
- ignore-sidecar-files
- album-path-joiner
- folder-as-tags
- tag
- session-tag
- overwrite
- pause-immich-jobs
- time-zone
- manage-epson-fastfoto
- on-errors
- log-level
- api-trace

---

## 19.2 `upload-gp`

### Keep as simple/curated
- takeout source path
- manage-burst
- manage-heic-jpeg

### Move to advanced opt-in
- include-type
- include-unmatched
- include-archived
- include-partner
- include-trashed
- sync-albums
- include-untitled-albums
- from-album-name
- partner-shared-album
- takeout-tag
- people-tag
- manage-raw-jpeg
- manage-epson-fastfoto
- date-range
- include-extensions
- exclude-extensions
- ban-file
- tag
- session-tag
- overwrite
- on-errors
- pause-immich-jobs
- time-zone
- log-level
- api-trace

### Remove
- `into-album` unless live binary help proves support

---

## 19.3 `upload-immich`

### Keep as simple required
- source server
- source API key

### Move to advanced opt-in
- from-admin-api-key
- from-client-timeout
- from-favorite
- from-archived
- from-trash
- from-partners
- from-no-album
- from-date-range
- from-albums
- from-minimal-rating
- from-people
- from-tags
- from-city
- from-state
- from-country
- from-make
- from-model
- from-include-type
- from-include-extensions
- from-exclude-extensions
- from-time-zone
- from-device-uuid
- from-skip-verify-ssl
- from-api-trace
- from-pause-immich-jobs
- destination tag
- destination session-tag
- destination overwrite
- destination time-zone
- destination manage-burst
- destination manage-raw-jpeg
- destination manage-heic-jpeg
- destination manage-epson-fastfoto
- destination api-trace
- on-errors
- log-level

---

## 19.4 `archive-folder`

### Keep as simple required
- source path
- destination folder

### Move to advanced opt-in
- date-range
- include-type
- include-extensions
- exclude-extensions
- ban-file
- recursive
- date-from-name
- ignore-sidecar-files
- folder-as-album
- folder-as-tags
- into-album
- album-path-joiner
- on-errors
- log-level

---

## 19.5 `archive-immich`

### Keep as simple required
- destination folder
- source server display/configuration reference

### Move to advanced opt-in
- from-date-range
- from-albums
- from-favorite
- from-archived
- from-trash
- from-no-album
- from-partners
- from-minimal-rating
- from-people
- from-tags
- from-city
- from-state
- from-country
- from-make
- from-model
- from-include-type
- from-include-extensions
- from-exclude-extensions
- from-time-zone
- from-device-uuid
- from-client-timeout
- from-skip-verify-ssl
- from-api-trace
- from-pause-immich-jobs
- log-level

---

## 19.6 `stack`

### Option A — conservative
Keep as simple:
- manage-burst
- manage-raw-jpeg
- manage-heic-jpeg

Move to advanced:
- date-range (only if verified)
- time-zone
- manage-epson-fastfoto
- pause-immich-jobs
- log-level
- api-trace

### Option B — fully unified
Move even stacking rules into advanced rows:

```text
[ ] --manage-burst        [ Stack ▼ ]
[ ] --manage-raw-jpeg     [ StackCoverRaw ▼ ]
[ ] --manage-heic-jpeg    [ StackCoverJPG ▼ ]
```

Option B is more consistent, but Option A is easier for users.

Recommendation:
- start with Option A
- migrate to Option B later if you want absolute consistency

---

# 20. Tests to update/add

This change will break old tests. That is expected.

## 20.1 Fix duplicate test names first
Before adding new tests, rename duplicated test functions in `test_app.py`.

Duplicate names silently override earlier tests.

---

## 20.2 Add generic advanced-row tests

### Disabled flag is not emitted
```python
def test_advanced_flag_disabled_not_emitted(gui):
    gui.toggle_advanced(True)

    gui.adv_rows["upload-folder"]["time-zone"].set_state({
        "enabled": False,
        "value": "UTC",
    })

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(False)
    assert "--time-zone=UTC" not in plan.argv
```

---

### Enabled text flag is emitted
```python
def test_advanced_flag_enabled_text_emitted(gui):
    gui.toggle_advanced(True)

    gui.adv_rows["upload-folder"]["time-zone"].set_state({
        "enabled": True,
        "value": "UTC",
    })

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(False)
    assert "--time-zone=UTC" in plan.argv
```

---

### Enabled boolean false is emitted
```python
def test_advanced_bool_false_emitted(gui):
    gui.toggle_advanced(True)

    gui.adv_rows["upload-folder"]["recursive"].set_state({
        "enabled": True,
        "value": False,
    })

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(False)
    assert "--recursive=false" in plan.argv
```

---

### Enabled boolean true is emitted as presence
```python
def test_advanced_bool_true_emitted_as_presence(gui):
    gui.toggle_advanced(True)

    gui.adv_rows["upload-gp"]["include-trashed"].set_state({
        "enabled": True,
        "value": True,
    })

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-gp"]["path"].setPlainText("/takeout")

    plan = gui.build_plan(False)
    assert "--include-trashed" in plan.argv
```

---

### Simple mode ignores advanced rows
```python
def test_simple_mode_ignores_advanced_flags(gui):
    gui.toggle_advanced(False)

    gui.adv_rows["upload-folder"]["time-zone"].set_state({
        "enabled": True,
        "value": "UTC",
    })

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(False)
    assert "--time-zone=UTC" not in plan.argv
```

---

## 20.3 Update golden tests

Minimal golden tests should now expect **no advanced flags** unless rows are explicitly enabled.

Example:

```python
def test_golden_upload_folder_simple(gui):
    gui.toggle_advanced(False)

    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    plan = gui.build_plan(False)

    assert plan.argv == [
        "upload",
        "from-folder",
        "--server=http://localhost:2283",
        "/photos",
    ]
```

Advanced golden tests must explicitly enable rows.

---

# 21. Manual verification with the real binary

The agent should verify the new behavior manually.

## 21.1 Verify CLI flags exist

```bash
/home/shsrra/.immich-go-gui/bin/immich-go upload from-folder --help
/home/shsrra/.immich-go-gui/bin/immich-go upload from-google-photos --help
/home/shsrra/.immich-go-gui/bin/immich-go upload from-immich --help
/home/shsrra/.immich-go-gui/bin/immich-go archive from-folder --help
/home/shsrra/.immich-go-gui/bin/immich-go archive from-immich --help
/home/shsrra/.immich-go-gui/bin/immich-go stack --help
```

Remove any advanced flag that is not present.

---

## 21.2 Verify simple-mode command is minimal

1. Open GUI
2. Simple mode on
3. Upload → From Folder
4. Enter:
   - server
   - API key
   - source path
5. Preview

Expected:

```bash
immich-go upload from-folder --server=http://localhost:2283 /path
```

No advanced flags should appear.

---

## 21.3 Verify advanced opt-in works

1. Switch to Advanced mode
2. Enable:
   - `--time-zone = UTC`
   - `--recursive = false`
   - `--log-level = DEBUG`
3. Preview

Expected:

```bash
immich-go upload from-folder \
  --server=http://localhost:2283 \
  --time-zone=UTC \
  --recursive=false \
  --log-level=DEBUG \
  /path
```

---

## 21.4 Verify disabled advanced values are ignored

1. Advanced mode on
2. Fill `--time-zone = UTC`
3. Leave the enable checkbox unchecked
4. Preview

Expected:

- no `--time-zone=UTC`

---

# 22. Implementation order for the agent

## Step 1 — Create core registry
- add `core/advanced_flags.py`
- define `AdvancedFlagDef`
- define `ADVANCED_FLAGS`
- add pure helpers for args/validation/emission

## Step 2 — Create Qt row widget
- add `AdvancedFlagRow`
- support all flag kinds
- add state get/set

## Step 3 — Replace advanced cards
- generate advanced cards from registry
- remove old advanced widgets
- remove old advanced keys from `self.inputs`

## Step 4 — Update command builder
- accept `advanced_state`
- apply advanced flags generically
- remove old hardcoded advanced emissions

## Step 5 — Update GUI state flow
- collect advanced state
- apply saved advanced state
- pass advanced state into `build_plan`
- ignore advanced state in Simple mode

## Step 6 — Update validation and errors
- validate only enabled advanced flags
- surface `plan.errors`

## Step 7 — Update persistence
- save advanced state
- load advanced state
- migrate old state safely with all advanced rows disabled

## Step 8 — Update tests
- fix duplicate test names
- rewrite golden tests
- add advanced-row tests
- add simple-mode suppression tests

---

# 23. Definition of Done

The implementation is complete only when:

## UI
- every advanced flag uses the same row pattern:
  ```text
  [checkbox] [flag] [options]
  ```
- all advanced rows are unchecked by default
- disabled rows are visually disabled
- Simple mode hides and ignores all advanced rows
- Advanced mode shows rows but does not auto-enable them

## Command generation
- no advanced flag is emitted unless its enable checkbox is checked
- boolean flags support both:
  - `--flag`
  - `--flag=false`
- value flags emit correct `--flag=value`
- repeatable flags emit multiple args correctly
- secret advanced flags go to env, not argv

## Correctness
- GP `into-album` is removed unless verified
- stack `date-range` is verified or removed
- all advanced flags are allowed by the tab schema
- `plan.errors` are shown to the user

## Persistence
- advanced row values persist
- advanced enabled state persists
- old saved state does not silently enable flags

## Tests
- no duplicate test names
- disabled advanced flags are not emitted
- enabled advanced flags are emitted correctly
- Simple mode ignores advanced flags
- golden tests reflect the new opt-in model

---

# 24. Recommended final policy

Use this exact product rule going forward:

> **Advanced flags are explicit overrides.**
> If the row is unchecked, the flag is not passed.
> If the row is checked, the flag is passed with the selected value.
> The GUI does not care whether the CLI default is true or false.

That is the cleanest model and exactly matches what you asked for:

```text
[checkbox for enabling flag] [flag] [flag options]
```

If you want, I can next turn this into:

1. a **file-by-file patch plan**, or  
2. a **ready-to-use `core/advanced_flags.py` starter implementation** with the full flag registry for all tabs.