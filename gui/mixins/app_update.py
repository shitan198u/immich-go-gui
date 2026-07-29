import webbrowser
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from PySide6.QtWidgets import QMessageBox

from core.app_update import get_latest_gui_release, is_update_available


def _gui_version() -> str:
    try:
        return _pkg_version("immich-go-gui")
    except PackageNotFoundError:
        return "dev"


class AppUpdateMixin:
    _APP_UPDATE_STATUS_DEFAULT = "Check for updates to see status."
    _APP_UPDATE_COLOR_OK = "#22C55E"
    _APP_UPDATE_COLOR_WARN = "#E5C07B"
    _APP_UPDATE_COLOR_ERR = "#EF4444"

    def _init_app_update_ui(self) -> None:
        if hasattr(self, "lbl_app_version"):
            self.lbl_app_version.setText(f"Current Version: {_gui_version()}")
        self._set_app_update_status(self._APP_UPDATE_STATUS_DEFAULT, "default")

    def _set_app_update_status(self, text: str, state: str) -> None:
        if not hasattr(self, "lbl_app_update_status"):
            return
        self.lbl_app_update_status.setText(text)
        if state == "ok":
            self.lbl_app_update_status.setStyleSheet(
                f"color: {self._APP_UPDATE_COLOR_OK};"
            )
        elif state == "warn":
            self.lbl_app_update_status.setStyleSheet(
                f"color: {self._APP_UPDATE_COLOR_WARN};"
            )
        elif state == "err":
            self.lbl_app_update_status.setStyleSheet(
                f"color: {self._APP_UPDATE_COLOR_ERR};"
            )
        else:
            self.lbl_app_update_status.setStyleSheet("")

    def check_for_application_updates(self) -> None:
        installed = _gui_version()
        release = get_latest_gui_release()
        if release is None:
            self._set_app_update_status("Could not check for updates.", "err")
            return

        if is_update_available(installed, release.version):
            self._set_app_update_status(
                f"Update available: v{release.version}", "warn"
            )
            msg = QMessageBox(self)
            msg.setWindowTitle("Update Available")
            msg.setText(
                f"A newer version is available (v{release.version}).\n"
                f"You are running v{installed}."
            )
            open_btn = msg.addButton(
                "Open Download Page", QMessageBox.ButtonRole.AcceptRole
            )
            msg.addButton(QMessageBox.StandardButton.Close)
            msg.exec()
            if msg.clickedButton() == open_btn:
                webbrowser.open(release.html_url)
            return

        display = clean_display_version(installed)
        self._set_app_update_status(f"Up to date (v{display})", "ok")

    def app_update_status_state(self) -> str:
        if not hasattr(self, "lbl_app_update_status"):
            return "default"
        text = self.lbl_app_update_status.text()
        if text.startswith("Up to date"):
            return "ok"
        if text.startswith("Update available"):
            return "warn"
        if text == "Could not check for updates.":
            return "err"
        return "default"


def clean_display_version(version: str) -> str:
    from core.binary_manager import clean_version

    return clean_version(version) or version
