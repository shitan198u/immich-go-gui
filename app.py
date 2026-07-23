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
from pathlib import Path
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
from core.profile_manager import (
    list_profiles, active_profile_name, set_active_profile_name,
    create_profile, rename_profile, duplicate_profile, delete_profile,
    validate_profile_name, ensure_default_profile
)
from core.process_tracker import (
    create_lock, release_lock, read_lock, is_lock_active,
    scan_locks, cleanup_stale_locks, reset_all_locks
)
from core.terminal_launcher import launch_external_terminal, LaunchResult


from core import (
    AppConfig,
    BINARY_BASE_DIR,
    METADATA_PATH,
    TESTED_IMMICH_GO_VERSION,
    ENV_KEY_MAP,
    ON_ERRORS_CUSTOM_LABEL,
    ON_ERRORS_CUSTOM_VALUE,
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
    default_secrets_path,
    get_api_key,
    get_binary_path,
    get_secret_with_fallback,
    load_binary_metadata,
    load_config,
    mask_command_for_display,
    normalize_server_url,
    save_binary_metadata,
    save_config,
    save_secret_with_fallback,
    set_api_key,
    validate_date_range,
    validate_state,
    SecretStore,
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
        self.settings = QSettings("Shitan198u", "ImmichGoGUI")

        # FIX Phase 1 #6: migrate old plain-text API key to keychain
        SecretStore.migrate_from_qsettings(self.settings)

        from core.terminal_launcher import cleanup_stale_temp_dirs
        cleanup_stale_temp_dirs()

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

        cleanup_stale_locks()
        active_locks = scan_locks()
        self.active_lock_path = active_locks[0].lock_path if active_locks else None
        self.running_process = bool(self.active_lock_path)
        if self.active_lock_path:
            self._start_process_timer()

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

        card_sec = Card("Security & Secret Management")
        sec_form = FormSection()

        self.cmb_secret_provider = QComboBox()
        self.cmb_secret_provider.addItem("OS Keyring (recommended)", "keyring")
        self.cmb_secret_provider.addItem("Local secrets file", "config")
        self.inputs["config"]["secret_provider"] = self.cmb_secret_provider
        sec_form.add_row(
            "Secret Storage",
            self.cmb_secret_provider,
            "OS Keyring uses system credential store (Keychain/KWallet/Credential Manager)."
        )

        self.admin_api_key_edit = QLineEdit()
        self.admin_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_api_key_edit.setPlaceholderText("Optional Immich Admin API key")
        self.inputs["config"]["admin_api_key"] = self.admin_api_key_edit
        sec_form.add_row(
            "Admin API Key",
            self.admin_api_key_edit,
            "Required for administrative operations like partner shared albums or user management."
        )

        self.lbl_secrets_path_hint = QLabel(f"Local secrets path: {default_secrets_path()}")
        self.lbl_secrets_path_hint.setObjectName("Hint")
        sec_form.add_row("", self.lbl_secrets_path_hint)

        card_sec.layout.addLayout(sec_form)
        page.addWidget(card_sec)

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
        self.binary_debounce = QTimer()
        self.binary_debounce.setSingleShot(True)
        self.binary_debounce.setInterval(400)
        self.binary_debounce.timeout.connect(self._on_manual_binary_changed)
        self.manual_binary_edit.textChanged.connect(lambda: self.binary_debounce.start())
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
        self.on_errors_combo.addItems(["stop", "continue", ON_ERRORS_CUSTOM_LABEL])
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

        self.allow_untested_check = QCheckBox("Allow untested immich-go versions")
        self.allow_untested_check.setChecked(False)
        self.inputs["config"]["allow_untested_updates"] = self.allow_untested_check
        adv_form.addRow("", self.allow_untested_check)

        self.preferred_terminal_combo = QComboBox()
        self.preferred_terminal_combo.addItems(["auto", "gnome-terminal", "konsole", "xfce4-terminal", "xterm"])
        self.inputs["config"]["preferred_terminal"] = self.preferred_terminal_combo
        adv_form.add_row("Preferred Terminal", self.preferred_terminal_combo)

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
        self.on_errors_spin.setVisible(text == ON_ERRORS_CUSTOM_LABEL)

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

        subhead = QLabel("Filtering & Source Behavior")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_type = QComboBox()
        c_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs["upload-folder"]["include-type"] = c_type
        form.add_row("Media Type", c_type)

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

        chk_rec = QCheckBox("Scan subdirectories recursively")
        chk_rec.setChecked(True)
        self.inputs["upload-folder"]["recursive"] = chk_rec
        form.addRow("", chk_rec)

        chk_ignore = QCheckBox("Ignore sidecar files")
        self.inputs["upload-folder"]["ignore-sidecar"] = chk_ignore
        form.addRow("", chk_ignore)

        chk_date_name = QCheckBox("Guess dates from filenames")
        chk_date_name.setChecked(True)
        self.inputs["upload-folder"]["date-from-name"] = chk_date_name
        form.addRow("", chk_date_name)

        t_joiner = QLineEdit()
        t_joiner.setPlaceholderText(" / ")
        self.inputs["upload-folder"]["album-path-joiner"] = t_joiner
        form.add_row("Album path joiner", t_joiner)

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

        t_tz = QLineEdit()
        t_tz.setPlaceholderText("UTC or America/New_York")
        self.inputs["upload-folder"]["time-zone"] = t_tz
        form.add_row("Time Zone Override", t_tz)

        chk_epson = QCheckBox("Scan Epson FastFoto dual-side photos")
        self.inputs["upload-folder"]["manage-epson"] = chk_epson
        form.addRow("", chk_epson)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

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

        chk_partner = QCheckBox("Include Partner Photos")
        chk_partner.setChecked(True)
        self.inputs["upload-gp"]["include-partner"] = chk_partner
        form.addRow("", chk_partner)

        chk_sync = QCheckBox("Sync Google Albums")
        chk_sync.setChecked(True)
        self.inputs["upload-gp"]["sync-albums"] = chk_sync
        form.addRow("", chk_sync)

        chk_archived = QCheckBox("Include Archived Photos")
        chk_archived.setChecked(True)
        self.inputs["upload-gp"]["include-archived"] = chk_archived
        form.addRow("", chk_archived)

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

        subhead = QLabel("Media & Album Controls")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

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

        chk_trashed = QCheckBox("Include Trashed Photos")
        self.inputs["upload-gp"]["include-trashed"] = chk_trashed
        form.addRow("", chk_trashed)

        chk_untitled = QCheckBox("Include Untitled Albums")
        self.inputs["upload-gp"]["include-untitled-albums"] = chk_untitled
        form.addRow("", chk_untitled)

        t_album_name = QLineEdit()
        t_album_name.setPlaceholderText("Album Name")
        self.inputs["upload-gp"]["from-album-name"] = t_album_name
        form.add_row("From Specific Album", t_album_name)

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

        subhead = QLabel("Additional Pair Handling")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_raw = QComboBox()
        c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs["upload-gp"]["manage-raw-jpeg"] = c_raw
        form.add_row("RAW + JPEG Pairs", c_raw)

        chk_epson = QCheckBox("Scan Epson FastFoto dual-side photos")
        self.inputs["upload-gp"]["manage-epson"] = chk_epson
        form.addRow("", chk_epson)

        subhead = QLabel("Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        d_range = QLineEdit()
        d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs["upload-gp"]["date-range"] = d_range
        form.add_row("Date range", d_range)

        inc_ext = QLineEdit()
        inc_ext.setPlaceholderText(".jpg,.heic,.mp4")
        self.inputs["upload-gp"]["include-ext"] = inc_ext
        form.add_row("Include extensions", inc_ext)

        exc_ext = QLineEdit()
        exc_ext.setPlaceholderText(".thm,.xmp")
        self.inputs["upload-gp"]["exclude-ext"] = exc_ext
        form.add_row("Exclude extensions", exc_ext)

        ban_file = QPlainTextEdit()
        ban_file.setPlaceholderText("@eaDir/\n.DS_Store")
        self.inputs["upload-gp"]["ban-file"] = ban_file
        form.add_row("Skip files matching patterns", ban_file)

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

        chk_overwrite = QCheckBox("Overwrite Existing")
        self.inputs["upload-gp"]["overwrite"] = chk_overwrite
        form.addRow("", chk_overwrite)

        c_err = QComboBox()
        c_err.addItems(["stop", "continue"])
        self.inputs["upload-gp"]["on-errors"] = c_err
        form.add_row("If a file fails", c_err)

        chk_pause = QCheckBox("Pause background jobs")
        chk_pause.setChecked(True)
        self.inputs["upload-gp"]["pause-jobs"] = chk_pause
        form.addRow("", chk_pause)

        t_tz = QLineEdit()
        t_tz.setPlaceholderText("UTC or America/New_York")
        self.inputs["upload-gp"]["time-zone"] = t_tz
        form.add_row("Time Zone Override", t_tz)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["upload-gp"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

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

        banner = QLabel("ℹ️ Destination Immich Server is configured in the Configuration tab. Source Immich Server is configured below.")
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "background-color: rgba(97, 175, 239, 0.12); padding: 10px 14px; "
            "border-radius: 6px; border: 1px solid #61AFEF; font-size: 13px;"
        )
        lay.addWidget(banner)

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

        d_range = QLineEdit()
        d_range.setPlaceholderText("2023-01-01,2023-12-31")
        self.inputs["upload-immich"]["from-date-range"] = d_range
        form.add_row("Date Range Filter", d_range)

        t_albums = QLineEdit()
        t_albums.setPlaceholderText("Family, Travel")
        self.inputs["upload-immich"]["from-albums"] = t_albums
        form.add_row("Filter by Albums", t_albums)

        chk_fav = QCheckBox("Only Favorites")
        self.inputs["upload-immich"]["from-favorite"] = chk_fav
        form.addRow("", chk_fav)

        card.layout.addLayout(form)
        lay.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Source Filtering & Credentials")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_from_admin = QLineEdit()
        t_from_admin.setEchoMode(QLineEdit.EchoMode.Password)
        t_from_admin.setPlaceholderText("Optional Source Admin API Key")
        self.inputs["upload-immich"]["from-admin-api-key"] = t_from_admin
        form.add_row(
            "Source Admin API Key",
            t_from_admin,
            "Only needed if source server requires admin-level operations."
        )

        chk_arch = QCheckBox("Include Source Archived")
        self.inputs["upload-immich"]["from-archived"] = chk_arch
        form.addRow("", chk_arch)

        chk_trash = QCheckBox("Include Source Trashed")
        self.inputs["upload-immich"]["from-trash"] = chk_trash
        form.addRow("", chk_trash)

        chk_partners = QCheckBox("Include Source Partner Photos")
        self.inputs["upload-immich"]["from-partners"] = chk_partners
        form.addRow("", chk_partners)

        chk_no_album = QCheckBox("Include Source Assets Not in Albums")
        self.inputs["upload-immich"]["from-no-album"] = chk_no_album
        form.addRow("", chk_no_album)

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

        c_from_type = QComboBox()
        c_from_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs["upload-immich"]["from-include-type"] = c_from_type
        form.add_row("Source Media Type", c_from_type)

        t_from_inc_ext = QLineEdit()
        t_from_inc_ext.setPlaceholderText(".jpg,.heic")
        self.inputs["upload-immich"]["from-include-ext"] = t_from_inc_ext
        form.add_row("Source Include Extensions", t_from_inc_ext)

        t_from_exc_ext = QLineEdit()
        t_from_exc_ext.setPlaceholderText(".mp4")
        self.inputs["upload-immich"]["from-exclude-ext"] = t_from_exc_ext
        form.add_row("Source Exclude Extensions", t_from_exc_ext)

        t_from_tz = QLineEdit()
        t_from_tz.setPlaceholderText("UTC")
        self.inputs["upload-immich"]["from-time-zone"] = t_from_tz
        form.add_row("Source Time Zone", t_from_tz)

        t_from_dev = QLineEdit()
        self.inputs["upload-immich"]["from-device-uuid"] = t_from_dev
        form.add_row("Source Device UUID", t_from_dev)

        from_timeout_spin = QSpinBox()
        from_timeout_spin.setRange(1, 1440)
        from_timeout_spin.setValue(20)
        from_timeout_spin.setSuffix(" minutes")
        self.inputs["upload-immich"]["from-client-timeout"] = from_timeout_spin
        form.add_row("Source Client Timeout", from_timeout_spin)

        chk_ssl_src = QCheckBox("Skip Source SSL Verification")
        self.inputs["upload-immich"]["from-skip-ssl"] = chk_ssl_src
        form.addRow("", chk_ssl_src)

        chk_from_trace = QCheckBox("Enable Source API Trace")
        self.inputs["upload-immich"]["from-api-trace"] = chk_from_trace
        form.addRow("", chk_from_trace)

        chk_from_pause = QCheckBox("Pause Source Immich Jobs")
        chk_from_pause.setChecked(True)
        self.inputs["upload-immich"]["from-pause-jobs"] = chk_from_pause
        form.addRow("", chk_from_pause)

        subhead = QLabel("Destination Settings & Pair Handling")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_dst_tags = QLineEdit()
        t_dst_tags.setPlaceholderText("migration")
        self.inputs["upload-immich"]["tag"] = t_dst_tags
        form.add_row("Destination Custom Tags", t_dst_tags)

        chk_dst_sess = QCheckBox("Destination Session Tag")
        self.inputs["upload-immich"]["session-tag"] = chk_dst_sess
        form.addRow("", chk_dst_sess)

        chk_dst_ovw = QCheckBox("Overwrite Existing on Destination")
        self.inputs["upload-immich"]["overwrite"] = chk_dst_ovw
        form.addRow("", chk_dst_ovw)

        t_dst_tz = QLineEdit()
        t_dst_tz.setPlaceholderText("UTC")
        self.inputs["upload-immich"]["time-zone"] = t_dst_tz
        form.add_row("Destination Time Zone", t_dst_tz)

        c_burst = QComboBox()
        c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs["upload-immich"]["manage-burst"] = c_burst
        form.add_row("Destination Burst Photos", c_burst)

        c_raw = QComboBox()
        c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs["upload-immich"]["manage-raw-jpeg"] = c_raw
        form.add_row("Destination RAW+JPEG Pairs", c_raw)

        c_heic = QComboBox()
        c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs["upload-immich"]["manage-heic-jpeg"] = c_heic
        form.add_row("Destination HEIC+JPEG Pairs", c_heic)

        chk_epson = QCheckBox("Scan Epson FastFoto dual-side photos")
        self.inputs["upload-immich"]["manage-epson"] = chk_epson
        form.addRow("", chk_epson)

        subhead = QLabel("Run Behavior & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_err = QComboBox()
        c_err.addItems(["stop", "continue"])
        self.inputs["upload-immich"]["on-errors"] = c_err
        form.add_row("If a file fails", c_err)

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["upload-immich"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

        chk_trace = QCheckBox("Enable Destination API Trace")
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
        self._add_browse_action(t_write, "Select Archive Destination")
        form.add_row("Destination Folder", t_write)

        card.layout.addLayout(form)
        lay.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Filtering & Source Behavior")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        d_range = QLineEdit()
        d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs["archive-folder"]["date-range"] = d_range
        form.add_row("Date Range", d_range)

        c_type = QComboBox()
        c_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs["archive-folder"]["include-type"] = c_type
        form.add_row("Media Type", c_type)

        inc_ext = QLineEdit()
        inc_ext.setPlaceholderText(".jpg,.heic,.mp4")
        self.inputs["archive-folder"]["include-ext"] = inc_ext
        form.add_row("Include extensions", inc_ext)

        exc_ext = QLineEdit()
        exc_ext.setPlaceholderText(".thm,.xmp")
        self.inputs["archive-folder"]["exclude-ext"] = exc_ext
        form.add_row("Exclude extensions", exc_ext)

        ban_file = QPlainTextEdit()
        ban_file.setPlaceholderText("@eaDir/\n.DS_Store")
        self.inputs["archive-folder"]["ban-file"] = ban_file
        form.add_row("Skip files matching patterns", ban_file)

        chk_rec = QCheckBox("Scan subdirectories recursively")
        chk_rec.setChecked(True)
        self.inputs["archive-folder"]["recursive"] = chk_rec
        form.addRow("", chk_rec)

        chk_ignore = QCheckBox("Ignore sidecar files")
        self.inputs["archive-folder"]["ignore-sidecar"] = chk_ignore
        form.addRow("", chk_ignore)

        chk_date_name = QCheckBox("Guess dates from filenames")
        chk_date_name.setChecked(True)
        self.inputs["archive-folder"]["date-from-name"] = chk_date_name
        form.addRow("", chk_date_name)

        subhead = QLabel("Folder & Album Organization")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_album = QComboBox()
        c_album.addItems(["NONE", "FOLDER", "PATH"])
        self.inputs["archive-folder"]["folder-album"] = c_album
        form.add_row("Folder as Album", c_album)

        chk_ftags = QCheckBox("Folder as Tags")
        self.inputs["archive-folder"]["folder-tags"] = chk_ftags
        form.addRow("", chk_ftags)

        t_album = QLineEdit()
        t_album.setPlaceholderText("e.g. Backup Album")
        self.inputs["archive-folder"]["into-album"] = t_album
        form.add_row("Put all into Album", t_album)

        t_joiner = QLineEdit()
        t_joiner.setPlaceholderText(" / ")
        self.inputs["archive-folder"]["album-path-joiner"] = t_joiner
        form.add_row("Album Path Joiner", t_joiner)

        subhead = QLabel("Run Behavior & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_err = QComboBox()
        c_err.addItems(["stop", "continue"])
        self.inputs["archive-folder"]["on-errors"] = c_err
        form.add_row("If a file fails", c_err)

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

        card = Card("Source Server")
        form = FormSection()

        t_server = QLineEdit()
        t_server.setEnabled(False)
        t_server.setText("Not Configured")
        self.inputs["archive-immich"]["target-server"] = t_server
        form.add_row("Source Immich Server URL", t_server, "Archive source server is configured in the Configuration tab.")

        card.layout.addLayout(form)
        lay.addWidget(card)

        card = Card("Options")
        form = FormSection()

        t_write = DroppableLineEdit()
        t_write.setPlaceholderText("/backup/photos")
        self.inputs["archive-immich"]["write-to"] = t_write
        self._add_browse_action(t_write, "Select Archive Destination")
        form.add_row("Destination Folder", t_write)

        d_range = QLineEdit()
        d_range.setPlaceholderText("2023-01-01,2023-12-31")
        self.inputs["archive-immich"]["from-date-range"] = d_range
        form.add_row("Date Range Filter", d_range)

        t_albums = QLineEdit()
        t_albums.setPlaceholderText("Family, Travel")
        self.inputs["archive-immich"]["from-albums"] = t_albums
        form.add_row("Specific Albums", t_albums)

        card.layout.addLayout(form)
        lay.addWidget(card)

        adv_card = Card("Advanced Options")
        form = FormSection()

        subhead = QLabel("Source Asset Filters")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        chk_fav = QCheckBox("Only Favorites")
        self.inputs["archive-immich"]["from-favorite"] = chk_fav
        form.addRow("", chk_fav)

        chk_arch = QCheckBox("Include Source Archived")
        self.inputs["archive-immich"]["from-archived"] = chk_arch
        form.addRow("", chk_arch)

        chk_trash = QCheckBox("Include Source Trashed")
        self.inputs["archive-immich"]["from-trash"] = chk_trash
        form.addRow("", chk_trash)

        chk_no_album = QCheckBox("Include Assets Not in Albums")
        self.inputs["archive-immich"]["from-no-album"] = chk_no_album
        form.addRow("", chk_no_album)

        chk_partners = QCheckBox("Include Partner Photos")
        self.inputs["archive-immich"]["from-partners"] = chk_partners
        form.addRow("", chk_partners)

        s_rating = QSpinBox()
        s_rating.setRange(0, 5)
        self.inputs["archive-immich"]["from-minimal-rating"] = s_rating
        form.add_row("Minimum Rating", s_rating)

        subhead = QLabel("People & Tags")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_people = QLineEdit()
        t_people.setPlaceholderText("John, Jane")
        self.inputs["archive-immich"]["from-people"] = t_people
        form.add_row("Filter by People", t_people)

        t_tags = QLineEdit()
        t_tags.setPlaceholderText("vacation, work")
        self.inputs["archive-immich"]["from-tags"] = t_tags
        form.add_row("Filter by Tags", t_tags)

        subhead = QLabel("Location & Camera Metadata")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_city = QLineEdit()
        t_city.setPlaceholderText("New York")
        self.inputs["archive-immich"]["from-city"] = t_city
        form.add_row("City", t_city)

        t_state = QLineEdit()
        t_state.setPlaceholderText("NY")
        self.inputs["archive-immich"]["from-state"] = t_state
        form.add_row("State", t_state)

        t_country = QLineEdit()
        t_country.setPlaceholderText("USA")
        self.inputs["archive-immich"]["from-country"] = t_country
        form.add_row("Country", t_country)

        t_make = QLineEdit()
        t_make.setPlaceholderText("Canon")
        self.inputs["archive-immich"]["from-make"] = t_make
        form.add_row("Camera Make", t_make)

        t_model = QLineEdit()
        t_model.setPlaceholderText("EOS R5")
        self.inputs["archive-immich"]["from-model"] = t_model
        form.add_row("Camera Model", t_model)

        subhead = QLabel("Media & Extensions")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_from_type = QComboBox()
        c_from_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs["archive-immich"]["from-include-type"] = c_from_type
        form.add_row("Source Media Type", c_from_type)

        t_from_inc_ext = QLineEdit()
        t_from_inc_ext.setPlaceholderText(".jpg,.heic")
        self.inputs["archive-immich"]["from-include-ext"] = t_from_inc_ext
        form.add_row("Include Extensions", t_from_inc_ext)

        t_from_exc_ext = QLineEdit()
        t_from_exc_ext.setPlaceholderText(".mp4")
        self.inputs["archive-immich"]["from-exclude-ext"] = t_from_exc_ext
        form.add_row("Exclude Extensions", t_from_exc_ext)

        subhead = QLabel("Source Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        t_from_tz = QLineEdit()
        t_from_tz.setPlaceholderText("UTC")
        self.inputs["archive-immich"]["from-time-zone"] = t_from_tz
        form.add_row("Source Time Zone", t_from_tz)

        t_from_dev = QLineEdit()
        self.inputs["archive-immich"]["from-device-uuid"] = t_from_dev
        form.add_row("Source Device UUID", t_from_dev)

        from_timeout_spin = QSpinBox()
        from_timeout_spin.setRange(1, 1440)
        from_timeout_spin.setValue(20)
        from_timeout_spin.setSuffix(" minutes")
        self.inputs["archive-immich"]["from-client-timeout"] = from_timeout_spin
        form.add_row("Source Client Timeout", from_timeout_spin)

        chk_ssl_src = QCheckBox("Skip Source SSL Verification")
        self.inputs["archive-immich"]["from-skip-ssl"] = chk_ssl_src
        form.addRow("", chk_ssl_src)

        chk_from_trace = QCheckBox("Enable Source API Trace")
        self.inputs["archive-immich"]["from-api-trace"] = chk_from_trace
        form.addRow("", chk_from_trace)

        chk_from_pause = QCheckBox("Pause Source Immich Jobs")
        chk_from_pause.setChecked(True)
        self.inputs["archive-immich"]["from-pause-jobs"] = chk_from_pause
        form.addRow("", chk_from_pause)

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

        d_range = QLineEdit()
        d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs["stack"]["date-range"] = d_range
        form.add_row("Date Range", d_range)

        t_tz = QLineEdit()
        t_tz.setPlaceholderText("America/New_York")
        self.inputs["stack"]["time-zone"] = t_tz
        form.add_row("Time Zone Override", t_tz)

        chk_epson = QCheckBox("Manage Epson FastFoto")
        self.inputs["stack"]["manage-epson"] = chk_epson
        form.addRow("", chk_epson)

        chk_pause = QCheckBox("Pause background jobs")
        chk_pause.setChecked(True)
        self.inputs["stack"]["pause-jobs"] = chk_pause
        form.addRow("", chk_pause)

        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)

        c_log = QComboBox()
        c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs["stack"]["log-level"] = c_log
        form.add_row("Log Level", c_log)

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
        if hasattr(self, "app_config"):
            self.app_config.advanced_mode = checked
        if hasattr(self, "btn_mode"):
            self.btn_mode.blockSignals(True)
            self.btn_mode.setChecked(checked)
            self.btn_mode.blockSignals(False)
        if hasattr(self, "lbl_mode"):
            self.lbl_mode.setText("Advanced" if checked else "Simple")
        for w in getattr(self, "adv_frames", []):
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

    def update_window_title(self):
        active = active_profile_name()
        self.setWindowTitle(f"Immich Go GUI — {active}")

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        save_action = QAction("Save Configuration", self)
        save_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_action)
        load_action = QAction("Load Configuration", self)
        load_action.triggered.connect(self.load_configuration)
        file_menu.addAction(load_action)

        reset_action = QAction("Reset Run State", self)
        reset_action.triggered.connect(self.on_reset_run_state_clicked)
        file_menu.addAction(reset_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.profiles_menu = menu_bar.addMenu("Profiles")
        self.update_profiles_menu()

        help_menu = menu_bar.addMenu("Help")
        compat_action = QAction("Check CLI Compatibility", self)
        compat_action.triggered.connect(self.show_cli_compatibility_dialog)
        help_menu.addAction(compat_action)

        about_action = QAction("About Immich-Go", self)
        about_action.triggered.connect(self.open_github_link)
        help_menu.addAction(about_action)

    def show_cli_compatibility_dialog(self):
        from core.cli_contract import check_fixtures, check_binary_help
        from core.binary_manager import get_binary_path, load_binary_metadata, TESTED_IMMICH_GO_VERSION

        meta = load_binary_metadata()
        bin_path = Path(get_binary_path(meta))

        report = check_fixtures(TESTED_IMMICH_GO_VERSION)
        if bin_path.exists():
            live_report = check_binary_help(bin_path, TESTED_IMMICH_GO_VERSION)
        else:
            live_report = None

        # Merge fixture + live-binary results
        missing: dict[str, set[str]] = {
            tab: set(flags)
            for tab, flags in report.missing_flags_by_tab.items()
        }
        unknown: dict[str, set[str]] = {
            tab: set(flags)
            for tab, flags in report.unknown_flags_by_tab.items()
        }

        supported = bool(report.supported)
        notes: list[str] = [report.notes] if report.notes else []

        if live_report:
            supported = supported and bool(live_report.supported)
            if live_report.notes:
                notes.append(live_report.notes)
            for tab, flags in live_report.missing_flags_by_tab.items():
                missing.setdefault(tab, set()).update(flags)
            for tab, flags in live_report.unknown_flags_by_tab.items():
                unknown.setdefault(tab, set()).update(flags)

        fully_compatible = supported and not any(missing.values())

        msg = [f"Tested Immich-Go Version: v{report.version}\n"]

        if live_report and fully_compatible:
            msg.append("Status: Fully Compatible with fixtures and live binary")
        elif fully_compatible:
            msg.append("Status: Fully Compatible with target schema")
        else:
            msg.append("Status: Compatibility Warning")

        if notes:
            msg.append("\nVersion Notes:")
            for note in notes:
                msg.append(note)

        if missing:
            msg.append("\nMissing CLI Flags:")
            for tab, flags in missing.items():
                if flags:
                    msg.append(f"  [{tab}]")
                    for flag in sorted(flags):
                        msg.append(f"    - {flag}")

        if unknown:
            msg.append("\nNew Upstream CLI Flags Detected:")
            for tab, flags in unknown.items():
                if flags:
                    msg.append(f"  [{tab}]")
                    for flag in sorted(flags):
                        msg.append(f"    - {flag}")

        QMessageBox.information(
            self,
            "Immich-Go CLI Compatibility",
            "\n".join(msg),
        )

    def on_reset_run_state_clicked(self):
        reply = QMessageBox.question(
            self,
            "Reset Run State",
            "Are you sure you want to reset all active run locks and clear running status?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from core.process_tracker import reset_all_locks
            reset_all_locks()
            self.active_lock_path = None
            self.running_process = False
            if hasattr(self, "check_process_timer"):
                self.check_process_timer.stop()
            self.lbl_running_warning.setVisible(False)
            self.update_status()

    def update_profiles_menu(self):
        if not hasattr(self, "profiles_menu"):
            return
        self.profiles_menu.clear()

        new_act = QAction("New Profile…", self)
        new_act.triggered.connect(self.on_new_profile_clicked)
        self.profiles_menu.addAction(new_act)

        dup_act = QAction("Duplicate Active Profile…", self)
        dup_act.triggered.connect(self.on_duplicate_profile_clicked)
        self.profiles_menu.addAction(dup_act)

        ren_act = QAction("Rename Active Profile…", self)
        ren_act.triggered.connect(self.on_rename_profile_clicked)
        self.profiles_menu.addAction(ren_act)

        del_act = QAction("Delete Active Profile…", self)
        del_act.triggered.connect(self.on_delete_profile_clicked)
        self.profiles_menu.addAction(del_act)

        self.profiles_menu.addSeparator()

        active = active_profile_name()
        for pinfo in list_profiles():
            act = QAction(pinfo.name, self)
            act.setCheckable(True)
            if pinfo.name == active:
                act.setChecked(True)
            act.triggered.connect(lambda checked, name=pinfo.name: self.switch_profile(name))
            self.profiles_menu.addAction(act)

    def switch_profile(self, target_name: str):
        active = active_profile_name()
        if target_name == active:
            return

        reply = QMessageBox.question(
            self,
            "Switch Profile",
            f"Save changes to current profile '{active}' before switching?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if reply == QMessageBox.StandardButton.Cancel:
            self.update_profiles_menu()
            return
        elif reply == QMessageBox.StandardButton.Save:
            self.save_configuration()

        try:
            set_active_profile_name(target_name)
            self.load_configuration()
            self.update_profiles_menu()
            self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "Error Switching Profile", str(e))

    def on_new_profile_clicked(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name:")
        if ok and name.strip():
            clean_n = name.strip()
            existing = [p.name for p in list_profiles()]
            valid, err = validate_profile_name(clean_n, existing)
            if not valid:
                QMessageBox.warning(self, "Invalid Name", err or "Invalid profile name.")
                return
            try:
                create_profile(clean_n)
                self.switch_profile(clean_n)
            except Exception as e:
                QMessageBox.critical(self, "Error Creating Profile", str(e))

    def on_duplicate_profile_clicked(self):
        from PySide6.QtWidgets import QInputDialog
        active = active_profile_name()
        name, ok = QInputDialog.getText(
            self, "Duplicate Profile", f"Enter name for duplicate of '{active}':"
        )
        if ok and name.strip():
            clean_n = name.strip()
            existing = [p.name for p in list_profiles()]
            valid, err = validate_profile_name(clean_n, existing)
            if not valid:
                QMessageBox.warning(self, "Invalid Name", err or "Invalid profile name.")
                return
            try:
                duplicate_profile(active, clean_n)
                self.switch_profile(clean_n)
            except Exception as e:
                QMessageBox.critical(self, "Error Duplicating Profile", str(e))

    def on_rename_profile_clicked(self):
        from PySide6.QtWidgets import QInputDialog
        active = active_profile_name()
        if active == "default":
            QMessageBox.warning(self, "Cannot Rename", "The 'default' profile cannot be renamed.")
            return

        name, ok = QInputDialog.getText(
            self, "Rename Profile", f"Enter new name for profile '{active}':", text=active
        )
        if ok and name.strip() and name.strip() != active:
            clean_n = name.strip()
            existing = [p.name for p in list_profiles() if p.name != active]
            valid, err = validate_profile_name(clean_n, existing)
            if not valid:
                QMessageBox.warning(self, "Invalid Name", err or "Invalid profile name.")
                return
            try:
                rename_profile(active, clean_n)
                self.update_profiles_menu()
                self.update_window_title()
            except Exception as e:
                QMessageBox.critical(self, "Error Renaming Profile", str(e))

    def on_delete_profile_clicked(self):
        active = active_profile_name()
        if active == "default":
            QMessageBox.warning(self, "Cannot Delete", "The 'default' profile cannot be deleted.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to permanently delete profile '{active}' and all its saved settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_profile(active)
                self.load_configuration()
                self.update_profiles_menu()
                self.update_window_title()
            except Exception as e:
                QMessageBox.critical(self, "Error Deleting Profile", str(e))

    def collect_form_state(self) -> dict:
        secret_keys = {"api_key", "from-api-key", "admin_api_key", "from-admin-api-key", "target-server"}
        state = {}
        for tab_key, widgets in self.inputs.items():
            tab_dict = {}
            for k, widget in widgets.items():
                if k in secret_keys:
                    continue
                if isinstance(widget, QLineEdit):
                    tab_dict[k] = widget.text()
                elif isinstance(widget, QPlainTextEdit):
                    tab_dict[k] = widget.toPlainText()
                elif isinstance(widget, QCheckBox):
                    tab_dict[k] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    tab_dict[k] = widget.currentText()
                elif isinstance(widget, QSpinBox):
                    tab_dict[k] = widget.value()
            if tab_dict:
                state[tab_key] = tab_dict
        return state

    def apply_form_state(self, state: dict) -> None:
        if not isinstance(state, dict):
            return
        secret_keys = {"api_key", "from-api-key", "admin_api_key", "from-admin-api-key", "target-server"}
        for tab_key, tab_dict in state.items():
            if tab_key in self.inputs and isinstance(tab_dict, dict):
                for k, val in tab_dict.items():
                    if k in secret_keys:
                        continue
                    widget = self.inputs[tab_key].get(k)
                    if widget is None:
                        continue
                    try:
                        widget.blockSignals(True)
                        if isinstance(widget, QLineEdit) and isinstance(val, str):
                            widget.setText(val)
                        elif isinstance(widget, QPlainTextEdit) and isinstance(val, str):
                            widget.setPlainText(val)
                        elif isinstance(widget, QCheckBox) and isinstance(val, bool):
                            widget.setChecked(val)
                        elif isinstance(widget, QComboBox) and isinstance(val, str):
                            widget.setCurrentText(val)
                        elif isinstance(widget, QSpinBox) and isinstance(val, (int, float)):
                            widget.setValue(int(val))
                    finally:
                        widget.blockSignals(False)

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

    ADVANCED_KEYS = {
        "upload-folder": {
            "include-type",
            "date-range",
            "include-ext",
            "exclude-ext",
            "ban-file",
            "recursive",
            "ignore-sidecar",
            "date-from-name",
            "album-path-joiner",
            "tag",
            "session-tag",
            "folder-tags",
            "on-errors",
            "overwrite",
            "pause-jobs",
            "time-zone",
            "manage-epson",
            "log-level",
            "api-trace",
        },
        "upload-gp": {
            "include-type",
            "into-album",
            "include-unmatched",
            "include-trashed",
            "include-untitled-albums",
            "from-album-name",
            "partner-album",
            "takeout-tag",
            "people-tag",
            "manage-raw-jpeg",
            "manage-epson",
            "date-range",
            "include-ext",
            "exclude-ext",
            "ban-file",
            "tag",
            "session-tag",
            "overwrite",
            "on-errors",
            "pause-jobs",
            "time-zone",
            "log-level",
            "api-trace",
        },
        "upload-immich": {
            "from-admin-api-key",
            "from-archived",
            "from-trash",
            "from-partners",
            "from-no-album",
            "from-minimal-rating",
            "from-people",
            "from-tags",
            "from-city",
            "from-state",
            "from-country",
            "from-make",
            "from-model",
            "from-include-type",
            "from-include-ext",
            "from-exclude-ext",
            "from-time-zone",
            "from-device-uuid",
            "from-client-timeout",
            "from-skip-ssl",
            "from-api-trace",
            "from-pause-jobs",
            "tag",
            "session-tag",
            "overwrite",
            "time-zone",
            "manage-burst",
            "manage-raw-jpeg",
            "manage-heic-jpeg",
            "manage-epson",
            "on-errors",
            "log-level",
            "api-trace",
        },
        "archive-folder": {
            "date-range",
            "include-type",
            "include-ext",
            "exclude-ext",
            "ban-file",
            "recursive",
            "ignore-sidecar",
            "date-from-name",
            "folder-album",
            "folder-tags",
            "into-album",
            "album-path-joiner",
            "on-errors",
            "log-level",
        },
        "archive-immich": {
            "from-favorite",
            "from-archived",
            "from-trash",
            "from-no-album",
            "from-partners",
            "from-minimal-rating",
            "from-people",
            "from-tags",
            "from-city",
            "from-state",
            "from-country",
            "from-make",
            "from-model",
            "from-include-type",
            "from-include-ext",
            "from-exclude-ext",
            "from-time-zone",
            "from-device-uuid",
            "from-client-timeout",
            "from-skip-ssl",
            "from-api-trace",
            "from-pause-jobs",
            "log-level",
        },
        "stack": {
            "date-range",
            "time-zone",
            "manage-epson",
            "pause-jobs",
            "log-level",
            "api-trace",
        },
    }


    def _collect_config_state(self) -> dict:
        cpu_default = min(max(os.cpu_count() or 2, 1), 20)
        c = self.inputs.get("config", {})
        state = {
            "server": c.get("server").text() if c.get("server") else "",
            "api_key": c.get("api_key").text().strip() if c.get("api_key") else "",
            "admin_api_key": c.get("admin_api_key").text().strip() if c.get("admin_api_key") else "",
            "secrets_provider": c.get("secret_provider").currentData() if c.get("secret_provider") else "keyring",
            "skip-ssl": c.get("skip-ssl").isChecked() if c.get("skip-ssl") else False,
            "client_timeout": c.get("client_timeout").value() if c.get("client_timeout") else 20,
            "concurrent": c.get("concurrent").value() if c.get("concurrent") else cpu_default,
            "concurrent_default": cpu_default,
            "device_uuid": c.get("device_uuid").text().strip() if c.get("device_uuid") else "",
            "on_errors": c.get("on_errors").currentText() if c.get("on_errors") else "stop",
            "on_errors_tolerance": c.get("on_errors_tolerance").value() if c.get("on_errors_tolerance") else 10,
            "pause_jobs": c.get("pause_jobs").isChecked() if c.get("pause_jobs") else True,
        }

        if not getattr(self, "is_advanced", False):
            state["client_timeout"] = 20
            state["concurrent"] = cpu_default
            state["device_uuid"] = ""
            state["on_errors"] = "stop"
            state["on_errors_tolerance"] = 10
            state["pause_jobs"] = True

        return state

    def _collect_tab_state(self, tab_key: str) -> dict:
        state = self._raw_tab_state(tab_key)
        if not getattr(self, "is_advanced", False):
            for key in self.ADVANCED_KEYS.get(tab_key, set()):
                state.pop(key, None)
        return state

    def _raw_tab_state(self, tab_key: str) -> dict:
        if tab_key not in self.inputs:
            return {}
        c = self.inputs[tab_key]

        def get_text(k: str, default: str = "") -> str:
            w = c.get(k)
            if not w:
                return default
            if hasattr(w, "text"):
                return w.text()
            if hasattr(w, "toPlainText"):
                return w.toPlainText()
            return default

        def get_bool(k: str, default: bool = False) -> bool:
            w = c.get(k)
            if not w:
                return default
            if hasattr(w, "isChecked"):
                return w.isChecked()
            return default

        def get_combo(k: str, default: str = "") -> str:
            w = c.get(k)
            if not w:
                return default
            if hasattr(w, "currentText"):
                return w.currentText()
            return default

        def get_int(k: str, default: int = 0) -> int:
            w = c.get(k)
            if not w:
                return default
            if hasattr(w, "value"):
                return w.value()
            return default

        if tab_key == "upload-folder":
            return {
                "path": get_text("path"),
                "include-type": get_combo("include-type", "all"),
                "folder-album": get_combo("folder-album", "NONE"),
                "into-album": get_text("into-album"),
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
                "date-range": get_text("date-range"),
                "include-ext": get_text("include-ext"),
                "exclude-ext": get_text("exclude-ext"),
                "ban-file": get_text("ban-file"),
                "recursive": get_bool("recursive", True),
                "ignore-sidecar": get_bool("ignore-sidecar", False),
                "date-from-name": get_bool("date-from-name", True),
                "album-path-joiner": get_text("album-path-joiner"),
                "tag": get_text("tag"),
                "session-tag": get_bool("session-tag", False),
                "folder-tags": get_bool("folder-tags", False),
                "on-errors": get_combo("on-errors", "stop"),
                "overwrite": get_bool("overwrite", False),
                "pause-jobs": get_bool("pause-jobs", True),
                "time-zone": get_text("time-zone"),
                "manage-epson": get_bool("manage-epson", False),
                "log-level": get_combo("log-level", "INFO"),
                "api-trace": get_bool("api-trace", False),
            }

        elif tab_key == "upload-gp":
            return {
                "path": get_text("path"),
                "include-type": get_combo("include-type", "all"),
                "into-album": get_text("into-album"),
                "include-unmatched": get_bool("include-unmatched", False),
                "include-partner": get_bool("include-partner", True),
                "sync-albums": get_bool("sync-albums", True),
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
                "manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
                "manage-epson": get_bool("manage-epson", False),
                "from-album-name": get_text("from-album-name"),
                "include-archived": get_bool("include-archived", True),
                "include-trashed": get_bool("include-trashed", False),
                "include-untitled-albums": get_bool("include-untitled-albums", False),
                "partner-album": get_text("partner-album"),
                "takeout-tag": get_bool("takeout-tag", True),
                "people-tag": get_bool("people-tag", True),
                "date-range": get_text("date-range"),
                "include-ext": get_text("include-ext"),
                "exclude-ext": get_text("exclude-ext"),
                "ban-file": get_text("ban-file"),
                "tag": get_text("tag"),
                "session-tag": get_bool("session-tag", False),
                "overwrite": get_bool("overwrite", False),
                "on-errors": get_combo("on-errors", "stop"),
                "pause-jobs": get_bool("pause-jobs", True),
                "time-zone": get_text("time-zone"),
                "log-level": get_combo("log-level", "INFO"),
                "api-trace": get_bool("api-trace", False),
            }

        elif tab_key == "upload-immich":
            return {
                "from-server": get_text("from-server"),
                "from-api-key": get_text("from-api-key"),
                "from-admin-api-key": get_text("from-admin-api-key"),
                "from-client-timeout": get_int("from-client-timeout", 20),
                "from-favorite": get_bool("from-favorite", False),
                "from-archived": get_bool("from-archived", False),
                "from-trash": get_bool("from-trash", False),
                "from-partners": get_bool("from-partners", False),
                "from-no-album": get_bool("from-no-album", False),
                "from-date-range": get_text("from-date-range"),
                "from-albums": get_text("from-albums"),
                "from-minimal-rating": get_int("from-minimal-rating", 0),
                "from-people": get_text("from-people"),
                "from-tags": get_text("from-tags"),
                "from-city": get_text("from-city"),
                "from-state": get_text("from-state"),
                "from-country": get_text("from-country"),
                "from-make": get_text("from-make"),
                "from-model": get_text("from-model"),
                "from-include-type": get_combo("from-include-type", "all"),
                "from-include-ext": get_text("from-include-ext"),
                "from-exclude-ext": get_text("from-exclude-ext"),
                "from-time-zone": get_text("from-time-zone"),
                "from-device-uuid": get_text("from-device-uuid"),
                "from-skip-ssl": get_bool("from-skip-ssl", False),
                "from-api-trace": get_bool("from-api-trace", False),
                "from-pause-jobs": get_bool("from-pause-jobs", True),
                "tag": get_text("tag"),
                "session-tag": get_bool("session-tag", False),
                "overwrite": get_bool("overwrite", False),
                "time-zone": get_text("time-zone"),
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
                "manage-epson": get_bool("manage-epson", False),
                "on-errors": get_combo("on-errors", "stop"),
                "log-level": get_combo("log-level", "INFO"),
                "api-trace": get_bool("api-trace", False),
            }

        elif tab_key == "archive-folder":
            return {
                "path": get_text("path"),
                "write-to": get_text("write-to"),
                "date-range": get_text("date-range"),
                "include-type": get_combo("include-type", "all"),
                "include-ext": get_text("include-ext"),
                "exclude-ext": get_text("exclude-ext"),
                "ban-file": get_text("ban-file"),
                "recursive": get_bool("recursive", True),
                "ignore-sidecar": get_bool("ignore-sidecar", False),
                "date-from-name": get_bool("date-from-name", True),
                "folder-album": get_combo("folder-album", "NONE"),
                "folder-tags": get_bool("folder-tags", False),
                "into-album": get_text("into-album"),
                "album-path-joiner": get_text("album-path-joiner"),
                "on-errors": get_combo("on-errors", "stop"),
                "log-level": get_combo("log-level", "INFO"),
            }

        elif tab_key == "archive-immich":
            return {
                "write-to": get_text("write-to"),
                "from-date-range": get_text("from-date-range"),
                "from-albums": get_text("from-albums"),
                "from-favorite": get_bool("from-favorite", False),
                "from-archived": get_bool("from-archived", False),
                "from-trash": get_bool("from-trash", False),
                "from-minimal-rating": get_int("from-minimal-rating", 0),
                "from-no-album": get_bool("from-no-album", False),
                "from-partners": get_bool("from-partners", False),
                "from-people": get_text("from-people"),
                "from-tags": get_text("from-tags"),
                "from-city": get_text("from-city"),
                "from-state": get_text("from-state"),
                "from-country": get_text("from-country"),
                "from-make": get_text("from-make"),
                "from-model": get_text("from-model"),
                "from-include-type": get_combo("from-include-type", "all"),
                "from-include-ext": get_text("from-include-ext"),
                "from-exclude-ext": get_text("from-exclude-ext"),
                "from-time-zone": get_text("from-time-zone"),
                "from-device-uuid": get_text("from-device-uuid"),
                "from-client-timeout": get_int("from-client-timeout", 20),
                "from-skip-ssl": get_bool("from-skip-ssl", False),
                "from-api-trace": get_bool("from-api-trace", False),
                "from-pause-jobs": get_bool("from-pause-jobs", True),
                "log-level": get_combo("log-level", "INFO"),
            }

        elif tab_key == "stack":
            return {
                "manage-burst": get_combo("manage-burst", "NoStack"),
                "manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
                "manage-heic-jpeg": get_combo("manage-heic-jpeg", "NoStack"),
                "date-range": get_text("date-range"),
                "time-zone": get_text("time-zone"),
                "manage-epson": get_bool("manage-epson", False),
                "pause-jobs": get_bool("pause-jobs", True),
                "log-level": get_combo("log-level", "INFO"),
                "api-trace": get_bool("api-trace", False),
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
        active_lock = getattr(self, "active_lock_path", None)
        is_running = (active_lock is not None and is_lock_active(active_lock)) or (getattr(self, "running_process", False) is True)
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
        if plan.errors:
            QMessageBox.critical(
                self, "Command Build Errors",
                "\n".join(f"• {e}" for e in plan.errors)
            )
            return

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
            cmd_str = " ".join(shlex.quote(p) for p in plan.display_argv)

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

    def update_binary(self, version: str | None = None, force_download: bool = False) -> bool:
        if version is None:
            version = self.get_latest_release_info()
            if not version:
                QMessageBox.critical(self, "Error", "Could not determine latest version.")
                return False

        clean_v = version.lstrip("v")
        version_dir = os.path.join(BINARY_BASE_DIR, clean_v)
        os.makedirs(version_dir, exist_ok=True)

        binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        binary_path = os.path.join(version_dir, binary_filename)

        if os.path.exists(binary_path) and not force_download:
            if self.binary_manager.verify_extracted_binary(binary_path):
                self._select_version(clean_v, binary_path)
                return True

        download_url = self.binary_manager.get_release_asset_url(version=clean_v)
        if not download_url:
            QMessageBox.critical(
                self, "Error",
                f"Could not determine download URL for version {clean_v} on this platform."
            )
            return False

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

        class DownloadThread(QThread):
            download_progress = Signal(int)
            download_complete = Signal(str)
            download_error = Signal(str)

            def __init__(self, url, dest_path):
                super().__init__()
                self.url = url
                self.dest_path = dest_path
                self.cancelled = False

            def run(self):
                try:
                    with requests.get(self.url, stream=True, timeout=60) as response:
                        response.raise_for_status()
                        total = int(response.headers.get("content-length", 0))
                        downloaded = 0
                        with open(self.dest_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=1024 * 1024):
                                if self.cancelled:
                                    self.download_error.emit("Download cancelled")
                                    return
                                downloaded += len(chunk)
                                f.write(chunk)
                                if total > 0:
                                    self.download_progress.emit(int(downloaded * 100 / total))
                    self.download_complete.emit(self.dest_path)
                except Exception as e:
                    self.download_error.emit(str(e))

        temp_archive_path = os.path.join(version_dir, "download.tmp")
        download_success = False

        try:
            download_thread = DownloadThread(download_url, temp_archive_path)

            def handle_download_complete(tmp_archive):
                nonlocal download_success
                progress_dialog.accept()
                temp_bin = binary_path + ".tmp"
                try:
                    if download_url.endswith(".zip"):
                        with zipfile.ZipFile(tmp_archive) as z:
                            for filename in z.namelist():
                                base = os.path.basename(filename)
                                if base in ("immich-go", "immich-go.exe"):
                                    with z.open(filename) as source, open(temp_bin, "wb") as target:
                                        target.write(source.read())
                                    break
                    elif download_url.endswith(".tar.gz") or download_url.endswith(".tgz"):
                        with tarfile.open(name=tmp_archive, mode="r:gz") as tar:
                            for member in tar.getmembers():
                                base = os.path.basename(member.name)
                                if base in ("immich-go", "immich-go.exe"):
                                    source = tar.extractfile(member)
                                    if source:
                                        with open(temp_bin, "wb") as target:
                                            target.write(source.read())
                                    break
                    else:
                        raise ValueError("Unsupported archive type")

                    if not self.binary_manager.verify_extracted_binary(temp_bin):
                        raise RuntimeError("Extracted binary failed post-install verification check.")

                    os.replace(temp_bin, binary_path)
                    self._select_version(clean_v, binary_path)
                    download_success = True
                except Exception as extraction_error:
                    if os.path.exists(temp_bin):
                        try:
                            os.remove(temp_bin)
                        except OSError:
                            pass
                    QMessageBox.critical(
                        self, "Extraction Error",
                        f"Failed to extract or verify binary: {str(extraction_error)}\n\n"
                        "Please download manually from GitHub."
                    )

                if os.path.exists(tmp_archive):
                    try:
                        os.remove(tmp_archive)
                    except OSError:
                        pass

            def handle_download_error(error):
                progress_dialog.reject()
                if os.path.exists(temp_archive_path):
                    try:
                        os.remove(temp_archive_path)
                    except OSError:
                        pass
                QMessageBox.critical(self, "Download Error", f"Failed to download: {error}")

            download_thread.download_progress.connect(progress_bar.setValue)
            download_thread.download_complete.connect(handle_download_complete)
            download_thread.download_error.connect(handle_download_error)

            def cancel_download():
                download_thread.cancelled = True
                progress_dialog.reject()

            cancel_button.clicked.connect(cancel_download)
            progress_dialog.show()
            download_thread.start()
            progress_dialog.exec()

        except Exception as e:
            if os.path.exists(temp_archive_path):
                try:
                    os.remove(temp_archive_path)
                except OSError:
                    pass
            QMessageBox.critical(
                self, "Download Error",
                f"Failed to initiate download: {str(e)}"
            )
            return False

        return download_success

    def build_environment(self, tab_key: str = None) -> dict:
        if tab_key is None:
            tab_key = self._get_active_tab_key()
        server = self.inputs.get("config", {}).get("server").text().strip() if self.inputs.get("config", {}).get("server") else ""
        api_key = self.inputs.get("config", {}).get("api_key").text().strip() if self.inputs.get("config", {}).get("api_key") else ""
        from_server = self.inputs.get("upload-immich", {}).get("from-server").text().strip() if self.inputs.get("upload-immich", {}).get("from-server") else ""
        from_api_key = self.inputs.get("upload-immich", {}).get("from-api-key").text().strip() if self.inputs.get("upload-immich", {}).get("from-api-key") else ""
        return build_environment(tab_key, server, api_key, from_server, from_api_key)

    def _start_process_timer(self):
        if not hasattr(self, "check_process_timer"):
            self.check_process_timer = QTimer(self)
            self.check_process_timer.timeout.connect(self._check_lock_file)
        if not self.check_process_timer.isActive():
            self.check_process_timer.start(1000)

    def _check_lock_file(self):
        active_path = getattr(self, "active_lock_path", None)
        if not active_path:
            if hasattr(self, "check_process_timer"):
                self.check_process_timer.stop()
            self.running_process = False
            self.update_status()
            return

        if not is_lock_active(active_path):
            if hasattr(self, "check_process_timer"):
                self.check_process_timer.stop()
            release_lock(active_path)
            self.active_lock_path = None
            self.running_process = False
            self.update_status()
        else:
            self.running_process = True
            self.update_status()

    def check_if_process_running(self):
        """Backward compatible alias for _check_lock_file."""
        self._check_lock_file()

    def closeEvent(self, event):
        active_locks = scan_locks()
        active_path = getattr(self, "active_lock_path", None)
        if active_locks or (active_path and is_lock_active(active_path)):
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

        event.accept()

    def run_command(self, plan_or_parts=None):
        if isinstance(plan_or_parts, CommandPlan):
            plan = plan_or_parts
        else:
            tab_key = self._get_active_tab_key()
            config_state = self._collect_config_state()
            tab_state = self._collect_tab_state(tab_key)
            binary_path = getattr(self, "binary_path", "./immich-go")
            plan = build_plan_from_state(tab_key, config_state, tab_state, binary_path, False)

        if plan.errors:
            QMessageBox.critical(
                self, "Command Build Errors",
                "\n".join(f"• {e}" for e in plan.errors)
            )
            return

        binary_path = plan.binary_path or getattr(self, "binary_path", "./immich-go")
        if not os.path.exists(binary_path):
            if not self.update_binary():
                QMessageBox.critical(
                    self, "Error",
                    "Immich-Go binary is missing or not executable."
                )
                return

        summary = f"{plan.tab_key}"
        if plan.argv:
            summary = " ".join(plan.argv[:3])

        lock_path = create_lock(
            tab_key=plan.tab_key,
            command_summary=summary,
            binary_path=binary_path,
        )

        pref_term = getattr(self.app_config, "preferred_terminal", "auto")
        full_cmd = [binary_path] + plan.argv

        res = launch_external_terminal(
            command=full_cmd,
            env=plan.env,
            lock_path=lock_path,
            preferred_terminal=pref_term,
        )

        if not res.ok:
            release_lock(lock_path)
            QMessageBox.critical(self, "Error Launching Terminal", res.message)
            self.btn_run.setEnabled(True)
            self.btn_dry_run.setEnabled(True)
            return

        self.active_lock_path = lock_path
        self.running_process = True
        self.btn_run.setEnabled(False)
        self.btn_dry_run.setEnabled(False)
        self._start_process_timer()
        self.update_status()

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

        if "secret_provider" in self.inputs["config"]:
            idx = self.inputs["config"]["secret_provider"].findData(self.app_config.secrets_provider)
            if idx >= 0:
                self.inputs["config"]["secret_provider"].setCurrentIndex(idx)

        prof_name = getattr(self.app_config, "profile_name", "default")
        self.inputs["config"]["api_key"].setText(
            get_secret_with_fallback(
                profile_name=prof_name,
                key="api_key",
                provider=self.app_config.secrets_provider,
            )
        )

        if "admin_api_key" in self.inputs["config"]:
            self.inputs["config"]["admin_api_key"].setText(
                get_secret_with_fallback(
                    profile_name=prof_name,
                    key="admin_api_key",
                    provider=self.app_config.secrets_provider,
                )
            )

        if "allow_untested_updates" in self.inputs["config"]:
            self.inputs["config"]["allow_untested_updates"].setChecked(
                self.app_config.allow_untested_updates
            )

        if "preferred_terminal" in self.inputs["config"]:
            self.inputs["config"]["preferred_terminal"].setCurrentText(
                self.app_config.preferred_terminal
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
            if self.app_config.on_errors == ON_ERRORS_CUSTOM_VALUE:
                self.inputs["config"]["on_errors"].setCurrentText(ON_ERRORS_CUSTOM_LABEL)
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

        self.apply_form_state(self.app_config.form_state)

        self.theme_mode = normalize_theme_mode(self.app_config.theme_mode)

        if hasattr(self, "theme_mode_combo"):
            self.theme_mode_combo.blockSignals(True)
            self.theme_mode_combo.setCurrentText(self.theme_mode)
            self.theme_mode_combo.blockSignals(False)

        self.apply_theme(self.theme_mode)
        self.toggle_advanced(self.app_config.advanced_mode)
        self.update_window_title()

    def save_configuration(self, show_popup: bool = True):
        self.app_config.server_url = self.inputs["config"]["server"].text()

        if "skip-ssl" in self.inputs["config"]:
            self.app_config.skip_ssl = self.inputs["config"]["skip-ssl"].isChecked()

        if "secret_provider" in self.inputs["config"]:
            self.app_config.secrets_provider = self.inputs["config"]["secret_provider"].currentData()

        if "allow_untested_updates" in self.inputs["config"]:
            self.app_config.allow_untested_updates = (
                self.inputs["config"]["allow_untested_updates"].isChecked()
            )

        if "preferred_terminal" in self.inputs["config"]:
            self.app_config.preferred_terminal = (
                self.inputs["config"]["preferred_terminal"].currentText()
            )

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
            if on_errors_text == ON_ERRORS_CUSTOM_LABEL:
                self.app_config.on_errors = ON_ERRORS_CUSTOM_VALUE
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

        self.app_config.form_state = self.collect_form_state()
        save_config(self.app_config)

        prof_name = getattr(self.app_config, "profile_name", "default")
        api_key = self.inputs["config"]["api_key"].text().strip()
        admin_key = self.inputs["config"]["admin_api_key"].text().strip() if "admin_api_key" in self.inputs["config"] else ""

        res_api = save_secret_with_fallback(
            profile_name=prof_name,
            key="api_key",
            value=api_key,
            provider=self.app_config.secrets_provider,
        )
        res_admin = save_secret_with_fallback(
            profile_name=prof_name,
            key="admin_api_key",
            value=admin_key,
            provider=self.app_config.secrets_provider,
        )

        msg = "Configuration saved successfully."
        if res_api.message:
            msg += f"\n\nNote (API Key): {res_api.message}"
        if res_admin.message:
            msg += f"\n\nNote (Admin Key): {res_admin.message}"

        if show_popup:
            QMessageBox.information(
                self,
                "Saved",
                msg,
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