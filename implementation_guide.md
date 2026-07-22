Here is the **short punch-list** to close Phase 1 completely.

I’m limiting this to the **must-fix items** first, then a few very small optional cleanups.

---

# Must-fix punch-list to close Phase 1

## 1) Make `upload-folder` and `archive-folder` paths absolute before building the command

### Why
`collect_paths()` already normalizes paths for `upload-gp`, but `upload-folder` and `archive-folder` still append the raw path. Since the external terminal runs from a temp directory, relative paths can break.

### File
`core/command_builder.py`

### Change
Replace the raw path append for these tabs.

#### Current pattern
```python
if tab_key == "upload-folder":
    if tab_state.get("path"):
        path_opt.append(tab_state["path"])
```

#### Replace with
```python
if tab_key == "upload-folder":
    raw_path = str(tab_state.get("path", "")).strip()
    if raw_path:
        path_opt.extend(collect_paths(raw_path))
```

#### Also do the same for `archive-folder`
```python
elif tab_key == "archive-folder":
    raw_path = str(tab_state.get("path", "")).strip()
    if raw_path:
        path_opt.extend(collect_paths(raw_path))
```

### Acceptance
- `~` expands correctly
- relative paths become absolute
- generated command no longer depends on terminal CWD

---

## 2) Restore destination / source validation warnings for archive tabs

### Why
`validate_destination_folder()` is imported but no longer used. You lost useful warnings like:
- destination inside source
- destination exists but is not a directory
- destination not writable

### File
`core/command_builder.py`

### Change
Update `validate_state()`.

#### For `upload-folder`
Replace the simple existence warning with expansion-based warnings:

```python
if tab_key == "upload-folder":
    p = tab_state.get("path", "").strip()
    if not p:
        result.errors.append("Source path is required.")
    else:
        _, path_warns = expand_source_paths(p)
        result.warnings.extend(path_warns)
```

#### For `archive-folder`
Replace the current minimal check with:

```python
elif tab_key == "archive-folder":
    p = tab_state.get("path", "").strip()
    w = tab_state.get("write-to", "").strip()

    if not p:
        result.errors.append("Source folder path is required.")
    if not w:
        result.errors.append("Destination folder is required.")

    if p and w:
        expanded_sources, path_warns = expand_source_paths(p)
        result.warnings.extend(path_warns)
        result.warnings.extend(validate_destination_folder(w, expanded_sources))
```

#### For `archive-immich`
Replace the current minimal check with:

```python
elif tab_key == "archive-immich":
    w = tab_state.get("write-to", "").strip()
    if not w:
        result.errors.append("Destination folder is required.")
    else:
        result.warnings.extend(validate_destination_folder(w, []))
```

### Optional but recommended
Also make `expand_source_paths()` normalize paths consistently.

### File
`core/validation.py`

#### Suggested replacement
```python
def expand_source_paths(raw_text: str) -> tuple[list[str], list[str]]:
    expanded: list[str] = []
    warnings: list[str] = []

    for line in raw_text.splitlines():
        item = line.strip()
        if not item:
            continue

        item = os.path.expanduser(item)
        if not os.path.isabs(item):
            item = os.path.abspath(item)

        matches = glob.glob(item, recursive=True)
        if matches:
            expanded.extend(sorted(matches))
        elif os.path.exists(item):
            expanded.append(item)
        else:
            warnings.append(f"Source path does not exist: {item}")

    return expanded, warnings
```

### Acceptance
- archive destination warnings are back
- upload-folder path warnings are more consistent
- relative paths and `~` behave sanely in validation too

---

## 3) Fix `CompatibilityReport.is_fully_compatible()` so missing fixtures cannot count as compatible

### Why
Right now, if fixtures are missing, `supported=False` but `missing_flags_by_tab` may be empty, so `is_fully_compatible()` can still return `True`.

### File
`core/cli_contract.py`

### Change
Replace:

```python
def is_fully_compatible(self) -> bool:
    return not any(self.missing_flags_by_tab.values())
```

with:

```python
def is_fully_compatible(self) -> bool:
    return self.supported and not any(self.missing_flags_by_tab.values())
```

### Acceptance
- missing fixtures now correctly mean “not fully compatible”
- compatibility status becomes trustworthy

---

## 4) Make the compatibility dialog merge fixture + live-binary results

### Why
The dialog currently computes `live_report`, but still displays mostly the fixture report. Live-binary missing/unknown flags can be hidden.

### File
`app.py`

### Change
Inside `show_cli_compatibility_dialog()`, replace the current report-display logic with merged logic.

