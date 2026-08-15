import tomllib
import zipfile
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox

from core import (
    METADATA_PATH,
    TESTED_IMMICH_GO_VERSION,
    default_config_dir,
    default_config_path,
    get_config_load_warning,
)
from core.profile_manager import profile_dir
from core.version import get_app_version as _gui_version


def _redact_diagnostics_toml(text: str) -> str:
    """Return TOML text with secret-like values redacted for diagnostics export."""
    try:
        data = tomllib.loads(text)
    except Exception:
        return "# [unparseable config omitted]\n"

    form_state = data.get("form_state")
    if isinstance(form_state, dict):

        def _redact_mapping(mapping: dict) -> None:
            for key, value in list(mapping.items()):
                key_l = str(key).lower()
                if any(s in key_l for s in ("api", "secret", "password", "token")):
                    mapping[key] = "***REDACTED***"
                elif isinstance(value, dict):
                    _redact_mapping(value)

        _redact_mapping(form_state)

    try:
        import tomli_w

        return tomli_w.dumps(data)
    except Exception:
        return "# [config redaction failed]\n"


class DiagnosticsMixin:
    def open_config_folder(self):
        from core.profile_manager import active_profile_name

        cfg_dir = profile_dir(active_profile_name())
        cfg_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(cfg_dir)))

    def open_log_folder(self):
        log_dir = default_config_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))

    def export_diagnostics(self):
        from core.profile_manager import global_profiles_path

        default_name = f"immich-go-diagnostics-{_gui_version()}.zip"
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Export Diagnostics",
            default_name,
            "Zip Archives (*.zip)",
        )
        if not dest:
            return
        if not dest.endswith(".zip"):
            dest += ".zip"

        cfg_dir = default_config_dir()
        log_dir = cfg_dir / "logs"
        meta_path = Path(METADATA_PATH)

        try:
            with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                summary = [
                    f"gui_version={_gui_version()}",
                    f"cli_target_version={TESTED_IMMICH_GO_VERSION}",
                ]
                warning = get_config_load_warning()
                if warning:
                    summary.append(f"config_load_warning={warning}")
                zf.writestr("summary.txt", "\n".join(summary) + "\n")

                cfg_path = default_config_path()
                if cfg_path.is_file():
                    zf.writestr(
                        "config.toml",
                        _redact_diagnostics_toml(cfg_path.read_text(encoding="utf-8")),
                    )

                profiles_path = global_profiles_path()
                if profiles_path.is_file():
                    zf.write(profiles_path, arcname="profiles.toml")

                if meta_path.is_file():
                    zf.write(meta_path, arcname="binary_metadata.json")

                if log_dir.is_dir():
                    logs = sorted(
                        log_dir.glob("*.log"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )
                    if logs:
                        tail = logs[0].read_text(encoding="utf-8", errors="replace")
                        if len(tail) > 200_000:
                            tail = tail[-200_000:]
                        zf.writestr("log_tail.txt", tail)

            QMessageBox.information(
                self,
                "Diagnostics Exported",
                f"Diagnostics package saved to:\n{dest}",
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Could not write diagnostics package:\n{exc}",
            )
