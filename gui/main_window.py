import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from core.binary_manager import BinaryManager
from core.command_builder import build_environment
from core.config_manager import (
    SecretStore,
    load_config,
)
from core.logging_config import setup_logging
from core.process_tracker import (
    cleanup_stale_locks,
    scan_locks,
)
from core.profile_manager import active_profile_name
from gui.browse_dialogs import BrowseDialogsMixin
from gui.mixins.app_update import AppUpdateMixin
from gui.mixins.binary_ui import BinaryUIMixin
from gui.mixins.confirm_dialog import ConfirmDialogMixin
from gui.mixins.connection import ConnectionMixin
from gui.mixins.diagnostics import DiagnosticsMixin
from gui.mixins.execution import ExecutionMixin
from gui.mixins.form_helpers import FormHelpersMixin
from gui.mixins.form_state import FormStateMixin
from gui.mixins.layout import LayoutMixin
from gui.mixins.menu import MenuMixin
from gui.mixins.monitor_mixin import MonitorMixin
from gui.mixins.persistence import PersistenceMixin
from gui.mixins.profiles_ui import ProfilesUIMixin
from gui.mixins.status import StatusMixin
from gui.mixins.theme_mixin import ThemeMixin
from gui.tabs.config_tab import build_config_tab
from gui.tabs.monitor_tab import build_monitor_tab
from gui.tabs.stack_tab import build_stack_tab
from gui.tray import TrayManager
from theme import (
    THEME_SYSTEM,
    apply_application_theme,
    connect_screen_changes,
    connect_system_theme_changes,
    normalize_theme_mode,
)


