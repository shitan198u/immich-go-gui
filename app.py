# nuitka-project: --assume-yes-for-downloads
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --include-data-files=immich-go-gui.png=immich-go-gui.png
# nuitka-project: --include-data-dir=assets=assets
# nuitka-project-if: {OS} == "Windows":
# nuitka-project: --standalone
# nuitka-project: --windows-console-mode=disable
# nuitka-project: --windows-icon-from-ico=immich-go-gui.ico
# nuitka-project: --company-name="Shitan198u"
# nuitka-project: --product-name="Immich-Go GUI"
# nuitka-project: --file-description="Immich-Go Graphical User Interface"
# nuitka-project: --copyright="MIT License"
# nuitka-project-if: {OS} == "Darwin":
# nuitka-project: --macos-create-app-bundle
# nuitka-project-if: {OS} == "Linux":
# nuitka-project: --standalone

import sys
import os
import re
import io
import subprocess
import shlex
import platform
import webbrowser
import zipfile
import tarfile
import glob
import json
import keyring
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QCheckBox, QComboBox, QPushButton, QFileDialog,
    QPlainTextEdit, QStackedWidget, QFrame, QSizePolicy,
    QScrollArea, QMessageBox, QDialog, QProgressBar, QSpinBox, QStyle, QLayout,
    QFormLayout, QToolButton, QTabWidget, QMenu
)
from PySide6.QtGui import (
    QAction, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPen, QColor,
    QBrush, QFont, QCursor
)
from PySide6.QtCore import (
    Qt, QEvent, QTimer, QSettings, QThread, Signal, QSize
)

import requests

SP = QStyle.StandardPixmap

from theme import (
    THEME_SYSTEM, THEME_LIGHT, THEME_DARK,
    normalize_theme_mode, set_fusion_style,
    apply_application_theme, connect_system_theme_changes,
    load_themed_icon
)
from core.network import test_immich_connection, ConnectionTestResult
from core.validation import (
    clean_date_range, normalize_extensions_csv, normalize_list_csv,
    expand_source_paths, validate_destination_folder
)


# ==========================================================
# PURE UTILITY & SECRET HELPERS
# ==========================================================

class ProcessTracker:
    """Tracks an externally-launched immich-go process via a lock file."""

    def __init__(self):
        self._lock_dir = os.path.join(
            tempfile.gettempdir(), "immich-go-gui"
        )
        os.makedirs(self._lock_dir, exist_ok=True)
        self._lock_path: str | None = None

    @property
    def is_running(self) -> bool:
        if self._lock_path is None:
            return False
        return os.path.exists(self._lock_path)

    def create_lock(self) -> str:
        """Create a lock file and return its path."""
        run_id = uuid.uuid4().hex[:12]
        self._lock_path = os.path.join(self._lock_dir, f"run-{run_id}.lock")
        with open(self._lock_path, "w") as f:
            f.write(str(os.getpid()))
        return self._lock_path

    def release_lock(self):
        if self._lock_path and os.path.exists(self._lock_path):
            try:
                os.remove(self._lock_path)
            except OSError:
                pass
        self._lock_path = None

    def wrap_command_with_lock(self, command_str: str) -> str:
        """Wrap a shell command so it removes the lock file on exit."""
        if self._lock_path is None:
            return command_str
        lock = self._lock_path
        return (
            f"trap 'rm -f {shlex.quote(lock)}' EXIT INT TERM; "
            f"{command_str}; "
            f"rm -f {shlex.quote(lock)}"
        )

from core import (
    AppConfig,
    BINARY_BASE_DIR,
    METADATA_PATH,
    TESTED_IMMICH_GO_VERSION,
    ENV_KEY_MAP,
    SECRET_FLAGS,
    SERVER_REQUIRED_TABS,
    SERVERLESS_TABS,
    TAB_COMMANDS,
    UPLOAD_TABS,
    BinaryManager,
    BinaryStatus,
    CommandPlan,
    SecretStore,
    UpdateDecision,
    UpdateSeverity,
    ValidationResult,
    VersionSupport,
    build_environment,
    build_plan_from_state,
    clean_version,
    clear_api_key,
    collect_paths,
    default_config_path,
    get_api_key,
    get_binary_path,
    load_binary_metadata,
    load_config,
    mask_command_for_display,
    normalize_server_url,
    save_binary_metadata,
    save_config,
    set_api_key,
    validate_date_range,
    validate_state,
)


# ==========================================================
# CUSTOM WIDGETS
# ==========================================================

class DroppableLineEdit(QLineEdit):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.setText(paths[0])
            self.filesDropped.emit(paths)
        event.acceptProposedAction()


class DroppablePlainTextEdit(QPlainTextEdit):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.setPlainText("\n".join(paths))
            self.filesDropped.emit(paths)
        event.acceptProposedAction()

class SwitchButton(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self.setFixedSize(38, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.toggled.emit(self._checked)
            self.update()

    def mouseReleaseEvent(self, event):
        self.setChecked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        app = QApplication.instance()
        theme = app.property("theme") if app else "dark"
        is_light = str(theme) == "light"
        if self._checked:
            border_color = QColor("#0F766E") if is_light else QColor("#4FB3A4")
            bg_color = QColor("#CCFBF1") if is_light else QColor("#17332F")
            circle_color = QColor("#0F766E") if is_light else QColor("#4FB3A4")
        else:
            border_color = QColor("#9CA3AF") if is_light else QColor("#3A4045")
            bg_color = QColor("#F8F9FA") if is_light else QColor("#1D2226")
            circle_color = QColor("#6B7280") if is_light else QColor("#5B6267")
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 11, 11)
        if self._checked:
            circle_x = self.width() - 2 - 16
        else:
            circle_x = 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(circle_color))
        painter.drawEllipse(circle_x, 2, 16, 16)


class Card(QFrame):
    def __init__(self, title, required=False, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(18)
        title_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        title_layout.addWidget(title_label)
        if required:
            req_label = QLabel("Required")
            req_label.setObjectName("ReqBadge")
            title_layout.addWidget(req_label)
        title_layout.addStretch()
        self.layout.addLayout(title_layout)
        self.layout.addSpacing(16)


class FormSection(QFormLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.setVerticalSpacing(16)
        self.setHorizontalSpacing(24)

    def add_row(self, label_text, widget, hint=""):
        lbl = QLabel(label_text)
        lbl.setObjectName("FieldLabel")
        if isinstance(widget, QPlainTextEdit):
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        elif isinstance(widget, QWidget):
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if hint:
            container = QVBoxLayout()
            container.setContentsMargins(0, 0, 0, 0)
            container.setSpacing(4)
            container.addWidget(widget)
            hint_lbl = QLabel(hint)
            hint_lbl.setObjectName("Hint")
            container.addWidget(hint_lbl)
            self.addRow(lbl, container)
        else:
            self.addRow(lbl, widget)


class ElidingLabel(QLabel):
    def __init__(self, text="", elide=Qt.TextElideMode.ElideMiddle, parent=None):
        super().__init__(parent)
        self._elide = elide
        self._full = text
        self.setWordWrap(False)
        self._refresh()

    def setText(self, text):
        self._full = text
        self._refresh()

    def text(self):
        return self._full

    def _refresh(self):
        fm = self.fontMetrics()
        w = self.contentsRect().width() or self.width()
        super().setText(fm.elidedText(self._full, self._elide, w) if w > 0 else self._full)

    def sizeHint(self):
        fm = self.fontMetrics()
        return QSize(fm.horizontalAdvance(self._full) + 2, fm.lineSpacing())

    def minimumSizeHint(self):
        fm = self.fontMetrics()
        return QSize(fm.horizontalAdvance("…") + 4, fm.lineSpacing())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refresh()

    def showEvent(self, e):
        super().showEvent(e)
        self._refresh()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._refresh()


class BasePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll)
        self.scroll_content = QWidget()
        self.scroll_layout = QHBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.container = QWidget()
        self.container.setMaximumWidth(1480)
        self.container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        self.scroll_layout.addStretch()
        self.scroll_layout.addWidget(self.container, 1)
        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)

    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def addStretch(self):
        self.layout.addStretch()


class NavItem(QPushButton):
    def __init__(self, text, icon, parent=None):
        super().__init__(text, parent)
        self.setObjectName("NavBtn")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon is not None and not icon.isNull():
            self.setIcon(icon)
            self.setIconSize(QSize(16, 16))


