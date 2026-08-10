"""System tray icon for the Monitor subsystem.

Provides a QSystemTrayIcon with status-aware icons, context menu,
balloon notifications, and minimize-to-tray behavior.
"""

from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class TrayManager:
    """Manages the system tray icon and its context menu."""

    def __init__(self, window, app_icon_path: str = "", fallback_icon_path: str = ""):
        self._window = window
        self._minimize_to_tray = False
        self._app_icon = self._resolve_icon(app_icon_path, fallback_icon_path)

        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()

        self._tray = QSystemTrayIcon(window)
        if self._app_icon:
            self._tray.setIcon(self._app_icon)

        self._tray.setToolTip("Immich-Go GUI — Idle")

        # Context menu
        self._menu = QMenu()
        self._status_action = QAction("Status: Idle")
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)
        self._menu.addSeparator()

        self._open_action = QAction("Open Immich-Go GUI")
        self._open_action.triggered.connect(self._show_window)
        self._menu.addAction(self._open_action)

        self._menu.addSeparator()
        self._quit_action = QAction("Quit")
        self._quit_action.triggered.connect(self._quit_app)
        self._menu.addAction(self._quit_action)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_tray_activated)

        # A QSystemTrayIcon without an icon is invisible on Windows, and on
        # platforms without a system tray show() is pointless.  Only show
        # when the tray is actually available and an icon was resolved.
        if self.tray_available and self._app_icon:
            self._tray.show()

    @staticmethod
    def _resolve_icon(app_icon_path: str, fallback_icon_path: str) -> QIcon | None:
        """Resolve the tray icon, falling back so it is never icon-less."""
        for candidate in (app_icon_path, fallback_icon_path):
            if candidate and Path(candidate).is_file():
                return QIcon(candidate)
        app_icon = QApplication.windowIcon()
        if app_icon and not app_icon.isNull():
            return app_icon
        return None

    def set_status(self, text: str) -> None:
        """Update tray tooltip and status menu item."""
        self._status_action.setText(f"Status: {text}")
        self._tray.setToolTip(f"Immich-Go GUI — {text}")

    def notify(
        self, title: str, message: str, icon_type: str = "info", duration_ms: int = 5000
    ) -> None:
        """Show a balloon notification."""
        icon = QSystemTrayIcon.MessageIcon.Information
        if icon_type == "warning":
            icon = QSystemTrayIcon.MessageIcon.Warning
        elif icon_type == "error":
            icon = QSystemTrayIcon.MessageIcon.Critical

        self._tray.showMessage(title, message, icon, duration_ms)

    def set_minimize_to_tray(self, enabled: bool) -> None:
        """Enable or disable minimize-to-tray behavior."""
        self._minimize_to_tray = bool(enabled and self.tray_available)

    def handle_close(self, event) -> bool:
        """Handle window close event. Returns True if handled (i.e., hidden to tray)."""
        if self._minimize_to_tray:
            self._window.hide()
            self._tray.showMessage(
                "Immich-Go GUI",
                "Minimized to tray. Right-click the tray icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
            event.ignore()
            return True
        return False

    def _show_window(self) -> None:
        """Show and raise the main window."""
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _quit_app(self) -> None:
        """Quit the application."""
        # Force close flag to skip confirmation
        self._window._force_close = True
        self._window.close()
        QApplication.instance().quit()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon click/double-click."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def shutdown(self) -> None:
        """Clean up the tray icon."""
        self._tray.hide()
        if self._tray.contextMenu():
            self._tray.contextMenu().deleteLater()