class ImmichGoGUI(
    QMainWindow,
    FormHelpersMixin,
    LayoutMixin,
    MenuMixin,
    ThemeMixin,
    StatusMixin,
    ConfirmDialogMixin,
    ExecutionMixin,
    BinaryUIMixin,
    AppUpdateMixin,
    FormStateMixin,
    PersistenceMixin,
    ProfilesUIMixin,
    ConnectionMixin,
    DiagnosticsMixin,
    BrowseDialogsMixin,
    MonitorMixin,
):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immich Go GUI")
        self.resize(1250, 750)
        self.setMinimumSize(900, 600)

        self.log = setup_logging()
        self.log.info("GUI started, profile=%s", active_profile_name())

        self.binary_manager = BinaryManager()
        self.app_config = load_config()
        self.settings = QSettings("Shitan198u", "ImmichGoGUI")

        SecretStore.migrate_from_qsettings(self.settings)

        from core.terminal_launcher import cleanup_stale_temp_dirs

        cleanup_stale_temp_dirs()
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(
            lambda: cleanup_stale_temp_dirs(max_age_hours=24)
        )
        self._cleanup_timer.start(6 * 3600 * 1000)  # 6 hours

        self._status_debounce = QTimer(self)
        self._status_debounce.setSingleShot(True)
        self._status_debounce.setInterval(150)
        self._status_debounce.timeout.connect(self._do_update_status)

        self.theme_mode = normalize_theme_mode(
            self.settings.value("theme_mode", THEME_SYSTEM)
        )
        apply_application_theme(self.theme_mode)

        self.is_advanced = False
        self.adv_rows = {}

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.inputs = {}
        self.adv_frames = []
        self._field_error_labels: dict[tuple[str, str], QLabel] = {}

        self._build_sidebar()
        self._build_content_area()
        self.create_menu_bar()

        self.config_tab = build_config_tab(self)
        self.upload_page = self._build_upload_page()
        self.archive_page = self._build_archive_page()
        self.stack_tab = build_stack_tab(self)
        self.monitor_tab = build_monitor_tab(self)

        self.stacked_widget.addWidget(self.config_tab)
        self.stacked_widget.addWidget(self.upload_page)
        self.stacked_widget.addWidget(self.archive_page)
        self.stacked_widget.addWidget(self.stack_tab)
        self.stacked_widget.addWidget(self.monitor_tab)

        self.stacked_widget.setCurrentIndex(0)
        self.update_header_crumb("configuration")
        self.footer.setVisible(False)

        self.check_binary_version()
        self.load_configuration()
        self.apply_theme(self.theme_mode)
        connect_system_theme_changes(self.on_system_theme_changed)
        connect_screen_changes(self._on_screen_changed)

        if not self._probe_keyring() and self.app_config.secrets_provider == "keyring":
            QMessageBox.warning(
                self,
                "Keyring Unavailable",
                "The OS keyring is not available on this system.\n\n"
                "API keys will be stored in plaintext in secrets.toml.\n"
                "Consider installing a Secret Service provider "
                "(GNOME Keyring, KWallet) for secure storage.",
            )

        cleanup_stale_locks()
        active_locks = scan_locks()
        self.active_lock_paths = {lock.lock_path for lock in active_locks}
        self.active_lock_path = active_locks[0].lock_path if active_locks else None
        self.running_process = bool(self.active_lock_paths)
        if self.active_lock_path:
            self._start_process_timer()

        self.stacked_widget.currentChanged.connect(lambda: self.update_status())

        for tab_dict in self.inputs.values():
            for widget in tab_dict.values():
                if isinstance(widget, QLineEdit):
                    widget.textChanged.connect(
                        lambda _, w=widget: self._schedule_status_update()
                    )
                elif isinstance(widget, QCheckBox):
                    widget.toggled.connect(
                        lambda _, w=widget: self._schedule_status_update()
                    )
                elif isinstance(widget, QComboBox):
                    widget.currentIndexChanged.connect(
                        lambda _, w=widget: self._schedule_status_update()
                    )
                elif isinstance(widget, QSpinBox):
                    widget.valueChanged.connect(
                        lambda _, w=widget: self._schedule_status_update()
                    )
                elif isinstance(widget, QPlainTextEdit):
                    widget.textChanged.connect(
                        lambda w=widget: self._schedule_status_update()
                    )

        self.update_status()

        # Initialize the monitor subsystem
        self.init_monitor()
        icon_root = Path(__file__).resolve().parent.parent
        self.tray_manager = TrayManager(
            self,
            str(icon_root / "immich-go-gui.ico"),
            str(icon_root / "immich-go-gui.png"),
        )
        self.tray_manager.set_minimize_to_tray(
            self.monitor_config.monitor_enabled and self.monitor_config.minimize_to_tray
        )
        self.monitor_enabled_check.toggled.connect(self._on_monitor_enabled_toggled)
        self.minimize_to_tray_check.toggled.connect(self._on_minimize_to_tray_toggled)
        self.launch_on_startup_check.toggled.connect(self._set_launch_on_startup)
        self._set_launch_on_startup(self.launch_on_startup_check.isChecked())
        if (
            self.monitor_config.monitor_enabled
            and self.monitor_config.start_minimized
            and self.tray_manager.tray_available
        ):
            self.hide()

    def _on_monitor_enabled_toggled(self, enabled: bool) -> None:
        self.set_monitor_enabled(enabled)
        self._sync_tray_minimize()

    def _on_minimize_to_tray_toggled(self, enabled: bool) -> None:
        self.monitor_config.minimize_to_tray = enabled
        self._sync_tray_minimize()
        self._save_monitor_state()

    def _sync_tray_minimize(self) -> None:
        """Push the effective minimize-to-tray preference to the tray manager."""
        if not hasattr(self, "tray_manager"):
            return
        self.tray_manager.set_minimize_to_tray(
            self.monitor_config.monitor_enabled
            and self.minimize_to_tray_check.isChecked()
        )

    def _shutdown_monitor_safely(self) -> None:
        """Shut down the monitor subsystem, logging (not swallowing) failures."""
        if not hasattr(self, "shutdown_monitor"):
            return
        try:
            self.shutdown_monitor()
        except Exception:
            if hasattr(self, "log"):
                self.log.exception("Monitor subsystem shutdown failed")

    def _set_launch_on_startup(self, enabled: bool) -> None:
        """Register or remove this application from Windows startup."""
        if sys.platform != "win32":
            return
        try:
            import winreg

            run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_path = Path(__file__).resolve().parent.parent / "app.py"
            command = f'"{sys.executable}" "{app_path}"'
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                run_key_path,
                0,
                winreg.KEY_SET_VALUE,
            ) as run_key:
                if enabled:
                    winreg.SetValueEx(run_key, "ImmichGoGUI", 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(run_key, "ImmichGoGUI")
                    except FileNotFoundError:
                        pass
        except OSError as exc:
            self.log.warning("Unable to configure Windows startup: %s", exc)

    def build_environment(self, tab_key: str = None) -> dict:
        if tab_key is None:
            tab_key = self._get_active_tab_key()
        server = (
            self.inputs.get("config", {}).get("server").text().strip()
            if self.inputs.get("config", {}).get("server")
            else ""
        )
        api_key = (
            self.inputs.get("config", {}).get("api_key").text().strip()
            if self.inputs.get("config", {}).get("api_key")
            else ""
        )
        from_server = (
            self.inputs.get("upload-immich", {}).get("from-server").text().strip()
            if self.inputs.get("upload-immich", {}).get("from-server")
            else ""
        )
        from_api_key = (
            self.inputs.get("upload-immich", {}).get("from-api-key").text().strip()
            if self.inputs.get("upload-immich", {}).get("from-api-key")
            else ""
        )
        return build_environment(tab_key, server, api_key, from_server, from_api_key)

    def _start_process_timer(self):
        if not hasattr(self, "check_process_timer"):
            self.check_process_timer = QTimer(self)
            self.check_process_timer.timeout.connect(self._check_lock_file)
        if not self.check_process_timer.isActive():
            self.check_process_timer.start(1000)

    def _check_lock_file(self):
        active_locks = scan_locks()
        self.active_lock_paths = {lock.lock_path for lock in active_locks}
        self.active_lock_path = active_locks[0].lock_path if active_locks else None

        if not self.active_lock_paths:
            if hasattr(self, "check_process_timer"):
                self.check_process_timer.stop()
            self.running_process = False
            self.update_status()
            return

        self.running_process = True
        self.update_status()

    def check_if_process_running(self):
        """Backward compatible alias for _check_lock_file."""
        self._check_lock_file()

    def closeEvent(self, event):
        if not getattr(self, "_force_close", False) and hasattr(self, "tray_manager"):
            if self.tray_manager.handle_close(event):
                return

        if getattr(self, "_force_close", False):
            self._shutdown_monitor_safely()
            if hasattr(self, "log"):
                self.log.info("GUI closed")
            event.accept()
            return

        active_locks = scan_locks()
        active_paths = getattr(self, "active_lock_paths", set())
        if active_locks or active_paths:
            reply = QMessageBox.question(
                self,
                "Running Command Detected",
                "A command appears to still be running in an external terminal.\n\nClose the GUI anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        reply = self._prompt_save_pending_configuration("closing")
        if reply == QMessageBox.StandardButton.Cancel:
            event.ignore()
            return
        if reply == QMessageBox.StandardButton.Save:
            self._save_pending_configuration(show_popup=False)

        self._shutdown_monitor_safely()
        if hasattr(self, "log"):
            self.log.info("GUI closed")
        event.accept()
