# nuitka-project: --assume-yes-for-downloads
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --include-data-files=immich-go-gui.png=immich-go-gui.png
# nuitka-project: --include-data-files=core/flags.toml=core/flags.toml
# nuitka-project: --include-data-dir=assets=assets
# nuitka-project: --include-data-dir=core/fixtures=core/fixtures

# nuitka-project-if: {OS} == "Windows":
#   nuitka-project: --standalone
#   nuitka-project: --windows-console-mode=disable
#   nuitka-project: --windows-icon-from-ico=immich-go-gui.ico
#   nuitka-project: --company-name="Shitan198u"
#   nuitka-project: --product-name="Immich-Go GUI"
#   nuitka-project: --file-description="Immich-Go Graphical User Interface"
#   nuitka-project: --copyright="MIT License"

# nuitka-project-if: {OS} == "Darwin":
#   nuitka-project: --macos-create-app-bundle
#   nuitka-project: --macos-app-icon=immich-go-gui.icns

# nuitka-project-if: {OS} == "Linux":
#   nuitka-project: --standalone

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from core import default_config_dir
from core.command_builder import build_plan_from_state
from core.logging_config import setup_logging
from gui import ImmichGoGUI
from theme import set_fusion_style


def _install_exception_hook(log: logging.Logger | None = None) -> None:
    """
    Install a global handler for uncaught exceptions.
    
    The handler logs unexpected exceptions, schedules an error dialog when a Qt application is running, and preserves the previous exception hook behavior. Keyboard interrupts are forwarded without displaying the dialog.
    
    Parameters:
        log: Logger used to record uncaught exceptions. The application logger is used when omitted.
    """
    logger = log or logging.getLogger("immich_go_gui")
    default_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        if exc_type is KeyboardInterrupt:
            default_hook(exc_type, exc_value, exc_tb)
            return
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        try:
            if QApplication.instance() is not None:

                def _show_dialog():
                    QMessageBox.critical(
                        None,
                        "Unexpected Error",
                        "An unexpected error occurred.\n\nSee the log file for details.",
                    )

                QTimer.singleShot(0, _show_dialog)
        except Exception:
            pass
        default_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def run_self_test() -> int:
    """
    Run diagnostics for the flag registry, command plan builder, and configuration directory.
    
    Returns:
        int: `0` if all diagnostics pass, `1` if any diagnostic fails.
    """
    try:
        from core.flag_registry import REGISTRY

        if not REGISTRY.tabs:
            print("self-test: flag registry empty", file=sys.stderr)
            return 1

        plan = build_plan_from_state(
            tab_key="upload-folder",
            config_state={
                "server": "http://localhost:2283",
                "api_key": "test-key",
                "skip-ssl": False,
            },
            tab_state={"path": "/tmp"},
            binary_path="./immich-go",
            dry_run=True,
        )
        if plan.errors:
            print(f"self-test: plan errors: {plan.errors}", file=sys.stderr)
            return 1

        cfg_dir = default_config_dir()
        cfg_dir.mkdir(parents=True, exist_ok=True)
        probe = cfg_dir / ".self-test-write"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        print("self-test: ok")
        return 0
    except Exception as exc:
        print(f"self-test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(run_self_test())

    log = setup_logging()
    _install_exception_hook(log)

    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "immich-go-gui.ico"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    set_fusion_style()
    base_font = QFont()
    base_font.setFamilies(
        [
            "Segoe UI",
            "Segoe UI Emoji",
            "Helvetica Neue",
            "Apple Color Emoji",
            "Noto Sans",
            "Noto Color Emoji",
            "DejaVu Sans",
            "Ubuntu",
            "sans-serif",
        ]
    )
    base_font.setPointSize(10)
    app.setFont(base_font)
    window = ImmichGoGUI()
    window.show()
    sys.exit(app.exec())
