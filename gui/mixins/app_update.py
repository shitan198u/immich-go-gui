import webbrowser
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from PySide6.QtWidgets import QMessageBox

from core.app_update import (
    clean_gui_release_version,
    get_latest_gui_release,
    is_parseable_semver,
    is_update_available,
)


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
        installed = _gui_version()
        if hasattr(self, "lbl_app_version"):
            self.lbl_app_version.setText(installed)
        if not is_parseable_semver(installed):
            self._set_app_update_status("Development build", "default")
        else:
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
        is_dev = not is_parseable_semver(installed)

        release = get_latest_gui_release()
        if release is None:
            self._set_app_update_status("Could not check for updates.", "err")
            QMessageBox.warning(
                self,
                "Update Check Failed",
                "Could not reach GitHub to check for updates.\n"
                "Check your network connection and try again.",
            )
            return

        if is_dev:
            self._set_app_update_status(
                f"Development build — latest release is v{release.version}",
                "default",
            )
            QMessageBox.information(
                self,
                "Development Build",
                f"You are running a development build ({installed}).\n"
                "Version comparison was skipped.\n"
                f"The latest published release is v{release.version}.",
            )
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
        QMessageBox.information(
            self,
            "Update Check",
            f"You are on the latest release (v{display}).",
        )

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
    return clean_gui_release_version(version) or version
