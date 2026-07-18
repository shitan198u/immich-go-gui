import sys
import os
import re
import io
import subprocess
import shlex
import platform
import webbrowser
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QCheckBox, QComboBox, QPushButton, QFileDialog,
    QPlainTextEdit, QStackedWidget, QFrame, QSizePolicy,
    QScrollArea, QMessageBox, QDialog, QProgressBar, QSpinBox
)
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPen, QColor, QBrush, QFont
from PySide6.QtCore import Qt, QDate, QTimer, QUrl, QSettings, QThread, Signal
import psutil
import requests

# ==========================================
# STYLESHEETS (Dark / Light Themes)
# ==========================================
DARK_THEME = """
    QMainWindow, QWidget { background-color: #0b0d0e; color: #ece7dd; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
    
    /* Header & Footer */
    #HeaderFrame, #FooterFrame { background-color: rgba(11,13,14,0.95); border: none; }
    #HeaderFrame { border-bottom: 1px solid #2a3034; }
    #FooterFrame { border-top: 1px solid #2a3034; }
    QLabel#AppName { font-family: 'Consolas', monospace; font-weight: 600; font-size: 16px; color: #ece7dd; }
    QLabel#Crumb { font-family: 'Consolas', monospace; font-size: 12px; color: #8b9298; }
    QLabel#ModeLabel { font-family: 'Consolas', monospace; font-size: 12px; color: #8b9298; padding-right: 8px; }
    
    /* Sidebar */
    #Sidebar { background-color: #15181b; border-right: 1px solid #2a3034; }
    QPushButton#NavBtn { text-align: left; padding: 10px 12px; font-size: 14px; font-weight: 500; color: #8b9298; border: 1px solid transparent; border-radius: 6px; background: transparent; }
    QPushButton#NavBtn:hover { background-color: #1d2226; color: #ece7dd; }
    QPushButton#NavBtn:checked { background-color: #23282c; color: #4fb3a4; border: 1px solid #3a4045; }
    QLabel#NavTitle { font-family: 'Consolas'; font-size: 10px; font-weight: 600; color: #5b6267; padding: 0 12px; margin-top: 16px; }
    
    #StatusFrame { border-top: 1px solid #2a3034; padding: 16px; background-color: #15181b; }
    QLabel#StatusText { font-size: 12px; color: #8b9298; }
    QPushButton#ActionLink { color: #4fb3a4; background: transparent; border: none; font-size: 11px; font-family: 'Consolas'; text-align: left; padding: 0; }
    QPushButton#ActionLink:hover { color: #6fd6c5; }
    
    /* Cards & Form Elements */
    QFrame#Card { background-color: #15181b; border: 1px solid #2a3034; border-radius: 8px; }
    QLabel#CardTitle { font-family: 'Consolas'; font-size: 12px; font-weight: 600; color: #8b9298; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
    QLabel#ReqBadge { font-size: 10px; color: #e1512e; background-color: rgba(225,81,46,0.08); border: 1px solid #4a2318; padding: 2px 6px; border-radius: 4px; font-family: 'Segoe UI'; font-weight: normal; text-transform: none; }
    QLabel#Subhead { font-family: 'Consolas'; font-size: 11px; color: #5b6267; text-transform: uppercase; letter-spacing: 1px; margin-top: 16px; margin-bottom: 8px; border-top: 1px solid #2a3034; padding-top: 12px; }
    
    QLabel#FieldLabel { font-size: 13px; font-weight: 500; color: #ece7dd; }
    QLabel#Hint { font-size: 12px; color: #5b6267; }
    
    QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {
        background-color: #1d2226; border: 1px solid #3a4045; color: #ece7dd; 
        padding: 9px 11px; border-radius: 6px; font-size: 14px;
        selection-background-color: #4fb3a4;
    }
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QPlainTextEdit:hover { border-color: #5b6267; }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus { border-color: #4fb3a4; background-color: #23282c; }
    QLineEdit:disabled { background-color: #15181b; color: #5b6267; border-color: #2a3034; }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView { background-color: #1d2226; color: #ece7dd; selection-background-color: #4fb3a4; border: 1px solid #3a4045; }
    
    /* Buttons */
    QPushButton#BtnRun { background-color: #e1512e; color: #ffffff; border: none; border-radius: 7px; padding: 10px 18px; font-weight: 600; font-size: 13.5px; }
    QPushButton#BtnRun:hover { background-color: #f1603d; }
    QPushButton#BtnRun:disabled { background: #4a2318; color: #8b9298; }
    
    QPushButton#BtnPreview { background-color: #1b3733; color: #6fd6c5; border: 1px solid #4fb3a4; border-radius: 7px; padding: 10px 18px; font-weight: 600; font-size: 13.5px; }
    QPushButton#BtnPreview:hover { background-color: #234a42; }
    QPushButton#BtnPreview:disabled { background: #15181b; color: #5b6267; border-color: #2a3034; }
    
    QPushButton { background-color: #2a3034; color: #ece7dd; border: none; border-radius: 6px; padding: 8px 16px; }
    QPushButton:hover { background-color: #3a4045; }
    
    /* Dialog */
    QDialog { background-color: #15181b; color: #ece7dd; border: 1px solid #3a4045; border-radius: 12px; }
    QLabel#DlgKicker { font-family: 'Consolas'; font-size: 11px; color: #5b6267; text-transform: uppercase; letter-spacing: 1px; }
    QLabel#DlgTitle { font-size: 18px; font-weight: 600; }
    QLabel#DlgDesc { font-size: 13px; color: #8b9298; }
    QPlainTextEdit#CmdBlock { background-color: #08090a; border: 1px solid #2a3034; color: #ece7dd; font-family: 'Consolas'; font-size: 13px; border-radius: 8px; padding: 16px; }
    
    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { border: none; background: #0b0d0e; width: 8px; margin: 0; }
    QScrollBar::handle:vertical { background: #3a4045; min-height: 20px; border-radius: 4px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    
    QMenu { background-color: #15181b; color: #ece7dd; border: 1px solid #3a4045; }
    QMenu::item:selected { background-color: #23282c; }
"""

