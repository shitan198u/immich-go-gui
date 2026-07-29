from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from gui.widgets.cards import spin_with_unit_label


class AdvancedFlagRow(QWidget):
    def __init__(self, def_, parent=None):
        super().__init__(parent)
        self.def_ = def_

        self.enable = QCheckBox(f"--{def_.flag}")
        self.enable.setObjectName("AdvancedFlagEnable")
        self.enable.setChecked(False)
        tooltip = self.def_.hint or self.def_.label
        self.enable.setToolTip(tooltip)

        self.value_widget = self._create_value_widget()
        self.value_widget.setEnabled(False)

        self.enable.toggled.connect(self.value_widget.setEnabled)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.enable, 0)
        if self.def_.kind == "duration_minutes":
            layout.addWidget(spin_with_unit_label(self.value_widget, "min"), 1)
        else:
            layout.addWidget(self.value_widget, 1)

    def _create_value_widget(self):
        kind = self.def_.kind

        if kind == "bool":
            w = QComboBox()
            w.addItems(["true", "false"])
            w.setCurrentText("true" if self.def_.default is not False else "false")
            return w

        if kind == "enum":
            w = QComboBox()
            w.addItems(list(self.def_.options))
            if self.def_.default is not None:
                w.setCurrentText(str(self.def_.default))
            return w

        if kind == "int":
            w = QSpinBox()
            # min/max from flags.toml (e.g. concurrent-tasks 1-20); wide fallback if omitted.
            w.setRange(
                self.def_.min_val if self.def_.min_val is not None else 0,
                self.def_.max_val if self.def_.max_val is not None else 999999,
            )
            if isinstance(self.def_.default, int):
                w.setValue(self.def_.default)
            if self.def_.hint:
                w.setToolTip(self.def_.hint)
            return w

        if kind == "duration_minutes":
            w = QSpinBox()
            w.setRange(1, 1440)
            if isinstance(self.def_.default, int):
                w.setValue(self.def_.default)
            else:
                w.setValue(20)
            if self.def_.hint:
                w.setToolTip(self.def_.hint)
            return w

        if kind == "lines_repeat":
            w = QPlainTextEdit()
            w.setPlaceholderText(self.def_.placeholder)
            w.setMaximumHeight(80)
            if self.def_.hint:
                w.setToolTip(self.def_.hint)
            return w

        # text, extensions, csv_repeat, date_range
        w = QLineEdit()
        if self.def_.secret_env:
            w.setEchoMode(QLineEdit.EchoMode.Password)
        w.setPlaceholderText(self.def_.placeholder)
        if self.def_.hint:
            w.setToolTip(self.def_.hint)
        return w

    def get_value(self):
        kind = self.def_.kind

        if kind == "bool":
            return self.value_widget.currentText() == "true"

        if kind == "enum":
            return self.value_widget.currentText()

        if kind in ("int", "duration_minutes"):
            return self.value_widget.value()

        if kind == "lines_repeat":
            return self.value_widget.toPlainText()

        return self.value_widget.text()

    def set_value(self, value):
        kind = self.def_.kind

        if kind == "bool":
            self.value_widget.setCurrentText("true" if bool(value) else "false")

        elif kind == "enum":
            self.value_widget.setCurrentText(str(value or ""))

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
        if not isinstance(state, dict):
            return
        self.enable.blockSignals(True)
        self.value_widget.blockSignals(True)
        try:
            is_enabled = bool(state.get("enabled", False))
            self.enable.setChecked(is_enabled)
            val = state.get("value", self.def_.default)
            if val is not None:
                self.set_value(val)
            self.value_widget.setEnabled(is_enabled)
        finally:
            self.enable.blockSignals(False)
            self.value_widget.blockSignals(False)
