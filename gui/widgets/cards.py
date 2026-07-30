from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    def __init__(self, title, required=False, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(18)
        title_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        title_layout.addWidget(title_label)
        if required:
            req_label = QLabel("Required")
            req_label.setObjectName("ReqBadge")
            title_layout.addWidget(req_label)
        title_layout.addStretch()
        self.layout.addLayout(title_layout)
        self.layout.addSpacing(16)


def spin_with_unit_label(spin: QWidget, unit: str) -> QWidget:
    """Place a spin box beside a static unit label (suffix text is not editable)."""
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    row.addWidget(spin)
    unit_lbl = QLabel(unit)
    unit_lbl.setObjectName("FieldLabel")
    row.addWidget(unit_lbl)
    row.addStretch()
    return container


class FormSection(QFormLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.setVerticalSpacing(16)
        self.setHorizontalSpacing(24)

    def add_row(self, label_text, widget, hint=""):
        lbl = QLabel(label_text)
        lbl.setObjectName("FieldLabel")
        if isinstance(widget, QPlainTextEdit):
            widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        elif isinstance(widget, QWidget):
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if hint:
            container = QVBoxLayout()
            container.setContentsMargins(0, 0, 0, 0)
            container.setSpacing(4)
            container.addWidget(widget)
            hint_lbl = QLabel(hint)
            hint_lbl.setObjectName("Hint")
            container.addWidget(hint_lbl)
            self.addRow(lbl, container)
        else:
            self.addRow(lbl, widget)
