"""
Immich-Go GUI – A PySide6 desktop front-end for the immich-go CLI.

Fixes applied (traceable by "# FIX:" comments):
  Phase 1 – Critical correctness & security wiring
  Phase 2 – CLI alignment
  Phase 3 – Path / Takeout handling
  Phase 4 – Qt polish (selected)
  TOML config support
"""

from __future__ import annotations

import glob
import os
import platform
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Optional

import keyring
from PySide6.QtCore import (
    QProcess,
    QSettings,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFontMetrics,
    QIcon,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from theme import (
    apply_base_palette,
    build_stylesheet,
    clear_icon_cache,
    load_themed_icon,
    theme_tokens,
)

# ---------------------------------------------------------------------------
# TOML config path
# ---------------------------------------------------------------------------
CONFIG_DIR = Path.home() / ".config" / "immich-go-gui"
CONFIG_FILE = CONFIG_DIR / "config.toml"

# ---------------------------------------------------------------------------
# Pure utility functions
# ---------------------------------------------------------------------------


def collect_paths(raw: str) -> list[str]:
    """
    Expand a raw path string into a list of concrete paths.

    Handles:
      - Multiple space-separated paths
      - Glob patterns (e.g. takeout-*.zip)
      - Quoted paths with spaces
    """
    if not raw or not raw.strip():
        return []
    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = raw.split()
    result: list[str] = []
    for token in tokens:
        expanded = glob.glob(token, recursive=True)
        if expanded:
            result.extend(sorted(expanded))
        else:
            result.append(token)  # keep as-is if no glob match
    return result


def mask_command_for_display(cmd: str) -> str:
    """
    Return a copy of *cmd* with secret flag values replaced by '********'.

    Handles both '--api-key=VALUE' and '--api-key VALUE' forms.
    """
    # FIX #2: removed trailing spaces from flag names
    secret_flags = {"--api-key", "--from-api-key", "--admin-api-key"}
    parts = cmd.split()
    masked: list[str] = []
    skip_next = False
    for i, part in enumerate(parts):
        if skip_next:
            masked.append("********")
            skip_next = False
            continue
        matched = False
        for flag in secret_flags:
            if part.startswith(f"{flag}="):
                masked.append(f"{flag}=********")
                matched = True
                break
            if part == flag:
                masked.append(part)
                skip_next = True
                matched = True
                break
        if not matched:
            masked.append(part)
    return " ".join(masked)


class SecretStore:
    """
    Store and retrieve API keys using the OS-native keychain
    (macOS Keychain / Linux Secret Service / Windows Credential Manager).
    """

    SERVICE = "immich-go-gui"

    @staticmethod
    def save(profile: str, api_key: str) -> None:
        keyring.set_password(SecretStore.SERVICE, profile, api_key)

    @staticmethod
    def load(profile: str) -> str:
        return keyring.get_password(SecretStore.SERVICE, profile) or ""

    @staticmethod
    def delete(profile: str) -> None:
        try:
            keyring.delete_password(SecretStore.SERVICE, profile)
        except keyring.errors.PasswordDeleteError:
            pass

    @staticmethod
    def migrate_from_qsettings(settings: QSettings, profile: str = "default") -> None:
        """One-time migration: move plain-text API key from QSettings to keychain."""
        old_key = settings.value("api_key", "")
        if old_key:
            SecretStore.save(profile, old_key)
            settings.remove("api_key")
            settings.sync()


def build_environment(
    server: str = "",
    api_key: str = "",
    from_server: str = "",
    from_api_key: str = "",
    admin_api_key: str = "",
) -> dict[str, str]:
    """
    Build an environment-variable dict for passing secrets to immich-go
    without exposing them on the command line.

    immich-go reads:
      IMMICH_GO_UPLOAD_SERVER, IMMICH_GO_UPLOAD_API_KEY,
      IMMICH_GO_UPLOAD_FROM_SERVER, IMMICH_GO_UPLOAD_FROM_API_KEY,
      IMMICH_GO_UPLOAD_ADMIN_API_KEY
    """
    env = dict(os.environ)
    # FIX #3: removed trailing spaces from env var names
    if server:
        env["IMMICH_GO_UPLOAD_SERVER"] = server
    if api_key:
        env["IMMICH_GO_UPLOAD_API_KEY"] = api_key
    if from_server:
        env["IMMICH_GO_UPLOAD_FROM_SERVER"] = from_server
    if from_api_key:
        env["IMMICH_GO_UPLOAD_FROM_API_KEY"] = from_api_key
    if admin_api_key:
        env["IMMICH_GO_UPLOAD_ADMIN_API_KEY"] = admin_api_key
    return env


def load_toml_config() -> dict:
    """Load config.toml, returning defaults if the file is missing."""
    defaults = {
        "schema_version": 1,
        "general": {
            "theme": "dark",
            "concurrent_tasks": 0,
            "log_level": "INFO",
            "log_file": "",
            "log_type": "text",
        },
        "ssl": {"skip_verify": False},
        "profiles": {"active": "default"},
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
            # shallow-merge over defaults
            for section, values in data.items():
                if isinstance(values, dict) and section in defaults and isinstance(defaults[section], dict):
                    defaults[section].update(values)
                else:
                    defaults[section] = values
            return defaults
        except Exception:
            pass
    return defaults


def save_toml_config(cfg: dict) -> None:
    """Persist config dict back to config.toml (requires tomli_w)."""
    try:
        import tomli_w
    except ImportError:
        return  # graceful degradation
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(cfg, f)


# ---------------------------------------------------------------------------
# Reusable drag-and-drop widgets
# ---------------------------------------------------------------------------
# FIX Phase 3 #33: replace fragile monkey-patching with proper subclasses


class DroppableLineEdit(QLineEdit):
    """QLineEdit that accepts file/folder drops and inserts all paths."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # FIX Phase 3 #30: handle multiple files
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        if paths:
            self.setText(" ".join(paths))
        event.acceptProposedAction()


class DroppablePlainTextEdit(QPlainTextEdit):
    """QPlainTextEdit that accepts file/folder drops (one path per line)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        if paths:
            self.setPlainText("\n".join(paths))
        event.acceptProposedAction()


# ---------------------------------------------------------------------------
# Reusable UI widgets
# ---------------------------------------------------------------------------


class Card(QWidget):
    """A rounded-corner container with a title and content layout."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(8)
        if title:
            lbl = QLabel(title)
            outer.addWidget(lbl)
        # FIX Phase 4 #7.1: renamed from 'layout' to 'content_layout'
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(6)
        outer.addLayout(self.content_layout)


class FormSection(QWidget):
    """A labelled group of form fields."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        if title:
            lbl = QLabel(title)
            lay.addWidget(lbl)
        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(6)
        lay.addLayout(self.form_layout)

    def add_row(self, label: str, widget: QWidget) -> None:
        self.form_layout.addRow(label, widget)


class ElidingLabel(QLabel):
    """QLabel that elides long text with '…'."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self.setMinimumWidth(60)

    def setText(self, text: str) -> None:
        self._full_text = text
        self._update_elided()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self) -> None:
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._full_text, Qt.TextElideMode.ElideMiddle, self.width())
        super().setText(elided)
        self.setToolTip(self._full_text)


class SwitchButton(QAbstractButton):
    """
    A toggle switch rendered as a pill-shaped button.
    FIX Phase 4 #7.2: inherits QAbstractButton for proper accessibility.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme_tokens()
        if self.isChecked():
            track_color = t["accent"]
            knob_x = self.width() - 15
        else:
            track_color = t["surface_hover"]
            knob_x = 3
        # Track
        painter.setPen(QPen(QColor(t["border"]), 1))
        painter.setBrush(QBrush(QColor(track_color)))
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 12, 12)
        # Knob
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(knob_x, 3, 20, 20)
        painter.end()


class NavItem(QPushButton):
    """A sidebar navigation button."""

    clicked_nav = Signal(str)

    def __init__(self, text: str, nav_id: str, icon_name: str = "",
                 theme: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.nav_id = nav_id
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            self.setIcon(load_themed_icon(icon_name, theme, 18))
        self.clicked.connect(lambda: self.clicked_nav.emit(self.nav_id))


class NavGroup(QWidget):
    """A labelled group of NavItems in the sidebar."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lbl = QLabel(title.upper())
        lbl.setStyleSheet("font-size: 10px; font-weight: bold; padding: 8px 12px 2px 12px;")
        lay.addWidget(lbl)
        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(2)
        lay.addLayout(self.items_layout)

    def add_item(self, item: NavItem) -> None:
        self.items_layout.addWidget(item)


class BasePage(QWidget):
    """Base class for content pages."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.page_layout = QVBoxLayout(self)
        self.page_layout.setContentsMargins(24, 20, 24, 20)
        self.page_layout.setSpacing(12)
        if title:
            heading = QLabel(title)
            heading.setStyleSheet("font-size: 20px; font-weight: bold;")
            self.page_layout.addWidget(heading)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Immich-Go GUI")
        self.setMinimumSize(1100, 720)

        # FIX Phase 4: set window icon
        self.setWindowIcon(load_themed_icon("immich", "dark", 32))

        # QSettings with proper metadata
        # FIX Phase 4 #7.8
        self.settings = QSettings("immich-go-gui", "immich-go-gui")

        # Load TOML config
        self.toml_cfg = load_toml_config()

        # Migrate old plain-text API key to keychain
        SecretStore.migrate_from_qsettings(self.settings)

        # Input registry
        self.inputs: dict[str, dict] = {
            "config": {},
            "upload-folder": {},
            "upload-gp": {},
            "upload-immich": {},
            "archive-folder": {},
            "archive-immich": {},
            "stack": {},
        }

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        # Stacked pages
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        # Build pages
        self.config_page = self._build_config_page()
        self.upload_page = self._build_upload_page()
        self.archive_page = self._build_archive_page()
        self.stack_page = self._build_stack_page()

        self.stack.addWidget(self.config_page)
        self.stack.addWidget(self.upload_page)
        self.stack.addWidget(self.archive_page)
        self.stack.addWidget(self.stack_page)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Debounce timer for status updates
        # FIX Phase 4 #7.12
        self._status_timer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.setInterval(300)
        self._status_timer.timeout.connect(self._flush_status)
        self._pending_status = ""

        # QProcess runner
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_process_output)
        self.process.finished.connect(self._on_process_finished)

        # Load saved configuration
        self.load_configuration()

        # Navigate to config page by default
        self._navigate("config")

    # -----------------------------------------------------------------------
    # Sidebar
    # -----------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(8, 12, 8, 12)
        lay.setSpacing(4)

        # App title
        title = QLabel("Immich-Go")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px 12px;")
        lay.addWidget(title)

        # Navigation groups
        self.nav_items: list[NavItem] = []

        grp_main = NavGroup("Main")
        nav_config = NavItem("Configuration", "config", "settings", "dark")
        nav_config.clicked_nav.connect(self._navigate)
        grp_main.add_item(nav_config)
        self.nav_items.append(nav_config)
        lay.addWidget(grp_main)

        grp_upload = NavGroup("Upload")
        nav_upload = NavItem("Upload", "upload", "upload", "dark")
        nav_upload.clicked_nav.connect(self._navigate)
        grp_upload.add_item(nav_upload)
        self.nav_items.append(nav_upload)
        lay.addWidget(grp_upload)

        grp_archive = NavGroup("Archive")
        nav_archive = NavItem("Archive", "archive", "archive", "dark")
        nav_archive.clicked_nav.connect(self._navigate)
        grp_archive.add_item(nav_archive)
        self.nav_items.append(nav_archive)
        lay.addWidget(grp_archive)

        grp_tools = NavGroup("Tools")
        nav_stack = NavItem("Stack", "stack", "stack", "dark")
        nav_stack.clicked_nav.connect(self._navigate)
        grp_tools.add_item(nav_stack)
        self.nav_items.append(nav_stack)
        lay.addWidget(grp_tools)

        lay.addStretch()

        # Theme toggle
        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Dark Theme")
        self.theme_switch = SwitchButton()
        self.theme_switch.setChecked(True)
        self.theme_switch.toggled.connect(self._on_theme_toggled)
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.theme_switch)
        theme_row.addStretch()
        lay.addLayout(theme_row)

        return sidebar

    @Slot(str)
    def _navigate(self, nav_id: str) -> None:
        page_map = {
            "config": 0,
            "upload": 1,
            "archive": 2,
            "stack": 3,
        }
        idx = page_map.get(nav_id, 0)
        self.stack.setCurrentIndex(idx)
        for item in self.nav_items:
            item.setChecked(item.nav_id == nav_id)

    # -----------------------------------------------------------------------
    # Configuration page
    # -----------------------------------------------------------------------

    def _build_config_page(self) -> BasePage:
        page = BasePage("Configuration")

        # Server connection card
        conn_card = Card("Immich Server Connection")
        self.server_edit = DroppableLineEdit()
        self.server_edit.setPlaceholderText("http://localhost:2283")
        conn_card.content_layout.addWidget(self._labelled_row("Server URL", self.server_edit))

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Enter API key (stored in OS keychain)")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        conn_card.content_layout.addWidget(self._labelled_row("API Key", self.api_key_edit))

        # FIX Phase 1 #7: Global skip-ssl lives HERE only
        self.ssl_skip_check = QCheckBox("Skip SSL Verification (--skip-verify-ssl)")
        self.ssl_skip_check.toggled.connect(self._on_ssl_skip_toggled)
        conn_card.content_layout.addWidget(self.ssl_skip_check)

        self.ssl_warning_label = QLabel(
            "⚠ Disabling SSL verification exposes your connection to "
            "man-in-the-middle attacks. Only use this on trusted local networks."
        )
        self.ssl_warning_label.setProperty("cssClass", "WarningHint")
        self.ssl_warning_label.setWordWrap(True)
        self.ssl_warning_label.setVisible(False)
        conn_card.content_layout.addWidget(self.ssl_warning_label)

        page.page_layout.addWidget(conn_card)

        # Logging card
        log_card = Card("Logging")
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARN", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        log_card.content_layout.addWidget(self._labelled_row("Log Level", self.log_level_combo))

        self.log_file_edit = QLineEdit()
        self.log_file_edit.setPlaceholderText("Optional log file path")
        log_card.content_layout.addWidget(self._labelled_row("Log File", self.log_file_edit))

        self.log_type_combo = QComboBox()
        self.log_type_combo.addItems(["text", "json"])
        log_card.content_layout.addWidget(self._labelled_row("Log Type", self.log_type_combo))

        page.page_layout.addWidget(log_card)

        # Defaults card
        defaults_card = Card("Defaults")
        cpu_count = os.cpu_count() or 4
        # FIX Phase 2 #17: default to CPU count
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 128)
        self.concurrent_spin.setValue(cpu_count)
        self.concurrent_spin.setSpecialValueText(f"Auto ({cpu_count})")
        defaults_card.content_layout.addWidget(
            self._labelled_row("Concurrent Tasks", self.concurrent_spin)
        )
        page.page_layout.addWidget(defaults_card)

        # Buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Configuration")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.save_configuration)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        page.page_layout.addLayout(btn_row)

        page.page_layout.addStretch()

        # Register inputs
        self.inputs["config"] = {
            "server": self.server_edit,
            "api_key": self.api_key_edit,
            "skip-ssl": self.ssl_skip_check,
            "log-level": self.log_level_combo,
            "log-file": self.log_file_edit,
            "log-type": self.log_type_combo,
            "concurrent-tasks": self.concurrent_spin,
        }

        return page

    @Slot(bool)
    def _on_ssl_skip_toggled(self, checked: bool) -> None:
        self.ssl_warning_label.setVisible(checked)

    # -----------------------------------------------------------------------
    # Upload page (tabbed)
    # -----------------------------------------------------------------------

    def _build_upload_page(self) -> BasePage:
        page = BasePage("Upload")
        tabs = QTabWidget()

        tabs.addTab(self._build_upload_folder_tab(), "From Folder")
        tabs.addTab(self._build_upload_gp_tab(), "Google Takeout")
        tabs.addTab(self._build_upload_immich_tab(), "From Immich")

        page.page_layout.addWidget(tabs)

        # Action buttons
        btn_row = QHBoxLayout()
        self.upload_preview_btn = QPushButton("Preview Command")
        self.upload_preview_btn.clicked.connect(lambda: self._preview("upload"))
        self.upload_run_btn = QPushButton("Run Upload")
        self.upload_run_btn.setObjectName("primaryBtn")
        self.upload_run_btn.clicked.connect(lambda: self._run("upload"))
        btn_row.addStretch()
        btn_row.addWidget(self.upload_preview_btn)
        btn_row.addWidget(self.upload_run_btn)
        page.page_layout.addLayout(btn_row)

        page.page_layout.addStretch()
        return page

    def _build_upload_folder_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        sec = FormSection("Source")
        self.folder_path_edit = DroppableLineEdit()
        self.folder_path_edit.setPlaceholderText("/path/to/photos")
        browse_folder_btn = QToolButton()
        browse_folder_btn.setIcon(load_themed_icon("folder", "dark", 18))
        browse_folder_btn.setToolTip("Browse folder or ZIP archive")
        browse_folder_btn.clicked.connect(self.browse_local_folder)
        row = QHBoxLayout()
        row.addWidget(self.folder_path_edit, stretch=1)
        row.addWidget(browse_folder_btn)
        container = QWidget()
        container.setLayout(row)
        sec.add_row("Path", container)
        lay.addWidget(sec)

        sec2 = FormSection("Options")

        self.create_album_check = QCheckBox("Create Album")
        sec2.add_row("", self.create_album_check)

        self.album_name_edit = QLineEdit()
        self.album_name_edit.setPlaceholderText("Album name")
        sec2.add_row("Album Name", self.album_name_edit)

        # FIX Phase 2 #13: emit --client-timeout
        self.client_timeout_spin = QSpinBox()
        self.client_timeout_spin.setRange(0, 3600)
        self.client_timeout_spin.setValue(300)
        self.client_timeout_spin.setSuffix(" s")
        sec2.add_row("Client Timeout", self.client_timeout_spin)

        # FIX Phase 2 #14: emit --device-uuid
        self.device_uuid_edit = QLineEdit()
        self.device_uuid_edit.setPlaceholderText("Optional device UUID")
        sec2.add_row("Device UUID", self.device_uuid_edit)

        # FIX Phase 2 #18: numeric --on-errors support
        self.on_errors_combo = QComboBox()
        self.on_errors_combo.addItems(["stop", "continue", "custom…"])
        self.on_errors_combo.currentTextChanged.connect(self._on_errors_changed)
        sec2.add_row("On Errors", self.on_errors_combo)

        self.on_errors_spin = QSpinBox()
        self.on_errors_spin.setRange(1, 9999)
        self.on_errors_spin.setValue(10)
        self.on_errors_spin.setVisible(False)
        sec2.add_row("Error Tolerance", self.on_errors_spin)

        # FIX Phase 2 #15: --api-trace on all upload tabs
        self.api_trace_check = QCheckBox("API Trace (--api-trace)")
        sec2.add_row("", self.api_trace_check)

        # FIX Phase 2 #11: --pause-immich-jobs only on upload tabs
        self.pause_jobs_check = QCheckBox("Pause Immich Jobs (--pause-immich-jobs)")
        sec2.add_row("", self.pause_jobs_check)

        # FIX Phase 1 #7: removed per-tab skip-ssl checkbox

        lay.addWidget(sec2)
        lay.addStretch()

        self.inputs["upload-folder"] = {
            "path": self.folder_path_edit,
            "create-album": self.create_album_check,
            "album-name": self.album_name_edit,
            "client-timeout": self.client_timeout_spin,
            "device-uuid": self.device_uuid_edit,
            "on-errors": self.on_errors_combo,
            "on-errors-tolerance": self.on_errors_spin,
            "api-trace": self.api_trace_check,
            "pause-immich-jobs": self.pause_jobs_check,
        }
        return w

    @Slot(str)
    def _on_errors_changed(self, text: str) -> None:
        self.on_errors_spin.setVisible(text == "custom…")

    def _build_upload_gp_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        sec = FormSection("Google Takeout Source")

        # FIX Phase 3 #27: QPlainTextEdit for multi-ZIP
        self.gp_path_edit = DroppablePlainTextEdit()
        self.gp_path_edit.setPlaceholderText(
            "Drag & drop Takeout ZIPs here, or type paths / glob patterns:\n"
            "  /downloads/takeout-001.zip /downloads/takeout-002.zip\n"
            "  /downloads/takeout-*.zip"
        )
        self.gp_path_edit.setMaximumHeight(100)

        browse_gp_btn = QToolButton()
        browse_gp_btn.setIcon(load_themed_icon("folder", "dark", 18))
        browse_gp_btn.setToolTip("Browse for Takeout ZIP files")
        browse_gp_btn.clicked.connect(self.browse_takeout_source)

        gp_row = QHBoxLayout()
        gp_row.addWidget(self.gp_path_edit, stretch=1)
        gp_row.addWidget(browse_gp_btn)
        gp_container = QWidget()
        gp_container.setLayout(gp_row)
        sec.add_row("Takeout ZIPs", gp_container)

        lay.addWidget(sec)

        sec2 = FormSection("Options")

        self.gp_create_album_check = QCheckBox("Create Album")
        sec2.add_row("", self.gp_create_album_check)

        self.gp_album_name_edit = QLineEdit()
        self.gp_album_name_edit.setPlaceholderText("Album name")
        sec2.add_row("Album Name", self.gp_album_name_edit)

        self.gp_api_trace_check = QCheckBox("API Trace (--api-trace)")
        sec2.add_row("", self.gp_api_trace_check)

        self.gp_pause_jobs_check = QCheckBox("Pause Immich Jobs (--pause-immich-jobs)")
        sec2.add_row("", self.gp_pause_jobs_check)

        lay.addWidget(sec2)
        lay.addStretch()

        self.inputs["upload-gp"] = {
            "path": self.gp_path_edit,
            "create-album": self.gp_create_album_check,
            "album-name": self.gp_album_name_edit,
            "api-trace": self.gp_api_trace_check,
            "pause-immich-jobs": self.gp_pause_jobs_check,
        }
        return w

    def _build_upload_immich_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        sec = FormSection("Source Immich Instance")

        self.from_server_edit = DroppableLineEdit()
        self.from_server_edit.setPlaceholderText("http://old-immich:2283")
        sec.add_row("From Server", self.from_server_edit)

        self.from_api_key_edit = QLineEdit()
        self.from_api_key_edit.setPlaceholderText("Source API key")
        self.from_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        sec.add_row("From API Key", self.from_api_key_edit)

        # FIX Phase 2 #19: --from-client-timeout
        self.from_client_timeout_spin = QSpinBox()
        self.from_client_timeout_spin.setRange(0, 3600)
        self.from_client_timeout_spin.setValue(300)
        self.from_client_timeout_spin.setSuffix(" s")
        sec.add_row("From Client Timeout", self.from_client_timeout_spin)

        lay.addWidget(sec)

        sec2 = FormSection("Options")

        self.immich_create_album_check = QCheckBox("Create Album")
        sec2.add_row("", self.immich_create_album_check)

        self.immich_album_name_edit = QLineEdit()
        self.immich_album_name_edit.setPlaceholderText("Album name")
        sec2.add_row("Album Name", self.immich_album_name_edit)

        self.immich_api_trace_check = QCheckBox("API Trace (--api-trace)")
        sec2.add_row("", self.immich_api_trace_check)

        self.immich_pause_jobs_check = QCheckBox("Pause Immich Jobs (--pause-immich-jobs)")
        sec2.add_row("", self.immich_pause_jobs_check)

        lay.addWidget(sec2)
        lay.addStretch()

        self.inputs["upload-immich"] = {
            "from-server": self.from_server_edit,
            "from-api-key": self.from_api_key_edit,
            "from-client-timeout": self.from_client_timeout_spin,
            "create-album": self.immich_create_album_check,
            "album-name": self.immich_album_name_edit,
            "api-trace": self.immich_api_trace_check,
            "pause-immich-jobs": self.immich_pause_jobs_check,
        }
        return w

    # -----------------------------------------------------------------------
    # Archive page (tabbed)
    # -----------------------------------------------------------------------

    def _build_archive_page(self) -> BasePage:
        page = BasePage("Archive")
        tabs = QTabWidget()

        tabs.addTab(self._build_archive_folder_tab(), "From Folder")
        tabs.addTab(self._build_archive_immich_tab(), "From Immich")

        page.page_layout.addWidget(tabs)

        btn_row = QHBoxLayout()
        self.archive_preview_btn = QPushButton("Preview Command")
        self.archive_preview_btn.clicked.connect(lambda: self._preview("archive"))
        self.archive_run_btn = QPushButton("Run Archive")
        self.archive_run_btn.setObjectName("primaryBtn")
        self.archive_run_btn.clicked.connect(lambda: self._run("archive"))
        btn_row.addStretch()
        btn_row.addWidget(self.archive_preview_btn)
        btn_row.addWidget(self.archive_run_btn)
        page.page_layout.addLayout(btn_row)

        page.page_layout.addStretch()
        return page

    def _build_archive_folder_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        sec = FormSection("Source")
        self.arch_folder_path_edit = DroppableLineEdit()
        self.arch_folder_path_edit.setPlaceholderText("/path/to/photos")
        browse_btn = QToolButton()
        browse_btn.setIcon(load_themed_icon("folder", "dark", 18))
        browse_btn.clicked.connect(lambda: self._browse_into(self.arch_folder_path_edit))
        row = QHBoxLayout()
        row.addWidget(self.arch_folder_path_edit, stretch=1)
        row.addWidget(browse_btn)
        container = QWidget()
        container.setLayout(row)
        sec.add_row("Path", container)
        lay.addWidget(sec)

        sec2 = FormSection("Destination")
        self.arch_folder_write_to_edit = DroppableLineEdit()
        self.arch_folder_write_to_edit.setPlaceholderText("/path/to/output")
        # FIX Phase 3 #32: browse button on archive destination
        browse_dest_btn = QToolButton()
        browse_dest_btn.setIcon(load_themed_icon("folder", "dark", 18))
        browse_dest_btn.setToolTip("Browse destination folder")
        browse_dest_btn.clicked.connect(lambda: self._browse_into(self.arch_folder_write_to_edit))
        dest_row = QHBoxLayout()
        dest_row.addWidget(self.arch_folder_write_to_edit, stretch=1)
        dest_row.addWidget(browse_dest_btn)
        dest_container = QWidget()
        dest_container.setLayout(dest_row)
        sec2.add_row("Write To", dest_container)
        lay.addWidget(sec2)

        sec3 = FormSection("Options")
        self.arch_manage_raw_jpeg_check = QCheckBox("Manage RAW+JPEG")
        sec3.add_row("", self.arch_manage_raw_jpeg_check)
        self.arch_manage_burst_check = QCheckBox("Manage Burst")
        sec3.add_row("", self.arch_manage_burst_check)
        self.arch_manage_heic_jpeg_check = QCheckBox("Manage HEIC+JPEG")
        sec3.add_row("", self.arch_manage_heic_jpeg_check)

        # Date range
        self.arch_from_date_edit = QLineEdit()
        self.arch_from_date_edit.setPlaceholderText("YYYY-MM-DD")
        sec3.add_row("From Date", self.arch_from_date_edit)
        self.arch_to_date_edit = QLineEdit()
        self.arch_to_date_edit.setPlaceholderText("YYYY-MM-DD")
        sec3.add_row("To Date", self.arch_to_date_edit)

        lay.addWidget(sec3)
        lay.addStretch()

        self.inputs["archive-folder"] = {
            "path": self.arch_folder_path_edit,
            "write-to": self.arch_folder_write_to_edit,
            "manage-raw-jpeg": self.arch_manage_raw_jpeg_check,
            "manage-burst": self.arch_manage_burst_check,
            "manage-heic-jpeg": self.arch_manage_heic_jpeg_check,
            "from-date": self.arch_from_date_edit,
            "to-date": self.arch_to_date_edit,
        }
        return w

    def _build_archive_immich_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        sec = FormSection("Source Immich Instance")
        self.arch_from_server_edit = DroppableLineEdit()
        self.arch_from_server_edit.setPlaceholderText("http://old-immich:2283")
        sec.add_row("From Server", self.arch_from_server_edit)

        self.arch_from_api_key_edit = QLineEdit()
        self.arch_from_api_key_edit.setPlaceholderText("Source API key")
        self.arch_from_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        sec.add_row("From API Key", self.arch_from_api_key_edit)

        self.arch_from_albums_edit = QLineEdit()
        self.arch_from_albums_edit.setPlaceholderText("Comma-separated album names")
        sec.add_row("From Albums", self.arch_from_albums_edit)

        lay.addWidget(sec)

        sec2 = FormSection("Destination")
        self.arch_immich_write_to_edit = DroppableLineEdit()
        self.arch_immich_write_to_edit.setPlaceholderText("/path/to/output")
        # FIX Phase 3 #32: browse button on archive destination
        browse_dest_btn2 = QToolButton()
        browse_dest_btn2.setIcon(load_themed_icon("folder", "dark", 18))
        browse_dest_btn2.setToolTip("Browse destination folder")
        browse_dest_btn2.clicked.connect(lambda: self._browse_into(self.arch_immich_write_to_edit))
        dest_row2 = QHBoxLayout()
        dest_row2.addWidget(self.arch_immich_write_to_edit, stretch=1)
        dest_row2.addWidget(browse_dest_btn2)
        dest_container2 = QWidget()
        dest_container2.setLayout(dest_row2)
        sec2.add_row("Write To", dest_container2)
        lay.addWidget(sec2)

        sec3 = FormSection("Options")
        self.arch_immich_manage_burst_check = QCheckBox("Manage Burst")
        sec3.add_row("", self.arch_immich_manage_burst_check)
        self.arch_immich_manage_raw_jpeg_check = QCheckBox("Manage RAW+JPEG")
        sec3.add_row("", self.arch_immich_manage_raw_jpeg_check)

        self.arch_immich_from_date_edit = QLineEdit()
        self.arch_immich_from_date_edit.setPlaceholderText("YYYY-MM-DD")
        sec3.add_row("From Date", self.arch_immich_from_date_edit)
        self.arch_immich_to_date_edit = QLineEdit()
        self.arch_immich_to_date_edit.setPlaceholderText("YYYY-MM-DD")
        sec3.add_row("To Date", self.arch_immich_to_date_edit)

        lay.addWidget(sec3)
        lay.addStretch()

        self.inputs["archive-immich"] = {
            "from-server": self.arch_from_server_edit,
            "from-api-key": self.arch_from_api_key_edit,
            "from-albums": self.arch_from_albums_edit,
            "write-to": self.arch_immich_write_to_edit,
            "manage-burst": self.arch_immich_manage_burst_check,
            "manage-raw-jpeg": self.arch_immich_manage_raw_jpeg_check,
            "from-date": self.arch_immich_from_date_edit,
            "to-date": self.arch_immich_to_date_edit,
        }
        return w

    # -----------------------------------------------------------------------
    # Stack page
    # -----------------------------------------------------------------------

    def _build_stack_page(self) -> BasePage:
        page = BasePage("Stack")

        card = Card("Stacking Options")

        self.stack_burst_check = QCheckBox("Stack Burst Photos")
        self.stack_burst_check.setChecked(True)
        card.content_layout.addWidget(self.stack_burst_check)

        self.stack_raw_jpeg_check = QCheckBox("Stack RAW+JPEG")
        self.stack_raw_jpeg_check.setChecked(True)
        card.content_layout.addWidget(self.stack_raw_jpeg_check)

        self.stack_timeshift_edit = QLineEdit()
        self.stack_timeshift_edit.setPlaceholderText("e.g. 2s, 500ms")
        card.content_layout.addWidget(self._labelled_row("Timeshift", self.stack_timeshift_edit))

        # FIX Phase 2 #15: --api-trace on stack
        self.stack_api_trace_check = QCheckBox("API Trace (--api-trace)")
        card.content_layout.addWidget(self.stack_api_trace_check)

        page.page_layout.addWidget(card)

        btn_row = QHBoxLayout()
        stack_preview_btn = QPushButton("Preview Command")
        stack_preview_btn.clicked.connect(lambda: self._preview("stack"))
        stack_run_btn = QPushButton("Run Stack")
        stack_run_btn.setObjectName("primaryBtn")
        stack_run_btn.clicked.connect(lambda: self._run("stack"))
        btn_row.addStretch()
        btn_row.addWidget(stack_preview_btn)
        btn_row.addWidget(stack_run_btn)
        page.page_layout.addLayout(btn_row)

        page.page_layout.addStretch()

        self.inputs["stack"] = {
            "stack-burst": self.stack_burst_check,
            "stack-raw-jpeg": self.stack_raw_jpeg_check,
            "timeshift": self.stack_timeshift_edit,
            "api-trace": self.stack_api_trace_check,
        }
        return page

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _labelled_row(self, label: str, widget: QWidget) -> QWidget:
        """Create a horizontal row with a label and a widget."""
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lbl = QLabel(label)
        lbl.setMinimumWidth(120)
        lay.addWidget(lbl)
        lay.addWidget(widget, stretch=1)
        return row

    def _browse_into(self, target: QLineEdit) -> None:
        """Open a folder browser and set the result into *target*."""
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            target.setText(path)

    # -----------------------------------------------------------------------
    # Browse actions
    # -----------------------------------------------------------------------

    def browse_local_folder(self) -> None:
        """
        FIX Phase 3 #31: allow selecting a folder OR a ZIP archive.
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Folder or ZIP Archive",
            "",
            "All Supported (*.zip *.ZIP);;ZIP Archives (*.zip);;All Files (*)",
        )
        if path:
            self.folder_path_edit.setText(path)
        else:
            # Fall back to folder selection
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                self.folder_path_edit.setText(folder)

    def browse_takeout_source(self) -> None:
        """
        FIX Phase 3 #28: multi-ZIP file picker for Google Takeout.
        """
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Google Takeout ZIP files",
            "",
            "ZIP Archives (*.zip *.ZIP);;All Files (*)",
        )
        if files:
            self.gp_path_edit.setPlainText("\n".join(files))

    # -----------------------------------------------------------------------
    # Command builder
    # -----------------------------------------------------------------------

    def _current_tab_key(self, page: str) -> str:
        """Return the input-dict key for the currently visible tab."""
        if page == "upload":
            tab_widget = self.upload_page.findChild(QTabWidget)
            if tab_widget:
                idx = tab_widget.currentIndex()
                return ["upload-folder", "upload-gp", "upload-immich"][idx]
        elif page == "archive":
            tab_widget = self.archive_page.findChild(QTabWidget)
            if tab_widget:
                idx = tab_widget.currentIndex()
                return ["archive-folder", "archive-immich"][idx]
        elif page == "stack":
            return "stack"
        return "config"

    def build_command(self, page: str) -> list[str]:
        """
        Build the immich-go CLI command list for the given page.

        FIX Phase 1 #1: correct global-flag ordering:
            immich-go [global-opts] command sub-command [cmd-opts] [paths]
        """
        cfg = self.inputs["config"]
        tab_key = self._current_tab_key(page)
        inp = self.inputs.get(tab_key, {})

        # ---- Global options (come FIRST) ----
        global_opts: list[str] = ["immich-go"]

        log_level = cfg["log-level"].currentText()
        if log_level != "INFO":
            global_opts.append(f"--log-level={log_level}")

        log_file = cfg["log-file"].text().strip()
        if log_file:
            global_opts.append(f"--log-file={log_file}")

        log_type = cfg["log-type"].currentText()
        if log_type != "text":
            global_opts.append(f"--log-type={log_type}")

        concurrent = cfg["concurrent-tasks"].value()
        if concurrent > 0:
            global_opts.append(f"--concurrent-tasks={concurrent}")

        # ---- Command + sub-command ----
        cmd: list[str] = []
        cmd_opts: list[str] = []
        path_opt: list[str] = []

        # Server / API key via env vars (not CLI args) — see run_command()
        # But we still include --server for non-secret display purposes
        server = cfg["server"].text().strip()
        if server:
            cmd_opts.append(f"--server={server}")

        # FIX Phase 1 #7: skip-ssl read from config ONLY
        if cfg["skip-ssl"].isChecked():
            cmd_opts.append("--skip-verify-ssl")

        if page == "upload":
            if tab_key == "upload-folder":
                cmd = ["upload", "from-folder"]
                path_text = inp["path"].text().strip()
                if path_text:
                    path_opt.append(path_text)
                if inp["create-album"].isChecked():
                    cmd_opts.append("--create-album")
                    album = inp["album-name"].text().strip()
                    if album:
                        cmd_opts.append(f"--album-name={album}")
                # FIX Phase 2 #13
                ct = inp["client-timeout"].value()
                if ct > 0:
                    cmd_opts.append(f"--client-timeout={ct}")
                # FIX Phase 2 #14
                duuid = inp["device-uuid"].text().strip()
                if duuid:
                    cmd_opts.append(f"--device-uuid={duuid}")
                # FIX Phase 2 #18
                oe = inp["on-errors"].currentText()
                if oe == "custom…":
                    cmd_opts.append(f"--on-errors={inp['on-errors-tolerance'].value()}")
                elif oe != "stop":
                    cmd_opts.append(f"--on-errors={oe}")
                # FIX Phase 2 #15
                if inp["api-trace"].isChecked():
                    cmd_opts.append("--api-trace")
                # FIX Phase 2 #11
                if inp["pause-immich-jobs"].isChecked():
                    cmd_opts.append("--pause-immich-jobs")

            elif tab_key == "upload-gp":
                cmd = ["upload", "from-google-photos"]
                # FIX Phase 3 #29: use collect_paths for multi-ZIP
                raw = inp["path"].toPlainText().strip()
                paths = collect_paths(raw.replace("\n", " "))
                path_opt.extend(paths)
                if inp["create-album"].isChecked():
                    cmd_opts.append("--create-album")
                    album = inp["album-name"].text().strip()
                    if album:
                        cmd_opts.append(f"--album-name={album}")
                if inp["api-trace"].isChecked():
                    cmd_opts.append("--api-trace")
                if inp["pause-immich-jobs"].isChecked():
                    cmd_opts.append("--pause-immich-jobs")

            elif tab_key == "upload-immich":
                cmd = ["upload", "from-immich"]
                from_server = inp["from-server"].text().strip()
                if from_server:
                    cmd_opts.append(f"--from-server={from_server}")
                # FIX Phase 2 #19
                fct = inp["from-client-timeout"].value()
                if fct > 0:
                    cmd_opts.append(f"--from-client-timeout={fct}")
                if inp["create-album"].isChecked():
                    cmd_opts.append("--create-album")
                    album = inp["album-name"].text().strip()
                    if album:
                        cmd_opts.append(f"--album-name={album}")
                if inp["api-trace"].isChecked():
                    cmd_opts.append("--api-trace")
                if inp["pause-immich-jobs"].isChecked():
                    cmd_opts.append("--pause-immich-jobs")

        elif page == "archive":
            if tab_key == "archive-folder":
                cmd = ["archive", "from-folder"]
                path_text = inp["path"].text().strip()
                if path_text:
                    path_opt.append(path_text)
                wt = inp["write-to"].text().strip()
                if wt:
                    cmd_opts.append(f"--write-to={wt}")
                if inp["manage-raw-jpeg"].isChecked():
                    cmd_opts.append("--manage-raw-jpeg")
                if inp["manage-burst"].isChecked():
                    cmd_opts.append("--manage-burst")
                if inp["manage-heic-jpeg"].isChecked():
                    cmd_opts.append("--manage-heic-jpeg")
                fd = inp["from-date"].text().strip()
                if fd:
                    cmd_opts.append(f"--from-date={fd}")
                td = inp["to-date"].text().strip()
                if td:
                    cmd_opts.append(f"--to-date={td}")

            elif tab_key == "archive-immich":
                cmd = ["archive", "from-immich"]
                from_server = inp["from-server"].text().strip()
                if from_server:
                    cmd_opts.append(f"--from-server={from_server}")
                wt = inp["write-to"].text().strip()
                if wt:
                    cmd_opts.append(f"--write-to={wt}")
                albums = inp["from-albums"].text().strip()
                if albums:
                    cmd_opts.append(f"--from-albums={albums}")
                if inp["manage-burst"].isChecked():
                    cmd_opts.append("--manage-burst")
                if inp["manage-raw-jpeg"].isChecked():
                    cmd_opts.append("--manage-raw-jpeg")
                fd = inp["from-date"].text().strip()
                if fd:
                    cmd_opts.append(f"--from-date={fd}")
                td = inp["to-date"].text().strip()
                if td:
                    cmd_opts.append(f"--to-date={td}")

        elif page == "stack":
            cmd = ["stack"]
            if inp["stack-burst"].isChecked():
                cmd_opts.append("--stack-burst")
            if inp["stack-raw-jpeg"].isChecked():
                cmd_opts.append("--stack-raw-jpeg")
            ts = inp["timeshift"].text().strip()
            if ts:
                cmd_opts.append(f"--timeshift={ts}")
            # FIX Phase 2 #15
            if inp["api-trace"].isChecked():
                cmd_opts.append("--api-trace")

        # FIX Phase 1 #1: correct ordering
        return global_opts + cmd + cmd_opts + path_opt

    # -----------------------------------------------------------------------
    # Preview & Run
    # -----------------------------------------------------------------------

    def _preview(self, page: str) -> None:
        cmd_list = self.build_command(page)
        cmd_str = " ".join(cmd_list)
        # FIX Phase 1 #4: mask secrets in preview
        masked = mask_command_for_display(cmd_str)
        self.show_confirm_dialog(masked, page)

    def show_confirm_dialog(self, masked_cmd: str, page: str) -> None:
        """
        Show a confirmation dialog with the (masked) command.
        FIX Phase 1 #10: SSL warning banner in preview dialog.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Confirm Command")
        dlg.setMinimumWidth(600)
        lay = QVBoxLayout(dlg)

        # SSL warning banner
        cfg = self.inputs["config"]
        if cfg["skip-ssl"].isChecked():
            warn = QLabel(
                "⚠ SSL verification is DISABLED. Your connection is vulnerable "
                "to man-in-the-middle attacks. Proceed only on trusted networks."
            )
            warn.setProperty("cssClass", "DangerHint")
            warn.setWordWrap(True)
            warn.setStyleSheet(
                "background-color: #3d2020; padding: 8px; border-radius: 6px;"
            )
            lay.addWidget(warn)

        lbl = QLabel("The following command will be executed:")
        lay.addWidget(lbl)

        cmd_display = QPlainTextEdit()
        cmd_display.setPlainText(masked_cmd)
        cmd_display.setReadOnly(True)
        cmd_display.setMaximumHeight(120)
        lay.addWidget(cmd_display)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.run_command(page)

    def run_command(self, page: str) -> None:
        """
        Execute the built command via QProcess.
        FIX Phase 1 #5: pass secrets via environment variables.
        """
        cmd_list = self.build_command(page)
        if not cmd_list:
            return

        program = cmd_list[0]
        args = cmd_list[1:]

        # Build environment with secrets
        cfg = self.inputs["config"]
        tab_key = self._current_tab_key(page)
        inp = self.inputs.get(tab_key, {})

        env = build_environment(
            server=cfg["server"].text().strip(),
            api_key=cfg["api_key"].text().strip(),
            from_server=inp.get("from-server", QLineEdit()).text().strip()
                if isinstance(inp.get("from-server"), QLineEdit) else "",
            from_api_key=inp.get("from-api-key", QLineEdit()).text().strip()
                if isinstance(inp.get("from-api-key"), QLineEdit) else "",
        )

        # Remove secret flags from args (they go via env now)
        clean_args = []
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            if arg.startswith("--api-key=") or arg.startswith("--from-api-key="):
                continue
            if arg in ("--api-key", "--from-api-key"):
                skip_next = True
                continue
            clean_args.append(arg)

        self.process.setProcessEnvironment(
            QProcess.ProcessEnvironment.fromDict(env)
        )

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.update_status(f"Running: {program} {' '.join(clean_args[:5])}…")

        self.process.start(program, clean_args)

    @Slot()
    def _on_process_output(self) -> None:
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self.update_status(data.strip()[:200])

    @Slot(int, QProcess.ExitStatus)
    def _on_process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self.progress_bar.setVisible(False)
        if exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0:
            self.update_status("✓ Command completed successfully.")
        else:
            self.update_status(f"✗ Command exited with code {exit_code}.")

    # -----------------------------------------------------------------------
    # Status bar (debounced)
    # -----------------------------------------------------------------------

    def update_status(self, msg: str) -> None:
        # FIX Phase 4 #7.12: debounce rapid status updates
        self._pending_status = msg
        self._status_timer.start()

    @Slot()
    def _flush_status(self) -> None:
        if self._pending_status:
            self.status_bar.showMessage(self._pending_status, 8000)
            self._pending_status = ""

    # -----------------------------------------------------------------------
    # Theme
    # -----------------------------------------------------------------------

    @Slot(bool)
    def _on_theme_toggled(self, checked: bool) -> None:
        theme = "dark" if checked else "light"
        clear_icon_cache()
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_stylesheet(theme))
            apply_base_palette(app, theme)
        # Update TOML config
        self.toml_cfg.setdefault("general", {})["theme"] = theme
        save_toml_config(self.toml_cfg)

    # -----------------------------------------------------------------------
    # Configuration persistence
    # -----------------------------------------------------------------------

    def save_configuration(self) -> None:
        """
        Save configuration to QSettings (non-secret) + SecretStore (API key)
        + TOML config file.
        FIX Phase 1 #6: API key goes to OS keychain, not QSettings.
        """
        cfg = self.inputs["config"]

        # Non-secret values → QSettings
        self.settings.setValue("server", cfg["server"].text())
        self.settings.setValue("skip_ssl", cfg["skip-ssl"].isChecked())
        self.settings.setValue("log_level", cfg["log-level"].currentText())
        self.settings.setValue("log_file", cfg["log-file"].text())
        self.settings.setValue("log_type", cfg["log-type"].currentText())
        self.settings.setValue("concurrent_tasks", cfg["concurrent-tasks"].value())
        self.settings.sync()

        # Secret → OS keychain
        api_key = cfg["api_key"].text().strip()
        if api_key:
            SecretStore.save("default", api_key)

        # TOML config
        self.toml_cfg.setdefault("general", {})
        self.toml_cfg["general"]["log_level"] = cfg["log-level"].currentText()
        self.toml_cfg["general"]["log_file"] = cfg["log-file"].text().strip()
        self.toml_cfg["general"]["log_type"] = cfg["log-type"].currentText()
        self.toml_cfg["general"]["concurrent_tasks"] = cfg["concurrent-tasks"].value()
        self.toml_cfg.setdefault("ssl", {})["skip_verify"] = cfg["skip-ssl"].isChecked()

        active_profile = self.toml_cfg.get("profiles", {}).get("active", "default")
        profiles = self.toml_cfg.setdefault("profiles", {})
        profile = profiles.setdefault(active_profile, {})
        profile["name"] = profile.get("name", "Default Server")
        profile["server_url"] = cfg["server"].text().strip()

        save_toml_config(self.toml_cfg)
        self.update_status("Configuration saved.")

    def load_configuration(self) -> None:
        """
        Load configuration from QSettings + SecretStore + TOML.
        FIX Phase 1 #6: API key loaded from OS keychain.
        """
        cfg = self.inputs["config"]

        # Try TOML first, fall back to QSettings
        active_profile = self.toml_cfg.get("profiles", {}).get("active", "default")
        profile = self.toml_cfg.get("profiles", {}).get(active_profile, {})

        server = profile.get("server_url", "") or self.settings.value("server", "")
        cfg["server"].setText(server)

        # API key from keychain
        api_key = SecretStore.load(active_profile)
        cfg["api_key"].setText(api_key)

        skip_ssl = self.toml_cfg.get("ssl", {}).get(
            "skip_verify",
            self.settings.value("skip_ssl", False, type=bool),
        )
        cfg["skip-ssl"].setChecked(bool(skip_ssl))

        log_level = self.toml_cfg.get("general", {}).get(
            "log_level",
            self.settings.value("log_level", "INFO"),
        )
        cfg["log-level"].setCurrentText(log_level)

        log_file = self.toml_cfg.get("general", {}).get(
            "log_file",
            self.settings.value("log_file", ""),
        )
        cfg["log-file"].setText(log_file)

        log_type = self.toml_cfg.get("general", {}).get(
            "log_type",
            self.settings.value("log_type", "text"),
        )
        cfg["log-type"].setCurrentText(log_type)

        cpu_count = os.cpu_count() or 4
        concurrent = self.toml_cfg.get("general", {}).get(
            "concurrent_tasks",
            self.settings.value("concurrent_tasks", cpu_count, type=int),
        )
        cfg["concurrent-tasks"].setValue(int(concurrent))

        # Theme
        theme = self.toml_cfg.get("general", {}).get("theme", "dark")
        self.theme_switch.setChecked(theme == "dark")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Immich-Go GUI")
    app.setOrganizationName("immich-go-gui")

    # Apply theme
    theme = "dark"
    cfg = load_toml_config()
    theme = cfg.get("general", {}).get("theme", "dark")
    app.setStyleSheet(build_stylesheet(theme))
    apply_base_palette(app, theme)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()