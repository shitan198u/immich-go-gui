from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
)


class FormStateMixin:
    def collect_form_state(self) -> dict:
        secret_keys = {
            "api_key",
            "from-api-key",
            "admin_api_key",
            "from-admin-api-key",
            "target-server",
        }
        fields = {}
        for tab_key, widgets in self.inputs.items():
            tab_dict = {}
            for k, widget in widgets.items():
                if k in secret_keys:
                    continue
                if isinstance(widget, QLineEdit):
                    tab_dict[k] = widget.text()
                elif isinstance(widget, QPlainTextEdit):
                    tab_dict[k] = widget.toPlainText()
                elif isinstance(widget, QCheckBox):
                    tab_dict[k] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    tab_dict[k] = widget.currentText()
                elif isinstance(widget, QSpinBox):
                    tab_dict[k] = widget.value()
            if tab_dict:
                fields[tab_key] = tab_dict

        adv_state = {}
        for tab_key, rows in getattr(self, "adv_rows", {}).items():
            tab_adv = {}
            for k, row in rows.items():
                if k == "from-dry-run":
                    continue
                st = row.state()
                if (getattr(row, "def_", None) and row.def_.secret_env) or (
                    k in secret_keys
                ):
                    st = {"enabled": False, "value": ""}
                tab_adv[k] = st
            if tab_adv:
                adv_state[tab_key] = tab_adv

        return {
            "fields": fields,
            "advanced": adv_state,
        }

    def apply_form_state(self, state: dict) -> None:
        if not isinstance(state, dict):
            return

        if "fields" in state or "advanced" in state:
            fields_state = state.get("fields", {})
            advanced_state = state.get("advanced", {})
        else:
            fields_state = state
            advanced_state = {}

        secret_keys = {
            "api_key",
            "from-api-key",
            "admin_api_key",
            "from-admin-api-key",
            "target-server",
        }
        for tab_key, tab_dict in fields_state.items():
            if tab_key in self.inputs and isinstance(tab_dict, dict):
                for k, val in tab_dict.items():
                    if k in secret_keys:
                        continue
                    widget = self.inputs[tab_key].get(k)
                    if widget is None:
                        continue
                    try:
                        widget.blockSignals(True)
                        if isinstance(widget, QLineEdit) and isinstance(val, str):
                            widget.setText(val)
                        elif isinstance(widget, QPlainTextEdit) and isinstance(
                            val, str
                        ):
                            widget.setPlainText(val)
                        elif isinstance(widget, QCheckBox) and isinstance(val, bool):
                            widget.setChecked(val)
                        elif isinstance(widget, QComboBox) and isinstance(val, str):
                            widget.setCurrentText(val)
                        elif isinstance(widget, QSpinBox) and isinstance(
                            val, (int, float)
                        ):
                            widget.setValue(int(val))
                    finally:
                        widget.blockSignals(False)

        if isinstance(advanced_state, dict):
            for tab_key, tab_adv in advanced_state.items():
                rows = getattr(self, "adv_rows", {}).get(tab_key, {})
                if isinstance(tab_adv, dict):
                    for k, row_state in tab_adv.items():
                        row = rows.get(k)
                        if row is not None and isinstance(row_state, dict):
                            row.set_state(row_state)

    def _collect_config_state(self) -> dict:
        c = self.inputs.get("config", {})
        return {
            "server": c.get("server").text() if c.get("server") else "",
            "api_key": c.get("api_key").text().strip() if c.get("api_key") else "",
            "admin_api_key": c.get("admin_api_key").text().strip()
            if c.get("admin_api_key")
            else "",
            "secrets_provider": c.get("secret_provider").currentData()
            if c.get("secret_provider")
            else "keyring",
            "skip-ssl": c.get("skip-ssl").isChecked() if c.get("skip-ssl") else False,
            "client_timeout_minutes": c.get("client_timeout_minutes").value()
            if c.get("client_timeout_minutes")
            else 60,
        }

    def _collect_tab_state(self, tab_key: str) -> dict:
        return self._raw_tab_state(tab_key)

    def _raw_tab_state(self, tab_key: str) -> dict:
        if tab_key not in self.inputs:
            return {}
        c = self.inputs[tab_key]

        def get_text(k: str, default: str = "") -> str:
            w = c.get(k)
            if not w:
                return default
            if hasattr(w, "text"):
                return w.text()
            if hasattr(w, "toPlainText"):
                return w.toPlainText()
            return default

        def get_bool(k: str, default: bool = False) -> bool:
            w = c.get(k)
            if not w:
                return default
            if hasattr(w, "isChecked"):
                return w.isChecked()
            return default

        def get_combo(k: str, default: str = "") -> str:
            w = c.get(k)
            if not w:
                return default
            if hasattr(w, "currentText"):
                return w.currentText()
            return default

        def get_int(k: str, default: int = 0) -> int:
            w = c.get(k)
            if not w:
                return default
            if hasattr(w, "value"):
                return w.value()
            return default

        if tab_key == "upload-folder":
            return {
                "path": get_text("path"),
                "folder-album": get_combo("folder-album", "NONE"),
                "into-album": get_text("into-album"),
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
            }

        elif tab_key == "upload-gp":
            return {
                "path": get_text("path"),
                "include-partner": get_bool("include-partner", True),
                "sync-albums": get_bool("sync-albums", True),
                "include-archived": get_bool("include-archived", True),
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
            }

        elif tab_key == "upload-icloud":
            return {
                "path": get_text("path"),
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
            }

        elif tab_key == "upload-picasa":
            return {
                "path": get_text("path"),
                "folder-album": get_combo("folder-album", "NONE"),
                "into-album": get_text("into-album"),
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
            }

        elif tab_key == "upload-immich":
            return {
                "from-server": get_text("from-server"),
                "from-api-key": get_text("from-api-key"),
                "from-date-range": get_text("from-date-range"),
                "from-albums": get_text("from-albums"),
            }

        elif tab_key == "archive-folder":
            return {
                "path": get_text("path"),
                "write-to": get_text("write-to"),
            }

        elif tab_key == "archive-gp":
            return {
                "path": get_text("path"),
                "write-to": get_text("write-to"),
                "include-partner": get_bool("include-partner", True),
                "sync-albums": get_bool("sync-albums", True),
                "include-archived": get_bool("include-archived", True),
            }

        elif tab_key == "archive-icloud" or tab_key == "archive-picasa":
            return {
                "path": get_text("path"),
                "write-to": get_text("write-to"),
            }

        elif tab_key == "archive-immich":
            return {
                "write-to": get_text("write-to"),
                "from-date-range": get_text("from-date-range"),
                "from-albums": get_text("from-albums"),
            }

        elif tab_key == "stack":
            return {
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
            }

        return {}

    def _collect_advanced_state(self, tab_key: str | None = None) -> dict | None:
        if not getattr(self, "is_advanced", False):
            return None
        if tab_key is not None:
            rows = getattr(self, "adv_rows", {}).get(tab_key, {})
            return {key: row.state() for key, row in rows.items()}
        return {
            tab: {key: row.state() for key, row in rows.items()}
            for tab, rows in getattr(self, "adv_rows", {}).items()
        }