class NavGroup(QWidget):
    def __init__(self, title, items, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(4)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("NavTitle")
            layout.addWidget(lbl)
        for item in items:
            layout.addWidget(item)


class StatusCard(QFrame):
    _DOT = {
        "ok": "#22C55E",
        "warn": "#F59E0B",
        "err": "#EF4444",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)
        self.dot_b, self.txt_b = self._row(lay, "Binary: …")
        self.dot_s, self.txt_s = self._row(lay, "Server: Not Set")
        self.set_binary("err", "Binary: Checking…")
        self.set_server("err", "Server: Not Set")

    def _row(self, lay, text):
        dot = QLabel()
        dot.setFixedSize(10, 10)
        txt = QLabel(text)
        txt.setObjectName("StatusText")
        r = QHBoxLayout()
        r.setSpacing(8)
        r.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        r.addWidget(txt, 1)
        r.addStretch()
        lay.addLayout(r)
        return dot, txt

    def _paint(self, dot, state):
        color = self._DOT.get(state, self._DOT["err"])
        dot.setStyleSheet(f"background:{color};border-radius:5px;")

    def set_binary(self, state, text):
        self._paint(self.dot_b, state)
        self.txt_b.setText(text)

    def set_server(self, state, text):
        self._paint(self.dot_s, state)
        self.txt_s.setText(text)


# ==========================================================
# MAIN APPLICATION
# ==========================================================

class ImmichGoGUI(QMainWindow):
    TAB_KEYS = [
        "config",
        "upload",
        "archive",
        "stack",
    ]

    # FIX Phase 2 #11/#12: define upload-only tab set for flag scoping
    UPLOAD_TABS = {"upload-folder", "upload-gp", "upload-immich"}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immich Go GUI")
        self.resize(1250, 750)
        self.setMinimumSize(900, 600)

        self.binary_manager = BinaryManager()
        self.app_config = load_config()
        self.settings = QSettings("YourOrganization", "ImmichGoGUI")

        # FIX Phase 1 #6: migrate old plain-text API key to keychain
        SecretStore.migrate_from_qsettings(self.settings)

        self.theme_mode = normalize_theme_mode(
            self.settings.value("theme_mode", THEME_SYSTEM)
        )
        apply_application_theme(self.theme_mode)

        self.is_advanced = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.inputs = {}
        self.adv_frames = []

        self._build_sidebar()
        self._build_content_area()
        self.create_menu_bar()

        self.config_tab = self._build_config_tab()
        self.upload_page = self._build_upload_page()
        self.archive_page = self._build_archive_page()
        self.stack_tab = self._build_stack_tab()

        self.stacked_widget.addWidget(self.config_tab)
        self.stacked_widget.addWidget(self.upload_page)
        self.stacked_widget.addWidget(self.archive_page)
        self.stacked_widget.addWidget(self.stack_tab)

        self.stacked_widget.setCurrentIndex(0)
        self.update_header_crumb("configuration")
        self.footer.setVisible(False)

        self.check_binary_version()
        self.load_configuration()
        self.apply_theme(self.theme_mode)
        connect_system_theme_changes(self.on_system_theme_changed)

        self.stacked_widget.currentChanged.connect(lambda: self.update_status())

        for tab_dict in self.inputs.values():
            for widget in tab_dict.values():
                if isinstance(widget, QLineEdit):
                    widget.textChanged.connect(lambda _, w=widget: self.update_status())
                elif isinstance(widget, QCheckBox):
                    widget.toggled.connect(lambda _, w=widget: self.update_status())
                elif isinstance(widget, QComboBox):
                    widget.currentIndexChanged.connect(lambda _, w=widget: self.update_status())
                elif isinstance(widget, QSpinBox):
                    widget.valueChanged.connect(lambda _, w=widget: self.update_status())
                elif isinstance(widget, QPlainTextEdit):
                    widget.textChanged.connect(lambda w=widget: self.update_status())

        self.update_status()

    def _get_active_tab_key(self) -> str:
        idx = self.stacked_widget.currentIndex()
        if idx == 0:
            return "config"
        elif idx == 1:
            u_idx = self.upload_tabs.currentIndex() if hasattr(self, "upload_tabs") else 0
            if u_idx == 0:
                return "upload-folder"
            elif u_idx == 1:
                return "upload-gp"
            else:
                return "upload-immich"
        elif idx == 2:
            a_idx = self.archive_tabs.currentIndex() if hasattr(self, "archive_tabs") else 0
            if a_idx == 0:
                return "archive-folder"
            else:
                return "archive-immich"
        elif idx == 3:
            return "stack"
        return "config"

    # ==========================================================
    # THEME METHODS
    # ==========================================================

    def apply_theme(self, mode=None):
        if mode is None:
            mode = getattr(self, "theme_mode", THEME_SYSTEM)
        mode = normalize_theme_mode(mode)
        self.theme_mode = mode
        if hasattr(self, "settings"):
            self.settings.setValue("theme_mode", mode)
        if hasattr(self, "theme_mode_combo"):
            self.theme_mode_combo.blockSignals(True)
            self.theme_mode_combo.setCurrentText(mode)
            self.theme_mode_combo.blockSignals(False)
        resolved = apply_application_theme(mode)
        for widget in self.findChildren(QWidget):
            try:
                widget.update()
            except TypeError:
                pass
        self.refresh_sidebar_icons(resolved)
        self.update()

    def refresh_sidebar_icons(self, theme: str):
        if not hasattr(self, "btn_config"):
            return
        nav_buttons = [
            self.btn_config, self.btn_upload,
            self.btn_archive, self.btn_stack
        ]
        for btn in nav_buttons:
            if hasattr(btn, "icon_name") and btn.icon_name:
                btn.setIcon(load_themed_icon(btn.icon_name, theme))
                btn.setIconSize(QSize(18, 18))
        for action in self.findChildren(QAction):
            if hasattr(action, "icon_name") and action.icon_name:
                action.setIcon(load_themed_icon(action.icon_name, theme))

    def on_system_theme_changed(self):
        if getattr(self, "theme_mode", THEME_SYSTEM) == THEME_SYSTEM:
            QTimer.singleShot(0, lambda: self.apply_theme(THEME_SYSTEM))

    def event(self, e):
        if e.type() == QEvent.Type.ThemeChange:
            if getattr(self, "theme_mode", THEME_SYSTEM) == THEME_SYSTEM:
                QTimer.singleShot(0, lambda: self.apply_theme(THEME_SYSTEM))
        return super().event(e)

    # ==========================================================
    # UI STRUCTURE BUILDERS
    # ==========================================================

    def _nav_icon(self, theme_name, sp_fallback):
        return QIcon.fromTheme(theme_name, self.style().standardIcon(sp_fallback, None, self))

    def _add_ssl_skip_row(self, form: FormSection, tab_dict: dict,
                          key: str = "skip-ssl",
                          label_text: str = "Skip SSL Verification"):
        chk_ssl = QCheckBox(label_text)
        tab_dict[key] = chk_ssl
        container = QVBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(4)
        container.addWidget(chk_ssl)
        warn_lbl = QLabel(
            "⚠️ Skipping SSL verification reduces security. "
            "Use only for trusted self-hosted servers with self-signed certificates."
        )
        warn_lbl.setObjectName("WarningHint")
        warn_lbl.setWordWrap(True)
        warn_lbl.setVisible(False)
        container.addWidget(warn_lbl)
        chk_ssl.toggled.connect(warn_lbl.setVisible)
        form.addRow("", container)
        return chk_ssl

    # FIX Phase 3 #32: helper to add trailing browse action on a QLineEdit
    def _add_browse_action(self, line_edit: QLineEdit, title: str):
        theme = getattr(self, "theme_mode", "dark")
        action = line_edit.addAction(
            load_themed_icon("folder", theme),
            QLineEdit.ActionPosition.TrailingPosition
        )
        action.icon_name = "folder"
        action.triggered.connect(lambda: self._browse_into(line_edit, title))
        for child in line_edit.findChildren(QToolButton):
            child.setAutoRaise(True)
            child.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _browse_into(self, line_edit: QLineEdit, title: str):
        folder = QFileDialog.getExistingDirectory(
            self,
            title,
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            line_edit.setText(folder)

    def _build_upload_page(self):
        page = BasePage()
        self.upload_tabs = QTabWidget()
        self.upload_tabs.setDocumentMode(True)

        self.upload_folder_tab = self._build_upload_folder_tab()
        self.upload_gp_tab = self._build_upload_gp_tab()
        self.upload_immich_tab = self._build_upload_immich_tab()

        self.upload_tabs.addTab(self.upload_folder_tab, "From Folder")
        self.upload_tabs.addTab(self.upload_gp_tab, "Google Takeout")
        self.upload_tabs.addTab(self.upload_immich_tab, "From Immich")

        page.addWidget(self.upload_tabs)
        self.upload_tabs.currentChanged.connect(self._on_upload_tab_changed)
        self._on_upload_tab_changed(self.upload_tabs.currentIndex())
        return page

    def _on_upload_tab_changed(self, index: int):
        crumbs = {
            0: "upload · from-folder",
            1: "upload · from-google-photos",
            2: "upload · from-immich",
        }
        self.update_header_crumb(crumbs.get(index, "upload"))
        self.update_status()

    def _build_archive_page(self):
        page = BasePage()
        self.archive_tabs = QTabWidget()
        self.archive_tabs.setDocumentMode(True)

        self.archive_folder_tab = self._build_archive_folder_tab()
        self.archive_immich_tab = self._build_archive_immich_tab()

        self.archive_tabs.addTab(self.archive_folder_tab, "From Folder")
        self.archive_tabs.addTab(self.archive_immich_tab, "From Immich")

        page.addWidget(self.archive_tabs)
        self.archive_tabs.currentChanged.connect(self._on_archive_tab_changed)
        self._on_archive_tab_changed(self.archive_tabs.currentIndex())
        return page

    def _on_archive_tab_changed(self, index: int):
        crumbs = {
            0: "archive · from-folder",
            1: "archive · from-immich",
        }
        self.update_header_crumb(crumbs.get(index, "archive"))
        self.update_status()

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)

        self.btn_config = NavItem("Configuration", None)
        self.btn_config.icon_name = "settings"
        self.btn_config.setChecked(True)
        self.btn_config.clicked.connect(
            lambda: self.switch_tab(0, "configuration", self.btn_config)
        )
        sidebar_layout.addWidget(NavGroup("", [self.btn_config]))

        self.btn_upload = NavItem("Upload", None)
        self.btn_upload.icon_name = "upload"
        self.btn_upload.clicked.connect(
            lambda: self.switch_tab(1, "upload", self.btn_upload)
        )
        sidebar_layout.addWidget(NavGroup("UPLOAD", [self.btn_upload]))

        self.btn_archive = NavItem("Archive", None)
        self.btn_archive.icon_name = "archive"
        self.btn_archive.clicked.connect(
            lambda: self.switch_tab(2, "archive", self.btn_archive)
        )
        sidebar_layout.addWidget(NavGroup("ARCHIVE", [self.btn_archive]))

        self.btn_stack = NavItem("Stack Assets", None)
        self.btn_stack.icon_name = "layers"
        self.btn_stack.clicked.connect(
            lambda: self.switch_tab(3, "stack", self.btn_stack)
        )
        sidebar_layout.addWidget(NavGroup("ORGANIZE", [self.btn_stack]))

        sidebar_layout.addStretch()

        self.status_card = StatusCard()
        sidebar_layout.addWidget(self.status_card)

        self.main_layout.addWidget(sidebar)

    def _build_content_area(self):
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("HeaderFrame")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        title_box = QVBoxLayout()
        self.lbl_app_name = QLabel("Immich Go GUI")
        self.lbl_app_name.setObjectName("AppName")
        self.lbl_crumb = QLabel("configuration")
        self.lbl_crumb.setObjectName("Crumb")
        title_box.addWidget(self.lbl_app_name)
        title_box.addWidget(self.lbl_crumb)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        adv_box = QHBoxLayout()
        self.lbl_mode = QLabel("Simple")
        self.lbl_mode.setObjectName("ModeLabel")
        adv_box.addWidget(self.lbl_mode)
        self.switch_advanced = SwitchButton()
        self.switch_advanced.toggled.connect(self.toggle_advanced)
        adv_box.addWidget(self.switch_advanced)
        header_layout.addLayout(adv_box)

        content_layout.addWidget(header)

        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)

        self.footer = QFrame()
        self.footer.setObjectName("FooterFrame")
        self.footer.setFixedHeight(70)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(24, 0, 24, 0)

        self.lbl_running_warning = QLabel(
            "⚠️ Immich-Go is currently running in a terminal. "
            "Close the terminal to run another command."
        )
        self.lbl_running_warning.setObjectName("RunningWarning")
        self.lbl_running_warning.setStyleSheet("color: #EAB308; font-weight: 500;")
        self.lbl_running_warning.setVisible(False)
        footer_layout.addWidget(self.lbl_running_warning)
        footer_layout.addStretch()

        self.btn_dry_run = QPushButton("Preview (Dry Run)")
        self.btn_dry_run.setObjectName("BtnPreview")
        self.btn_dry_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dry_run.clicked.connect(lambda: self.show_confirm_dialog(True))
        footer_layout.addWidget(self.btn_dry_run)

        self.btn_run = QPushButton("Run Command")
        self.btn_run.setObjectName("BtnRun")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.clicked.connect(lambda: self.show_confirm_dialog(False))
        footer_layout.addWidget(self.btn_run)

        content_layout.addWidget(self.footer)
        self.main_layout.addWidget(content_frame)

    def _build_config_tab(self):
        page = BasePage()
        self.inputs["config"] = {}

        card = Card("Immich Server Connection", required=True)
        form = FormSection()

        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("http://localhost:2283")
        self.inputs["config"]["server"] = self.server_url_edit
        form.add_row("Server URL", self.server_url_edit)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Paste your Immich API key")
        self.inputs["config"]["api_key"] = self.api_key_edit
        form.add_row(
            "API Key",
            self.api_key_edit,
            "You can generate an API key in Immich under Account Settings -> API Keys."
        )

        self._add_ssl_skip_row(form, self.inputs["config"])

        self.btn_test_connection = QPushButton("Test Connection")
        self.btn_test_connection.clicked.connect(self.on_test_connection_clicked)
        form.add_row("", self.btn_test_connection)

        card.layout.addLayout(form)
        page.addWidget(card)

        card2 = Card("Binary Management")
        row = QHBoxLayout()
        row.setSpacing(16)
        row.setAlignment(Qt.AlignmentFlag.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl_binary_version = QLabel("Checking version…")
        self.lbl_binary_version.setObjectName("FieldLabel")
        self.lbl_binary_version.setWordWrap(True)
        self.lbl_binary_path = ElidingLabel("", Qt.TextElideMode.ElideMiddle)
        self.lbl_binary_path.setObjectName("Hint")
        info.addWidget(self.lbl_binary_version)
        info.addWidget(self.lbl_binary_path)
        row.addLayout(info, 1)
        btn_check = QPushButton("Check for Updates")
        self.btn_check_updates = btn_check
        btn_check.clicked.connect(self.check_for_updates)
        row.addWidget(btn_check, 0, Qt.AlignmentFlag.AlignTop)
        card2.layout.addLayout(row)

        manual_form = FormSection()
        self.manual_binary_edit = QLineEdit()
        self.manual_binary_edit.setPlaceholderText(
            "/usr/local/bin/immich-go  (leave empty to use managed binary)"
        )
        meta = load_binary_metadata()
        if meta.get("manual_path"):
            self.manual_binary_edit.setText(meta["manual_path"])
        self.manual_binary_edit.textChanged.connect(self._on_manual_binary_changed)
        manual_form.add_row(
            "Manual Binary Path",
            self.manual_binary_edit,
            "If set, this path is used instead of the managed binary."
        )
        card2.layout.addLayout(manual_form)
        page.addWidget(card2)

        card3 = Card("Appearance")
        theme_form = FormSection()
        self.theme_mode_combo = QComboBox()
        self.theme_mode_combo.addItems([THEME_SYSTEM, THEME_LIGHT, THEME_DARK])
        self.theme_mode_combo.setCurrentText(self.theme_mode)
        self.theme_mode_combo.currentTextChanged.connect(self.apply_theme)
        theme_form.add_row(
            "Theme",
            self.theme_mode_combo,
            "System follows your operating system theme when supported by Qt."
        )
        card3.layout.addLayout(theme_form)
        page.addWidget(card3)

        adv_card = Card("Advanced Configuration")
        adv_form = FormSection()

        self.client_timeout_spin = QSpinBox()
        self.client_timeout_spin.setRange(1, 1440)
        self.client_timeout_spin.setValue(20)
        self.client_timeout_spin.setSuffix(" minutes")
        self.inputs["config"]["client_timeout"] = self.client_timeout_spin
        adv_form.add_row("Client Timeout", self.client_timeout_spin)

        cpu_count = os.cpu_count() or 2
        self.concurrent_tasks_spin = QSpinBox()
        self.concurrent_tasks_spin.setRange(1, 20)
        self.concurrent_tasks_spin.setValue(min(max(cpu_count, 1), 20))
        self.inputs["config"]["concurrent"] = self.concurrent_tasks_spin
        adv_form.add_row("Concurrent Tasks", self.concurrent_tasks_spin)

        self.device_uuid_edit = QLineEdit()
        self.inputs["config"]["device_uuid"] = self.device_uuid_edit
        adv_form.add_row("Device UUID", self.device_uuid_edit)

        self.on_errors_combo = QComboBox()
        self.on_errors_combo.addItems(["stop", "continue", "custom…"])
        self.on_errors_combo.currentTextChanged.connect(self._on_errors_changed)
        self.inputs["config"]["on_errors"] = self.on_errors_combo
        adv_form.add_row("On Errors", self.on_errors_combo)

        self.on_errors_spin = QSpinBox()
        self.on_errors_spin.setRange(1, 9999)
        self.on_errors_spin.setValue(10)
        self.on_errors_spin.setVisible(False)
        self.inputs["config"]["on_errors_tolerance"] = self.on_errors_spin
        adv_form.add_row("Error Tolerance", self.on_errors_spin)

        self.pause_immich_jobs_check = QCheckBox("Pause Immich Jobs")
        self.pause_immich_jobs_check.setChecked(True)
        self.inputs["config"]["pause_jobs"] = self.pause_immich_jobs_check
        adv_form.addRow("", self.pause_immich_jobs_check)

        adv_card.layout.addLayout(adv_form)
        adv_card.setVisible(False)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)

        page.addStretch()
        return page

    def _on_manual_binary_changed(self, text: str):
        meta = load_binary_metadata()
        meta["manual_path"] = text.strip()
        save_binary_metadata(meta)
        self.binary_path = get_binary_path(meta)
        self.check_binary_version()

    def _on_errors_changed(self, text):
        self.on_errors_spin.setVisible(text == "custom…")

    def _build_upload_folder_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(24)
        self.inputs["upload-folder"] = {}

        card = Card("Source Configuration", required=True)
        form = FormSection()

        self.source_path_edit = DroppableLineEdit()
        self.source_path_edit.setPlaceholderText("/path/to/files or /path/to/archive.zip")
        self.inputs["upload-folder"]["path"] = self.source_path_edit

        btn_folder = QPushButton("Select Folder…")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.clicked.connect(self.browse_folder_upload)

        btn_zip = QPushButton("Select ZIP Archive…")
        btn_zip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zip.clicked.connect(self.browse_zip_upload)

        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(0, 4, 0, 0)
        btn_box.setSpacing(10)
        btn_box.addWidget(btn_folder)
        btn_box.addWidget(btn_zip)
        btn_box.addStretch()

        path_container = QWidget()
        path_layout = QVBoxLayout(path_container)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(6)
        path_layout.addWidget(self.source_path_edit)
        path_layout.addLayout(btn_box)

        form.add_row(
            "Folder / ZIP to upload",
            path_container,
            "Every file inside this folder will be considered. ZIP archives are also supported."
        )

        card.layout.addLayout(form)
        lay.addWidget(card)

        card = Card("Options")
        form = FormSection()

        c_type = QComboBox()
        c_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs["upload-folder"]["include-type"] = c_type
        form.add_row("Media Type", c_type)

        c_album = QComboBox()
        c_album.addItems(["NONE", "FOLDER", "PATH"])
        self.inputs["upload-folder"]["folder-album"] = c_album
        form.add_row("Album Organization", c_album)

        t_album = QLineEdit()
        t_album.setPlaceholderText("e.g. Family Archive")
        self.inputs["upload-folder"]["into-album"] = t_album
        form.add_row("Put all into Album", t_album)

        c_burst = QComboBox()
        c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs["upload-folder"]["manage-burst"] = c_burst
        form.add_row("Burst Photos", c_burst)

        c_raw = QComboBox()
        c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs["upload-folder"]["manage-raw-jpeg"] = c_raw
        form.add_row("RAW + JPEG Pairs", c_raw)

        c_heic = QComboBox()
        c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs["upload-folder"]["manage-heic-jpeg"] = c_heic
        form.add_row("HEIC + JPEG Pairs", c_heic)

        card.layout.addLayout(form)
        lay.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        d_range = QLineEdit()
        d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs["upload-folder"]["date-range"] = d_range
        form.add_row("Date range", d_range)

        inc_ext = QLineEdit()
        inc_ext.setPlaceholderText(".jpg,.heic,.mp4")
        self.inputs["upload-folder"]["include-ext"] = inc_ext
        form.add_row("Include extensions", inc_ext)

        exc_ext = QLineEdit()
        exc_ext.setPlaceholderText(".thm,.xmp")
        self.inputs["upload-folder"]["exclude-ext"] = exc_ext
        form.add_row("Exclude extensions", exc_ext)

        ban_file = QPlainTextEdit()
        ban_file.setPlaceholderText("@eaDir/\n.DS_Store")
        self.inputs["upload-folder"]["ban-file"] = ban_file
        form.add_row("Skip files matching patterns", ban_file)

        chk_ignore = QCheckBox("Ignore sidecar files")
        self.inputs["upload-folder"]["ignore-sidecar"] = chk_ignore
        form.addRow("", chk_ignore)

        chk_date_name = QCheckBox("Guess dates from filenames")
        chk_date_name.setChecked(True)
        self.inputs["upload-folder"]["date-from-name"] = chk_date_name
        form.addRow("", chk_date_name)

        subhead = QLabel("Tagging")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_tags = QLineEdit()
        t_tags.setPlaceholderText("vacation, family/reunion")
        self.inputs["upload-folder"]["tag"] = t_tags
        form.add_row("Custom Tags (comma separated)", t_tags)

        chk_sess = QCheckBox("Session Tag")
        self.inputs["upload-folder"]["session-tag"] = chk_sess
        form.addRow("", chk_sess)

        chk_ftags = QCheckBox("Folder as Tags")
        self.inputs["upload-folder"]["folder-tags"] = chk_ftags
        form.addRow("", chk_ftags)

        subhead = QLabel("Run Behavior")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_err = QComboBox()
        c_err.addItems(["stop", "continue"])
        self.inputs["upload-folder"]["on-errors"] = c_err
        form.add_row("If a file fails", c_err)

        chk_overwrite = QCheckBox("Overwrite Existing")
        self.inputs["upload-folder"]["overwrite"] = chk_overwrite
        form.addRow("", chk_overwrite)

        chk_pause = QCheckBox("Pause background jobs")
        chk_pause.setChecked(True)
        self.inputs["upload-folder"]["pause-jobs"] = chk_pause
        form.addRow("", chk_pause)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        # FIX Phase 1 #7: removed per-tab skip-ssl (now global in config only)

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["upload-folder"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

        chk_trace = QCheckBox("Enable API Trace")
        self.inputs["upload-folder"]["api-trace"] = chk_trace
        form.addRow("", chk_trace)

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        lay.addWidget(adv_card)
        self.adv_frames.append(adv_card)

        lay.addStretch()
        return page

    def _build_upload_gp_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(24)
        self.inputs["upload-gp"] = {}

        card = Card("Source Configuration", required=True)
        form = FormSection()

        # FIX Phase 3 #27: QPlainTextEdit for multi-ZIP / glob input
        self.gp_path_edit = DroppablePlainTextEdit()
        self.gp_path_edit.setPlaceholderText(
            "/path/to/takeout-*.zip\n"
            "/path/to/takeout-001.zip\n"
            "/path/to/takeout-002.zip\n"
            "…or an extracted folder path"
        )
        self.gp_path_edit.setMaximumHeight(100)
        self.inputs["upload-gp"]["path"] = self.gp_path_edit

        btn_zips = QPushButton("Select ZIP Files…")
        btn_zips.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zips.clicked.connect(self.browse_takeout_zips)

        btn_folder = QPushButton("Select Extracted Folder…")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.clicked.connect(self.browse_takeout_folder)

        gp_btn_box = QHBoxLayout()
        gp_btn_box.setContentsMargins(0, 4, 0, 0)
        gp_btn_box.setSpacing(10)
        gp_btn_box.addWidget(btn_zips)
        gp_btn_box.addWidget(btn_folder)
        gp_btn_box.addStretch()

        gp_container = QWidget()
        gp_layout = QVBoxLayout(gp_container)
        gp_layout.setContentsMargins(0, 0, 0, 0)
        gp_layout.setSpacing(6)
        gp_layout.addWidget(self.gp_path_edit)
        gp_layout.addLayout(gp_btn_box)

        form.add_row(
            "Takeout Source",
            gp_container,
            "Paste multiple ZIP paths (one per line) or a glob pattern like takeout-*.zip"
        )

        card.layout.addLayout(form)
        lay.addWidget(card)

        card = Card("Options")
        form = FormSection()

        c_type = QComboBox()
        c_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs["upload-gp"]["include-type"] = c_type
        form.add_row("Media Type", c_type)

        t_album = QLineEdit()
        t_album.setPlaceholderText("e.g. Family Archive")
        self.inputs["upload-gp"]["into-album"] = t_album
        form.add_row("Put all into Album", t_album)

        chk_unmatched = QCheckBox("Include Unmatched Files")
        self.inputs["upload-gp"]["include-unmatched"] = chk_unmatched
        form.addRow("", chk_unmatched)

        chk_partner = QCheckBox("Include Partner Photos")
        chk_partner.setChecked(True)
        self.inputs["upload-gp"]["include-partner"] = chk_partner
        form.addRow("", chk_partner)

        chk_sync = QCheckBox("Sync Google Albums")
        chk_sync.setChecked(True)
        self.inputs["upload-gp"]["sync-albums"] = chk_sync
        form.addRow("", chk_sync)

        c_burst = QComboBox()
        c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs["upload-gp"]["manage-burst"] = c_burst
        form.add_row("Burst Photos", c_burst)

        c_heic = QComboBox()
        c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs["upload-gp"]["manage-heic-jpeg"] = c_heic
        form.add_row("HEIC + JPEG Pairs", c_heic)

        card.layout.addLayout(form)
        lay.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Takeout Specifics")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_album_name = QLineEdit()
        t_album_name.setPlaceholderText("Album Name")
        self.inputs["upload-gp"]["from-album-name"] = t_album_name
        form.add_row("From Specific Album", t_album_name)

        chk_archived = QCheckBox("Include Archived")
        chk_archived.setChecked(True)
        self.inputs["upload-gp"]["include-archived"] = chk_archived
        form.addRow("", chk_archived)

        chk_trashed = QCheckBox("Include Trashed")
        self.inputs["upload-gp"]["include-trashed"] = chk_trashed
        form.addRow("", chk_trashed)

        t_partner_album = QLineEdit()
        t_partner_album.setPlaceholderText("Album name for partner photos")
        self.inputs["upload-gp"]["partner-album"] = t_partner_album
        form.add_row("Partner Shared Album", t_partner_album)

        chk_takeout_tag = QCheckBox("Takeout Tag")
        chk_takeout_tag.setChecked(True)
        self.inputs["upload-gp"]["takeout-tag"] = chk_takeout_tag
        form.addRow("", chk_takeout_tag)

        chk_people_tag = QCheckBox("People Tag")
        chk_people_tag.setChecked(True)
        self.inputs["upload-gp"]["people-tag"] = chk_people_tag
        form.addRow("", chk_people_tag)

        subhead = QLabel("Tagging")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_tags = QLineEdit()
        t_tags.setPlaceholderText("vacation, family/reunion")
        self.inputs["upload-gp"]["tag"] = t_tags
        form.add_row("Custom Tags (comma separated)", t_tags)

        chk_sess = QCheckBox("Session Tag")
        self.inputs["upload-gp"]["session-tag"] = chk_sess
        form.addRow("", chk_sess)

        subhead = QLabel("Run Behavior")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_err = QComboBox()
        c_err.addItems(["stop", "continue"])
        self.inputs["upload-gp"]["on-errors"] = c_err
        form.add_row("If a file fails", c_err)

        chk_pause = QCheckBox("Pause background jobs")
        chk_pause.setChecked(True)
        self.inputs["upload-gp"]["pause-jobs"] = chk_pause
        form.addRow("", chk_pause)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        # FIX Phase 1 #7: removed per-tab skip-ssl

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["upload-gp"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

        # FIX Phase 2 #15: add --api-trace to upload-gp
        chk_trace = QCheckBox("Enable API Trace")
        self.inputs["upload-gp"]["api-trace"] = chk_trace
        form.addRow("", chk_trace)

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        lay.addWidget(adv_card)
        self.adv_frames.append(adv_card)

        lay.addStretch()
        return page

    def _build_upload_immich_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(24)
        self.inputs["upload-immich"] = {}

        card = Card("Source Configuration", required=True)
        form = FormSection()

        t_server = QLineEdit()
        t_server.setPlaceholderText("http://old-server:2283")
        self.inputs["upload-immich"]["from-server"] = t_server
        form.add_row("Source Server URL", t_server)

        t_api = QLineEdit()
        t_api.setEchoMode(QLineEdit.EchoMode.Password)
        t_api.setPlaceholderText("Source API Key")
        self.inputs["upload-immich"]["from-api-key"] = t_api
        form.add_row("Source API Key", t_api)

        # FIX Phase 2 #19: add --from-client-timeout
        from_timeout_spin = QSpinBox()
        from_timeout_spin.setRange(1, 1440)
        from_timeout_spin.setValue(20)
        from_timeout_spin.setSuffix(" minutes")
        self.inputs["upload-immich"]["from-client-timeout"] = from_timeout_spin
        form.add_row("Source Client Timeout", from_timeout_spin)

        chk_fav = QCheckBox("Only Favorites")
        self.inputs["upload-immich"]["from-favorite"] = chk_fav
        form.addRow("", chk_fav)

        chk_arch = QCheckBox("Include Archived")
        self.inputs["upload-immich"]["from-archived"] = chk_arch
        form.addRow("", chk_arch)

        chk_trash = QCheckBox("Include Trashed")
        self.inputs["upload-immich"]["from-trash"] = chk_trash
        form.addRow("", chk_trash)

        card.layout.addLayout(form)
        lay.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Source Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        d_range = QLineEdit()
        d_range.setPlaceholderText("2023-01-01,2023-12-31")
        self.inputs["upload-immich"]["from-date-range"] = d_range
        form.add_row("Date Range Filter", d_range)

        t_albums = QLineEdit()
        t_albums.setPlaceholderText("Family, Travel")
        self.inputs["upload-immich"]["from-albums"] = t_albums
        form.add_row("Filter by Albums", t_albums)

        s_rating = QSpinBox()
        s_rating.setRange(0, 5)
        self.inputs["upload-immich"]["from-minimal-rating"] = s_rating
        form.add_row("Minimum Rating", s_rating)

        t_people = QLineEdit()
        t_people.setPlaceholderText("John, Jane")
        self.inputs["upload-immich"]["from-people"] = t_people
        form.add_row("Filter by People", t_people)

        t_tags = QLineEdit()
        t_tags.setPlaceholderText("vacation, work")
        self.inputs["upload-immich"]["from-tags"] = t_tags
        form.add_row("Filter by Tags", t_tags)

        subhead = QLabel("Metadata Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_city = QLineEdit()
        t_city.setPlaceholderText("New York")
        self.inputs["upload-immich"]["from-city"] = t_city
        form.add_row("City", t_city)

        t_state = QLineEdit()
        t_state.setPlaceholderText("NY")
        self.inputs["upload-immich"]["from-state"] = t_state
        form.add_row("State", t_state)

        t_country = QLineEdit()
        t_country.setPlaceholderText("USA")
        self.inputs["upload-immich"]["from-country"] = t_country
        form.add_row("Country", t_country)

        t_make = QLineEdit()
        t_make.setPlaceholderText("Canon")
        self.inputs["upload-immich"]["from-make"] = t_make
        form.add_row("Camera Make", t_make)

        t_model = QLineEdit()
        t_model.setPlaceholderText("EOS R5")
        self.inputs["upload-immich"]["from-model"] = t_model
        form.add_row("Camera Model", t_model)

        subhead = QLabel("Run Behavior")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_err = QComboBox()
        c_err.addItems(["stop", "continue"])
        self.inputs["upload-immich"]["on-errors"] = c_err
        form.add_row("If a file fails", c_err)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        # FIX Phase 1 #7: removed per-tab skip-ssl (config-level only)

        chk_ssl_src = QCheckBox("Skip Source SSL Verification")
        self.inputs["upload-immich"]["from-skip-ssl"] = chk_ssl_src
        form.addRow("", chk_ssl_src)

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["upload-immich"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

        # FIX Phase 2 #15: add --api-trace to upload-immich
        chk_trace = QCheckBox("Enable API Trace")
        self.inputs["upload-immich"]["api-trace"] = chk_trace
        form.addRow("", chk_trace)

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        lay.addWidget(adv_card)
        self.adv_frames.append(adv_card)

        lay.addStretch()
        return page

    def _build_archive_folder_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(24)
        self.inputs["archive-folder"] = {}

        card = Card("Source Configuration", required=True)
        form = FormSection()

        p_edit = DroppableLineEdit()
        p_edit.setPlaceholderText("/path/to/files or /path/to/archive.zip")
        self.inputs["archive-folder"]["path"] = p_edit

        btn_folder = QPushButton("Select Folder…")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.clicked.connect(self.browse_folder_archive)

        btn_zip = QPushButton("Select ZIP Archive…")
        btn_zip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zip.clicked.connect(self.browse_zip_archive)

        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(0, 4, 0, 0)
        btn_box.setSpacing(10)
        btn_box.addWidget(btn_folder)
        btn_box.addWidget(btn_zip)
        btn_box.addStretch()

        p_container = QWidget()
        p_layout = QVBoxLayout(p_container)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(6)
        p_layout.addWidget(p_edit)
        p_layout.addLayout(btn_box)

        form.add_row("Source Folder Path", p_container)

        card.layout.addLayout(form)
        lay.addWidget(card)

        card = Card("Options")
        form = FormSection()

        t_write = DroppableLineEdit()
        t_write.setPlaceholderText("/organized-photos")
        self.inputs["archive-folder"]["write-to"] = t_write
        # FIX Phase 3 #32: browse button on archive destination
        self._add_browse_action(t_write, "Select Archive Destination")
        form.add_row("Destination Folder", t_write)

        c_raw = QComboBox()
        c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs["archive-folder"]["manage-raw-jpeg"] = c_raw
        form.add_row("Manage RAW+JPEG", c_raw)

        card.layout.addLayout(form)
        lay.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        d_range = QLineEdit()
        d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs["archive-folder"]["date-range"] = d_range
        form.add_row("Date Range", d_range)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["archive-folder"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        lay.addWidget(adv_card)
        self.adv_frames.append(adv_card)

        lay.addStretch()
        return page

    def _build_archive_immich_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(24)
        self.inputs["archive-immich"] = {}

        card = Card("Target Server")
        form = FormSection()

        t_server = QLineEdit()
        t_server.setEnabled(False)
        t_server.setText("Not Configured")
        self.inputs["archive-immich"]["target-server"] = t_server
        form.add_row("Immich Server URL", t_server, "Update in Configuration tab.")

        card.layout.addLayout(form)
        lay.addWidget(card)

        card = Card("Options")
        form = FormSection()

        t_write = DroppableLineEdit()
        t_write.setPlaceholderText("/backup/photos")
        self.inputs["archive-immich"]["write-to"] = t_write
        # FIX Phase 3 #32: browse button on archive destination
        self._add_browse_action(t_write, "Select Archive Destination")
        form.add_row("Destination Folder", t_write)

        c_burst = QComboBox()
        c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs["archive-immich"]["manage-burst"] = c_burst
        form.add_row("Manage Bursts", c_burst)

        c_raw = QComboBox()
        c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs["archive-immich"]["manage-raw-jpeg"] = c_raw
        form.add_row("Manage RAW+JPEG", c_raw)

        card.layout.addLayout(form)
        lay.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Source Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        d_range = QLineEdit()
        d_range.setPlaceholderText("2023-01-01,2023-12-31")
        self.inputs["archive-immich"]["from-date-range"] = d_range
        form.add_row("Date Range Filter", d_range)

        t_albums = QLineEdit()
        t_albums.setPlaceholderText("Family, Travel")
        self.inputs["archive-immich"]["from-albums"] = t_albums
        form.add_row("Specific Albums", t_albums)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        # FIX Phase 1 #7: removed per-tab skip-ssl

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["archive-immich"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        lay.addWidget(adv_card)
        self.adv_frames.append(adv_card)

        lay.addStretch()
        return page

    def _build_stack_tab(self):
        page = BasePage()
        self.inputs["stack"] = {}

        card = Card("Target Server")
        form = FormSection()

        t_server = QLineEdit()
        t_server.setEnabled(False)
        t_server.setText("Not Configured")
        self.inputs["stack"]["target-server"] = t_server
        form.add_row("Immich Server URL", t_server, "Update in Configuration tab.")

        card.layout.addLayout(form)
        page.addWidget(card)

        card = Card("Options")
        form = FormSection()

        c_burst = QComboBox()
        c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs["stack"]["manage-burst"] = c_burst
        form.add_row("Manage Bursts", c_burst)

        c_raw = QComboBox()
        c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs["stack"]["manage-raw-jpeg"] = c_raw
        form.add_row("Manage RAW+JPEG", c_raw)

        c_heic = QComboBox()
        c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs["stack"]["manage-heic-jpeg"] = c_heic
        form.add_row("Manage HEIC+JPEG", c_heic)

        card.layout.addLayout(form)
        page.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Detection Tuning")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_tz = QLineEdit()
        t_tz.setPlaceholderText("America/New_York")
        self.inputs["stack"]["time-zone"] = t_tz
        form.add_row("Time Zone Override", t_tz)

        chk_epson = QCheckBox("Manage Epson FastFoto")
        self.inputs["stack"]["manage-epson"] = chk_epson
        form.addRow("", chk_epson)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        # FIX Phase 1 #7: removed per-tab skip-ssl

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["stack"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

        # FIX Phase 2 #15: add --api-trace to stack
        chk_trace = QCheckBox("Enable API Trace")
        self.inputs["stack"]["api-trace"] = chk_trace
        form.addRow("", chk_trace)

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)

        page.addStretch()
        return page

    # ==========================================================
    # UI INTERACTIONS & LOGIC
    # ==========================================================

    def toggle_advanced(self, checked):
        self.is_advanced = checked
        self.lbl_mode.setText("Advanced" if checked else "Simple")
        for w in self.adv_frames:
            w.setVisible(checked)

    def switch_tab(self, index, crumb, btn):
        self.stacked_widget.setCurrentIndex(index)
        if index == 1 and hasattr(self, "upload_tabs"):
            u_crumbs = {
                0: "upload · from-folder",
                1: "upload · from-google-photos",
                2: "upload · from-immich",
            }
            crumb = u_crumbs.get(self.upload_tabs.currentIndex(), "upload")
        elif index == 2 and hasattr(self, "archive_tabs"):
            a_crumbs = {
                0: "archive · from-folder",
                1: "archive · from-immich",
            }
            crumb = a_crumbs.get(self.archive_tabs.currentIndex(), "archive")
        self.update_header_crumb(crumb)
        for w in [
            self.btn_config,
            self.btn_upload,
            self.btn_archive,
            self.btn_stack,
        ]:
            w.setChecked(False)
        btn.setChecked(True)
        self.footer.setVisible(index != 0)
        tab_key = self._get_active_tab_key()
        if tab_key in self.inputs and "target-server" in self.inputs[tab_key]:
            srv_edit = self.inputs.get("config", {}).get("server")
            srv = srv_edit.text() if srv_edit else ""
            self.inputs[tab_key]["target-server"].setText(srv if srv else "Not Configured")

    def update_header_crumb(self, text):
        self.lbl_crumb.setText(text)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        save_action = QAction("Save Configuration", self)
        save_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_action)
        load_action = QAction("Load Configuration", self)
        load_action.triggered.connect(self.load_configuration)
        file_menu.addAction(load_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About Immich-Go", self)
        about_action.triggered.connect(self.open_github_link)
        help_menu.addAction(about_action)

    def browse_folder_upload(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", "", QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.inputs["upload-folder"]["path"].setText(folder)

    def browse_zip_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ZIP Archive", "", "ZIP archives (*.zip *.ZIP);;All Files (*)", options=QFileDialog.Option(0)
        )
        if file_path:
            self.inputs["upload-folder"]["path"].setText(file_path)

    def browse_takeout_zips(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Takeout ZIP parts", "", "ZIP archives (*.zip *.ZIP);;All Files (*)", options=QFileDialog.Option(0)
        )
        if files:
            self.inputs["upload-gp"]["path"].setPlainText("\n".join(files))

    def browse_takeout_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Extracted Folder", "", QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.inputs["upload-gp"]["path"].setPlainText(folder)

    def browse_folder_archive(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", "", QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.inputs["archive-folder"]["path"].setText(folder)

    def browse_zip_archive(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ZIP Archive", "", "ZIP archives (*.zip *.ZIP);;All Files (*)", options=QFileDialog.Option(0)
        )
        if file_path:
            self.inputs["archive-folder"]["path"].setText(file_path)

    def browse_takeout_source(self):
        self.browse_takeout_zips()

    def browse_local_folder(self):
        self.browse_folder_upload()

    def _collect_config_state(self) -> dict:
        cpu_default = min(max(os.cpu_count() or 2, 1), 20)
        c = self.inputs.get("config", {})
        return {
            "server": c.get("server").text() if c.get("server") else "",
            "api_key": c.get("api_key").text().strip() if c.get("api_key") else "",
            "skip-ssl": c.get("skip-ssl").isChecked() if c.get("skip-ssl") else False,
            "client_timeout": c.get("client_timeout").value() if c.get("client_timeout") else 20,
            "concurrent": c.get("concurrent").value() if c.get("concurrent") else cpu_default,
            "concurrent_default": cpu_default,
            "device_uuid": c.get("device_uuid").text().strip() if c.get("device_uuid") else "",
            "on_errors": c.get("on_errors").currentText() if c.get("on_errors") else "stop",
            "on_errors_tolerance": c.get("on_errors_tolerance").value() if c.get("on_errors_tolerance") else 10,
            "pause_jobs": c.get("pause_jobs").isChecked() if c.get("pause_jobs") else True,
        }

    def _collect_tab_state(self, tab_key: str) -> dict:
        if tab_key not in self.inputs:
            return {}
        c = self.inputs[tab_key]

        if tab_key == "upload-folder":
            return {
                "path": c["path"].text(),
                "include-type": c["include-type"].currentText(),
                "folder-album": c["folder-album"].currentText(),
                "into-album": c["into-album"].text(),
                "manage-burst": c["manage-burst"].currentText(),
                "manage-raw-jpeg": c["manage-raw-jpeg"].currentText(),
                "manage-heic-jpeg": c["manage-heic-jpeg"].currentText(),
                "date-range": c["date-range"].text(),
                "include-ext": c["include-ext"].text(),
                "exclude-ext": c["exclude-ext"].text(),
                "ban-file": c["ban-file"].toPlainText(),
                "ignore-sidecar": c["ignore-sidecar"].isChecked(),
                "date-from-name": c["date-from-name"].isChecked(),
                "tag": c["tag"].text(),
                "session-tag": c["session-tag"].isChecked(),
                "folder-tags": c["folder-tags"].isChecked(),
                "on-errors": c["on-errors"].currentText() if "on-errors" in c else "stop",
                "overwrite": c["overwrite"].isChecked(),
                "pause-jobs": c["pause-jobs"].isChecked() if "pause-jobs" in c else True,
                "log-level": c["log-level"].currentText() if "log-level" in c else "INFO",
                "api-trace": c["api-trace"].isChecked() if "api-trace" in c else False,
            }

        elif tab_key == "upload-gp":
            return {
                "path": c["path"].toPlainText(),
                "include-type": c["include-type"].currentText(),
                "into-album": c["into-album"].text(),
                "include-unmatched": c["include-unmatched"].isChecked(),
                "include-partner": c["include-partner"].isChecked(),
                "sync-albums": c["sync-albums"].isChecked(),
                "manage-burst": c["manage-burst"].currentText(),
                "manage-heic-jpeg": c["manage-heic-jpeg"].currentText(),
                "from-album-name": c["from-album-name"].text(),
                "include-archived": c["include-archived"].isChecked(),
                "include-trashed": c["include-trashed"].isChecked(),
                "partner-album": c["partner-album"].text(),
                "takeout-tag": c["takeout-tag"].isChecked(),
                "people-tag": c["people-tag"].isChecked(),
                "tag": c["tag"].text(),
                "session-tag": c["session-tag"].isChecked(),
                "on-errors": c["on-errors"].currentText() if "on-errors" in c else "stop",
                "pause-jobs": c["pause-jobs"].isChecked() if "pause-jobs" in c else True,
                "log-level": c["log-level"].currentText() if "log-level" in c else "INFO",
                "api-trace": c["api-trace"].isChecked() if "api-trace" in c else False,
            }

        elif tab_key == "upload-immich":
            return {
                "from-server": c["from-server"].text(),
                "from-api-key": c["from-api-key"].text(),
                "from-client-timeout": c["from-client-timeout"].value() if "from-client-timeout" in c else 20,
                "from-favorite": c["from-favorite"].isChecked(),
                "from-archived": c["from-archived"].isChecked(),
                "from-trash": c["from-trash"].isChecked(),
                "from-date-range": c["from-date-range"].text(),
                "from-albums": c["from-albums"].text(),
                "from-minimal-rating": c["from-minimal-rating"].value(),
                "from-people": c["from-people"].text(),
                "from-tags": c["from-tags"].text(),
                "from-city": c["from-city"].text(),
                "from-state": c["from-state"].text(),
                "from-country": c["from-country"].text(),
                "from-make": c["from-make"].text(),
                "from-model": c["from-model"].text(),
                "from-skip-ssl": c["from-skip-ssl"].isChecked(),
                "on-errors": c["on-errors"].currentText() if "on-errors" in c else "stop",
                "log-level": c["log-level"].currentText() if "log-level" in c else "INFO",
                "api-trace": c["api-trace"].isChecked() if "api-trace" in c else False,
            }

        elif tab_key == "archive-folder":
            return {
                "path": c["path"].text(),
                "write-to": c["write-to"].text(),
                "manage-raw-jpeg": c["manage-raw-jpeg"].currentText(),
                "date-range": c["date-range"].text(),
                "log-level": c["log-level"].currentText() if "log-level" in c else "INFO",
            }

        elif tab_key == "archive-immich":
            return {
                "write-to": c["write-to"].text(),
                "manage-burst": c["manage-burst"].currentText(),
                "manage-raw-jpeg": c["manage-raw-jpeg"].currentText(),
                "from-date-range": c["from-date-range"].text(),
                "from-albums": c["from-albums"].text(),
                "log-level": c["log-level"].currentText() if "log-level" in c else "INFO",
            }

        elif tab_key == "stack":
            return {
                "manage-burst": c["manage-burst"].currentText(),
                "manage-raw-jpeg": c["manage-raw-jpeg"].currentText(),
                "manage-heic-jpeg": c["manage-heic-jpeg"].currentText(),
                "time-zone": c["time-zone"].text(),
                "manage-epson": c["manage-epson"].isChecked(),
                "log-level": c["log-level"].currentText() if "log-level" in c else "INFO",
                "api-trace": c["api-trace"].isChecked() if "api-trace" in c else False,
            }

        return {}

    def validate_inputs(self) -> ValidationResult:
        tab_key = self._get_active_tab_key()
        if tab_key == "config":
            return ValidationResult()

        config_state = self._collect_config_state()
        tab_state = self._collect_tab_state(tab_key)

        return validate_state(
            tab_key=tab_key,
            config_state=config_state,
            tab_state=tab_state,
        )

    def on_test_connection_clicked(self):
        srv_widget = self.inputs.get("config", {}).get("server")
        api_widget = self.inputs.get("config", {}).get("api_key")
        ssl_widget = self.inputs.get("config", {}).get("skip-ssl")

        server_url = srv_widget.text().strip() if srv_widget else ""
        api_key = api_widget.text().strip() if api_widget else ""
        skip_ssl = ssl_widget.isChecked() if ssl_widget else False

        if not server_url:
            QMessageBox.warning(self, "Test Connection", "Please enter a Server URL first.")
            return
        if not api_key:
            QMessageBox.warning(self, "Test Connection", "Please enter an API Key first.")
            return

        res = test_immich_connection(server_url, api_key, skip_ssl=skip_ssl)
        if res.ok:
            QMessageBox.information(self, "Test Connection Succeeded", res.message)
        else:
            QMessageBox.warning(self, "Test Connection Failed", res.message)

    def update_status(self):
        is_running = getattr(self, "running_process", None) is not None
        validation = self.validate_inputs()

        if is_running:
            self.lbl_running_warning.setVisible(True)
            self.btn_run.setEnabled(False)
            self.btn_dry_run.setEnabled(False)
        else:
            self.lbl_running_warning.setVisible(False)

        active_tab = self._get_active_tab_key()
        if active_tab == "config":
            srv_widget = self.inputs.get("config", {}).get("server")
            api_widget = self.inputs.get("config", {}).get("api_key")
            srv_text = srv_widget.text().strip() if srv_widget else ""
            key_text = api_widget.text().strip() if api_widget else ""
            if srv_text and key_text:
                self.status_card.set_server("ok", "Server: Configured")
            else:
                self.status_card.set_server("err", "Server: Not Set")
        elif validation.is_valid:
            self.status_card.set_server("ok", "Server: Ready")
            if not is_running:
                self.btn_run.setEnabled(True)
                self.btn_dry_run.setEnabled(True)
        else:
            first_error = validation.errors[0] if validation.errors else "Server: Not Set"
            self.status_card.set_server("err", f"Server: {first_error}")
            if not is_running:
                self.btn_run.setEnabled(False)
                self.btn_dry_run.setEnabled(False)

        srv_edit = self.inputs.get("config", {}).get("server")
        srv = normalize_server_url(srv_edit.text()) if srv_edit else ""
        for t in ["archive-immich", "stack"]:
            if t in self.inputs and "target-server" in self.inputs[t]:
                self.inputs[t]["target-server"].setText(srv if srv else "Not Configured")

    def build_plan(self, dry_run: bool) -> CommandPlan:
        tab_key = self._get_active_tab_key()
        if tab_key == "config":
            return CommandPlan(errors=["No executable tab selected."], tab_key=tab_key)

        config_state = self._collect_config_state()
        tab_state = self._collect_tab_state(tab_key)

        binary_path = getattr(self, "binary_path", "")
        if not binary_path:
            binary_path = get_binary_path(load_binary_metadata()) or "./immich-go"

        return build_plan_from_state(
            tab_key=tab_key,
            config_state=config_state,
            tab_state=tab_state,
            binary_path=binary_path,
            dry_run=dry_run,
        )

    def build_command(self, dry_run: bool) -> list[str]:
        """Backwards-compatible wrapper returning plan.argv."""
        return self.build_plan(dry_run).argv

    def show_confirm_dialog(self, is_dry_run):
        if self.stacked_widget.currentIndex() == 0:
            return

        ready, msg = self.check_binary_ready()
        if not ready:
            reply = QMessageBox.question(
                self, "Binary Not Ready",
                f"{msg}\n\nDo you want to download it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if not self.update_binary(force_download=True):
                    return
                ready, msg = self.check_binary_ready()
                if not ready:
                    QMessageBox.critical(self, "Error", msg)
                    return
            else:
                return

        validation = self.validate_inputs()
        if validation.errors:
            QMessageBox.warning(
                self, "Validation Errors",
                "\n".join(f"• {e}" for e in validation.errors)
            )
            return

        plan = self.build_plan(dry_run=is_dry_run)
        if validation.warnings:
            for w in validation.warnings:
                if w not in plan.warnings:
                    plan.warnings.insert(0, w)

        dlg = QDialog(self)
        dlg.setWindowTitle("Confirm Execution")
        dlg.setModal(True)
        dlg.resize(680, 520)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(10)

        kicker = QLabel("Dry run" if is_dry_run else "Live execution")
        kicker.setObjectName("DlgKicker")
        layout.addWidget(kicker)

        title = QLabel("This is what will run")
        title.setObjectName("DlgTitle")
        layout.addWidget(title)

        desc = QLabel(
            "A dry run simulates the action. No files are changed."
            if is_dry_run
            else "This executes the real command in an external terminal."
        )
        desc.setObjectName("DlgDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        lbl_binary = QLabel("Binary")
        lbl_binary.setObjectName("Subhead")
        layout.addWidget(lbl_binary)

        binary_edit = QLineEdit(plan.binary_path)
        binary_edit.setReadOnly(True)
        layout.addWidget(binary_edit)

        lbl_cmd = QLabel("Command")
        lbl_cmd.setObjectName("Subhead")
        layout.addWidget(lbl_cmd)

        if sys.platform.startswith("win"):
            cmd_str = subprocess.list2cmdline(plan.display_argv)
        else:
            cmd_str = (
                plan.display_argv[0] + " "
                + " ".join(shlex.quote(p) for p in plan.display_argv[1:])
            )

        cmd_block = QPlainTextEdit()
        cmd_block.setObjectName("CmdBlock")
        cmd_block.setPlainText(cmd_str)
        cmd_block.setReadOnly(True)
        cmd_block.setMaximumHeight(110)
        layout.addWidget(cmd_block)

        immich_env = {
            k: v for k, v in plan.env.items()
            if k.startswith("IMMICH_GO_")
        }
        if immich_env:
            lbl_env = QLabel("Environment Variables")
            lbl_env.setObjectName("Subhead")
            layout.addWidget(lbl_env)

            env_lines = []
            secret_env_keys = {"API_KEY", "FROM_API_KEY", "ADMIN_API_KEY"}
            for k, v in sorted(immich_env.items()):
                is_secret = any(s in k for s in secret_env_keys)
                display_v = "********" if is_secret else v
                env_lines.append(f"{k}={display_v}")

            env_block = QPlainTextEdit()
            env_block.setObjectName("CmdBlock")
            env_block.setPlainText("\n".join(env_lines))
            env_block.setReadOnly(True)
            env_block.setMaximumHeight(75)
            layout.addWidget(env_block)

        if plan.warnings:
            lbl_warn = QLabel("Warnings")
            lbl_warn.setObjectName("Subhead")
            layout.addWidget(lbl_warn)

            for w in plan.warnings:
                warn_lbl = QLabel(f"⚠️ {w}")
                warn_lbl.setObjectName("WarningHint")
                warn_lbl.setWordWrap(True)
                warn_lbl.setStyleSheet(
                    "background-color: rgba(229,192,123,0.12); padding: 8px; "
                    "border-radius: 6px; border: 1px solid #E5C07B;"
                )
                layout.addWidget(warn_lbl)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_copy = QPushButton("Copy Command")
        btn_copy.setObjectName("BtnPreview")
        btn_copy.clicked.connect(
            lambda: QApplication.clipboard().setText(cmd_str)
        )
        btn_row.addWidget(btn_copy)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("BtnPreview")
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("Run preview" if is_dry_run else "Start execution")
        btn_confirm.setObjectName("BtnRun")
        btn_confirm.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_confirm)

        layout.addLayout(btn_row)

        if dlg.exec():
            self.run_command(plan)

    # ==========================================================
    # BACKEND LOGIC
    # ==========================================================

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
            self.lbl_binary_version.setText(f"Current Version: {version_text}")
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
        allow_untested = getattr(self.app_config, "allow_untested_updates", False) if hasattr(self, "app_config") else False

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

    def update_binary(self, version: str | None = None, force_download: bool = False):
        if version is None:
            version = self.get_latest_release_info()
            if not version:
                QMessageBox.critical(self, "Error", "Could not determine latest version.")
                return False

        clean_version = version.lstrip("v")
        version_dir = os.path.join(BINARY_BASE_DIR, clean_version)
        os.makedirs(version_dir, exist_ok=True)

        binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        binary_path = os.path.join(version_dir, binary_filename)

        if os.path.exists(binary_path) and not force_download:
            self._select_version(clean_version, binary_path)
            return True

        download_url = self.get_download_url(version=clean_version)
        if not download_url:
            QMessageBox.critical(
                self, "Error",
                f"Could not determine download URL for version {clean_version} on this platform."
            )
            return False

        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Downloading Immich-Go")
        progress_dialog.setFixedWidth(400)
        layout = QVBoxLayout(progress_dialog)
        status_label = QLabel(f"Downloading Immich-Go v{clean_version}...")
        layout.addWidget(status_label)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        layout.addWidget(progress_bar)
        cancel_button = QPushButton("Cancel")
        layout.addWidget(cancel_button)
        progress_dialog.setWindowFlags(
            progress_dialog.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )

        class DownloadThread(QThread):
            download_progress = Signal(int)
            download_complete = Signal(bytes)
            download_error = Signal(str)

            def __init__(self, download_url):
                super().__init__()
                self.download_url = download_url

            def run(self):
                try:
                    response = requests.get(self.download_url, stream=True, timeout=60)
                    response.raise_for_status()
                    total_size = int(response.headers.get("content-length", 0))
                    block_size = 1024
                    downloaded_size = 0
                    content = io.BytesIO()
                    for data in response.iter_content(block_size):
                        downloaded_size += len(data)
                        content.write(data)
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.download_progress.emit(progress)
                    self.download_complete.emit(content.getvalue())
                except Exception as e:
                    self.download_error.emit(str(e))

        try:
            download_thread = DownloadThread(download_url)

            def handle_download_complete(content):
                progress_dialog.accept()
                try:
                    if download_url.endswith(".zip"):
                        with zipfile.ZipFile(io.BytesIO(content)) as z:
                            for filename in z.namelist():
                                base = os.path.basename(filename)
                                if base in ("immich-go", "immich-go.exe"):
                                    with z.open(filename) as source, open(binary_path, "wb") as target:
                                        target.write(source.read())
                                    break
                    elif download_url.endswith(".tar.gz"):
                        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
                            for member in tar.getmembers():
                                base = os.path.basename(member.name)
                                if base in ("immich-go", "immich-go.exe"):
                                    source = tar.extractfile(member)
                                    if source:
                                        with open(binary_path, "wb") as target:
                                            target.write(source.read())
                                    break
                    else:
                        raise ValueError("Unsupported archive type")
                    if not sys.platform.startswith("win"):
                        os.chmod(binary_path, 0o755)

                    self._select_version(clean_version, binary_path)
                except Exception as extraction_error:
                    QMessageBox.critical(
                        self, "Extraction Error",
                        f"Failed to extract binary: {str(extraction_error)}\n\n"
                        "Please download manually from GitHub."
                    )

            def handle_download_error(error):
                progress_dialog.reject()
                QMessageBox.critical(self, "Download Error", f"Failed to download: {error}")

            download_thread.download_progress.connect(progress_bar.setValue)
            download_thread.download_complete.connect(handle_download_complete)
            download_thread.download_error.connect(handle_download_error)

            def cancel_download():
                download_thread.terminate()
                progress_dialog.reject()

            cancel_button.clicked.connect(cancel_download)
            progress_dialog.show()
            download_thread.start()
            progress_dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self, "Download Error",
                f"Failed to initiate download: {str(e)}"
            )
            return False
        return True

    def build_environment(self, tab_key: str = None) -> dict:
        if tab_key is None:
            tab_key = self._get_active_tab_key()
        server = self.inputs.get("config", {}).get("server").text().strip() if self.inputs.get("config", {}).get("server") else ""
        api_key = self.inputs.get("config", {}).get("api_key").text().strip() if self.inputs.get("config", {}).get("api_key") else ""
        from_server = self.inputs.get("upload-immich", {}).get("from-server").text().strip() if self.inputs.get("upload-immich", {}).get("from-server") else ""
        from_api_key = self.inputs.get("upload-immich", {}).get("from-api-key").text().strip() if self.inputs.get("upload-immich", {}).get("from-api-key") else ""
        return build_environment(tab_key, server, api_key, from_server, from_api_key)

    def run_command(self, plan_or_parts=None):
        if isinstance(plan_or_parts, CommandPlan):
            plan = plan_or_parts
            command_parts = plan.argv
            env = plan.env
            binary_path = plan.binary_path or getattr(self, "binary_path", "./immich-go")
        else:
            command_parts = plan_or_parts or []
            tab_key = self._get_active_tab_key()
            env = self.build_environment(tab_key)
            binary_path = getattr(self, "binary_path", "./immich-go")

        if not os.path.exists(binary_path):
            if not self.update_binary():
                QMessageBox.critical(
                    self, "Error",
                    "Immich-Go binary is missing or not executable."
                )
                return

        # Defense-in-depth: strip any secret flags that may have leaked
        # into argv from legacy code paths. With CommandPlan, secrets are never
        # added to argv, but this prevents accidental CLI exposure.
        clean_parts = []
        skip_next = False
        for part in command_parts:
            if skip_next:
                skip_next = False
                continue
            if part.startswith("--api-key=") or part.startswith("--from-api-key=") or part.startswith("--admin-api-key="):
                continue
            if part in ("--api-key", "--from-api-key", "--admin-api-key"):
                skip_next = True
                continue
            clean_parts.append(part)

        command = [binary_path] + clean_parts

        self.process_tracker = ProcessTracker()
        lock_path = self.process_tracker.create_lock()

        try:
            self.btn_run.setDisabled(True)
            self.btn_dry_run.setDisabled(True)

            if sys.platform.startswith("win"):
                cmd_string = subprocess.list2cmdline(command)
                bat_content = (
                    f"@echo off\n"
                    f"{cmd_string}\n"
                    f'del /f "{lock_path}" 2>nul\n'
                )
                bat_path = lock_path.replace(".lock", ".bat")
                with open(bat_path, "w") as f:
                    f.write(bat_content)
                subprocess.Popen(
                    ["cmd", "/c", "start", "cmd", "/k", bat_path],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    env=env,
                )
            elif sys.platform.startswith("darwin"):
                cmd_str = shlex.join(command)
                wrapped = self.process_tracker.wrap_command_with_lock(cmd_str)
                apple_script = (
                    'tell application "Terminal" to do script '
                    f'"{wrapped}; exec bash"'
                )
                subprocess.Popen(["osascript", "-e", apple_script], env=env)
            else:
                cmd_str = shlex.join(command)
                wrapped = self.process_tracker.wrap_command_with_lock(cmd_str)
                terminals = [
                    ("gnome-terminal", "--", "bash", "-c", f"{wrapped}; exec bash"),
                    ("konsole", "-e", "bash", "-c", f"{wrapped}; exec bash"),
                    ("xfce4-terminal", "-e", "bash", "-c", f"{wrapped}; exec bash"),
                    ("xterm", "-hold", "-e", "bash", "-c", wrapped),
                ]
                for term in terminals:
                    try:
                        subprocess.Popen(term, env=env)
                        break
                    except FileNotFoundError:
                        continue
                else:
                    self.process_tracker.release_lock()
                    QMessageBox.critical(self, "Error", "No suitable terminal emulator found.")
                    self.btn_run.setDisabled(False)
                    self.btn_dry_run.setDisabled(False)
                    return

            self.running_process = True
            self.check_process_timer = QTimer()
            self.check_process_timer.timeout.connect(self._check_lock_file)
            self.check_process_timer.start(1000)
            self.update_status()

        except Exception as e:
            self.process_tracker.release_lock()
            QMessageBox.critical(self, "Error", f"Failed to run command: {e}")
            self.btn_run.setDisabled(False)
            self.btn_dry_run.setDisabled(False)

    def _check_lock_file(self):
        if not hasattr(self, "process_tracker"):
            if hasattr(self, "check_process_timer"):
                self.check_process_timer.stop()
            return

        if not self.process_tracker.is_running:
            if hasattr(self, "check_process_timer"):
                self.check_process_timer.stop()
            self.process_tracker.release_lock()
            self.running_process = None
            self.update_status()

    def check_if_process_running(self):
        """Backward compatible alias for _check_lock_file."""
        self._check_lock_file()

    # ==========================================================
    # PERSISTENCE
    # ==========================================================

    def _migrate_legacy_qsettings_to_config(self):
        cfg = AppConfig()
        cfg.server_url = self.settings.value("server_url", "")
        cfg.skip_ssl = self.settings.value("skip_ssl", False, type=bool)
        cfg.theme_mode = normalize_theme_mode(
            self.settings.value("theme_mode", THEME_SYSTEM)
        )
        save_config(cfg)
        old_key = self.settings.value("api_key", "")
        if old_key:
            set_api_key(old_key, cfg)
            self.settings.remove("api_key")
            self.settings.sync()

    def load_configuration(self):
        self.app_config = load_config()

        if not default_config_path().exists():
            self._migrate_legacy_qsettings_to_config()
            self.app_config = load_config()

        self.inputs["config"]["server"].setText(self.app_config.server_url)

        if "skip-ssl" in self.inputs["config"]:
            self.inputs["config"]["skip-ssl"].setChecked(self.app_config.skip_ssl)

        self.inputs["config"]["api_key"].setText(
            get_api_key(self.app_config)
        )

        if "client_timeout" in self.inputs["config"]:
            self.inputs["config"]["client_timeout"].setValue(
                self.app_config.client_timeout_minutes
            )

        if "concurrent" in self.inputs["config"] and self.app_config.concurrent_tasks > 0:
            self.inputs["config"]["concurrent"].setValue(
                self.app_config.concurrent_tasks
            )

        if "device_uuid" in self.inputs["config"]:
            self.inputs["config"]["device_uuid"].setText(
                self.app_config.device_uuid
            )

        if "on_errors" in self.inputs["config"]:
            if self.app_config.on_errors == "custom":
                self.inputs["config"]["on_errors"].setCurrentText("custom…")
            else:
                self.inputs["config"]["on_errors"].setCurrentText(
                    self.app_config.on_errors
                )

        if "on_errors_tolerance" in self.inputs["config"]:
            self.inputs["config"]["on_errors_tolerance"].setValue(
                self.app_config.on_errors_tolerance
            )

        if "pause_jobs" in self.inputs["config"]:
            self.inputs["config"]["pause_jobs"].setChecked(
                self.app_config.pause_immich_jobs
            )

        self.theme_mode = normalize_theme_mode(self.app_config.theme_mode)

        if hasattr(self, "theme_mode_combo"):
            self.theme_mode_combo.blockSignals(True)
            self.theme_mode_combo.setCurrentText(self.theme_mode)
            self.theme_mode_combo.blockSignals(False)

        self.apply_theme(self.theme_mode)

    def save_configuration(self):
        self.app_config.server_url = self.inputs["config"]["server"].text()

        if "skip-ssl" in self.inputs["config"]:
            self.app_config.skip_ssl = self.inputs["config"]["skip-ssl"].isChecked()

        if "client_timeout" in self.inputs["config"]:
            self.app_config.client_timeout_minutes = (
                self.inputs["config"]["client_timeout"].value()
            )

        if "concurrent" in self.inputs["config"]:
            self.app_config.concurrent_tasks = (
                self.inputs["config"]["concurrent"].value()
            )

        if "device_uuid" in self.inputs["config"]:
            self.app_config.device_uuid = (
                self.inputs["config"]["device_uuid"].text().strip()
            )

        if "on_errors" in self.inputs["config"]:
            on_errors_text = self.inputs["config"]["on_errors"].currentText()
            if on_errors_text == "custom…":
                self.app_config.on_errors = "custom"
            else:
                self.app_config.on_errors = on_errors_text

        if "on_errors_tolerance" in self.inputs["config"]:
            self.app_config.on_errors_tolerance = (
                self.inputs["config"]["on_errors_tolerance"].value()
            )

        if "pause_jobs" in self.inputs["config"]:
            self.app_config.pause_immich_jobs = (
                self.inputs["config"]["pause_jobs"].isChecked()
            )

        if hasattr(self, "theme_mode_combo"):
            self.app_config.theme_mode = self.theme_mode_combo.currentText()

        save_config(self.app_config)

        api_key = self.inputs["config"]["api_key"].text().strip()
        set_api_key(api_key, self.app_config)

        QMessageBox.information(
            self,
            "Saved",
            "Configuration saved successfully.",
        )

    def open_github_link(self):
        webbrowser.open("https://github.com/simulot/immich-go")


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    set_fusion_style()
    base_font = QFont()
    base_font.setFamilies([
        "Segoe UI", "Segoe UI Emoji",
        "Helvetica Neue", "Apple Color Emoji",
        "Noto Sans", "Noto Color Emoji", "DejaVu Sans", "Ubuntu",
        "sans-serif",
    ])
    base_font.setPointSize(10)
    app.setFont(base_font)
    window = ImmichGoGUI()
    window.show()
    sys.exit(app.exec())