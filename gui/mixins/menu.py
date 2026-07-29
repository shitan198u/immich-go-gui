import webbrowser
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from core import TESTED_IMMICH_GO_VERSION
from core.profile_manager import active_profile_name, list_profiles


def _gui_version() -> str:
    try:
        return _pkg_version("immich-go-gui")
    except PackageNotFoundError:
        return "dev"


class MenuMixin:
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        save_action = QAction("Save Configuration", self)
        save_action.triggered.connect(self._save_from_menu)
        file_menu.addAction(save_action)
        load_action = QAction("Load Configuration", self)
        load_action.triggered.connect(self.load_configuration)
        file_menu.addAction(load_action)

        reset_action = QAction("Reset Run State", self)
        reset_action.triggered.connect(self.on_reset_run_state_clicked)
        file_menu.addAction(reset_action)

        reset_adv_action = QAction("Reset Advanced Flags", self)
        reset_adv_action.triggered.connect(self._confirm_reset_advanced_flags)
        file_menu.addAction(reset_adv_action)

        file_menu.addSeparator()

        open_config_action = QAction("Open Config Folder", self)
        open_config_action.triggered.connect(self.open_config_folder)
        file_menu.addAction(open_config_action)

        open_log_action = QAction("Open Log Folder", self)
        open_log_action.triggered.connect(self.open_log_folder)
        file_menu.addAction(open_log_action)

        export_diag_action = QAction("Export Diagnostics…", self)
        export_diag_action.triggered.connect(self.export_diagnostics)
        file_menu.addAction(export_diag_action)

        file_menu.addSeparator()

        app_update_action = QAction("Check for Application Updates…", self)
        app_update_action.triggered.connect(self.check_for_application_updates)
        file_menu.addAction(app_update_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.profiles_menu = menu_bar.addMenu("Profiles")
        self.update_profiles_menu()

        help_menu = menu_bar.addMenu("Help")
        compat_action = QAction("Check CLI Compatibility", self)
        compat_action.triggered.connect(self.show_cli_compatibility_dialog)
        help_menu.addAction(compat_action)

        help_menu.addSeparator()

        cli_repo_action = QAction("Immich-Go CLI GitHub", self)
        cli_repo_action.triggered.connect(self.open_immich_go_cli_link)
        help_menu.addAction(cli_repo_action)

        gui_repo_action = QAction("Immich-Go GUI GitHub", self)
        gui_repo_action.triggered.connect(self.open_immich_go_gui_link)
        help_menu.addAction(gui_repo_action)

        help_menu.addSeparator()

        about_action = QAction("About Immich-Go GUI", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def update_profiles_menu(self):
        if not hasattr(self, "profiles_menu"):
            return
        self.profiles_menu.clear()

        new_act = QAction("New Profile…", self)
        new_act.triggered.connect(self.on_new_profile_clicked)
        self.profiles_menu.addAction(new_act)

        dup_act = QAction("Duplicate Active Profile…", self)
        dup_act.triggered.connect(self.on_duplicate_profile_clicked)
        self.profiles_menu.addAction(dup_act)

        ren_act = QAction("Rename Active Profile…", self)
        ren_act.triggered.connect(self.on_rename_profile_clicked)
        self.profiles_menu.addAction(ren_act)

        del_act = QAction("Delete Active Profile…", self)
        del_act.triggered.connect(self.on_delete_profile_clicked)
        self.profiles_menu.addAction(del_act)

        self.profiles_menu.addSeparator()

        active = active_profile_name()
        for pinfo in list_profiles():
            act = QAction(pinfo.name, self)
            act.setCheckable(True)
            if pinfo.name == active:
                act.setChecked(True)
            act.triggered.connect(
                lambda checked, name=pinfo.name: self.switch_profile(name)
            )
            self.profiles_menu.addAction(act)

    def show_cli_compatibility_dialog(self):
        from core.binary_manager import (
            TESTED_IMMICH_GO_VERSION,
            get_binary_path,
            load_binary_metadata,
        )
        from core.cli_contract import check_binary_help, check_fixtures

        meta = load_binary_metadata()
        bin_path = Path(get_binary_path(meta))

        report = check_fixtures(TESTED_IMMICH_GO_VERSION)
        if bin_path.exists():
            live_report = check_binary_help(bin_path, TESTED_IMMICH_GO_VERSION)
        else:
            live_report = None

        missing: dict[str, set[str]] = {
            tab: set(flags) for tab, flags in report.missing_flags_by_tab.items()
        }
        unknown: dict[str, set[str]] = {
            tab: set(flags) for tab, flags in report.unknown_flags_by_tab.items()
        }

        supported = bool(report.supported)
        notes: list[str] = [report.notes] if report.notes else []

        if live_report:
            supported = supported and bool(live_report.supported)
            if live_report.notes:
                notes.append(live_report.notes)
            for tab, flags in live_report.missing_flags_by_tab.items():
                missing.setdefault(tab, set()).update(flags)
            for tab, flags in live_report.unknown_flags_by_tab.items():
                unknown.setdefault(tab, set()).update(flags)

        fully_compatible = supported and not any(missing.values())

        msg = [f"Tested Immich-Go Version: v{report.version}\n"]

        if live_report and fully_compatible:
            msg.append("Status: Fully Compatible with fixtures and live binary")
        elif fully_compatible:
            msg.append("Status: Fully Compatible with target schema")
        else:
            msg.append("Status: Compatibility Warning")

        if notes:
            msg.append("\nVersion Notes:")
            for note in notes:
                msg.append(note)

        if missing:
            msg.append("\nMissing CLI Flags:")
            for tab, flags in missing.items():
                if flags:
                    msg.append(f"  [{tab}]")
                    for flag in sorted(flags):
                        msg.append(f"    - {flag}")

        if unknown:
            msg.append("\nNew Upstream CLI Flags Detected:")
            for tab, flags in unknown.items():
                if flags:
                    msg.append(f"  [{tab}]")
                    for flag in sorted(flags):
                        msg.append(f"    - {flag}")

        QMessageBox.information(
            self,
            "Immich-Go CLI Compatibility",
            "\n".join(msg),
        )

    def on_reset_run_state_clicked(self):
        reply = QMessageBox.question(
            self,
            "Reset Run State",
            "Are you sure you want to reset all active run locks and clear running status?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from core.process_tracker import reset_all_locks

            reset_all_locks()
            self.active_lock_path = None
            self.running_process = False
            if hasattr(self, "check_process_timer"):
                self.check_process_timer.stop()
            self.lbl_running_warning.setVisible(False)
            self.update_status()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About Immich-Go GUI",
            "<h3>Immich-Go GUI</h3>"
            "<p>A modern PySide6 desktop interface for <b>immich-go</b>.</p>"
            f"<p><b>Version:</b> {_gui_version()} (CLI Target: v{TESTED_IMMICH_GO_VERSION})</p>"
            "<hr/>"
            "<p><b>Immich-Go GUI Repository:</b><br/>"
            "<a href='https://github.com/shitan198u/immich-go-gui'>https://github.com/shitan198u/immich-go-gui</a></p>"
            "<p><b>Immich-Go CLI Engine:</b><br/>"
            "<a href='https://github.com/simulot/immich-go'>https://github.com/simulot/immich-go</a></p>",
        )

    def open_immich_go_cli_link(self):
        webbrowser.open("https://github.com/simulot/immich-go")

    def open_immich_go_gui_link(self):
        webbrowser.open("https://github.com/shitan198u/immich-go-gui")

    def _confirm_reset_advanced_flags(self):
        reply = QMessageBox.question(
            self,
            "Reset Advanced Flags",
            "Reset all advanced flags to defaults for all tabs?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.reset_advanced_flags()

    def reset_advanced_flags(self, tab_key: str | None = None):
        """Resets advanced flag enable checkboxes to False and values to defaults."""
        tabs = [tab_key] if tab_key else list(getattr(self, "adv_rows", {}).keys())

        for t in tabs:
            for row in getattr(self, "adv_rows", {}).get(t, {}).values():
                row.set_state(
                    {
                        "enabled": False,
                        "value": row.def_.default,
                    }
                )
