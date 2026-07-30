from typing import cast

from PySide6.QtWidgets import QMessageBox, QWidget

from core import (
    AppConfig,
    SecretStore,
    default_config_dir,
    default_config_path,
    get_config_load_warning,
    get_secret_with_fallback,
    load_config,
    save_config,
    save_secret_with_fallback,
    save_server_url,
    set_api_key,
)
from theme import THEME_SYSTEM, normalize_theme_mode


class PersistenceMixin:
    def _migrate_legacy_qsettings_to_config(self):
        cfg = AppConfig()
        cfg.server_url = self.settings.value("server_url", "")
        cfg.skip_ssl = self.settings.value("skip_ssl", False, type=bool)
        cfg.theme_mode = normalize_theme_mode(
            self.settings.value("theme_mode", THEME_SYSTEM)
        )
        save_config(cfg)
        old_key = self.settings.value("api_key", "")
        if old_key:
            set_api_key(old_key, cfg)
            self.settings.remove("api_key")
            self.settings.sync()

    def load_configuration(self):
        from core.profile_manager import migrate_single_config_to_default

        migrate_single_config_to_default()
        self.app_config = load_config()

        if not default_config_path().exists():
            legacy_root = default_config_dir() / "config.toml"
            if not legacy_root.exists():
                self._migrate_legacy_qsettings_to_config()
            self.app_config = load_config()

        config_inputs = self.inputs["config"]
        secret_widgets = ("server", "api_key", "admin_api_key")
        for key in secret_widgets:
            widget = config_inputs.get(key)
            if widget is not None:
                widget.blockSignals(True)
        try:
            config_inputs["server"].setText(self.app_config.server_url)

            prof_name = getattr(self.app_config, "profile_name", "default")
            config_inputs["api_key"].setText(
                get_secret_with_fallback(
                    profile_name=prof_name,
                    key="api_key",
                    provider=self.app_config.secrets_provider,
                )
            )

            if "admin_api_key" in config_inputs:
                config_inputs["admin_api_key"].setText(
                    get_secret_with_fallback(
                        profile_name=prof_name,
                        key="admin_api_key",
                        provider=self.app_config.secrets_provider,
                    )
                )
        finally:
            for key in secret_widgets:
                widget = config_inputs.get(key)
                if widget is not None:
                    widget.blockSignals(False)

        if "skip-ssl" in self.inputs["config"]:
            self.inputs["config"]["skip-ssl"].setChecked(self.app_config.skip_ssl)

        if "client_timeout_minutes" in self.inputs["config"]:
            self.inputs["config"]["client_timeout_minutes"].setValue(
                self.app_config.client_timeout_minutes
            )

        if "secret_provider" in self.inputs["config"]:
            idx = self.inputs["config"]["secret_provider"].findData(
                self.app_config.secrets_provider
            )
            if idx >= 0:
                self.inputs["config"]["secret_provider"].setCurrentIndex(idx)

        if "allow_untested_updates" in self.inputs["config"]:
            self.inputs["config"]["allow_untested_updates"].setChecked(
                self.app_config.allow_untested_updates
            )

        if "preferred_terminal" in self.inputs["config"]:
            self.inputs["config"]["preferred_terminal"].setCurrentText(
                self.app_config.preferred_terminal
            )

        self.theme_mode = normalize_theme_mode(self.app_config.theme_mode)

        if hasattr(self, "theme_mode_combo"):
            self.theme_mode_combo.blockSignals(True)
            self.theme_mode_combo.setCurrentText(self.theme_mode)
            self.theme_mode_combo.blockSignals(False)

        self.apply_theme(self.theme_mode)
        self.toggle_advanced(self.app_config.advanced_mode)

        cfg_warning = get_config_load_warning()
        if cfg_warning:
            QMessageBox.warning(cast(QWidget, self), "Configuration Reset", cfg_warning)

        self.update_window_title()
        self._update_secret_status()
        self._mark_configuration_clean()
        self._mark_server_details_clean()

    def _collect_server_snapshot(self) -> dict:
        config_inputs = self.inputs.get("config", {})
        return {
            "server_url": config_inputs.get("server").text()
            if config_inputs.get("server")
            else "",
            "api_key": config_inputs.get("api_key").text().strip()
            if config_inputs.get("api_key")
            else "",
        }

    def _collect_persisted_state(self) -> dict:
        """Snapshot of application settings (track B) saved by save_configuration."""
        config_inputs = self.inputs.get("config", {})
        state = {
            "skip_ssl": config_inputs["skip-ssl"].isChecked()
            if config_inputs.get("skip-ssl")
            else False,
            "client_timeout_minutes": config_inputs["client_timeout_minutes"].value()
            if config_inputs.get("client_timeout_minutes")
            else 60,
            "secrets_provider": config_inputs["secret_provider"].currentData()
            if config_inputs.get("secret_provider")
            else "keyring",
            "allow_untested_updates": config_inputs[
                "allow_untested_updates"
            ].isChecked()
            if config_inputs.get("allow_untested_updates")
            else False,
            "preferred_terminal": config_inputs["preferred_terminal"].currentText()
            if config_inputs.get("preferred_terminal")
            else "auto",
            "theme_mode": self.theme_mode_combo.currentText()
            if hasattr(self, "theme_mode_combo")
            else normalize_theme_mode(self.theme_mode),
            "advanced_mode": bool(getattr(self, "is_advanced", False)),
            "admin_api_key": config_inputs.get("admin_api_key").text().strip()
            if config_inputs.get("admin_api_key")
            else "",
        }
        if state["secrets_provider"] is None:
            state["secrets_provider"] = "keyring"
        return state

    def _mark_configuration_clean(self) -> None:
        self._config_clean_snapshot = self._collect_persisted_state()

    def _mark_server_details_clean(self) -> None:
        self._server_clean_snapshot = self._collect_server_snapshot()

    def has_unsaved_changes(self) -> bool:
        if not hasattr(self, "_config_clean_snapshot"):
            return False
        return self._collect_persisted_state() != self._config_clean_snapshot

    def has_unsaved_server_details(self) -> bool:
        if not hasattr(self, "_server_clean_snapshot"):
            return False
        return self._collect_server_snapshot() != self._server_clean_snapshot

    def save_server_details(self, show_popup: bool = True):
        server_url = self.inputs["config"]["server"].text()
        self.app_config.server_url = server_url
        prof_name = getattr(self.app_config, "profile_name", "default")
        cfg_path = default_config_path(prof_name)
        try:
            save_server_url(server_url, path=cfg_path, profile_name=prof_name)
        except OSError as exc:
            QMessageBox.critical(
                cast(QWidget, self),
                "Save Failed",
                f"Could not write configuration to:\n{cfg_path}\n\n{exc}",
            )
            return

        prof_name = getattr(self.app_config, "profile_name", "default")
        api_key = self.inputs["config"]["api_key"].text().strip()
        try:
            res_api = save_secret_with_fallback(
                profile_name=prof_name,
                key="api_key",
                value=api_key,
                provider=self.app_config.secrets_provider,
            )
        except OSError as exc:
            QMessageBox.critical(
                cast(QWidget, self),
                "Save Failed",
                f"Could not save API key:\n{exc}",
            )
            return

        if show_popup:
            msg = "Server connection saved."
            if res_api.message:
                msg += f"\n\nNote (API Key): {res_api.message}"
            QMessageBox.information(
                cast(QWidget, self),
                "Saved",
                msg,
                QMessageBox.StandardButton.Ok,
            )
        self._update_secret_status()
        self._mark_server_details_clean()

    def _save_pending_configuration(self, show_popup: bool = False) -> None:
        """Persist whichever configuration tracks are dirty."""
        if self.has_unsaved_server_details():
            self.save_server_details(show_popup=show_popup)
            if self.has_unsaved_server_details():
                return  # server-details save failed; avoid a redundant error dialog
        if self.has_unsaved_changes():
            self.save_configuration(show_popup=show_popup)

    def _save_from_menu(self) -> None:
        """File → Save Configuration: persist server details when dirty, then app settings."""
        if self.has_unsaved_server_details():
            self.save_server_details(show_popup=False)
            if self.has_unsaved_server_details():
                return
        self.save_configuration(show_popup=True)

    def save_configuration(self, show_popup: bool = True):
        prof_name = getattr(self.app_config, "profile_name", "default") or "default"
        # Server URL is track A; use the widget when that track is dirty, otherwise
        # keep the on-disk URL so app-settings-only saves cannot wipe credentials.
        if self.has_unsaved_server_details():
            self.app_config.server_url = self.inputs["config"]["server"].text()
        else:
            self.app_config.server_url = load_config(profile_name=prof_name).server_url

        if "skip-ssl" in self.inputs["config"]:
            self.app_config.skip_ssl = self.inputs["config"]["skip-ssl"].isChecked()

        if "client_timeout_minutes" in self.inputs["config"]:
            self.app_config.client_timeout_minutes = self.inputs["config"][
                "client_timeout_minutes"
            ].value()

        if "secret_provider" in self.inputs["config"]:
            self.app_config.secrets_provider = self.inputs["config"][
                "secret_provider"
            ].currentData()

        if "allow_untested_updates" in self.inputs["config"]:
            self.app_config.allow_untested_updates = self.inputs["config"][
                "allow_untested_updates"
            ].isChecked()

        if "preferred_terminal" in self.inputs["config"]:
            self.app_config.preferred_terminal = self.inputs["config"][
                "preferred_terminal"
            ].currentText()

        if hasattr(self, "theme_mode_combo"):
            self.app_config.theme_mode = self.theme_mode_combo.currentText()

        self.app_config.advanced_mode = bool(getattr(self, "is_advanced", False))

        prof_name = getattr(self.app_config, "profile_name", "default") or "default"
        cfg_path = default_config_path(prof_name)
        try:
            save_config(self.app_config, path=cfg_path, profile_name=prof_name)
        except OSError as exc:
            QMessageBox.critical(
                cast(QWidget, self),
                "Save Failed",
                f"Could not write configuration to:\n{cfg_path}\n\n{exc}",
            )
            return

        prof_name = getattr(self.app_config, "profile_name", "default")
        admin_key = (
            self.inputs["config"]["admin_api_key"].text().strip()
            if "admin_api_key" in self.inputs["config"]
            else ""
        )

        try:
            res_admin = save_secret_with_fallback(
                profile_name=prof_name,
                key="admin_api_key",
                value=admin_key,
                provider=self.app_config.secrets_provider,
            )
        except OSError as exc:
            QMessageBox.critical(
                cast(QWidget, self),
                "Save Failed",
                f"Could not save admin API key:\n{exc}",
            )
            return

        msg = f"Configuration saved to:\n{cfg_path}"
        if res_admin.message:
            msg += f"\n\nNote (Admin Key): {res_admin.message}"

        if show_popup:
            QMessageBox.information(
                cast(QWidget, self),
                "Saved",
                msg,
                QMessageBox.StandardButton.Ok,
            )
        self._update_secret_status()
        self._mark_configuration_clean()
        self._mark_server_details_clean()

    def _probe_keyring(self) -> bool:
        """One-time check: can we actually talk to the keyring?"""
        try:
            import keyring

            keyring.get_password("immich-go-gui-probe", "probe")
            return True
        except Exception:
            return False

    def _secrets_file_has_key(self) -> bool:
        from core.config_manager import load_secrets

        return bool(load_secrets().get("api_key"))

    def _update_secret_status(self):
        """Shows whether secrets are in keyring or file fallback."""
        if not hasattr(self, "lbl_secret_status"):
            return
        prof = getattr(self.app_config, "profile_name", "default")
        provider = self.app_config.secrets_provider
        api_val = SecretStore.get_secret(prof, "api_key")
        if provider == "keyring" and api_val:
            self.lbl_secret_status.setText("Secrets stored in OS keyring")
            self.lbl_secret_status.setStyleSheet("color: #22C55E;")
        elif provider == "config" or (not api_val and self._secrets_file_has_key()):
            self.lbl_secret_status.setText(
                "Secrets stored in plaintext secrets.toml — prefer OS keyring"
            )
            self.lbl_secret_status.setStyleSheet("color: #E5C07B;")
        else:
            self.lbl_secret_status.setText("")

    def _prompt_save_pending_configuration(
        self, context: str
    ) -> QMessageBox.StandardButton | None:
        """Single save prompt when any configuration track is dirty."""
        server_dirty = self.has_unsaved_server_details()
        app_dirty = self.has_unsaved_changes()
        if not server_dirty and not app_dirty:
            return None

        if server_dirty and app_dirty:
            body = (
                "Server connection and other settings changed. "
                f"Save before {context}?"
            )
        elif server_dirty:
            body = (
                "Server URL or API key changed. "
                f"Save connection details before {context}?"
            )
        else:
            body = (
                "Theme, timeout, or other settings changed. "
                f"Save before {context}?"
            )

        return QMessageBox.question(
            cast(QWidget, self),
            "Save configuration?",
            body,
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

    def _prompt_save_server_details(self) -> QMessageBox.StandardButton:
        return QMessageBox.question(
            cast(QWidget, self),
            "Save server connection?",
            "Server URL or API key changed. Save connection details before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

    def _prompt_save_app_settings(self) -> QMessageBox.StandardButton:
        return QMessageBox.question(
            cast(QWidget, self),
            "Save settings?",
            "Theme, timeout, or other configuration settings changed. Save before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