LIGHT_THEME = """
    QMainWindow, QWidget { background-color: #f4f5f7; color: #1f2937; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
    
    #HeaderFrame, #FooterFrame { background-color: rgba(248,249,250,0.95); border: none; }
    #HeaderFrame { border-bottom: 1px solid #d1d5db; }
    #FooterFrame { border-top: 1px solid #d1d5db; }
    QLabel#AppName { font-family: 'Consolas', monospace; font-weight: 600; font-size: 16px; color: #1f2937; }
    QLabel#Crumb { font-family: 'Consolas', monospace; font-size: 12px; color: #4b5563; }
    QLabel#ModeLabel { font-family: 'Consolas', monospace; font-size: 12px; color: #4b5563; padding-right: 8px; }
    
    #Sidebar { background-color: #ffffff; border-right: 1px solid #d1d5db; }
    QPushButton#NavBtn { text-align: left; padding: 10px 12px; font-size: 14px; font-weight: 500; color: #4b5563; border: 1px solid transparent; border-radius: 6px; background: transparent; }
    QPushButton#NavBtn:hover { background-color: #f8f9fa; color: #1f2937; }
    QPushButton#NavBtn:checked { background-color: #eef0f2; color: #0f766e; border: 1px solid #9ca3af; }
    QLabel#NavTitle { font-family: 'Consolas'; font-size: 10px; font-weight: 600; color: #6b7280; padding: 0 12px; margin-top: 16px; }
    
    #StatusFrame { border-top: 1px solid #d1d5db; padding: 16px; background-color: #ffffff; }
    QLabel#StatusText { font-size: 12px; color: #4b5563; }
    QPushButton#ActionLink { color: #0f766e; background: transparent; border: none; font-size: 11px; font-family: 'Consolas'; text-align: left; padding: 0; }
    QPushButton#ActionLink:hover { color: #14b8a6; }
    
    QFrame#Card { background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 8px; }
    QLabel#CardTitle { font-family: 'Consolas'; font-size: 12px; font-weight: 600; color: #4b5563; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
    QLabel#ReqBadge { font-size: 10px; color: #c2410c; background-color: #fed7aa; border: 1px solid #fb923c; padding: 2px 6px; border-radius: 4px; font-family: 'Segoe UI'; font-weight: normal; text-transform: none; }
    QLabel#Subhead { font-family: 'Consolas'; font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; margin-top: 16px; margin-bottom: 8px; border-top: 1px solid #d1d5db; padding-top: 12px; }
    
    QLabel#FieldLabel { font-size: 13px; font-weight: 500; color: #1f2937; }
    QLabel#Hint { font-size: 12px; color: #6b7280; }
    
    QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {
        background-color: #f8f9fa; border: 1px solid #9ca3af; color: #1f2937; 
        padding: 9px 11px; border-radius: 6px; font-size: 14px;
        selection-background-color: #0f766e;
    }
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QPlainTextEdit:hover { border-color: #6b7280; }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus { border-color: #0f766e; background-color: #eef0f2; }
    QLineEdit:disabled { background-color: #eef0f2; color: #6b7280; border-color: #d1d5db; }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView { background-color: #f8f9fa; color: #1f2937; selection-background-color: #0f766e; border: 1px solid #9ca3af; }
    
    QPushButton#BtnRun { background-color: #c2410c; color: #ffffff; border: none; border-radius: 7px; padding: 10px 18px; font-weight: 600; font-size: 13.5px; }
    QPushButton#BtnRun:hover { background-color: #ea580c; }
    QPushButton#BtnRun:disabled { background: #fed7aa; color: #c2410c; }
    
    QPushButton#BtnPreview { background-color: #ccfbf1; color: #0f766e; border: 1px solid #14b8a6; border-radius: 7px; padding: 10px 18px; font-weight: 600; font-size: 13.5px; }
    QPushButton#BtnPreview:hover { background-color: #99f6e4; }
    QPushButton#BtnPreview:disabled { background: #f8f9fa; color: #6b7280; border-color: #d1d5db; }
    
    QPushButton { background-color: #eef0f2; color: #1f2937; border: none; border-radius: 6px; padding: 8px 16px; }
    QPushButton:hover { background-color: #d1d5db; }
    
    QDialog { background-color: #ffffff; color: #1f2937; border: 1px solid #9ca3af; border-radius: 12px; }
    QLabel#DlgKicker { font-family: 'Consolas'; font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; }
    QLabel#DlgTitle { font-size: 18px; font-weight: 600; }
    QLabel#DlgDesc { font-size: 13px; color: #4b5563; }
    QPlainTextEdit#CmdBlock { background-color: #1e1e1e; border: 1px solid #d1d5db; color: #ece7dd; font-family: 'Consolas'; font-size: 13px; border-radius: 8px; padding: 16px; }
    
    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { border: none; background: #eef0f2; width: 8px; margin: 0; }
    QScrollBar::handle:vertical { background: #9ca3af; min-height: 20px; border-radius: 4px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    
    QMenu { background-color: #ffffff; color: #1f2937; border: 1px solid #9ca3af; }
    QMenu::item:selected { background-color: #eef0f2; }
"""

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

