import sys
import os
import re
import io
import subprocess
import shlex
import platform
import webbrowser
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStyleFactory, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QCheckBox, QComboBox, QPushButton, QFileDialog,
    QPlainTextEdit, QStackedWidget, QFrame, QSizePolicy,
    QScrollArea, QMessageBox, QDialog, QProgressBar, QSpinBox, QStyle, QLayout
)
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QGuiApplication, QPalette, QIcon, QPainter, QPen, QColor, QBrush, QFont
from PySide6.QtCore import Qt, QEvent, QDate, QTimer, QUrl, QSettings, QThread, Signal, QSize
import psutil
import requests

# ==========================================
# STYLESHEETS & THEME ENGINE
# ==========================================

THEME_SYSTEM = "System"
THEME_LIGHT = "Light"
THEME_DARK = "Dark"

def theme_tokens(theme: str) -> dict:
    if theme == "dark":
        return {
            "bg": "#0E1113",
            "sidebar": "#121619",
            "surface": "#151A1E",
            "surface_alt": "#1B2126",
            "input_bg": "#1B2126",
            "input_focus_bg": "#20272D",
            "border": "#262D34",
            "border_strong": "#343C43",
            "text": "#E8ECEF",
            "text_muted": "#97A1AA",
            "text_faint": "#6B757D",
            "accent": "#4FB3A4",
            "accent_hover": "#6FD6C5",
            "accent_subtle": "#17332F",
            "primary": "#E1512E",
            "primary_hover": "#F1603D",
            "on_primary": "#FFFFFF",
            "button_bg": "#20262B",
            "button_hover": "#2A3238",
            "scrollbar": "#0E1113",
            "scrollbar_handle": "#3A434B",
        }
    return {
        "bg": "#F5F7F9",
        "sidebar": "#FFFFFF",
        "surface": "#FFFFFF",
        "surface_alt": "#F8FAFC",
        "input_bg": "#F8FAFC",
        "input_focus_bg": "#FFFFFF",
        "border": "#D8DEE4",
        "border_strong": "#C7CED6",
        "text": "#18222C",
        "text_muted": "#5D6B7A",
        "text_faint": "#7C8794",
        "accent": "#0F766E",
        "accent_hover": "#14B8A6",
        "accent_subtle": "#E4F5F2",
        "primary": "#C2410C",
        "primary_hover": "#EA580C",
        "on_primary": "#FFFFFF",
        "button_bg": "#EEF1F4",
        "button_hover": "#E2E7EC",
        "scrollbar": "#EEF1F4",
        "scrollbar_handle": "#AEB8C2",
    }

def build_stylesheet(theme: str) -> str:
    t = theme_tokens(theme)
    return f"""
QMainWindow, QWidget {{
    background-color: {t["bg"]};
    color: {t["text"]};
    font-family: "Segoe UI", system-ui, sans-serif;
    font-size: 14px;
}}
#HeaderFrame, #FooterFrame {{
    background-color: {t["bg"]};
    border: none;
}}
#HeaderFrame {{
    border-bottom: 1px solid {t["border"]};
}}
#FooterFrame {{
    border-top: 1px solid {t["border"]};
}}
QLabel#AppName {{
    font-family: "Consolas", monospace;
    font-weight: 600;
    font-size: 16px;
    color: {t["text"]};
}}
QLabel#Crumb {{
    font-family: "Consolas", monospace;
    font-size: 12px;
    color: {t["text_muted"]};
}}
QLabel#ModeLabel {{
    font-family: "Consolas", monospace;
    font-size: 12px;
    color: {t["text_muted"]};
    padding-right: 8px;
}}
#Sidebar {{
    background-color: {t["sidebar"]};
    border-right: 1px solid {t["border"]};
}}
QPushButton#NavBtn {{
    text-align: left;
    padding: 10px 12px;
    font-size: 14px;
    font-weight: 500;
    color: {t["text_muted"]};
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
}}
QPushButton#NavBtn:hover {{
    background-color: {t["surface_alt"]};
    color: {t["text"]};
}}
QPushButton#NavBtn:checked {{
    background-color: {t["accent_subtle"]};
    color: {t["accent"]};
    border: 1px solid {t["accent"]};
}}
QLabel#NavTitle {{
    font-family: "Consolas", monospace;
    font-size: 10px;
    font-weight: 600;
    color: {t["text_faint"]};
    padding: 0 12px;
    margin-top: 16px;
}}
QFrame#Card {{
    background-color: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 8px;
}}
QLabel#CardTitle {{
    font-family: "Consolas", monospace;
    font-size: 12px;
    font-weight: 600;
    color: {t["text_muted"]};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
}}
QLabel#ReqBadge {{
    font-size: 10px;
    color: {t["primary"]};
    background-color: {t["accent_subtle"]};
    border: 1px solid {t["primary"]};
    padding: 2px 6px;
    border-radius: 4px;
}}
QLabel#Subhead {{
    font-family: "Consolas", monospace;
    font-size: 11px;
    color: {t["text_faint"]};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 16px;
    margin-bottom: 8px;
    border-top: 1px solid {t["border"]};
    padding-top: 12px;
}}
QLabel#FieldLabel {{
    font-size: 13px;
    font-weight: 500;
    color: {t["text"]};
}}
QLabel#Hint {{
    font-size: 12px;
    color: {t["text_muted"]};
}}
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
    background-color: {t["input_bg"]};
    border: 1px solid {t["border_strong"]};
    color: {t["text"]};
    padding: 9px 11px;
    border-radius: 6px;
    font-size: 14px;
    selection-background-color: {t["accent"]};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QPlainTextEdit:hover {{
    border-color: {t["accent"]};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {t["accent"]};
    background-color: {t["input_focus_bg"]};
}}
QLineEdit:disabled {{
    background-color: {t["surface_alt"]};
    color: {t["text_faint"]};
    border-color: {t["border"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {t["surface"]};
    color: {t["text"]};
    selection-background-color: {t["accent_subtle"]};
    selection-color: {t["accent"]};
    border: 1px solid {t["border"]};
}}
QPushButton {{
    background-color: {t["button_bg"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 6px;
    padding: 8px 16px;
}}
QPushButton:hover {{
    background-color: {t["button_hover"]};
}}
QPushButton#BtnRun {{
    background-color: {t["primary"]};
    color: {t["on_primary"]};
    border: none;
    border-radius: 7px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 13.5px;
}}
QPushButton#BtnRun:hover {{
    background-color: {t["primary_hover"]};
}}
QPushButton#BtnRun:disabled {{
    background-color: {t["surface_alt"]};
    color: {t["text_faint"]};
    border: 1px solid {t["border"]};
}}
QPushButton#BtnPreview {{
    background-color: {t["accent_subtle"]};
    color: {t["accent"]};
    border: 1px solid {t["accent"]};
    border-radius: 7px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 13.5px;
}}
QPushButton#BtnPreview:hover {{
    background-color: {t["button_hover"]};
}}
QPushButton#BtnPreview:disabled {{
    background-color: {t["surface_alt"]};
    color: {t["text_faint"]};
    border-color: {t["border"]};
}}
QDialog {{
    background-color: {t["surface"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 12px;
}}
QLabel#DlgKicker {{
    font-family: "Consolas", monospace;
    font-size: 11px;
    color: {t["text_faint"]};
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QLabel#DlgTitle {{
    font-size: 18px;
    font-weight: 600;
    color: {t["text"]};
}}
QLabel#DlgDesc {{
    font-size: 13px;
    color: {t["text_muted"]};
}}
QPlainTextEdit#CmdBlock {{
    background-color: #0B0D0E;
    border: 1px solid {t["border"]};
    color: #ECE7DD;
    font-family: "Consolas", monospace;
    font-size: 13px;
    border-radius: 8px;
    padding: 16px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    border: none;
    background: {t["scrollbar"]};
    width: 8px;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {t["scrollbar_handle"]};
    min-height: 20px;
    min-width: 20px;
    border-radius: 4px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0; width: 0;
}}
QMenu {{
    background-color: {t["surface"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
}}
QMenu::item:selected {{
    background-color: {t["accent_subtle"]};
    color: {t["accent"]};
}}
"""

def detect_system_theme() -> str:
    try:
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorScheme"):
            scheme = hints.colorScheme()
            if scheme == Qt.ColorScheme.Dark: return "dark"
            if scheme == Qt.ColorScheme.Light: return "light"
    except Exception:
        pass
    app = QApplication.instance()
    if app is None: return "dark"
    pal = app.palette()
    try:
        bg = pal.color(QPalette.ColorRole.Window)
        fg = pal.color(QPalette.ColorRole.WindowText)
    except AttributeError:
        bg = pal.color(QPalette.Window)
        fg = pal.color(QPalette.WindowText)
    return "dark" if fg.lightness() > bg.lightness() else "light"

