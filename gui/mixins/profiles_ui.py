from PySide6.QtWidgets import QInputDialog, QMessageBox

from core.profile_manager import (
    active_profile_name,
    create_profile,
    delete_profile,
    duplicate_profile,
    list_profiles,
    rename_profile,
    set_active_profile_name,
    validate_profile_name,
)


class ProfilesUIMixin:
    def update_window_title(self):
        active = active_profile_name()
        self.setWindowTitle(f"Immich Go GUI — {active}")

    def _prompt_profile_switch_saves(self, active: str) -> bool:
        """Return True to continue switching, False to cancel."""
        if self.has_unsaved_server_details():
            reply = self._prompt_save_server_details()
            if reply == QMessageBox.StandardButton.Cancel:
                return False
            if reply == QMessageBox.StandardButton.Save:
                self.save_server_details(show_popup=False)

        if self.has_unsaved_changes():
            reply = self._prompt_save_app_settings()
            if reply == QMessageBox.StandardButton.Cancel:
                return False
            if reply == QMessageBox.StandardButton.Save:
                self.save_configuration(show_popup=False)

        return True

    def switch_profile(self, target_name: str):
        active = active_profile_name()
        if target_name == active:
            return

        if self.has_unsaved_server_details() or self.has_unsaved_changes():
            if not self._prompt_profile_switch_saves(active):
                self.update_profiles_menu()
                return

        try:
            set_active_profile_name(target_name)
            self.load_configuration()
            self.update_profiles_menu()
            self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "Error Switching Profile", str(e))

    def on_new_profile_clicked(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name:")
        if ok and name.strip():
            clean_n = name.strip()
            existing = [p.name for p in list_profiles()]
            valid, err = validate_profile_name(clean_n, existing)
            if not valid:
                QMessageBox.warning(
                    self, "Invalid Name", err or "Invalid profile name."
                )
                return
            try:
                create_profile(clean_n)
                self.switch_profile(clean_n)
            except Exception as e:
                QMessageBox.critical(self, "Error Creating Profile", str(e))

    def on_duplicate_profile_clicked(self):
        active = active_profile_name()
        name, ok = QInputDialog.getText(
            self, "Duplicate Profile", f"Enter name for duplicate of '{active}':"
        )
        if ok and name.strip():
            clean_n = name.strip()
            existing = [p.name for p in list_profiles()]
            valid, err = validate_profile_name(clean_n, existing)
            if not valid:
                QMessageBox.warning(
                    self, "Invalid Name", err or "Invalid profile name."
                )
                return
            try:
                duplicate_profile(active, clean_n)
                self.switch_profile(clean_n)
            except Exception as e:
                QMessageBox.critical(self, "Error Duplicating Profile", str(e))

    def on_rename_profile_clicked(self):
        active = active_profile_name()
        if active == "default":
            QMessageBox.warning(
                self, "Cannot Rename", "The 'default' profile cannot be renamed."
            )
            return

        name, ok = QInputDialog.getText(
            self,
            "Rename Profile",
            f"Enter new name for profile '{active}':",
            text=active,
        )
        if ok and name.strip() and name.strip() != active:
            clean_n = name.strip()
            existing = [p.name for p in list_profiles() if p.name != active]
            valid, err = validate_profile_name(clean_n, existing)
            if not valid:
                QMessageBox.warning(
                    self, "Invalid Name", err or "Invalid profile name."
                )
                return
            try:
                rename_profile(active, clean_n)
                self.update_profiles_menu()
                self.update_window_title()
            except Exception as e:
                QMessageBox.critical(self, "Error Renaming Profile", str(e))

    def on_delete_profile_clicked(self):
        active = active_profile_name()
        if active == "default":
            QMessageBox.warning(
                self, "Cannot Delete", "The 'default' profile cannot be deleted."
            )
            return

        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to permanently delete profile '{active}' and all its saved settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_profile(active)
                self.load_configuration()
                self.update_profiles_menu()
                self.update_window_title()
            except Exception as e:
                QMessageBox.critical(self, "Error Deleting Profile", str(e))
