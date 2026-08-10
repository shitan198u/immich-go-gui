from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.advanced_flags import ADVANCED_FLAGS
from gui.widgets import AdvancedFlagRow, Card, FormSection
from theme import load_themed_icon


class FormHelpersMixin:
    def _make_field_error_label(self) -> QLabel:
        lbl = QLabel("")
        lbl.setObjectName("FieldError")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #E06C75; font-size: 12px;")
        lbl.hide()
        return lbl

    def _register_field_error_label(
        self, tab_key: str, field_key: str, label: QLabel
    ) -> None:
        self._field_error_labels[(tab_key, field_key)] = label

    def _wrap_with_field_error(
        self, tab_key: str, field_key: str, widget: QWidget
    ) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(widget)
        err = self._make_field_error_label()
        layout.addWidget(err)
        self._register_field_error_label(tab_key, field_key, err)
        self._bind_field_error_clear(tab_key, field_key, widget)
        return container

    def _bind_field_error_clear(self, tab_key: str, field_key: str, widget) -> None:
        def clear_error(*_args):
            self._clear_field_error(tab_key, field_key)

        if hasattr(widget, "textChanged"):
            widget.textChanged.connect(clear_error)
        elif hasattr(widget, "plainTextChanged"):
            widget.plainTextChanged.connect(clear_error)

    def _clear_field_error(self, tab_key: str, field_key: str) -> None:
        lbl = self._field_error_labels.get((tab_key, field_key))
        if lbl is not None:
            lbl.clear()
            lbl.hide()

    def _apply_field_errors(
        self, tab_key: str, field_errors: dict[str, str] | None
    ) -> None:
        field_errors = field_errors or {}
        for (label_tab, field_key), lbl in self._field_error_labels.items():
            if field_key in ("server", "api_key") or label_tab == tab_key:
                msg = field_errors.get(field_key, "")
            else:
                msg = ""
            if msg:
                lbl.setText(msg)
                lbl.show()
            else:
                lbl.clear()
                lbl.hide()

    def _add_ssl_skip_row(
        self,
        form: FormSection,
        tab_dict: dict,
        key: str = "skip-ssl",
        label_text: str = "Skip SSL Verification",
    ):
        chk_ssl = QCheckBox(label_text)
        tab_dict[key] = chk_ssl
        container = QVBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(4)
        container.addWidget(chk_ssl)
        warn_lbl = QLabel(
            "⚠️ Skipping SSL verification reduces security. "
            "Use only for trusted self-hosted servers with self-signed certificates."
        )
        warn_lbl.setObjectName("WarningHint")
        warn_lbl.setWordWrap(True)
        warn_lbl.setVisible(False)
        container.addWidget(warn_lbl)
        chk_ssl.toggled.connect(warn_lbl.setVisible)
        form.addRow("", container)
        return chk_ssl

    def _add_browse_action(self, line_edit: QLineEdit, title: str):
        theme = getattr(self, "theme_mode", "dark")
        action = line_edit.addAction(
            load_themed_icon("folder", theme), QLineEdit.ActionPosition.TrailingPosition
        )
        action.icon_name = "folder"
        action.triggered.connect(lambda: self._browse_into(line_edit, title))
        for child in line_edit.findChildren(QToolButton):
            child.setAutoRaise(True)
            child.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _browse_into(self, line_edit: QLineEdit, title: str):
        folder = QFileDialog.getExistingDirectory(
            self,
            title,
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            line_edit.setText(folder)

    def _build_advanced_flags_card(self, tab_key: str, schema_key: str | None = None):
        """Build an advanced-flags card.

        Args:
            tab_key: Storage key for ``adv_rows`` (also the default schema).
            schema_key: Optional different schema to source flag definitions
                from (e.g. the Monitor tab reuses "upload-folder" flags but
                stores rows under its own key).
        """
        card = Card("Advanced Flags")
        form = FormSection()

        hint = QLabel(
            "Advanced flags are disabled by default. "
            "Check the box next to a flag to enable it and pass it to immich-go."
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        form.addRow("", hint)

        if not hasattr(self, "adv_rows"):
            self.adv_rows = {}
        self.adv_rows[tab_key] = {}

        for def_ in ADVANCED_FLAGS.get(schema_key or tab_key, ()):
            row = AdvancedFlagRow(def_)
            row.enable.toggled.connect(lambda _, r=row: self._schedule_status_update())
            if hasattr(row.value_widget, "textChanged"):
                row.value_widget.textChanged.connect(
                    lambda *_, r=row: self._schedule_status_update()
                )
            elif hasattr(row.value_widget, "currentIndexChanged"):
                row.value_widget.currentIndexChanged.connect(
                    lambda _, r=row: self._schedule_status_update()
                )
            elif hasattr(row.value_widget, "valueChanged"):
                row.value_widget.valueChanged.connect(
                    lambda _, r=row: self._schedule_status_update()
                )
            self.adv_rows[tab_key][def_.key] = row
            form.addRow("", row)

        card.layout.addLayout(form)
        card.setVisible(False)
        self.adv_frames.append(card)
        return card