# ==========================================
# MAIN APPLICATION
# ==========================================
class ImmichGoGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immich Go GUI")
        self.resize(1100, 750)
        self.setStyleSheet(DARK_THEME)
        
        self.is_advanced = False
        self.is_light_theme = False
        
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
        self.update_binary()
        self.load_configuration()
        
        # Validation timer
        self.command_update_timer = QTimer(self)
        self.command_update_timer.timeout.connect(self.update_status)
        self.command_update_timer.start(300)

    # ==========================================
    # UI STRUCTURE BUILDERS
    # ==========================================
    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        
        self.btn_config = QPushButton(" ⚙  Configuration")
        self.btn_config.setObjectName("NavBtn")
        self.btn_config.setCheckable(True)
        self.btn_config.setChecked(True)
        self.btn_config.clicked.connect(lambda: self.switch_tab(0, "configuration", self.btn_config))
        sidebar_layout.addWidget(self.btn_config)
        
        lbl_upload = QLabel("UPLOAD")
        lbl_upload.setObjectName("NavTitle")
        sidebar_layout.addWidget(lbl_upload)
        
        self.btn_upload_folder = QPushButton(" 📁  Folder Upload")
        self.btn_upload_folder.setObjectName("NavBtn")
        self.btn_upload_folder.setCheckable(True)
        self.btn_upload_folder.clicked.connect(lambda: self.switch_tab(1, "upload · from-folder", self.btn_upload_folder))
        sidebar_layout.addWidget(self.btn_upload_folder)
        
        self.btn_upload_gp = QPushButton(" 📦  Google Takeout")
        self.btn_upload_gp.setObjectName("NavBtn")
        self.btn_upload_gp.setCheckable(True)
        self.btn_upload_gp.clicked.connect(lambda: self.switch_tab(2, "upload · from-google-photos", self.btn_upload_gp))
        sidebar_layout.addWidget(self.btn_upload_gp)
        
        self.btn_upload_immich = QPushButton(" 🔄  From Immich Server")
        self.btn_upload_immich.setObjectName("NavBtn")
        self.btn_upload_immich.setCheckable(True)
        self.btn_upload_immich.clicked.connect(lambda: self.switch_tab(3, "upload · from-immich", self.btn_upload_immich))
        sidebar_layout.addWidget(self.btn_upload_immich)
        
        lbl_archive = QLabel("ARCHIVE")
        lbl_archive.setObjectName("NavTitle")
        sidebar_layout.addWidget(lbl_archive)
        
        self.btn_archive_folder = QPushButton(" 🗄️  Archive Folder")
        self.btn_archive_folder.setObjectName("NavBtn")
        self.btn_archive_folder.setCheckable(True)
        self.btn_archive_folder.clicked.connect(lambda: self.switch_tab(4, "archive · from-folder", self.btn_archive_folder))
        sidebar_layout.addWidget(self.btn_archive_folder)
        
        self.btn_archive_immich = QPushButton(" 💾  Archive Server")
        self.btn_archive_immich.setObjectName("NavBtn")
        self.btn_archive_immich.setCheckable(True)
        self.btn_archive_immich.clicked.connect(lambda: self.switch_tab(5, "archive · from-immich", self.btn_archive_immich))
        sidebar_layout.addWidget(self.btn_archive_immich)
        
        lbl_organize = QLabel("ORGANIZE")
        lbl_organize.setObjectName("NavTitle")
        sidebar_layout.addWidget(lbl_organize)
        
        self.btn_stack = QPushButton(" 📚  Stack Assets")
        self.btn_stack.setObjectName("NavBtn")
        self.btn_stack.setCheckable(True)
        self.btn_stack.clicked.connect(lambda: self.switch_tab(6, "stack", self.btn_stack))
        sidebar_layout.addWidget(self.btn_stack)
        
        sidebar_layout.addStretch()
        
        # Status Frame
        status_frame = QFrame()
        status_frame.setObjectName("StatusFrame")
        status_layout = QVBoxLayout(status_frame)
        
        row1 = QHBoxLayout()
        self.lbl_binary_status = QLabel("🟢 Binary: Ready")
        self.lbl_binary_status.setObjectName("StatusText")
        row1.addWidget(self.lbl_binary_status)
        row1.addStretch()
        btn_update = QPushButton("Update")
        btn_update.setObjectName("ActionLink")
        btn_update.clicked.connect(self.update_binary)
        row1.addWidget(btn_update)
        status_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        self.status_indicator = QLabel("🔴 Server: Not Set")
        self.status_indicator.setObjectName("StatusText")
        row2.addWidget(self.status_indicator)
        row2.addStretch()
        btn_setup = QPushButton("Setup")
        btn_setup.setObjectName("ActionLink")
        btn_setup.clicked.connect(lambda: self.switch_tab(0, "configuration", self.btn_config))
        row2.addWidget(btn_setup)
        status_layout.addLayout(row2)
        
        sidebar_layout.addWidget(status_frame)
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

    # ==========================================
    # FORM HELPER METHODS
    # ==========================================
    def create_card(self, title, required=False):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_layout = QHBoxLayout()
        title_label = QLabel(title.upper())
        title_label.setObjectName("CardTitle")
        title_layout.addWidget(title_label)
        
        if required:
            req_label = QLabel("Required")
            req_label.setObjectName("ReqBadge")
            title_layout.addWidget(req_label)
            
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        return card, layout

    def create_form_row(self, label_text, widget, hint=""):
        row_widget = QWidget()
        layout = QVBoxLayout(row_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        lbl = QLabel(label_text)
        lbl.setObjectName("FieldLabel")
        layout.addWidget(lbl)
        
        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setObjectName("Hint")
            layout.addWidget(hint_lbl)
            
        layout.addWidget(widget)
        return row_widget

    def add_subhead(self, parent_layout, text):
        lbl = QLabel(text)
        lbl.setObjectName("Subhead")
        parent_layout.addWidget(lbl)

    def _build_config_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(32, 32, 32, 32)
        self.inputs['config'] = {}

        # Server Connection
        card, card_layout = self.create_card("Immich Server Connection", required=True)
        
        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("http://localhost:2283")
        self.inputs['config']['server'] = self.server_url_edit
        card_layout.addWidget(self.create_form_row("Server URL", self.server_url_edit))
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Paste your Immich API key")
        self.inputs['config']['api_key'] = self.api_key_edit
        card_layout.addWidget(self.create_form_row("API Key", self.api_key_edit))
        
        hint = QLabel("You can generate an API key in Immich under Account Settings -> API Keys.")
        hint.setObjectName("Hint")
        card_layout.addWidget(hint)
        layout.addWidget(card)

        # Binary Management
        card, card_layout = self.create_card("Binary Management")
        row = QHBoxLayout()
        lbl = QLabel("Current Version: v0.22.0\nLocated at: ./immich-go/")
        lbl.setObjectName("FieldLabel")
        row.addWidget(lbl)
        row.addStretch()
        btn_check = QPushButton("Check for Updates")
        btn_check.clicked.connect(self.update_binary)
        row.addWidget(btn_check)
        card_layout.addLayout(row)
        layout.addWidget(card)

        # Appearance
        card, card_layout = self.create_card("Appearance")
        row = QHBoxLayout()
        txt_box = QVBoxLayout()
        l1 = QLabel("Light Theme")
        l1.setObjectName("FieldLabel")
        l2 = QLabel("Toggle between dark and light interface modes")
        l2.setObjectName("Hint")
        txt_box.addWidget(l1)
        txt_box.addWidget(l2)
        row.addLayout(txt_box)
        row.addStretch()
        
        self.switch_theme = SwitchButton()
        self.switch_theme.toggled.connect(self.toggle_theme)
        row.addWidget(self.switch_theme)
        card_layout.addLayout(row)
        layout.addWidget(card)

        # Advanced Config
        adv_card, adv_layout = self.create_card("Advanced Configuration")
        adv_container = QWidget()
        adv_form = QVBoxLayout(adv_container)
        
        self.client_timeout_spin = QSpinBox()
        self.client_timeout_spin.setRange(1, 1440)
        self.client_timeout_spin.setValue(20)
        self.client_timeout_spin.setSuffix(" minutes")
        self.inputs['config']['client_timeout'] = self.client_timeout_spin
        adv_form.addWidget(self.create_form_row("Client Timeout", self.client_timeout_spin))
        
        self.concurrent_tasks_spin = QSpinBox()
        self.concurrent_tasks_spin.setRange(1, 20)
        self.concurrent_tasks_spin.setValue(2)
        self.inputs['config']['concurrent'] = self.concurrent_tasks_spin
        adv_form.addWidget(self.create_form_row("Concurrent Tasks", self.concurrent_tasks_spin))
        
        self.device_uuid_edit = QLineEdit()
        self.inputs['config']['device_uuid'] = self.device_uuid_edit
        adv_form.addWidget(self.create_form_row("Device UUID", self.device_uuid_edit))
        
        self.on_errors_combo = QComboBox()
        self.on_errors_combo.addItems(["stop", "continue"])
        self.inputs['config']['on_errors'] = self.on_errors_combo
        adv_form.addWidget(self.create_form_row("On Errors", self.on_errors_combo))
        
        self.pause_immich_jobs_check = QCheckBox("Pause Immich Jobs")
        self.pause_immich_jobs_check.setChecked(True)
        self.inputs['config']['pause_jobs'] = self.pause_immich_jobs_check
        adv_form.addWidget(self.pause_immich_jobs_check)
        
        adv_layout.addWidget(adv_container)
        self.adv_frames.append(adv_container)
        adv_card.setVisible(False)
        layout.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        layout.addStretch()
        return scroll

    def _build_upload_folder_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(32, 32, 32, 32)
        self.inputs['upload-folder'] = {}

        # Source Config
        card, card_layout = self.create_card("Source Configuration", required=True)
        self.source_path_edit = QLineEdit()
        self.source_path_edit.setPlaceholderText("/path/to/files")
        self.source_path_edit.setAcceptDrops(True)
        self.source_path_edit.dragEnterEvent = self.dragEnterEvent
        self.source_path_edit.dropEvent = self.dropEvent
        self.inputs['upload-folder']['path'] = self.source_path_edit
        card_layout.addWidget(self.create_form_row("Folder to upload", self.source_path_edit, "Every file inside this folder will be considered."))
        
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_local_folder)
        card_layout.addWidget(btn_browse)
        layout.addWidget(card)

        # Options
        card, card_layout = self.create_card("Options")
        
        c_type = QComboBox(); c_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs['upload-folder']['include-type'] = c_type
        card_layout.addWidget(self.create_form_row("Media Type", c_type))
        
        c_album = QComboBox(); c_album.addItems(["NONE", "FOLDER", "PATH"])
        self.inputs['upload-folder']['folder-album'] = c_album
        card_layout.addWidget(self.create_form_row("Album Organization", c_album))
        
        t_album = QLineEdit(); t_album.setPlaceholderText("e.g. Family Archive")
        self.inputs['upload-folder']['into-album'] = t_album
        card_layout.addWidget(self.create_form_row("Put all into Album", t_album))
        
        c_burst = QComboBox(); c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs['upload-folder']['manage-burst'] = c_burst
        card_layout.addWidget(self.create_form_row("Burst Photos", c_burst))
        
        c_raw = QComboBox(); c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs['upload-folder']['manage-raw-jpeg'] = c_raw
        card_layout.addWidget(self.create_form_row("RAW + JPEG Pairs", c_raw))
        
        c_heic = QComboBox(); c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs['upload-folder']['manage-heic-jpeg'] = c_heic
        card_layout.addWidget(self.create_form_row("HEIC + JPEG Pairs", c_heic))
        layout.addWidget(card)

        # Advanced Options
        adv_card, adv_layout = self.create_card("Advanced Options")
        adv_container = QWidget()
        adv_form = QVBoxLayout(adv_container)
        
        self.add_subhead(adv_form, "Filtering")
        d_range = QLineEdit(); d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs['upload-folder']['date-range'] = d_range
        adv_form.addWidget(self.create_form_row("Date range", d_range))
        
        inc_ext = QLineEdit(); inc_ext.setPlaceholderText(".jpg,.heic,.mp4")
        self.inputs['upload-folder']['include-ext'] = inc_ext
        adv_form.addWidget(self.create_form_row("Include extensions", inc_ext))
        
        exc_ext = QLineEdit(); exc_ext.setPlaceholderText(".thm,.xmp")
        self.inputs['upload-folder']['exclude-ext'] = exc_ext
        adv_form.addWidget(self.create_form_row("Exclude extensions", exc_ext))
        
        ban_file = QPlainTextEdit(); ban_file.setPlaceholderText("@eaDir/\n.DS_Store")
        self.inputs['upload-folder']['ban-file'] = ban_file
        adv_form.addWidget(self.create_form_row("Skip files matching patterns", ban_file))
        
        chk_ignore = QCheckBox("Ignore sidecar files")
        self.inputs['upload-folder']['ignore-sidecar'] = chk_ignore
        adv_form.addWidget(chk_ignore)
        
        chk_date_name = QCheckBox("Guess dates from filenames")
        chk_date_name.setChecked(True)
        self.inputs['upload-folder']['date-from-name'] = chk_date_name
        adv_form.addWidget(chk_date_name)
        
        self.add_subhead(adv_form, "Tagging")
        t_tags = QLineEdit(); t_tags.setPlaceholderText("vacation, family/reunion")
        self.inputs['upload-folder']['tag'] = t_tags
        adv_form.addWidget(self.create_form_row("Custom Tags (comma separated)", t_tags))
        
        chk_sess = QCheckBox("Session Tag")
        self.inputs['upload-folder']['session-tag'] = chk_sess
        adv_form.addWidget(chk_sess)
        
        chk_ftags = QCheckBox("Folder as Tags")
        self.inputs['upload-folder']['folder-tags'] = chk_ftags
        adv_form.addWidget(chk_ftags)
        
        self.add_subhead(adv_form, "Run Behavior")
        c_err = QComboBox(); c_err.addItems(["stop", "continue"])
        self.inputs['upload-folder']['on-errors'] = c_err
        adv_form.addWidget(self.create_form_row("If a file fails", c_err))
        
        chk_overwrite = QCheckBox("Overwrite Existing")
        self.inputs['upload-folder']['overwrite'] = chk_overwrite
        adv_form.addWidget(chk_overwrite)
        
        chk_pause = QCheckBox("Pause background jobs")
        chk_pause.setChecked(True)
        self.inputs['upload-folder']['pause-jobs'] = chk_pause
        adv_form.addWidget(chk_pause)
        
        self.add_subhead(adv_form, "Connection & Debug")
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['upload-folder']['skip-ssl'] = chk_ssl
        adv_form.addWidget(chk_ssl)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['upload-folder']['log-level'] = c_log
        adv_form.addWidget(self.create_form_row("Log Level", c_log))
        
        chk_trace = QCheckBox("Enable API Trace")
        self.inputs['upload-folder']['api-trace'] = chk_trace
        adv_form.addWidget(chk_trace)
        
        adv_layout.addWidget(adv_container)
        self.adv_frames.append(adv_container)
        adv_card.setVisible(False)
        layout.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        layout.addStretch()
        return scroll

    def _build_upload_gp_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(32, 32, 32, 32)
        self.inputs['upload-gp'] = {}

        # Source Config
        card, card_layout = self.create_card("Source Configuration", required=True)
        self.gp_path_edit = QLineEdit()
        self.gp_path_edit.setPlaceholderText("/path/to/takeout")
        self.gp_path_edit.setAcceptDrops(True)
        self.gp_path_edit.dragEnterEvent = self.dragEnterEvent
        self.gp_path_edit.dropEvent = self.dropEvent
        self.inputs['upload-gp']['path'] = self.gp_path_edit
        card_layout.addWidget(self.create_form_row("Takeout File/Folder Path", self.gp_path_edit))
        
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_takeout_source)
        card_layout.addWidget(btn_browse)
        layout.addWidget(card)

        # Options
        card, card_layout = self.create_card("Options")
        
        c_type = QComboBox(); c_type.addItems(["all", "IMAGE", "VIDEO"])
        self.inputs['upload-gp']['include-type'] = c_type
        card_layout.addWidget(self.create_form_row("Media Type", c_type))
        
        t_album = QLineEdit(); t_album.setPlaceholderText("e.g. Family Archive")
        self.inputs['upload-gp']['into-album'] = t_album
        card_layout.addWidget(self.create_form_row("Put all into Album", t_album))
        
        chk_unmatched = QCheckBox("Include Unmatched Files")
        self.inputs['upload-gp']['include-unmatched'] = chk_unmatched
        card_layout.addWidget(chk_unmatched)
        
        chk_partner = QCheckBox("Include Partner Photos")
        chk_partner.setChecked(True)
        self.inputs['upload-gp']['include-partner'] = chk_partner
        card_layout.addWidget(chk_partner)
        
        chk_sync = QCheckBox("Sync Google Albums")
        chk_sync.setChecked(True)
        self.inputs['upload-gp']['sync-albums'] = chk_sync
        card_layout.addWidget(chk_sync)
        
        c_burst = QComboBox(); c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs['upload-gp']['manage-burst'] = c_burst
        card_layout.addWidget(self.create_form_row("Burst Photos", c_burst))
        
        c_heic = QComboBox(); c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs['upload-gp']['manage-heic-jpeg'] = c_heic
        card_layout.addWidget(self.create_form_row("HEIC + JPEG Pairs", c_heic))
        layout.addWidget(card)

        # Advanced Options
        adv_card, adv_layout = self.create_card("Advanced Options")
        adv_container = QWidget()
        adv_form = QVBoxLayout(adv_container)
        
        self.add_subhead(adv_form, "Takeout Specifics")
        t_album_name = QLineEdit(); t_album_name.setPlaceholderText("Album Name")
        self.inputs['upload-gp']['from-album-name'] = t_album_name
        adv_form.addWidget(self.create_form_row("From Specific Album", t_album_name))
        
        chk_archived = QCheckBox("Include Archived")
        chk_archived.setChecked(True)
        self.inputs['upload-gp']['include-archived'] = chk_archived
        adv_form.addWidget(chk_archived)
        
        chk_trashed = QCheckBox("Include Trashed")
        self.inputs['upload-gp']['include-trashed'] = chk_trashed
        adv_form.addWidget(chk_trashed)
        
        t_partner_album = QLineEdit(); t_partner_album.setPlaceholderText("Album name for partner photos")
        self.inputs['upload-gp']['partner-album'] = t_partner_album
        adv_form.addWidget(self.create_form_row("Partner Shared Album", t_partner_album))
        
        chk_takeout_tag = QCheckBox("Takeout Tag")
        chk_takeout_tag.setChecked(True)
        self.inputs['upload-gp']['takeout-tag'] = chk_takeout_tag
        adv_form.addWidget(chk_takeout_tag)
        
        chk_people_tag = QCheckBox("People Tag")
        chk_people_tag.setChecked(True)
        self.inputs['upload-gp']['people-tag'] = chk_people_tag
        adv_form.addWidget(chk_people_tag)
        
        self.add_subhead(adv_form, "Tagging")
        t_tags = QLineEdit(); t_tags.setPlaceholderText("vacation, family/reunion")
        self.inputs['upload-gp']['tag'] = t_tags
        adv_form.addWidget(self.create_form_row("Custom Tags (comma separated)", t_tags))
        
        chk_sess = QCheckBox("Session Tag")
        self.inputs['upload-gp']['session-tag'] = chk_sess
        adv_form.addWidget(chk_sess)
        
        self.add_subhead(adv_form, "Run Behavior")
        c_err = QComboBox(); c_err.addItems(["stop", "continue"])
        self.inputs['upload-gp']['on-errors'] = c_err
        adv_form.addWidget(self.create_form_row("If a file fails", c_err))
        
        chk_pause = QCheckBox("Pause background jobs")
        chk_pause.setChecked(True)
        self.inputs['upload-gp']['pause-jobs'] = chk_pause
        adv_form.addWidget(chk_pause)
        
        self.add_subhead(adv_form, "Connection & Debug")
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['upload-gp']['skip-ssl'] = chk_ssl
        adv_form.addWidget(chk_ssl)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['upload-gp']['log-level'] = c_log
        adv_form.addWidget(self.create_form_row("Log Level", c_log))
        
        adv_layout.addWidget(adv_container)
        self.adv_frames.append(adv_container)
        adv_card.setVisible(False)
        layout.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        layout.addStretch()
        return scroll

    def _build_upload_immich_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(32, 32, 32, 32)
        self.inputs['upload-immich'] = {}

        # Source Config
        card, card_layout = self.create_card("Source Configuration", required=True)
        t_server = QLineEdit(); t_server.setPlaceholderText("http://old-server:2283")
        self.inputs['upload-immich']['from-server'] = t_server
        card_layout.addWidget(self.create_form_row("Source Server URL", t_server))
        
        t_api = QLineEdit(); t_api.setEchoMode(QLineEdit.Password); t_api.setPlaceholderText("Source API Key")
        self.inputs['upload-immich']['from-api-key'] = t_api
        card_layout.addWidget(self.create_form_row("Source API Key", t_api))
        
        chk_fav = QCheckBox("Only Favorites")
        self.inputs['upload-immich']['from-favorite'] = chk_fav
        card_layout.addWidget(chk_fav)
        
        chk_arch = QCheckBox("Include Archived")
        self.inputs['upload-immich']['from-archived'] = chk_arch
        card_layout.addWidget(chk_arch)
        
        chk_trash = QCheckBox("Include Trashed")
        self.inputs['upload-immich']['from-trash'] = chk_trash
        card_layout.addWidget(chk_trash)
        layout.addWidget(card)

        # Advanced Options
        adv_card, adv_layout = self.create_card("Advanced Options")
        adv_container = QWidget()
        adv_form = QVBoxLayout(adv_container)
        
        self.add_subhead(adv_form, "Source Filtering")
        d_range = QLineEdit(); d_range.setPlaceholderText("2023-01-01,2023-12-31")
        self.inputs['upload-immich']['from-date-range'] = d_range
        adv_form.addWidget(self.create_form_row("Date Range Filter", d_range))
        
        t_albums = QLineEdit(); t_albums.setPlaceholderText("Family, Travel")
        self.inputs['upload-immich']['from-albums'] = t_albums
        adv_form.addWidget(self.create_form_row("Filter by Albums", t_albums))
        
        s_rating = QSpinBox(); s_rating.setRange(0, 5)
        self.inputs['upload-immich']['from-minimal-rating'] = s_rating
        adv_form.addWidget(self.create_form_row("Minimum Rating", s_rating))
        
        t_people = QLineEdit(); t_people.setPlaceholderText("John, Jane")
        self.inputs['upload-immich']['from-people'] = t_people
        adv_form.addWidget(self.create_form_row("Filter by People", t_people))
        
        t_tags = QLineEdit(); t_tags.setPlaceholderText("vacation, work")
        self.inputs['upload-immich']['from-tags'] = t_tags
        adv_form.addWidget(self.create_form_row("Filter by Tags", t_tags))
        
        self.add_subhead(adv_form, "Metadata Filtering")
        t_city = QLineEdit(); t_city.setPlaceholderText("New York")
        self.inputs['upload-immich']['from-city'] = t_city
        adv_form.addWidget(self.create_form_row("City", t_city))
        
        t_state = QLineEdit(); t_state.setPlaceholderText("NY")
        self.inputs['upload-immich']['from-state'] = t_state
        adv_form.addWidget(self.create_form_row("State", t_state))
        
        t_country = QLineEdit(); t_country.setPlaceholderText("USA")
        self.inputs['upload-immich']['from-country'] = t_country
        adv_form.addWidget(self.create_form_row("Country", t_country))
        
        t_make = QLineEdit(); t_make.setPlaceholderText("Canon")
        self.inputs['upload-immich']['from-make'] = t_make
        adv_form.addWidget(self.create_form_row("Camera Make", t_make))
        
        t_model = QLineEdit(); t_model.setPlaceholderText("EOS R5")
        self.inputs['upload-immich']['from-model'] = t_model
        adv_form.addWidget(self.create_form_row("Camera Model", t_model))
        
        self.add_subhead(adv_form, "Run Behavior")
        c_err = QComboBox(); c_err.addItems(["stop", "continue"])
        self.inputs['upload-immich']['on-errors'] = c_err
        adv_form.addWidget(self.create_form_row("If a file fails", c_err))
        
        self.add_subhead(adv_form, "Connection & Debug")
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['upload-immich']['skip-ssl'] = chk_ssl
        adv_form.addWidget(chk_ssl)
        
        chk_ssl_src = QCheckBox("Skip Source SSL Verification")
        self.inputs['upload-immich']['from-skip-ssl'] = chk_ssl_src
        adv_form.addWidget(chk_ssl_src)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['upload-immich']['log-level'] = c_log
        adv_form.addWidget(self.create_form_row("Log Level", c_log))
        
        adv_layout.addWidget(adv_container)
        self.adv_frames.append(adv_container)
        adv_card.setVisible(False)
        layout.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        layout.addStretch()
        return scroll

    def _build_archive_folder_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(32, 32, 32, 32)
        self.inputs['archive-folder'] = {}

        # Source Config
        card, card_layout = self.create_card("Source Configuration", required=True)
        p_edit = QLineEdit(); p_edit.setPlaceholderText("/path/to/files")
        p_edit.setAcceptDrops(True)
        p_edit.dragEnterEvent = self.dragEnterEvent
        p_edit.dropEvent = self.dropEvent
        self.inputs['archive-folder']['path'] = p_edit
        card_layout.addWidget(self.create_form_row("Source Folder Path", p_edit))
        
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_local_folder)
        card_layout.addWidget(btn_browse)
        layout.addWidget(card)

        # Options
        card, card_layout = self.create_card("Options")
        t_write = QLineEdit(); t_write.setPlaceholderText("/organized-photos")
        self.inputs['archive-folder']['write-to'] = t_write
        card_layout.addWidget(self.create_form_row("Destination Folder", t_write))
        
        c_raw = QComboBox(); c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs['archive-folder']['manage-raw-jpeg'] = c_raw
        card_layout.addWidget(self.create_form_row("Manage RAW+JPEG", c_raw))
        layout.addWidget(card)

        # Advanced Options
        adv_card, adv_layout = self.create_card("Advanced Options")
        adv_container = QWidget()
        adv_form = QVBoxLayout(adv_container)
        
        self.add_subhead(adv_form, "Filtering")
        d_range = QLineEdit(); d_range.setPlaceholderText("YYYY-MM-DD,YYYY-MM-DD")
        self.inputs['archive-folder']['date-range'] = d_range
        adv_form.addWidget(self.create_form_row("Date Range", d_range))
        
        self.add_subhead(adv_form, "Connection & Debug")
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['archive-folder']['log-level'] = c_log
        adv_form.addWidget(self.create_form_row("Log Level", c_log))
        
        adv_layout.addWidget(adv_container)
        self.adv_frames.append(adv_container)
        adv_card.setVisible(False)
        layout.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        layout.addStretch()
        return scroll

    def _build_archive_immich_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(32, 32, 32, 32)
        self.inputs['archive-immich'] = {}

        # Target Server
        card, card_layout = self.create_card("Target Server")
        t_server = QLineEdit(); t_server.setEnabled(False); t_server.setText("Not Configured")
        self.inputs['archive-immich']['target-server'] = t_server
        card_layout.addWidget(self.create_form_row("Immich Server URL", t_server, "Update in Configuration tab."))
        layout.addWidget(card)

        # Options
        card, card_layout = self.create_card("Options")
        t_write = QLineEdit(); t_write.setPlaceholderText("/backup/photos")
        self.inputs['archive-immich']['write-to'] = t_write
        card_layout.addWidget(self.create_form_row("Destination Folder", t_write))
        
        c_burst = QComboBox(); c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs['archive-immich']['manage-burst'] = c_burst
        card_layout.addWidget(self.create_form_row("Manage Bursts", c_burst))
        
        c_raw = QComboBox(); c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs['archive-immich']['manage-raw-jpeg'] = c_raw
        card_layout.addWidget(self.create_form_row("Manage RAW+JPEG", c_raw))
        layout.addWidget(card)

        # Advanced Options
        adv_card, adv_layout = self.create_card("Advanced Options")
        adv_container = QWidget()
        adv_form = QVBoxLayout(adv_container)
        
        self.add_subhead(adv_form, "Source Filtering")
        d_range = QLineEdit(); d_range.setPlaceholderText("2023-01-01,2023-12-31")
        self.inputs['archive-immich']['from-date-range'] = d_range
        adv_form.addWidget(self.create_form_row("Date Range Filter", d_range))
        
        t_albums = QLineEdit(); t_albums.setPlaceholderText("Family, Travel")
        self.inputs['archive-immich']['from-albums'] = t_albums
        adv_form.addWidget(self.create_form_row("Specific Albums", t_albums))
        
        self.add_subhead(adv_form, "Connection & Debug")
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['archive-immich']['skip-ssl'] = chk_ssl
        adv_form.addWidget(chk_ssl)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['archive-immich']['log-level'] = c_log
        adv_form.addWidget(self.create_form_row("Log Level", c_log))
        
        adv_layout.addWidget(adv_container)
        self.adv_frames.append(adv_container)
        adv_card.setVisible(False)
        layout.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        layout.addStretch()
        return scroll

    def _build_stack_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(32, 32, 32, 32)
        self.inputs['stack'] = {}

        # Target Server
        card, card_layout = self.create_card("Target Server")
        t_server = QLineEdit(); t_server.setEnabled(False); t_server.setText("Not Configured")
        self.inputs['stack']['target-server'] = t_server
        card_layout.addWidget(self.create_form_row("Immich Server URL", t_server, "Update in Configuration tab."))
        layout.addWidget(card)

        # Options
        card, card_layout = self.create_card("Options")
        c_burst = QComboBox(); c_burst.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        self.inputs['stack']['manage-burst'] = c_burst
        card_layout.addWidget(self.create_form_row("Manage Bursts", c_burst))
        
        c_raw = QComboBox(); c_raw.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        self.inputs['stack']['manage-raw-jpeg'] = c_raw
        card_layout.addWidget(self.create_form_row("Manage RAW+JPEG", c_raw))
        
        c_heic = QComboBox(); c_heic.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])
        self.inputs['stack']['manage-heic-jpeg'] = c_heic
        card_layout.addWidget(self.create_form_row("Manage HEIC+JPEG", c_heic))
        layout.addWidget(card)

        # Advanced Options
        adv_card, adv_layout = self.create_card("Advanced Options")
        adv_container = QWidget()
        adv_form = QVBoxLayout(adv_container)
        
        self.add_subhead(adv_form, "Detection Tuning")
        t_tz = QLineEdit(); t_tz.setPlaceholderText("America/New_York")
        self.inputs['stack']['time-zone'] = t_tz
        adv_form.addWidget(self.create_form_row("Time Zone Override", t_tz))
        
        chk_epson = QCheckBox("Manage Epson FastFoto")
        self.inputs['stack']['manage-epson'] = chk_epson
        adv_form.addWidget(chk_epson)
        
        self.add_subhead(adv_form, "Connection & Debug")
        chk_ssl = QCheckBox("Skip SSL Verification")
        self.inputs['stack']['skip-ssl'] = chk_ssl
        adv_form.addWidget(chk_ssl)
        
        c_log = QComboBox(); c_log.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.inputs['stack']['log-level'] = c_log
        adv_form.addWidget(self.create_form_row("Log Level", c_log))
        
        adv_layout.addWidget(adv_container)
        self.adv_frames.append(adv_container)
        adv_card.setVisible(False)
        layout.addWidget(adv_card)
        self.adv_frames.append(adv_card)
        
        layout.addStretch()
        return scroll

    # ==========================================
    # UI INTERACTIONS & LOGIC
    # ==========================================
    def toggle_theme(self, checked):
        self.is_light_theme = checked
        if checked:
            self.setStyleSheet(LIGHT_THEME)
        else:
            self.setStyleSheet(DARK_THEME)

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
            self.status_indicator.setText("🟢 Server: Ready")
            self.btn_run.setEnabled(True)
            self.btn_dry_run.setEnabled(True)
        else:
            self.status_indicator.setText("🔴 Server: Not Set")
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

    def build_command(self, dry_run):
        idx = self.stacked_widget.currentIndex()
        tab_keys = ["config", "upload-folder", "upload-gp", "upload-immich", "archive-folder", "archive-immich", "stack"]
        tab_key = tab_keys[idx]
        
        if tab_key == "config":
            return []
            
        opts = []
        c = self.inputs[tab_key]
        
        # Base command
        if tab_key == "upload-folder": opts += ["upload", "from-folder"]
        elif tab_key == "upload-gp": opts += ["upload", "from-google-photos"]
        elif tab_key == "upload-immich": opts += ["upload", "from-immich"]
        elif tab_key == "archive-folder": opts += ["archive", "from-folder"]
        elif tab_key == "archive-immich": opts += ["archive", "from-immich"]
        elif tab_key == "stack": opts += ["stack"]
        
        opts.append("--no-ui")  # Always disable interactive UI
        
        # Server options (except for local archive)
        if tab_key != "archive-folder":
            srv = self.inputs['config']['server'].text()
            api = self.inputs['config']['api_key'].text()
            if srv: opts.append(f"--server={srv}")
            if api: opts.append(f"--api-key={api}")
            
        # Run behavior (from config advanced)
        conc = self.inputs['config']['concurrent'].value()
        if conc != 2: opts.append(f"--concurrent-tasks={conc}")
        
        if 'pause-jobs' in c:
            if not c['pause-jobs'].isChecked(): opts.append("--pause-immich-jobs=false")
        elif not self.inputs['config']['pause_jobs'].isChecked():
            opts.append("--pause-immich-jobs=false")
            
        if 'on-errors' in c:
            if c['on-errors'].currentText() != "stop": opts.append(f"--on-errors={c['on-errors'].currentText()}")
        elif self.inputs['config']['on_errors'].currentText() != "stop":
            opts.append(f"--on-errors={self.inputs['config']['on_errors'].currentText()}")

        # Tab specific options
        if tab_key == "upload-folder":
            if c['include-type'].currentText() != "all": opts.append(f"--include-type={c['include-type'].currentText()}")
            if c['folder-album'].currentText() != "NONE": opts.append(f"--folder-as-album={c['folder-album'].currentText()}")
            if c['into-album'].text(): opts.append(f'--into-album={c["into-album"].text()}')
            if c['overwrite'].isChecked(): opts.append("--overwrite")
            if c['manage-burst'].currentText() != "NoStack": opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
            if c['manage-raw-jpeg'].currentText() != "NoStack": opts.append(f"--manage-raw-jpeg={c['manage-raw-jpeg'].currentText()}")
            if c['manage-heic-jpeg'].currentText() != "NoStack": opts.append(f"--manage-heic-jpeg={c['manage-heic-jpeg'].currentText()}")
            
            # Advanced
            if c['date-range'].text(): opts.append(f'--date-range={c["date-range"].text()}')
            if c['include-ext'].text(): opts.append(f'--include-extensions={c["include-ext"].text()}')
            if c['exclude-ext'].text(): opts.append(f'--exclude-extensions={c["exclude-ext"].text()}')
            for line in c['ban-file'].toPlainText().split('\n'):
                if line.strip(): opts.append(f'--ban-file="{line.strip()}"')
            if c['ignore-sidecar'].isChecked(): opts.append("--ignore-sidecar-files")
            if not c['date-from-name'].isChecked(): opts.append("--date-from-name=false")
            
            if c['tag'].text():
                for t in c['tag'].text().split(','):
                    if t.strip(): opts.append(f'--tag="{t.strip()}"')
            if c['session-tag'].isChecked(): opts.append("--session-tag")
            if c['folder-tags'].isChecked(): opts.append("--folder-as-tags")
            
            if c['skip-ssl'].isChecked(): opts.append("--skip-verify-ssl")
            if c['log-level'].currentText() != "INFO": opts.append(f"--log-level={c['log-level'].currentText()}")
            if c['api-trace'].isChecked(): opts.append("--api-trace")
            
            if c['path'].text(): opts.append(f'"{c["path"].text()}"')

        elif tab_key == "upload-gp":
            if c['include-type'].currentText() != "all": opts.append(f"--include-type={c['include-type'].currentText()}")
            if c['into-album'].text(): opts.append(f'--into-album={c["into-album"].text()}')
            if c['include-unmatched'].isChecked(): opts.append("--include-unmatched=true")
            if not c['include-partner'].isChecked(): opts.append("--include-partner=false")
            if not c['sync-albums'].isChecked(): opts.append("--sync-albums=false")
            if c['manage-burst'].currentText() != "NoStack": opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
            if c['manage-heic-jpeg'].currentText() != "NoStack": opts.append(f"--manage-heic-jpeg={c['manage-heic-jpeg'].currentText()}")
            
            # Advanced
            if c['from-album-name'].text(): opts.append(f'--from-album-name={c["from-album-name"].text()}')
            if not c['include-archived'].isChecked(): opts.append("--include-archived=false")
            if c['include-trashed'].isChecked(): opts.append("--include-trashed=true")
            if c['partner-album'].text(): opts.append(f'--partner-shared-album={c["partner-album"].text()}')
            if not c['takeout-tag'].isChecked(): opts.append("--takeout-tag=false")
            if not c['people-tag'].isChecked(): opts.append("--people-tag=false")
            
            if c['tag'].text():
                for t in c['tag'].text().split(','):
                    if t.strip(): opts.append(f'--tag="{t.strip()}"')
            if c['session-tag'].isChecked(): opts.append("--session-tag")
            
            if c['skip-ssl'].isChecked(): opts.append("--skip-verify-ssl")
            if c['log-level'].currentText() != "INFO": opts.append(f"--log-level={c['log-level'].currentText()}")
            
            if c['path'].text(): opts.append(f'"{c["path"].text()}"')

        elif tab_key == "upload-immich":
            if c['from-server'].text(): opts.append(f"--from-server={c['from-server'].text()}")
            if c['from-api-key'].text(): opts.append(f"--from-api-key={c['from-api-key'].text()}")
            if c['from-favorite'].isChecked(): opts.append("--from-favorite=true")
            if c['from-archived'].isChecked(): opts.append("--from-archived=true")
            if c['from-trash'].isChecked(): opts.append("--from-trash=true")
            
            # Advanced
            if c['from-date-range'].text(): opts.append(f'--from-date-range={c["from-date-range"].text()}')
            if c['from-albums'].text():
                for a in c['from-albums'].text().split(','):
                    if a.strip(): opts.append(f'--from-albums="{a.strip()}"')
            if c['from-minimal-rating'].value() > 0: opts.append(f"--from-minimal-rating={c['from-minimal-rating'].value()}")
            if c['from-people'].text():
                for p in c['from-people'].text().split(','):
                    if p.strip(): opts.append(f'--from-people="{p.strip()}"')
            if c['from-tags'].text():
                for t in c['from-tags'].text().split(','):
                    if t.strip(): opts.append(f'--from-tags="{t.strip()}"')
                    
            if c['from-city'].text(): opts.append(f'--from-city={c["from-city"].text()}')
            if c['from-state'].text(): opts.append(f'--from-state={c["from-state"].text()}')
            if c['from-country'].text(): opts.append(f'--from-country={c["from-country"].text()}')
            if c['from-make'].text(): opts.append(f'--from-make={c["from-make"].text()}')
            if c['from-model'].text(): opts.append(f'--from-model={c["from-model"].text()}')
            
            if c['skip-ssl'].isChecked(): opts.append("--skip-verify-ssl")
            if c['from-skip-ssl'].isChecked(): opts.append("--from-skip-verify-ssl")
            if c['log-level'].currentText() != "INFO": opts.append(f"--log-level={c['log-level'].currentText()}")

        elif tab_key == "archive-folder":
            if c['write-to'].text(): opts.append(f'--write-to-folder={c["write-to"].text()}')
            if c['manage-raw-jpeg'].currentText() != "NoStack": opts.append(f"--manage-raw-jpeg={c['manage-raw-jpeg'].currentText()}")
            
            # Advanced
            if c['date-range'].text(): opts.append(f'--date-range={c["date-range"].text()}')
            if c['log-level'].currentText() != "INFO": opts.append(f"--log-level={c['log-level'].currentText()}")
            
            if c['path'].text(): opts.append(f'"{c["path"].text()}"')

        elif tab_key == "archive-immich":
            if c['write-to'].text(): opts.append(f'--write-to-folder={c["write-to"].text()}')
            if c['manage-burst'].currentText() != "NoStack": opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
            if c['manage-raw-jpeg'].currentText() != "NoStack": opts.append(f"--manage-raw-jpeg={c['manage-raw-jpeg'].currentText()}")
            
            # Advanced
            if c['from-date-range'].text(): opts.append(f'--from-date-range={c["from-date-range"].text()}')
            if c['from-albums'].text():
                for a in c['from-albums'].text().split(','):
                    if a.strip(): opts.append(f'--from-albums="{a.strip()}"')
                    
            if c['skip-ssl'].isChecked(): opts.append("--skip-verify-ssl")
            if c['log-level'].currentText() != "INFO": opts.append(f"--log-level={c['log-level'].currentText()}")

        elif tab_key == "stack":
            if c['manage-burst'].currentText() != "NoStack": opts.append(f"--manage-burst={c['manage-burst'].currentText()}")
            if c['manage-raw-jpeg'].currentText() != "NoStack": opts.append(f"--manage-raw-jpeg={c['manage-raw-jpeg'].currentText()}")
            if c['manage-heic-jpeg'].currentText() != "NoStack": opts.append(f"--manage-heic-jpeg={c['manage-heic-jpeg'].currentText()}")
            
            # Advanced
            if c['time-zone'].text(): opts.append(f'--time-zone={c["time-zone"].text()}')
            if c['manage-epson'].isChecked(): opts.append("--manage-epson-fastfoto=true")
            
            if c['skip-ssl'].isChecked(): opts.append("--skip-verify-ssl")
            if c['log-level'].currentText() != "INFO": opts.append(f"--log-level={c['log-level'].currentText()}")

        if dry_run:
            if "--dry-run" not in opts: opts.append("--dry-run")
        else:
            if "--dry-run" in opts: opts.remove("--dry-run")
            
        return opts

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

    def update_binary(self):
        binary_folder = os.path.abspath(os.path.join(os.getcwd(), "immich-go"))
        if not os.path.exists(binary_folder): os.makedirs(binary_folder)
        
        binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        binary_path = os.path.join(binary_folder, binary_filename)
        self.binary_path = binary_path

        if os.path.exists(binary_path):
            self.lbl_binary_status.setText("🟢 Binary: Ready")
            return True

        self.lbl_binary_status.setText("🔴 Binary: Missing")
        QMessageBox.warning(self, "Binary Missing", "Please download the immich-go binary and place it in the 'immich-go' folder.")
        return False

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
            self.status_indicator.setText("⚠️ Running... Close terminal to continue.")
        else:
            self.check_process_timer.stop()
            self.running_process = None
            self.btn_run.setDisabled(False)
            self.btn_dry_run.setDisabled(False)
            self.update_status()

    def save_configuration(self):
        self.settings.setValue("server_url", self.inputs['config']['server'].text())
        self.settings.setValue("api_key", self.inputs['config']['api_key'].text())
        QMessageBox.information(self, "Saved", "Configuration saved successfully.")

    def load_configuration(self):
        self.inputs['config']['server'].setText(self.settings.value("server_url", ""))
        self.inputs['config']['api_key'].setText(self.settings.value("api_key", ""))

    def open_github_link(self):
        webbrowser.open("https://github.com/simulot/immich-go")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = ImmichGoGUI()
    window.show()
    sys.exit(app.exec())