#### Use this after `report` and `live_report` are created
```python
missing = {
    tab: set(flags)
    for tab, flags in report.missing_flags_by_tab.items()
}
unknown = {
    tab: set(flags)
    for tab, flags in report.unknown_flags_by_tab.items()
}

supported = bool(report.supported)
notes = list(report.notes)

if live_report:
    supported = supported and bool(live_report.supported)
    notes.extend(live_report.notes)

    for tab, flags in live_report.missing_flags_by_tab.items():
        missing.setdefault(tab, set()).update(flags)

    for tab, flags in live_report.unknown_flags_by_tab.items():
        unknown.setdefault(tab, set()).update(flags)

fully_compatible = supported and not any(missing.values())
```

#### Then replace the status block with
```python
if live_report and fully_compatible:
    msg.append("Status: Fully Compatible with fixtures and live binary")
elif fully_compatible:
    msg.append("Status: Fully Compatible with target schema")
else:
    msg.append("Status: Compatibility Warning")
```

#### Then display `notes`, `missing`, and `unknown` from the merged variables
Example:

```python
if notes:
    msg.append("")
    msg.append("Notes:")
    for note in notes:
        msg.append(f"• {note}")

if missing:
    msg.append("")
    msg.append("Missing flags:")
    for tab, flags in missing.items():
        msg.append(f"[{tab}]")
        for flag in sorted(flags):
            msg.append(f"  - {flag}")

if unknown:
    msg.append("")
    msg.append("Unknown flags:")
    for tab, flags in unknown.items():
        msg.append(f"[{tab}]")
        for flag in sorted(flags):
            msg.append(f"  - {flag}")
```

### Acceptance
- live-binary incompatibilities are visible
- fixture + live results are no longer disconnected
- missing fixtures cannot be masked by a clean live report or vice versa

---

# Tests to add after those fixes

Add these so the fixes stay fixed.

---

## Test 1: upload-folder path is absolutized

```python
def test_upload_folder_path_is_absolutized(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)

    gui.inputs["upload-folder"]["path"].setText("relative/folder")

    opts = gui.build_command(False)
    assert opts[-1]
    assert os.path.isabs(opts[-1])
```

---

## Test 2: archive-folder path is absolutized

```python
def test_archive_folder_path_is_absolutized(gui):
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)

    gui.inputs["archive-folder"]["path"].setText("relative/source")
    gui.inputs["archive-folder"]["write-to"].setText("/tmp/dest")

    opts = gui.build_command(False)
    assert opts[-1]
    assert os.path.isabs(opts[-1])
```

---

## Test 3: archive destination warnings are restored

```python
def test_archive_folder_destination_warnings(gui, tmp_path):
    src = tmp_path / "src"
    dest = src / "dest"
    src.mkdir()
    dest.mkdir()

    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)

    gui.inputs["archive-folder"]["path"].setText(str(src))
    gui.inputs["archive-folder"]["write-to"].setText(str(dest))

    validation = gui.validate_inputs()
    assert any("inside source" in w for w in validation.warnings)
```

---

## Test 4: missing fixtures are not “fully compatible”

```python
def test_missing_fixtures_not_fully_compatible(tmp_path):
    report = check_fixtures(tmp_path / "missing-fixtures")
    assert report.supported is False
    assert report.is_fully_compatible() is False
```

---

# Optional quick wins after Phase 1 closure

These are not required to call Phase 1 done, but they are cheap and worthwhile.

---

## A. Replace placeholder QSettings identity

### File
`app.py`

### Change
Replace:

```python
self.settings = QSettings("YourOrganization", "ImmichGoGUI")
```

with something real, e.g.:

```python
self.settings = QSettings("Shitan198u", "ImmichGoGUI")
```

---

## B. Debounce manual binary path checking

### File
`app.py`

### Why
Right now binary checking happens on every keystroke.

### Change
Use a debounce timer.

```python
self.binary_debounce = QTimer()
self.binary_debounce.setSingleShot(True)
self.binary_debounce.setInterval(400)
self.binary_debounce.timeout.connect(self._on_manual_binary_changed)

self.manual_binary_edit.textChanged.connect(lambda: self.binary_debounce.start())
```

---

## C. Make copied command include the binary path

### File
`core/command_builder.py`

### Change
If you want the copied command to be directly runnable, change:

```python
plan.display_argv = mask_command_for_display(plan.argv)
```

to:

```python
plan.display_argv = mask_command_for_display([binary_path] + plan.argv)
```

### Note
If you do this, verify the confirm dialog display still looks right, since it currently shows the binary path separately too.

---

# Final closure checklist

After doing the 4 must-fix items, verify:

- [ ] `upload-folder` path is absolute in generated command
- [ ] `archive-folder` path is absolute in generated command
- [ ] archive destination warnings are visible again
- [ ] missing compatibility fixtures are not reported as fully compatible
- [ ] compatibility dialog shows merged fixture + live-binary issues
- [ ] new tests pass
- [ ] existing golden tests still pass

---

# Bottom line

If you complete these **4 required changes**, then I would consider **Phase 1 fully closed**.

At that point, the app’s critical command-generation and safety foundation is solid enough to move on to the next phase.