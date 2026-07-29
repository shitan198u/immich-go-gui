import os
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from core import (
    BINARY_BASE_DIR,
    clean_version,
    get_binary_path,
    load_binary_metadata,
    save_binary_metadata,
)


class InstallWorker(QThread):
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, manager, ver, cancel_fn):
        super().__init__()
        self.manager = manager
        self.ver = ver
        self.cancel_fn = cancel_fn

    def run(self):
        ok, msg = self.manager.download_and_install(
            version=self.ver,
            progress_cb=self.progress.emit,
            cancel_check=self.cancel_fn,
        )
        self.finished.emit(ok, msg)


class BinaryUIMixin:
    def get_latest_release_info(self) -> str | None:
        return self.binary_manager.get_latest_version()

    def get_download_url(self, version: str | None = None) -> str | None:
        return self.binary_manager.get_download_url(version)

    def check_binary_ready(self) -> tuple[bool, str]:
        """Check that the binary exists and is executable."""
        status = self.binary_manager.check_binary()
        if status.state == "err":
            return False, status.message
        return True, "Binary ready."

    def check_binary_version(self):
        status = self.binary_manager.check_binary()
        self.binary_path = self.binary_manager.resolve_binary_path()
        self.current_version = status.version_text

        self._set_binary_status(
            status.state,
            status.card_text,
            status.version_text,
        )
        if hasattr(self, "btn_check_updates"):
            if status.state == "err":
                self.btn_check_updates.setText("Download Immich-Go")
            else:
                self.btn_check_updates.setText("Check for Updates")

    def _set_binary_status(self, state: str, card_text: str, version_text: str):
        if hasattr(self, "status_card"):
            self.status_card.set_binary(state, card_text)
        if hasattr(self, "lbl_binary_version"):
            self.lbl_binary_version.setText(version_text)
        if hasattr(self, "lbl_binary_path"):
            self.lbl_binary_path.setText(getattr(self, "binary_path", ""))

    def check_for_updates(self):
        self.check_binary_version()

        latest_version = self.binary_manager.get_latest_version()
        if not latest_version:
            QMessageBox.warning(
                self,
                "Update Check",
                "Failed to fetch the latest version information from GitHub.",
            )
            return

        current_version = getattr(self, "current_version", "Unknown")

        if clean_version(current_version) == clean_version(latest_version):
            QMessageBox.information(
                self,
                "Update Check",
                f"You are already on the latest version ({current_version}).",
            )
            return

        release_notes = self.binary_manager.get_release_notes(latest_version)
        allow_untested = (
            getattr(self.app_config, "allow_untested_updates", False)
            if hasattr(self, "app_config")
            else False
        )

        decision = self.binary_manager.evaluate_update(
            current_version=current_version,
            latest_version=latest_version,
            allow_untested=allow_untested,
            release_notes=release_notes,
        )

        if not decision.allowed:
            QMessageBox.warning(
                self,
                "Update Not Allowed",
                decision.message,
            )
            return

        if decision.requires_confirmation:
            reply = QMessageBox.question(
                self,
                "Update Available",
                f"Latest version: {latest_version}\n"
                f"Current version: {current_version}\n\n"
                f"{decision.message}\n\n"
                f"Do you want to download and install {latest_version}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        self.update_binary(version=latest_version, force_download=True)

    def _select_version(self, version: str, binary_path: str):
        self.binary_manager.select_version(version, binary_path)
        self.binary_path = binary_path
        self.check_binary_version()

    def _on_manual_binary_changed(self, text: str = ""):
        meta = load_binary_metadata()
        meta["manual_path"] = self.manual_binary_edit.text().strip()
        save_binary_metadata(meta)
        self.binary_path = get_binary_path(meta)
        self.check_binary_version()

    def update_binary(
        self, version: str | None = None, force_download: bool = False
    ) -> bool:
        if version is None:
            version = self.get_latest_release_info()
            if not version:
                QMessageBox.critical(
                    self, "Error", "Could not determine latest version."
                )
                return False

        clean_v = version.lstrip("v")
        binary_filename = (
            "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        )
        binary_path = os.path.join(BINARY_BASE_DIR, clean_v, binary_filename)

        if os.path.exists(binary_path) and not force_download:
            if self.binary_manager.verify_extracted_binary(binary_path):
                self._select_version(clean_v, binary_path)
                return True

        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Downloading Immich-Go")
        progress_dialog.setFixedWidth(400)
        layout = QVBoxLayout(progress_dialog)
        status_label = QLabel(f"Downloading Immich-Go v{clean_v}...")
        layout.addWidget(status_label)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        layout.addWidget(progress_bar)
        cancel_button = QPushButton("Cancel")
        layout.addWidget(cancel_button)
        progress_dialog.setWindowFlags(
            progress_dialog.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )

        cancelled = False

        def on_cancel():
            nonlocal cancelled
            cancelled = True
            progress_dialog.reject()

        cancel_button.clicked.connect(on_cancel)

        result_box = {"success": False, "message": ""}

        worker = InstallWorker(self.binary_manager, clean_v, lambda: cancelled)
        worker.progress.connect(progress_bar.setValue)

        def on_finished(ok, msg):
            result_box["success"] = ok
            result_box["message"] = msg
            progress_dialog.accept()

        worker.finished.connect(on_finished)
        worker.start()
        progress_dialog.exec()
        worker.wait()

        success = result_box["success"]
        message = result_box["message"]

        if success:
            self.binary_path = self.binary_manager.resolve_binary_path()
            self.check_binary_version()
        elif cancelled:
            QMessageBox.information(self, "Cancelled", "Download was cancelled.")
        else:
            QMessageBox.critical(
                self, "Update Failed", message or "Download/installation failed."
            )

        return success
