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
#   nuitka-project: --include-data-files=immich-go-gui.ico=immich-go-gui.ico
#   nuitka-project: --company-name="shitan198u"
#   nuitka-project: --product-name="Immich-Go GUI"
#   nuitka-project: --file-description="Immich-Go Graphical User Interface"
#   nuitka-project: --copyright="Copyright (C) 2026 shitan198u"

# nuitka-project-if: {OS} == "Darwin":
#   nuitka-project: --macos-create-app-bundle
#   nuitka-project: --macos-app-icon=immich-go-gui.icns
#   nuitka-project: --company-name="shitan198u"
#   nuitka-project: --product-name="Immich-Go GUI"
#   nuitka-project: --copyright="Copyright (C) 2026 shitan198u"

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


def run_terminal_smoke_test(timeout_seconds: float = 15.0) -> int:
    """
    Run smoke diagnostics: verify Qt application initialization and that
    launch_external_terminal successfully spawns the OS-native terminal
    and executes a non-destructive test command.

    Parameters:
        timeout_seconds: Maximum time to wait for the sentinel command to execute.

    Returns:
        int: `0` on success, `1` on failure.
    """
    import os
    import shutil
    import tempfile
    import time

    try:
        # 1. Initialize Qt (verifies PySide6 shared libraries & plugins load in standalone bundle)
        app = QApplication.instance()
        if app is None:
            if (
                sys.platform.startswith("linux")
                and not os.environ.get("DISPLAY")
                and not os.environ.get("WAYLAND_DISPLAY")
            ):
                os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            app = QApplication(sys.argv)

        from core.process_tracker import create_lock, release_lock
        from core.terminal_launcher import launch_external_terminal

        temp_dir = Path(tempfile.mkdtemp(prefix="immich-smoke-"))
        sentinel_file = temp_dir / "sentinel.txt"
        # 2. Write a cross-platform helper script that writes the sentinel token
        token = f"SMOKE_SUCCESS_{int(time.time())}"
        if sys.platform.startswith("win"):
            helper = temp_dir / "helper.bat"
            helper.write_text(
                f'@echo {token} > "{sentinel_file}"\r\n', encoding="utf-8"
            )
        else:
            helper = temp_dir / "helper.sh"
            helper.write_text(
                f'#!/bin/sh\necho "{token}" > "{sentinel_file}"\n', encoding="utf-8"
            )
            helper.chmod(0o755)

        lock_path = create_lock(
            tab_key="smoke-test",
            command_summary="smoke-test-terminal",
            binary_path=str(helper),
        )

        # 3. Launch external terminal with headless flag to prevent interactive shell prompts
        launch_env = {"IMMICH_GO_GUI_HEADLESS": "1"}
        result = launch_external_terminal(
            command=[str(helper)],
            env=launch_env,
            lock_path=lock_path,
        )

        if not result.ok:
            print(
                f"smoke-test-terminal: failed to launch terminal: {result.message}",
                file=sys.stderr,
            )
            release_lock(lock_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return 1

        # 4. Poll for sentinel file with strict timeout to prevent CI hangs
        deadline = time.time() + timeout_seconds
        success = False
        while time.time() < deadline:
            if sentinel_file.is_file():
                try:
                    content = sentinel_file.read_text(encoding="utf-8")
                    if token in content:
                        success = True
                        break
                except OSError:
                    pass
            time.sleep(0.3)

        # 5. Clean up launched terminal process
        if result.pid:
            try:
                if sys.platform.startswith("win"):
                    import subprocess

                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(result.pid)],
                        capture_output=True,
                        check=False,
                    )
                else:
                    import signal

                    os.kill(result.pid, signal.SIGTERM)
            except Exception:
                pass

        if sys.platform == "darwin":
            try:
                import subprocess

                subprocess.run(
                    ["osascript", "-e", 'tell application "Terminal" to quit'],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
            except Exception:
                pass

        release_lock(lock_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

        if not success:
            print(
                f"smoke-test-terminal: timed out after {timeout_seconds}s waiting for sentinel execution",
                file=sys.stderr,
            )
            return 1

        print("smoke-test-terminal: ok")
        return 0

    except Exception as exc:
        print(f"smoke-test-terminal failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(run_self_test())
    if "--smoke-test-terminal" in sys.argv:
        sys.exit(run_terminal_smoke_test())

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