def apply_base_palette(theme: str):
    t = theme_tokens(theme)
    app = QApplication.instance()
    if app is None: return
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(t["bg"]))
    pal.setColor(QPalette.WindowText, QColor(t["text"]))
    pal.setColor(QPalette.Base, QColor(t["input_bg"]))
    pal.setColor(QPalette.AlternateBase, QColor(t["surface_alt"]))
    pal.setColor(QPalette.Text, QColor(t["text"]))
    pal.setColor(QPalette.Button, QColor(t["button_bg"]))
    pal.setColor(QPalette.ButtonText, QColor(t["text"]))
    pal.setColor(QPalette.Highlight, QColor(t["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ToolTipBase, QColor(t["surface"]))
    pal.setColor(QPalette.ToolTipText, QColor(t["text"]))
    app.setPalette(pal)

def apply_application_theme(mode: str) -> str:
    resolved = detect_system_theme() if mode == THEME_SYSTEM else mode.lower()
    app = QApplication.instance()
    if app is None: return resolved
    app.setProperty("theme", resolved)
    apply_base_palette(resolved)
    app.setStyleSheet(build_stylesheet(resolved))
    return resolved






# ==========================================
# CUSTOM WIDGETS
# ==========================================
class SwitchButton(QWidget):
    toggled = Signal(bool)  # Fixed: Class-level signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self.setFixedSize(38, 22)
        self.setCursor(Qt.PointingHandCursor)

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
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        
        # Determine colors based on app theme (simplified check for light mode)
        is_light = QApplication.instance().styleSheet().find("#ffffff") != -1
        
        if self._checked:
            border_color = QColor("#0f766e") if is_light else QColor("#4fb3a4")
            bg_color = QColor("#ccfbf1") if is_light else QColor("#1b3733")
            circle_color = QColor("#0f766e") if is_light else QColor("#4fb3a4")
        else:
            border_color = QColor("#9ca3af") if is_light else QColor("#3a4045")
            bg_color = QColor("#f8f9fa") if is_light else QColor("#1d2226")
            circle_color = QColor("#6b7280") if is_light else QColor("#5b6267")
            
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 11, 11)
        
        if self._checked:
            circle_x = self.width() - 2 - 16
        else:
            circle_x = 2
            
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(circle_color))
        painter.drawEllipse(circle_x, 2, 16, 16)

from PySide6.QtWidgets import QFormLayout

class Card(QFrame):
    def __init__(self, title, required=False, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(18)
        
        title_layout = QHBoxLayout()
        title_label = QLabel(title.upper())
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
        self.setLabelAlignment(Qt.AlignLeft)
        self.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.setVerticalSpacing(16)
        self.setHorizontalSpacing(24)
        
    def add_row(self, label_text, widget, hint=""):
        lbl = QLabel(label_text)
        lbl.setObjectName("FieldLabel")
        
        # Set proper sizing policy so widgets can expand naturally without hardcoded max-width
        if isinstance(widget, QWidget):
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            
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
    """Preferred width = full text; minimum width = tiny. Elides when shrunk."""
    def __init__(self, text="", elide=Qt.ElideMiddle, parent=None):
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

    def resizeEvent(self, e):  super().resizeEvent(e);  self._refresh()
    def showEvent(self, e):    super().showEvent(e);    self._refresh()
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
        self.scroll_layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        self.container = QWidget()
        self.container.setMaximumWidth(1100)
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(32, 32, 32, 32)
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
        self.setCursor(Qt.PointingHandCursor)
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
            lbl = QLabel(title.upper())
            lbl.setObjectName("NavTitle")
            layout.addWidget(lbl)
            
        for item in items:
            layout.addWidget(item)

class StatusCard(QFrame):
    _DOT = {"ok": "#22c55e", "warn": "#f59e0b", "err": "#ef4444"}
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(8)
        self.dot_b, self.txt_b = self._row(lay, "Binary: …")
        self.dot_s, self.txt_s = self._row(lay, "Server: Not Set")
        self.set_binary("err", "Binary: Checking…")
        self.set_server("err", "Server: Not Set")

    def _row(self, lay, text):
        dot = QLabel(); dot.setFixedSize(10, 10)
        txt = QLabel(text); txt.setObjectName("StatusText")
        r = QHBoxLayout(); r.setSpacing(8)
        r.addWidget(dot, 0, Qt.AlignVCenter); r.addWidget(txt, 1); r.addStretch()
        lay.addLayout(r)
        return dot, txt

    def _paint(self, dot, state):
        dot.setStyleSheet(f"background:{self._DOT.get(state, self._DOT['err'])};border-radius:5px;")

    def set_binary(self, state, text): self._paint(self.dot_b, state); self.txt_b.setText(text)
    def set_server(self, state, text): self._paint(self.dot_s, state); self.txt_s.setText(text)

# ==========================================
# MAIN APPLICATION
# ==========================================
class ImmichGoGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immich Go GUI")
        self.resize(1250, 750)
        self.setMinimumSize(900, 600)
        
        self.settings = QSettings("YourOrganization", "ImmichGoGUI")
        
        self.is_advanced = False
        self.theme_mode = self.settings.value("theme_mode", THEME_SYSTEM)
        
        apply_application_theme(self.theme_mode)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.inputs = {}  # Dictionary to hold all form inputs per tab
        self.adv_frames = []  # List to hold advanced containers for toggling
        
        self._build_sidebar()
        self._build_content_area()
        
        self.create_menu_bar()
        
        # Initialize UI forms
        self.config_tab = self._build_config_tab()
        self.upload_folder_tab = self._build_upload_folder_tab()
        self.upload_gp_tab = self._build_upload_gp_tab()
        self.upload_immich_tab = self._build_upload_immich_tab()
        self.archive_folder_tab = self._build_archive_folder_tab()
        self.archive_immich_tab = self._build_archive_immich_tab()
        self.stack_tab = self._build_stack_tab()
        
        self.stacked_widget.addWidget(self.config_tab)
        self.stacked_widget.addWidget(self.upload_folder_tab)
        self.stacked_widget.addWidget(self.upload_gp_tab)
        self.stacked_widget.addWidget(self.upload_immich_tab)
        self.stacked_widget.addWidget(self.archive_folder_tab)
        self.stacked_widget.addWidget(self.archive_immich_tab)
        self.stacked_widget.addWidget(self.stack_tab)
        
        self.stacked_widget.setCurrentIndex(0)
        self.update_header_crumb("configuration")
        self.footer.setVisible(False)  # Hide footer on config tab
        
        self.settings = QSettings("YourOrganization", "ImmichGoGUI")
        self.check_binary_version()
        self.load_configuration()
        self.apply_theme(self.theme_mode)
        self.connect_system_theme_changes()
        
        # Connect signals for validation
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

    # ==========================================
    # UI STRUCTURE BUILDERS
    # ==========================================

    def apply_theme(self, mode=None):
        if mode is None:
            mode = getattr(self, "theme_mode", THEME_SYSTEM)
        
        self.theme_mode = mode
        
        if hasattr(self, "theme_mode_combo"):
            self.theme_mode_combo.blockSignals(True)
            self.theme_mode_combo.setCurrentText(mode)
            self.theme_mode_combo.blockSignals(False)
            
        apply_application_theme(mode)
        
        for widget in self.findChildren(QWidget):
            try:
                widget.update()
            except TypeError:
                pass
            
        self.update()

    def connect_system_theme_changes(self):
        try:
            hints = QGuiApplication.styleHints()
            if hasattr(hints, "colorSchemeChanged"):
                hints.colorSchemeChanged.connect(lambda *_: self.on_system_theme_changed())
        except Exception:
            pass

    def on_system_theme_changed(self):
        if getattr(self, "theme_mode", THEME_SYSTEM) == THEME_SYSTEM:
            QTimer.singleShot(0, lambda: self.apply_theme(THEME_SYSTEM))

    def event(self, e):
        if e.type() == QEvent.Type.ThemeChange:
            if getattr(self, "theme_mode", THEME_SYSTEM) == THEME_SYSTEM:
                QTimer.singleShot(0, lambda: self.apply_theme(THEME_SYSTEM))
        return super().event(e)

    def _nav_icon(self, theme_name, sp_fallback):
        return QIcon.fromTheme(theme_name, self.style().standardIcon(sp_fallback, None, self))

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        
        self.btn_config = NavItem("Configuration", self._nav_icon("preferences-system", QStyle.SP_FileDialogDetailedView))
        self.btn_config.setChecked(True)
        self.btn_config.clicked.connect(lambda: self.switch_tab(0, "configuration", self.btn_config))
        sidebar_layout.addWidget(NavGroup("", [self.btn_config]))
        
        self.btn_upload_folder = NavItem("Folder Upload", self._nav_icon("folder", QStyle.SP_DirOpenIcon))
        self.btn_upload_folder.clicked.connect(lambda: self.switch_tab(1, "upload · from-folder", self.btn_upload_folder))
        self.btn_upload_gp = NavItem("Google Takeout", self._nav_icon("package-x-generic", QStyle.SP_DialogSaveButton))
        self.btn_upload_gp.clicked.connect(lambda: self.switch_tab(2, "upload · from-google-photos", self.btn_upload_gp))
        self.btn_upload_immich = NavItem("From Immich Server", self._nav_icon("view-refresh", QStyle.SP_BrowserReload))
        self.btn_upload_immich.clicked.connect(lambda: self.switch_tab(3, "upload · from-immich", self.btn_upload_immich))
        sidebar_layout.addWidget(NavGroup("UPLOAD", [self.btn_upload_folder, self.btn_upload_gp, self.btn_upload_immich]))
        
        self.btn_archive_folder = NavItem("Archive Folder", self._nav_icon("drive-harddisk", QStyle.SP_DriveHDIcon))
        self.btn_archive_folder.clicked.connect(lambda: self.switch_tab(4, "archive · from-folder", self.btn_archive_folder))
        self.btn_archive_immich = NavItem("Archive Server", self._nav_icon("network-server", QStyle.SP_DriveNetIcon))
        self.btn_archive_immich.clicked.connect(lambda: self.switch_tab(5, "archive · from-immich", self.btn_archive_immich))
        sidebar_layout.addWidget(NavGroup("ARCHIVE", [self.btn_archive_folder, self.btn_archive_immich]))
        
        self.btn_stack = NavItem("Stack Assets", self._nav_icon("view-list", QStyle.SP_FileDialogListView))
        self.btn_stack.clicked.connect(lambda: self.switch_tab(6, "stack", self.btn_stack))
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
        
        # Header
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
        
        # Advanced Toggle
        adv_box = QHBoxLayout()
        self.lbl_mode = QLabel("Simple")
        self.lbl_mode.setObjectName("ModeLabel")
        adv_box.addWidget(self.lbl_mode)
        self.switch_advanced = SwitchButton()
        self.switch_advanced.toggled.connect(self.toggle_advanced)
        adv_box.addWidget(self.switch_advanced)
        header_layout.addLayout(adv_box)
        
        content_layout.addWidget(header)
        
        # Stacked Widget
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        
        # Footer
        self.footer = QFrame()
        self.footer.setObjectName("FooterFrame")
        self.footer.setFixedHeight(70)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(24, 0, 24, 0)
        footer_layout.addStretch()
        
        self.btn_dry_run = QPushButton("Preview (Dry Run)")
        self.btn_dry_run.setObjectName("BtnPreview")
        self.btn_dry_run.setCursor(Qt.PointingHandCursor)
        self.btn_dry_run.clicked.connect(lambda: self.show_confirm_dialog(True))
        footer_layout.addWidget(self.btn_dry_run)
        
        self.btn_run = QPushButton("Run Command")
        self.btn_run.setObjectName("BtnRun")
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(lambda: self.show_confirm_dialog(False))
        footer_layout.addWidget(self.btn_run)
        
        content_layout.addWidget(self.footer)
        
        self.main_layout.addWidget(content_frame)

    def _build_config_tab(self):
        page = BasePage()
        self.inputs['config'] = {}

        # Server Connection
        card = Card("Immich Server Connection", required=True)
        form = FormSection()
        
        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("http://localhost:2283")
        self.inputs['config']['server'] = self.server_url_edit
        form.add_row("Server URL", self.server_url_edit)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Paste your Immich API key")
        self.inputs['config']['api_key'] = self.api_key_edit
        form.add_row("API Key", self.api_key_edit, "You can generate an API key in Immich under Account Settings -> API Keys.")
        
        card.layout.addLayout(form)
        page.addWidget(card)

        # Binary Management
        card2 = Card("Binary Management")
        row = QHBoxLayout()
        row.setSpacing(16)
        row.setAlignment(Qt.AlignTop)

        info = QVBoxLayout(); info.setSpacing(2)
        self.lbl_binary_version = QLabel("Checking version…")
        self.lbl_binary_version.setObjectName("FieldLabel")
        self.lbl_binary_version.setWordWrap(True)
        self.lbl_binary_path = ElidingLabel("", Qt.ElideMiddle)
        self.lbl_binary_path.setObjectName("Hint")
        info.addWidget(self.lbl_binary_version)
        info.addWidget(self.lbl_binary_path)
        row.addLayout(info, 1)

        btn_check = QPushButton("Check for Updates")
        self.btn_check_updates = btn_check
        btn_check.clicked.connect(self.check_for_updates)
        row.addWidget(btn_check, 0, Qt.AlignTop)
        card2.layout.addLayout(row)
        page.addWidget(card2)

        # Appearance
        card3 = Card("Appearance")
        appearance_form = FormSection()

        self.theme_mode_combo = QComboBox()
        self.theme_mode_combo.addItems([THEME_SYSTEM, THEME_LIGHT, THEME_DARK])
        self.theme_mode_combo.setCurrentText(THEME_SYSTEM)
        self.theme_mode_combo.currentTextChanged.connect(self.apply_theme)

        appearance_form.add_row(
            "Theme",
            self.theme_mode_combo,
            "System follows your operating system theme when supported."
        )

        card3.layout.addLayout(appearance_form)
        page.addWidget(card3)

        # Advanced Config
        adv_card = Card("Advanced Configuration")
        adv_form = FormSection()
        
        self.client_timeout_spin = QSpinBox()
        self.client_timeout_spin.setRange(1, 1440)
        self.client_timeout_spin.setValue(20)
        self.client_timeout_spin.setSuffix(" minutes")
        self.inputs['config']['client_timeout'] = self.client_timeout_spin
        adv_form.add_row("Client Timeout", self.client_timeout_spin)
        
        self.concurrent_tasks_spin = QSpinBox()
        self.concurrent_tasks_spin.setRange(1, 20)
        self.concurrent_tasks_spin.setValue(2)
        self.inputs['config']['concurrent'] = self.concurrent_tasks_spin
        adv_form.add_row("Concurrent Tasks", self.concurrent_tasks_spin)
        
        self.device_uuid_edit = QLineEdit()
        self.inputs['config']['device_uuid'] = self.device_uuid_edit
        adv_form.add_row("Device UUID", self.device_uuid_edit)
        
        self.on_errors_combo = QComboBox()
        self.on_errors_combo.addItems(["stop", "continue"])
        self.inputs['config']['on_errors'] = self.on_errors_combo
        adv_form.add_row("On Errors", self.on_errors_combo)
        
        self.pause_immich_jobs_check = QCheckBox("Pause Immich Jobs")
        self.pause_immich_jobs_check.setChecked(True)
        self.inputs['config']['pause_jobs'] = self.pause_immich_jobs_check
        adv_form.addRow("", self.pause_immich_jobs_check)
        
        adv_card.layout.addLayout(adv_form)
        adv_card.setVisible(False)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        page.addStretch()
        return page

    def _build_upload_folder_tab(self):
        page = BasePage()
        self.inputs['upload-folder'] = {}

        # Source Config
        card = Card("Source Configuration", required=True)
        form = FormSection()
        self.source_path_edit = QLineEdit()
        self.source_path_edit.setPlaceholderText("/path/to/files")
        self.source_path_edit.setAcceptDrops(True)
        self.source_path_edit.dragEnterEvent = self.dragEnterEvent
        self.source_path_edit.dropEvent = self.dropEvent
        self.inputs['upload-folder']['path'] = self.source_path_edit
        form.add_row("Folder to upload", self.source_path_edit, "Every file inside this folder will be considered.")
        
        browse_action = self.source_path_edit.addAction(self.style().standardIcon(QStyle.SP_DirIcon), QLineEdit.TrailingPosition)
        browse_action.triggered.connect(self.browse_local_folder)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Options
        card = Card("Options")
        form = FormSection()
        
        c_type = QComboBox(); c_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs['upload-folder']['include-type'] = c_type
        form.add_row("Media Type", c_type)
        
        c_album = QComboBox(); c_album.addItems(["NONE", "FOLDER", "PATH"])
        self.inputs['upload-folder']['folder-album'] = c_album
        form.add_row("Album Organization", c_album)
        
        t_album = QLineEdit(); t_album.setPlaceholderText("e.g. Family Archive")
        self.inputs['upload-folder']['into-album'] = t_album
        form.add_row("Put all into Album", t_album)
        
        c_burst = QComboBox(); c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs['upload-folder']['manage-burst'] = c_burst
        form.add_row("Burst Photos", c_burst)
        
        c_raw = QComboBox(); c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs['upload-folder']['manage-raw-jpeg'] = c_raw
        form.add_row("RAW + JPEG Pairs", c_raw)
        
        c_heic = QComboBox(); c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs['upload-folder']['manage-heic-jpeg'] = c_heic
        form.add_row("HEIC + JPEG Pairs", c_heic)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Advanced Options
        adv_card = Card("Advanced Options")
        form = FormSection()
        
        subhead = QLabel("Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        d_range = QLineEdit(); d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs['upload-folder']['date-range'] = d_range
        form.add_row("Date range", d_range)
        
        inc_ext = QLineEdit(); inc_ext.setPlaceholderText(".jpg,.heic,.mp4")
        self.inputs['upload-folder']['include-ext'] = inc_ext
        form.add_row("Include extensions", inc_ext)
        
        exc_ext = QLineEdit(); exc_ext.setPlaceholderText(".thm,.xmp")
        self.inputs['upload-folder']['exclude-ext'] = exc_ext
        form.add_row("Exclude extensions", exc_ext)
        
        ban_file = QPlainTextEdit(); ban_file.setPlaceholderText("@eaDir/\n.DS_Store")
        self.inputs['upload-folder']['ban-file'] = ban_file
        form.add_row("Skip files matching patterns", ban_file)
        
        chk_ignore = QCheckBox("Ignore sidecar files")
        self.inputs['upload-folder']['ignore-sidecar'] = chk_ignore
        form.addRow("", chk_ignore)
        
        chk_date_name = QCheckBox("Guess dates from filenames")
        chk_date_name.setChecked(True)
        self.inputs['upload-folder']['date-from-name'] = chk_date_name
        form.addRow("", chk_date_name)
        
        subhead = QLabel("Tagging")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        t_tags = QLineEdit(); t_tags.setPlaceholderText("vacation, family/reunion")
        self.inputs['upload-folder']['tag'] = t_tags
        form.add_row("Custom Tags (comma separated)", t_tags)
        
        chk_sess = QCheckBox("Session Tag")
        self.inputs['upload-folder']['session-tag'] = chk_sess
        form.addRow("", chk_sess)
        
        chk_ftags = QCheckBox("Folder as Tags")
        self.inputs['upload-folder']['folder-tags'] = chk_ftags
        form.addRow("", chk_ftags)
        
        subhead = QLabel("Run Behavior")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        c_err = QComboBox(); c_err.addItems(["stop", "continue"])
        self.inputs['upload-folder']['on-errors'] = c_err
        form.add_row("If a file fails", c_err)
        
        chk_overwrite = QCheckBox("Overwrite Existing")
        self.inputs['upload-folder']['overwrite'] = chk_overwrite
        form.addRow("", chk_overwrite)
        
        chk_pause = QCheckBox("Pause background jobs")
        chk_pause.setChecked(True)
        self.inputs['upload-folder']['pause-jobs'] = chk_pause
        form.addRow("", chk_pause)
        
        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['upload-folder']['skip-ssl'] = chk_ssl
        form.addRow("", chk_ssl)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['upload-folder']['log-level'] = c_log
        form.add_row("Log Level", c_log)
        
        chk_trace = QCheckBox("Enable API Trace")
        self.inputs['upload-folder']['api-trace'] = chk_trace
        form.addRow("", chk_trace)
        

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        page.addStretch()
        return page

    def _build_upload_gp_tab(self):
        page = BasePage()
        self.inputs['upload-gp'] = {}

        # Source Config
        card = Card("Source Configuration", required=True)
        form = FormSection()
        self.gp_path_edit = QLineEdit()
        self.gp_path_edit.setPlaceholderText("/path/to/takeout")
        self.gp_path_edit.setAcceptDrops(True)
        self.gp_path_edit.dragEnterEvent = self.dragEnterEvent
        self.gp_path_edit.dropEvent = self.dropEvent
        self.inputs['upload-gp']['path'] = self.gp_path_edit
        form.add_row("Takeout File/Folder Path", self.gp_path_edit)
        
        browse_action = self.gp_path_edit.addAction(self.style().standardIcon(QStyle.SP_DirIcon), QLineEdit.TrailingPosition)
        browse_action.triggered.connect(self.browse_takeout_source)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Options
        card = Card("Options")
        form = FormSection()
        
        c_type = QComboBox(); c_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs['upload-gp']['include-type'] = c_type
        form.add_row("Media Type", c_type)
        
        t_album = QLineEdit(); t_album.setPlaceholderText("e.g. Family Archive")
        self.inputs['upload-gp']['into-album'] = t_album
        form.add_row("Put all into Album", t_album)
        
        chk_unmatched = QCheckBox("Include Unmatched Files")
        self.inputs['upload-gp']['include-unmatched'] = chk_unmatched
        form.addRow("", chk_unmatched)
        
        chk_partner = QCheckBox("Include Partner Photos")
        chk_partner.setChecked(True)
        self.inputs['upload-gp']['include-partner'] = chk_partner
        form.addRow("", chk_partner)
        
        chk_sync = QCheckBox("Sync Google Albums")
        chk_sync.setChecked(True)
        self.inputs['upload-gp']['sync-albums'] = chk_sync
        form.addRow("", chk_sync)
        
        c_burst = QComboBox(); c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs['upload-gp']['manage-burst'] = c_burst
        form.add_row("Burst Photos", c_burst)
        
        c_heic = QComboBox(); c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs['upload-gp']['manage-heic-jpeg'] = c_heic
        form.add_row("HEIC + JPEG Pairs", c_heic)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Advanced Options
        adv_card = Card("Advanced Options")
        form = FormSection()
        
        subhead = QLabel("Takeout Specifics")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        t_album_name = QLineEdit(); t_album_name.setPlaceholderText("Album Name")
        self.inputs['upload-gp']['from-album-name'] = t_album_name
        form.add_row("From Specific Album", t_album_name)
        
        chk_archived = QCheckBox("Include Archived")
        chk_archived.setChecked(True)
        self.inputs['upload-gp']['include-archived'] = chk_archived
        form.addRow("", chk_archived)
        
        chk_trashed = QCheckBox("Include Trashed")
        self.inputs['upload-gp']['include-trashed'] = chk_trashed
        form.addRow("", chk_trashed)
        
        t_partner_album = QLineEdit(); t_partner_album.setPlaceholderText("Album name for partner photos")
        self.inputs['upload-gp']['partner-album'] = t_partner_album
        form.add_row("Partner Shared Album", t_partner_album)
        
        chk_takeout_tag = QCheckBox("Takeout Tag")
        chk_takeout_tag.setChecked(True)
        self.inputs['upload-gp']['takeout-tag'] = chk_takeout_tag
        form.addRow("", chk_takeout_tag)
        
        chk_people_tag = QCheckBox("People Tag")
        chk_people_tag.setChecked(True)
        self.inputs['upload-gp']['people-tag'] = chk_people_tag
        form.addRow("", chk_people_tag)
        
        subhead = QLabel("Tagging")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        t_tags = QLineEdit(); t_tags.setPlaceholderText("vacation, family/reunion")
        self.inputs['upload-gp']['tag'] = t_tags
        form.add_row("Custom Tags (comma separated)", t_tags)
        
        chk_sess = QCheckBox("Session Tag")
        self.inputs['upload-gp']['session-tag'] = chk_sess
        form.addRow("", chk_sess)
        
        subhead = QLabel("Run Behavior")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        c_err = QComboBox(); c_err.addItems(["stop", "continue"])
        self.inputs['upload-gp']['on-errors'] = c_err
        form.add_row("If a file fails", c_err)
        
        chk_pause = QCheckBox("Pause background jobs")
        chk_pause.setChecked(True)
        self.inputs['upload-gp']['pause-jobs'] = chk_pause
        form.addRow("", chk_pause)
        
        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['upload-gp']['skip-ssl'] = chk_ssl
        form.addRow("", chk_ssl)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['upload-gp']['log-level'] = c_log
        form.add_row("Log Level", c_log)
        

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        page.addStretch()
        return page

    def _build_upload_immich_tab(self):
        page = BasePage()
        self.inputs['upload-immich'] = {}

        # Source Config
        card = Card("Source Configuration", required=True)
        form = FormSection()
        t_server = QLineEdit(); t_server.setPlaceholderText("http://old-server:2283")
        self.inputs['upload-immich']['from-server'] = t_server
        form.add_row("Source Server URL", t_server)
        
        t_api = QLineEdit(); t_api.setEchoMode(QLineEdit.Password); t_api.setPlaceholderText("Source API Key")
        self.inputs['upload-immich']['from-api-key'] = t_api
        form.add_row("Source API Key", t_api)
        
        chk_fav = QCheckBox("Only Favorites")
        self.inputs['upload-immich']['from-favorite'] = chk_fav
        form.addRow("", chk_fav)
        
        chk_arch = QCheckBox("Include Archived")
        self.inputs['upload-immich']['from-archived'] = chk_arch
        form.addRow("", chk_arch)
        
        chk_trash = QCheckBox("Include Trashed")
        self.inputs['upload-immich']['from-trash'] = chk_trash
        form.addRow("", chk_trash)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Advanced Options
        adv_card = Card("Advanced Options")
        form = FormSection()
        
        subhead = QLabel("Source Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        d_range = QLineEdit(); d_range.setPlaceholderText("2023-01-01,2023-12-31")
        self.inputs['upload-immich']['from-date-range'] = d_range
        form.add_row("Date Range Filter", d_range)
        
        t_albums = QLineEdit(); t_albums.setPlaceholderText("Family, Travel")
        self.inputs['upload-immich']['from-albums'] = t_albums
        form.add_row("Filter by Albums", t_albums)
        
        s_rating = QSpinBox(); s_rating.setRange(0, 5)
        self.inputs['upload-immich']['from-minimal-rating'] = s_rating
        form.add_row("Minimum Rating", s_rating)
        
        t_people = QLineEdit(); t_people.setPlaceholderText("John, Jane")
        self.inputs['upload-immich']['from-people'] = t_people
        form.add_row("Filter by People", t_people)
        
        t_tags = QLineEdit(); t_tags.setPlaceholderText("vacation, work")
        self.inputs['upload-immich']['from-tags'] = t_tags
        form.add_row("Filter by Tags", t_tags)
        
        subhead = QLabel("Metadata Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        t_city = QLineEdit(); t_city.setPlaceholderText("New York")
        self.inputs['upload-immich']['from-city'] = t_city
        form.add_row("City", t_city)
        
        t_state = QLineEdit(); t_state.setPlaceholderText("NY")
        self.inputs['upload-immich']['from-state'] = t_state
        form.add_row("State", t_state)
        
        t_country = QLineEdit(); t_country.setPlaceholderText("USA")
        self.inputs['upload-immich']['from-country'] = t_country
        form.add_row("Country", t_country)
        
        t_make = QLineEdit(); t_make.setPlaceholderText("Canon")
        self.inputs['upload-immich']['from-make'] = t_make
        form.add_row("Camera Make", t_make)
        
        t_model = QLineEdit(); t_model.setPlaceholderText("EOS R5")
        self.inputs['upload-immich']['from-model'] = t_model
        form.add_row("Camera Model", t_model)
        
        subhead = QLabel("Run Behavior")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        c_err = QComboBox(); c_err.addItems(["stop", "continue"])
        self.inputs['upload-immich']['on-errors'] = c_err
        form.add_row("If a file fails", c_err)
        
        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['upload-immich']['skip-ssl'] = chk_ssl
        form.addRow("", chk_ssl)
        
        chk_ssl_src = QCheckBox("Skip Source SSL Verification")
        self.inputs['upload-immich']['from-skip-ssl'] = chk_ssl_src
        form.addRow("", chk_ssl_src)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['upload-immich']['log-level'] = c_log
        form.add_row("Log Level", c_log)
        

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        page.addStretch()
        return page

    def _build_archive_folder_tab(self):
        page = BasePage()
        self.inputs['archive-folder'] = {}

        # Source Config
        card = Card("Source Configuration", required=True)
        form = FormSection()
        p_edit = QLineEdit(); p_edit.setPlaceholderText("/path/to/files")
        p_edit.setAcceptDrops(True)
        p_edit.dragEnterEvent = self.dragEnterEvent
        p_edit.dropEvent = self.dropEvent
        self.inputs['archive-folder']['path'] = p_edit
        form.add_row("Source Folder Path", p_edit)
        
        browse_action = p_edit.addAction(self.style().standardIcon(QStyle.SP_DirIcon), QLineEdit.TrailingPosition)
        browse_action.triggered.connect(self.browse_local_folder)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Options
        card = Card("Options")
        form = FormSection()
        t_write = QLineEdit(); t_write.setPlaceholderText("/organized-photos")
        self.inputs['archive-folder']['write-to'] = t_write
        form.add_row("Destination Folder", t_write)
        
        c_raw = QComboBox(); c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs['archive-folder']['manage-raw-jpeg'] = c_raw
        form.add_row("Manage RAW+JPEG", c_raw)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Advanced Options
        adv_card = Card("Advanced Options")
        form = FormSection()
        
        subhead = QLabel("Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        d_range = QLineEdit(); d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs['archive-folder']['date-range'] = d_range
        form.add_row("Date Range", d_range)
        
        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['archive-folder']['log-level'] = c_log
        form.add_row("Log Level", c_log)
        

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        page.addStretch()
        return page

    def _build_archive_immich_tab(self):
        page = BasePage()
        self.inputs['archive-immich'] = {}

        # Target Server
        card = Card("Target Server")
        form = FormSection()
        t_server = QLineEdit(); t_server.setEnabled(False); t_server.setText("Not Configured")
        self.inputs['archive-immich']['target-server'] = t_server
        form.add_row("Immich Server URL", t_server, "Update in Configuration tab.")
        card.layout.addLayout(form)
        page.addWidget(card)

        # Options
        card = Card("Options")
        form = FormSection()
        t_write = QLineEdit(); t_write.setPlaceholderText("/backup/photos")
        self.inputs['archive-immich']['write-to'] = t_write
        form.add_row("Destination Folder", t_write)
        
        c_burst = QComboBox(); c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs['archive-immich']['manage-burst'] = c_burst
        form.add_row("Manage Bursts", c_burst)
        
        c_raw = QComboBox(); c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs['archive-immich']['manage-raw-jpeg'] = c_raw
        form.add_row("Manage RAW+JPEG", c_raw)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Advanced Options
        adv_card = Card("Advanced Options")
        form = FormSection()
        
        subhead = QLabel("Source Filtering")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        d_range = QLineEdit(); d_range.setPlaceholderText("2023-01-01,2023-12-31")
        self.inputs['archive-immich']['from-date-range'] = d_range
        form.add_row("Date Range Filter", d_range)
        
        t_albums = QLineEdit(); t_albums.setPlaceholderText("Family, Travel")
        self.inputs['archive-immich']['from-albums'] = t_albums
        form.add_row("Specific Albums", t_albums)
        
        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['archive-immich']['skip-ssl'] = chk_ssl
        form.addRow("", chk_ssl)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['archive-immich']['log-level'] = c_log
        form.add_row("Log Level", c_log)
        

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        page.addStretch()
        return page

    def _build_stack_tab(self):
        page = BasePage()
        self.inputs['stack'] = {}

        # Target Server
        card = Card("Target Server")
        form = FormSection()
        t_server = QLineEdit(); t_server.setEnabled(False); t_server.setText("Not Configured")
        self.inputs['stack']['target-server'] = t_server
        form.add_row("Immich Server URL", t_server, "Update in Configuration tab.")
        card.layout.addLayout(form)
        page.addWidget(card)

        # Options
        card = Card("Options")
        form = FormSection()
        c_burst = QComboBox(); c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs['stack']['manage-burst'] = c_burst
        form.add_row("Manage Bursts", c_burst)
        
        c_raw = QComboBox(); c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs['stack']['manage-raw-jpeg'] = c_raw
        form.add_row("Manage RAW+JPEG", c_raw)
        
        c_heic = QComboBox(); c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs['stack']['manage-heic-jpeg'] = c_heic
        form.add_row("Manage HEIC+JPEG", c_heic)
        card.layout.addLayout(form)
        page.addWidget(card)

        # Advanced Options
        adv_card = Card("Advanced Options")
        form = FormSection()
        
        subhead = QLabel("Detection Tuning")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        t_tz = QLineEdit(); t_tz.setPlaceholderText("America/New_York")
        self.inputs['stack']['time-zone'] = t_tz
        form.add_row("Time Zone Override", t_tz)
        
        chk_epson = QCheckBox("Manage Epson FastFoto")
        self.inputs['stack']['manage-epson'] = chk_epson
        form.addRow("", chk_epson)
        
        subhead = QLabel("Connection & Debug")
        subhead.setObjectName("Subhead")
        form.addRow(subhead)
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['stack']['skip-ssl'] = chk_ssl
        form.addRow("", chk_ssl)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['stack']['log-level'] = c_log
        form.add_row("Log Level", c_log)
        

        adv_card.setVisible(False)
        adv_card.layout.addLayout(form)
        page.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        page.addStretch()
        return page

    # ==========================================
    # UI INTERACTIONS & LOGIC
    # ==========================================

    def toggle_advanced(self, checked):
        self.is_advanced = checked
        self.lbl_mode.setText("Advanced" if checked else "Simple")
        for w in self.adv_frames:
            w.setVisible(checked)

    def switch_tab(self, index, crumb, btn):
        self.stacked_widget.setCurrentIndex(index)
        self.update_header_crumb(crumb)
        
        for w in [self.btn_config, self.btn_upload_folder, self.btn_upload_gp, self.btn_upload_immich, 
                  self.btn_archive_folder, self.btn_archive_immich, self.btn_stack]:
            w.setChecked(False)
        btn.setChecked(True)
        
        self.footer.setVisible(index != 0)
        
        # Update target server fields when switching tabs
        if crumb == "stack" or crumb.startswith("archive"):
            tab_key = crumb.split(" · ")[0] if " · " in crumb else crumb
            if tab_key in self.inputs and 'target-server' in self.inputs[tab_key]:
                srv = self.inputs['config']['server'].text()
                self.inputs[tab_key]['target-server'].setText(srv if srv else "Not Configured")

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

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        target = self.sender() if self.sender() else event.widget()
        if isinstance(target, QLineEdit):
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            target.setText(paths[0])
            event.acceptProposedAction()

    def browse_takeout_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Extracted Folder")
        if folder: self.inputs['upload-gp']['path'].setText(folder)

    def browse_local_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Upload Folder")
        if folder:
            if self.stacked_widget.currentIndex() == 1:
                self.inputs['upload-folder']['path'].setText(folder)
            elif self.stacked_widget.currentIndex() == 4:
                self.inputs['archive-folder']['path'].setText(folder)

    def validate_inputs(self):
        srv = self.inputs['config']['server'].text()
        api = self.inputs['config']['api_key'].text()
        if not re.match(r"^https?://.+", srv) or not api:
            return False
        return True

    def update_status(self):
        if self.validate_inputs():
            self.status_card.set_server("ok",  "Server: Ready")
            self.btn_run.setEnabled(True)
            self.btn_dry_run.setEnabled(True)
        else:
            self.status_card.set_server("err", "Server: Not Set")
            self.btn_run.setEnabled(False)
            self.btn_dry_run.setEnabled(False)
            
        # Update target servers live
        srv = self.inputs.get('config', {}).get('server').text() if 'config' in self.inputs and 'server' in self.inputs['config'] else ""
        for t in ['archive-immich', 'stack']:
            if t in self.inputs and 'target-server' in self.inputs[t]:
                self.inputs[t]['target-server'].setText(srv if srv else "Not Configured")

    # ==========================================
    # COMMAND BUILDER LOGIC
    # ==========================================
    def get_global_options(self):
        # Not used in the new per-tab structure, kept for compatibility
        return []

    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    def build_command(self, dry_run):
        idx = self.stacked_widget.currentIndex()
        tab_keys = ["config", "upload-folder", "upload-gp", "upload-immich", "archive-folder", "archive-immich", "stack"]
        tab_key = tab_keys[idx]
        
        if tab_key == "config":
            return []
            
        c = self.inputs[tab_key]
        
        global_opts = ["--no-ui"]  # Always disable interactive UI
        cmd = []
        cmd_opts = []
        path_opt = []
        
        # Extract global log-level from the current tab
        if 'log-level' in c and c['log-level'].currentText() != "INFO":
            global_opts.append(f"--log-level={c['log-level'].currentText()}")
        
        # Base command
        if tab_key == "upload-folder": cmd = ["upload", "from-folder"]
        elif tab_key == "upload-gp": cmd = ["upload", "from-google-photos"]
        elif tab_key == "upload-immich": cmd = ["upload", "from-immich"]
        elif tab_key == "archive-folder": cmd = ["archive", "from-folder"]
        elif tab_key == "archive-immich": cmd = ["archive", "from-immich"]
        elif tab_key == "stack": cmd = ["stack"]
        
        # Server options (except for local archive)
        if tab_key != "archive-folder":
            srv = self.inputs['config']['server'].text()
            api = self.inputs['config']['api_key'].text()
            if srv: cmd_opts.append(f"--server={srv}")
            if api: cmd_opts.append(f"--api-key={api}")
            
        # Run behavior (from config advanced)
        conc = self.inputs['config']['concurrent'].value()
        if conc != 2: cmd_opts.append(f"--concurrent-tasks={conc}")
        
        if 'pause-jobs' in c:
            if not c['pause-jobs'].isChecked(): cmd_opts.append("--pause-immich-jobs=false")
        elif not self.inputs['config']['pause_jobs'].isChecked():
            cmd_opts.append("--pause-immich-jobs=false")
            
        if 'on-errors' in c:
            if c['on-errors'].currentText() != "stop": cmd_opts.append(f"--on-errors={c['on-errors'].currentText()}")
        elif self.inputs['config']['on_errors'].currentText() != "stop":
            cmd_opts.append(f"--on-errors={self.inputs['config']['on_errors'].currentText()}")

        # Tab specific options
        if tab_key == "upload-folder":
            if c['include-type'].currentText() != "all": cmd_opts.append(f"--include-type={c['include-type'].currentText()}")
            if c['folder-album'].currentText() != "NONE": cmd_opts.append(f"--folder-as-album={c['folder-album'].currentText()}")
            if c['into-album'].text(): cmd_opts.append(f'--into-album={c["into-album"].text()}')
            if c['overwrite'].isChecked(): cmd_opts.append("--overwrite")
            if c['manage-burst'].currentText() != "NoStack": cmd_opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
            if c['manage-raw-jpeg'].currentText() != "NoStack": cmd_opts.append(f"--manage-raw-jpeg={c['manage-raw-jpeg'].currentText()}")
            if c['manage-heic-jpeg'].currentText() != "NoStack": cmd_opts.append(f"--manage-heic-jpeg={c['manage-heic-jpeg'].currentText()}")
            
            # Advanced
            if c['date-range'].text(): cmd_opts.append(f'--date-range={c["date-range"].text()}')
            if c['include-ext'].text(): cmd_opts.append(f'--include-extensions={c["include-ext"].text()}')
            if c['exclude-ext'].text(): cmd_opts.append(f'--exclude-extensions={c["exclude-ext"].text()}')
            for line in c['ban-file'].toPlainText().split('\n'):
                if line.strip(): cmd_opts.append(f'--ban-file="{line.strip()}"')
            if c['ignore-sidecar'].isChecked(): cmd_opts.append("--ignore-sidecar-files")
            if not c['date-from-name'].isChecked(): cmd_opts.append("--date-from-name=false")
            
            if c['tag'].text():
                for t in c['tag'].text().split(','):
                    if t.strip(): cmd_opts.append(f'--tag="{t.strip()}"')
            if c['session-tag'].isChecked(): cmd_opts.append("--session-tag")
            if c['folder-tags'].isChecked(): cmd_opts.append("--folder-as-tags")
            
            if c['skip-ssl'].isChecked(): cmd_opts.append("--skip-verify-ssl")
            if c['api-trace'].isChecked(): cmd_opts.append("--api-trace")
            
            if c['path'].text(): path_opt.append(f'"{c["path"].text()}"')

        elif tab_key == "upload-gp":
            if c['include-type'].currentText() != "all": cmd_opts.append(f"--include-type={c['include-type'].currentText()}")
            if c['into-album'].text(): cmd_opts.append(f'--into-album={c["into-album"].text()}')
            if c['include-unmatched'].isChecked(): cmd_opts.append("--include-unmatched=true")
            if not c['include-partner'].isChecked(): cmd_opts.append("--include-partner=false")
            if not c['sync-albums'].isChecked(): cmd_opts.append("--sync-albums=false")
            if c['manage-burst'].currentText() != "NoStack": cmd_opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
            if c['manage-heic-jpeg'].currentText() != "NoStack": cmd_opts.append(f"--manage-heic-jpeg={c['manage-heic-jpeg'].currentText()}")
            
            # Advanced
            if c['from-album-name'].text(): cmd_opts.append(f'--from-album-name={c["from-album-name"].text()}')
            if not c['include-archived'].isChecked(): cmd_opts.append("--include-archived=false")
            if c['include-trashed'].isChecked(): cmd_opts.append("--include-trashed=true")
            if c['partner-album'].text(): cmd_opts.append(f'--partner-shared-album={c["partner-album"].text()}')
            if not c['takeout-tag'].isChecked(): cmd_opts.append("--takeout-tag=false")
            if not c['people-tag'].isChecked(): cmd_opts.append("--people-tag=false")
            
            if c['tag'].text():
                for t in c['tag'].text().split(','):
                    if t.strip(): cmd_opts.append(f'--tag="{t.strip()}"')
            if c['session-tag'].isChecked(): cmd_opts.append("--session-tag")
            
            if c['skip-ssl'].isChecked(): cmd_opts.append("--skip-verify-ssl")
            
            if c['path'].text(): path_opt.append(f'"{c["path"].text()}"')

        elif tab_key == "upload-immich":
            if c['from-server'].text(): cmd_opts.append(f"--from-server={c['from-server'].text()}")
            if c['from-api-key'].text(): cmd_opts.append(f"--from-api-key={c['from-api-key'].text()}")
            if c['from-favorite'].isChecked(): cmd_opts.append("--from-favorite=true")
            if c['from-archived'].isChecked(): cmd_opts.append("--from-archived=true")
            if c['from-trash'].isChecked(): cmd_opts.append("--from-trash=true")
            
            # Advanced
            if c['from-date-range'].text(): cmd_opts.append(f'--from-date-range={c["from-date-range"].text()}')
            if c['from-albums'].text():
                for a in c['from-albums'].text().split(','):
                    if a.strip(): cmd_opts.append(f'--from-albums="{a.strip()}"')
            if c['from-minimal-rating'].value() > 0: cmd_opts.append(f"--from-minimal-rating={c['from-minimal-rating'].value()}")
            if c['from-people'].text():
                for p in c['from-people'].text().split(','):
                    if p.strip(): cmd_opts.append(f'--from-people="{p.strip()}"')
            if c['from-tags'].text():
                for t in c['from-tags'].text().split(','):
                    if t.strip(): cmd_opts.append(f'--from-tags="{t.strip()}"')
                    
            if c['from-city'].text(): cmd_opts.append(f'--from-city={c["from-city"].text()}')
            if c['from-state'].text(): cmd_opts.append(f'--from-state={c["from-state"].text()}')
            if c['from-country'].text(): cmd_opts.append(f'--from-country={c["from-country"].text()}')
            if c['from-make'].text(): cmd_opts.append(f'--from-make={c["from-make"].text()}')
            if c['from-model'].text(): cmd_opts.append(f'--from-model={c["from-model"].text()}')
            
            if c['skip-ssl'].isChecked(): cmd_opts.append("--skip-verify-ssl")
            if c['from-skip-ssl'].isChecked(): cmd_opts.append("--from-skip-verify-ssl")

        elif tab_key == "archive-folder":
            if c['write-to'].text(): cmd_opts.append(f'--write-to-folder={c["write-to"].text()}')
            if c['manage-raw-jpeg'].currentText() != "NoStack": cmd_opts.append(f"--manage-raw-jpeg={c['manage-raw-jpeg'].currentText()}")
            
            # Advanced
            if c['date-range'].text(): cmd_opts.append(f'--date-range={c["date-range"].text()}')
            
            if c['path'].text(): path_opt.append(f'"{c["path"].text()}"')

        elif tab_key == "archive-immich":
            if c['write-to'].text(): cmd_opts.append(f'--write-to-folder={c["write-to"].text()}')
            if c['manage-burst'].currentText() != "NoStack": cmd_opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
            if c['manage-raw-jpeg'].currentText() != "NoStack": cmd_opts.append(f"--manage-raw-jpeg={c['manage-raw-jpeg'].currentText()}")
            
            # Advanced
            if c['from-date-range'].text(): cmd_opts.append(f'--from-date-range={c["from-date-range"].text()}')
            if c['from-albums'].text():
                for a in c['from-albums'].text().split(','):
                    if a.strip(): cmd_opts.append(f'--from-albums="{a.strip()}"')
                    
            if c['skip-ssl'].isChecked(): cmd_opts.append("--skip-verify-ssl")

        elif tab_key == "stack":
            if c['manage-burst'].currentText() != "NoStack": cmd_opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
            if c['manage-raw-jpeg'].currentText() != "NoStack": cmd_opts.append(f"--manage-raw-jpeg={c['manage-raw-jpeg'].currentText()}")
            if c['manage-heic-jpeg'].currentText() != "NoStack": cmd_opts.append(f"--manage-heic-jpeg={c['manage-heic-jpeg'].currentText()}")
            
            # Advanced
            if c['time-zone'].text(): cmd_opts.append(f'--time-zone={c["time-zone"].text()}')
            if c['manage-epson'].isChecked(): cmd_opts.append("--manage-epson-fastfoto=true")
            
            if c['skip-ssl'].isChecked(): cmd_opts.append("--skip-verify-ssl")

        if dry_run:
            if "--dry-run" not in cmd_opts: cmd_opts.append("--dry-run")
        else:
            if "--dry-run" in cmd_opts: cmd_opts.remove("--dry-run")
            
        return global_opts + cmd + cmd_opts + path_opt

    def show_confirm_dialog(self, is_dry_run):
        if self.stacked_widget.currentIndex() == 0: return

        cmd_parts = self.build_command(is_dry_run)
        binary_path = self.binary_path if hasattr(self, "binary_path") else "./immich-go"
        cmd_str = f"{binary_path} " + " ".join(shlex.quote(p) if not p.startswith('"') else p for p in cmd_parts)

        dlg = QDialog(self)
        dlg.setWindowTitle("Confirm Execution")
        dlg.setModal(True)
        dlg.resize(600, 300)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 22, 22, 22)
        
        kicker = QLabel("Dry run" if is_dry_run else "Live execution")
        kicker.setObjectName("DlgKicker")
        layout.addWidget(kicker)
        
        title = QLabel("This is what will run")
        title.setObjectName("DlgTitle")
        layout.addWidget(title)
        
        desc = QLabel("A dry run simulates the action. No files are changed." if is_dry_run else "This executes the real command.")
        desc.setObjectName("DlgDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(16)
        
        cmd_block = QPlainTextEdit()
        cmd_block.setObjectName("CmdBlock")
        cmd_block.setPlainText(cmd_str)
        cmd_block.setReadOnly(True)
        layout.addWidget(cmd_block)
        
        layout.addSpacing(16)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
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
            self.run_command(cmd_parts)

    # ==========================================
    # BACKEND LOGIC (Intact from original)
    # ==========================================
    @staticmethod
    def get_latest_release_info():
        try:
            api_url = "https://api.github.com/repos/simulot/immich-go/releases/latest"
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()['tag_name']
        except Exception as e:
            print(f"Failed to fetch release information: {e}")
            return None

    def get_download_url(self, version=None):
        os_name = sys.platform
        arch = platform.machine().lower()
        download_mapping = {
            ('win32', 'amd64'): 'immich-go_Windows_x86_64.zip',
            ('win32', 'x86_64'): 'immich-go_Windows_x86_64.zip',
            ('win32', 'arm64'): 'immich-go_Windows_arm64.zip',
            ('darwin', 'x86_64'): 'immich-go_Darwin_x86_64.tar.gz',
            ('darwin', 'arm64'): 'immich-go_Darwin_arm64.tar.gz',
            ('linux', 'x86_64'): 'immich-go_Linux_x86_64.tar.gz',
            ('linux', 'arm64'): 'immich-go_Linux_arm64.tar.gz',
            ('freebsd', 'x86_64'): 'immich-go_Freebsd_x86_64.tar.gz'
        }
        if arch in ['x64', 'x86_64']: arch = 'x86_64'
        key = (os_name, arch)
        if key in download_mapping:
            if version is None: version = self.get_latest_release_info() or '0.22.1'
            filename = download_mapping[key]
            return f'https://github.com/simulot/immich-go/releases/download/{version}/{filename}'
        return None

    def check_binary_version(self):
        binary_folder = os.path.abspath(os.path.join(os.getcwd(), "immich-go"))
        binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        self.binary_path = os.path.join(binary_folder, binary_filename)

        if not os.path.exists(self.binary_path):
            if hasattr(self, 'lbl_binary_version'):
                self.lbl_binary_version.setText("Current Version: Not found")
                self.lbl_binary_path.setText(self.binary_path)
                self.current_version = "Not found"
            if hasattr(self, 'status_card'):
                self.status_card.set_binary("err", "Binary: Missing")
            if hasattr(self, 'btn_check_updates'):
                self.btn_check_updates.setText("Download Immich-Go")
            return
            
        try:
            result = subprocess.run([self.binary_path, "version"], capture_output=True, text=True, timeout=2)
            version_text = result.stdout.strip() if result.stdout else "Unknown version"
            if "," in version_text: version_text = version_text.split(",")[0]
            if hasattr(self, 'lbl_binary_version'):
                self.lbl_binary_version.setText(f"Current Version: {version_text}")
                self.lbl_binary_path.setText(self.binary_path)
                self.current_version = version_text
            if hasattr(self, 'status_card'):
                self.status_card.set_binary("ok",  "Binary: Ready")
            if hasattr(self, 'btn_check_updates'):
                self.btn_check_updates.setText("Check for Updates")
        except Exception:
            if hasattr(self, 'lbl_binary_version'):
                self.lbl_binary_version.setText("Current Version: Unknown")
                self.lbl_binary_path.setText(self.binary_path)
                self.current_version = "Unknown"
            if hasattr(self, 'status_card'):
                self.status_card.set_binary("ok",  "Binary: Ready")
            if hasattr(self, 'btn_check_updates'):
                self.btn_check_updates.setText("Check for Updates")

    def check_for_updates(self):
        self.check_binary_version()
        latest_version = self.get_latest_release_info()
        if not latest_version:
            QMessageBox.warning(self, "Update Check", "Failed to fetch the latest version information from GitHub.")
            return
            
        current_version = getattr(self, "current_version", "Unknown")
                
        if current_version == "Not found":
            reply = QMessageBox.question(self, "Download Immich-Go", 
                f"The latest version is {latest_version}.\n\nDo you want to download and install it now?",
                QMessageBox.Yes | QMessageBox.No)
        else:
            reply = QMessageBox.question(self, "Update Check", 
                f"Latest version: {latest_version}\nCurrent version: {current_version}\n\nDo you want to download and install the latest version?",
                QMessageBox.Yes | QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            self.update_binary(force_download=True)

    def update_binary(self, force_download=False):
        binary_folder = os.path.abspath(os.path.join(os.getcwd(), "immich-go"))
        if not os.path.exists(binary_folder):
            os.makedirs(binary_folder)

        # Determine correct binary name for OS
        binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        binary_path = os.path.join(binary_folder, binary_filename)
        self.binary_path = binary_path

        # Check if binary exists
        if not os.path.exists(binary_path) or force_download:
            # Create download progress dialog
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Downloading Immich-Go")
            progress_dialog.setFixedWidth(400)

            layout = QVBoxLayout()

            # Status label
            status_label = QLabel("Downloading Immich-Go binary...")
            layout.addWidget(status_label)

            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            layout.addWidget(progress_bar)

            # Cancel button
            cancel_button = QPushButton("Cancel")
            layout.addWidget(cancel_button)

            progress_dialog.setLayout(layout)

            # Prevent closing the dialog
            progress_dialog.setWindowFlags(progress_dialog.windowFlags() & ~Qt.WindowCloseButtonHint)

            # Thread for download to keep UI responsive
            # ==========================================
            # THREAD WORKERS
            # ==========================================
            class DownloadThread(QThread):
                download_progress = Signal(int)
                download_complete = Signal(bytes)
                download_error = Signal(str)

                def __init__(self, download_url):
                    super().__init__()
                    self.download_url = download_url

                def run(self):
                    try:
                        response = requests.get(self.download_url, stream=True)
                        response.raise_for_status()

                        total_size = int(response.headers.get('content-length', 0))
                        block_size = 1024  # 1 Kibibyte
                        downloaded_size = 0

                        # Buffer to store downloaded content
                        content = io.BytesIO()

                        for data in response.iter_content(block_size):
                            downloaded_size += len(data)
                            content.write(data)

                            # Calculate and emit progress
                            if total_size > 0:
                                progress = int((downloaded_size / total_size) * 100)
                                self.download_progress.emit(progress)

                        self.download_complete.emit(content.getvalue())

                    except Exception as e:
                        self.download_error.emit(str(e))

            # Set up download thread
            try:
                download_url = self.get_download_url()

                if not download_url:
                    raise ValueError("Could not determine download URL for your system")

                download_thread = DownloadThread(download_url)

                # Connect signals
                def update_progress(value):
                    progress_bar.setValue(value)

                def handle_download_complete(content):
                    progress_dialog.accept()

                    # Determine extraction method based on file type
                    try:
                        if download_url.endswith('.zip'):
                            import zipfile
                            with zipfile.ZipFile(io.BytesIO(content)) as z:
                                # Extract the binary, handling different archive structures
                                for filename in z.namelist():
                                    if filename.endswith('immich-go') or filename.endswith('immich-go.exe'):
                                        with z.open(filename) as source, open(binary_path, 'wb') as target:
                                            target.write(source.read())
                                        break
                        elif download_url.endswith('.tar.gz'):
                            import tarfile
                            with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as tar:
                                # Extract the binary, handling different archive structures
                                for member in tar.getmembers():
                                    if member.name.endswith('immich-go') or member.name.endswith('immich-go.exe'):
                                        source = tar.extractfile(member)
                                        with open(binary_path, 'wb') as target:
                                            target.write(source.read())
                                        break
                        else:
                            raise ValueError("Unsupported archive type")

                        if sys.platform.startswith("win"):
                            self.check_binary_version()

                        # Set executable permissions for non-Windows systems
                        if not sys.platform.startswith("win"):
                            os.chmod(binary_path, 0o755)
                            self.check_binary_version()

                    except Exception as extraction_error:
                        QMessageBox.critical(self, "Extraction Error",
                            f"Failed to extract binary: {str(extraction_error)}\n\n" "Please download manually from GitHub.")

                def handle_download_error(error):
                    progress_dialog.reject()
                    # If download fails, show manual download dialog
                    error_dialog = QDialog(self)
                    error_dialog.setWindowTitle("Binary Download Failed")
                    error_dialog.setFixedWidth(450)

                    layout = QVBoxLayout()

                    # Error message
                    error_label = QLabel("Automatic binary download failed")
                    error_label.setStyleSheet("color: red; font-weight: bold;")
                    layout.addWidget(error_label)

                    # Detailed error information
                    details_label = QLabel(f"Error: {error}")
                    details_label.setWordWrap(True)
                    layout.addWidget(details_label)

                    # Manual download instructions
                    version = self.get_latest_release_info() or "latest"
                    download_url = "https://github.com/simulot/immich-go/releases/tag/" + version

                    instructions_label = QLabel(
                        "Please download the binary manually:\n\n" f"1. Visit: {download_url}\n" f"2. Download the appropriate binary for your system\n" f"3. Place it in: {binary_folder}\n" "4. Rename to 'immich-go' (or 'immich-go.exe' on Windows)\n" "5. Ensure it has executable permissions"
                    )
                    instructions_label.setWordWrap(True)
                    layout.addWidget(instructions_label)

                    # URL copy button
                    url_layout = QHBoxLayout()
                    url_edit = QLineEdit(download_url)
                    url_edit.setReadOnly(True)
                    copy_btn = QPushButton("Copy URL")
                    copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(download_url))
                    url_layout.addWidget(url_edit)
                    url_layout.addWidget(copy_btn)
                    layout.addLayout(url_layout)

                    # Open browser button
                    open_btn = QPushButton("Open Download Page")
                    open_btn.clicked.connect(lambda: webbrowser.open(download_url))
                    layout.addWidget(open_btn)

                    error_dialog.setLayout(layout)
                    error_dialog.exec()

                # Connect thread signals
                download_thread.download_progress.connect(update_progress)
                download_thread.download_complete.connect(handle_download_complete)
                download_thread.download_error.connect(handle_download_error)

                # Setup cancel button
                def cancel_download():
                    download_thread.terminate()
                    progress_dialog.reject()

                cancel_button.clicked.connect(cancel_download)

                # Start the download
                progress_dialog.show()
                download_thread.start()

                # Block until dialog is closed
                progress_dialog.exec()

            except Exception as e:
                QMessageBox.critical(self, "Download Error",
                    f"Failed to initiate download: {str(e)}\n\n" "Please download manually from GitHub.")
                return False

        return True


    def run_command(self, command_parts=None):
        if command_parts is None: command_parts = []
        if not hasattr(self, 'binary_path') or not os.path.exists(self.binary_path):
            if not self.update_binary():
                QMessageBox.critical(self, "Error", "Immich-Go binary is missing or not executable.")
                return

        command = [self.binary_path] + command_parts

        try:
            self.btn_run.setDisabled(True)
            self.btn_dry_run.setDisabled(True)

            if sys.platform.startswith("win"):
                cmd_string = subprocess.list2cmdline(command)
                proc = subprocess.Popen(['cmd', '/c', 'start', 'cmd', '/k', cmd_string], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                self.running_process = proc.pid
            elif sys.platform.startswith("darwin"):
                apple_script = f'tell application "Terminal" to do script "{shlex.join(command)}; exec bash"'
                proc = subprocess.Popen(["osascript", "-e", apple_script])
                self.running_process = proc
            else:
                terminals = [
                    ("gnome-terminal", "--", "bash", "-c", f"{shlex.join(command)}; exec bash"),
                    ("konsole", "-e", "bash", "-c", f"{shlex.join(command)}; exec bash"),
                    ("xfce4-terminal", "-e", "bash", "-c", f"{shlex.join(command)}; exec bash"),
                    ("xterm", "-hold", "-e", shlex.join(command))
                ]
                for term in terminals:
                    try:
                        proc = subprocess.Popen(term)
                        self.running_process = proc
                        break
                    except FileNotFoundError: continue
                else:
                    QMessageBox.critical(self, "Error", "No suitable terminal emulator found.")
                    self.btn_run.setDisabled(False)
                    self.btn_dry_run.setDisabled(False)
                    return

            self.check_process_timer = QTimer()
            self.check_process_timer.timeout.connect(self.check_if_process_running)
            self.check_process_timer.start(1000)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run command: {e}")
            self.btn_run.setDisabled(False)
            self.btn_dry_run.setDisabled(False)

    def check_if_process_running(self):
        still_running = False
        if sys.platform.startswith("win"):
            if psutil.pid_exists(self.running_process): still_running = True
        else:
            if hasattr(self.running_process, "poll") and self.running_process.poll() is None: still_running = True

        if still_running:
            self.status_card.set_server("warn", "Running... Close terminal to continue.")
        else:
            self.check_process_timer.stop()
            self.running_process = None
            self.btn_run.setDisabled(False)
            self.btn_dry_run.setDisabled(False)
            self.update_status()

    # ==========================================
    # PERSISTENCE
    # ==========================================
    def save_configuration(self):
        self.settings.setValue("server_url", self.inputs['config']['server'].text())
        self.settings.setValue("api_key", self.inputs['config']['api_key'].text())
        if hasattr(self, "theme_mode_combo"):
            self.settings.setValue("theme_mode", self.theme_mode_combo.currentText())
        QMessageBox.information(self, "Saved", "Configuration saved successfully.")

    def load_configuration(self):
        self.inputs['config']['server'].setText(self.settings.value("server_url", ""))
        self.inputs['config']['api_key'].setText(self.settings.value("api_key", ""))
        theme_mode = self.settings.value("theme_mode", THEME_SYSTEM)
        if hasattr(self, "theme_mode_combo"):
            self.theme_mode_combo.blockSignals(True)
            self.theme_mode_combo.setCurrentText(theme_mode)
            self.theme_mode_combo.blockSignals(False)
        self.theme_mode = theme_mode
        self.apply_theme(theme_mode)

    def open_github_link(self):
        webbrowser.open("https://github.com/simulot/immich-go")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Build a font stack that degrades gracefully across platforms and
    # includes an emoji-capable fallback so icon glyphs (📁 📦 🔄 etc.)
    # don't render as empty "tofu" boxes when the primary UI font has
    # no color-emoji coverage (common on Linux).
    base_font = QFont()
    base_font.setFamilies([
        "Segoe UI", "Segoe UI Emoji",   # Windows
        "Helvetica Neue", "Apple Color Emoji",  # macOS
        "Noto Sans", "Noto Color Emoji", "DejaVu Sans", "Ubuntu",  # Linux
        "sans-serif",
    ])
    base_font.setPointSize(10)
    app.setFont(base_font)
    window = ImmichGoGUI()
    window.show()
    sys.exit(app.exec())