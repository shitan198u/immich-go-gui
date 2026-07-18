import sys
import os
import re
import subprocess
import shlex
import platform
import webbrowser
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QPushButton,
    QFileDialog,
    QPlainTextEdit,
    QStackedWidget,
    QFrame,
    QScrollArea,
    QMessageBox,
    QDialog,
    QGroupBox,
    QSpinBox,
    QDateEdit,
)
from PySide6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDropEvent,
    QPainter,
    QPen,
    QColor,
    QBrush,
    QFont,
)
from PySide6.QtCore import Qt, QDate, QTimer, QSettings, Signal
import psutil
import requests

# ==========================================
# CUSTOM WIDGETS & STYLES
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
    QGroupBox#Card { background-color: #15181b; border: 1px solid #2a3034; border-radius: 8px; padding: 20px 22px; margin-top: 16px; font-family: 'Consolas'; font-size: 12px; font-weight: 600; color: #8b9298; text-transform: uppercase; letter-spacing: 1px; }
    QGroupBox#Card::title { subcontrol-origin: margin; left: 22px; padding: 0 5px; }

    QLabel#ReqBadge { font-size: 10px; color: #e1512e; background-color: rgba(225,81,46,0.08); border: 1px solid #4a2318; padding: 2px 6px; border-radius: 4px; font-family: 'Segoe UI'; font-weight: normal; text-transform: none; }

    QLabel#FieldLabel { font-size: 13px; font-weight: 500; color: #ece7dd; }
    QLabel#Hint { font-size: 12px; color: #5b6267; }

    QLineEdit, QComboBox, QSpinBox, QDateEdit {
        background-color: #1d2226; border: 1px solid #3a4045; color: #ece7dd;
        padding: 9px 11px; border-radius: 6px; font-size: 14px;
        selection-background-color: #4fb3a4;
    }
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDateEdit:hover { border-color: #5b6267; }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus { border-color: #4fb3a4; background-color: #23282c; }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView { background-color: #1d2226; color: #ece7dd; selection-background-color: #4fb3a4; border: 1px solid #3a4045; }

    /* Checkboxes */
    QCheckBox { spacing: 8px; color: #ece7dd; }
    QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #3a4045; background: #1d2226; }
    QCheckBox::indicator:hover { border-color: #4fb3a4; }
    QCheckBox::indicator:checked { background: #4fb3a4; border: 1px solid #4fb3a4; }

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


class SwitchButton(QWidget):
    """A custom toggle switch replicating the HTML mini-switch"""

    toggled = Signal(bool)

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
        if self._checked:
            painter.setPen(QPen(QColor("#4fb3a4"), 1))
            painter.setBrush(QBrush(QColor("#1b3733")))
        else:
            painter.setPen(QPen(QColor("#3a4045"), 1))
            painter.setBrush(QBrush(QColor("#1d2226")))
        painter.drawRoundedRect(rect, 11, 11)
        if self._checked:
            painter.setBrush(QBrush(QColor("#4fb3a4")))
            circle_x = self.width() - 2 - 16
        else:
            painter.setBrush(QBrush(QColor("#5b6267")))
            circle_x = 2
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(circle_x, 2, 16, 16)


# ==========================================
# MAIN APPLICATION
# ==========================================
class ImmichGoGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immich Go GUI")
        self.resize(1000, 700)
        self.setStyleSheet(DARK_THEME)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.advanced_widgets = []
        self.is_advanced = False

        self._build_sidebar()
        self._build_content_area()

        self.create_menu_bar()

        # Initialize UI forms
        self.config_tab = self.create_configuration_tab()
        self.takeout_tab = self.create_google_takeout_tab()
        self.local_tab = self.create_local_upload_tab()
        self.stack_tab = self.create_stack_tab()

        self.stacked_widget.addWidget(self.config_tab)
        self.stacked_widget.addWidget(self.takeout_tab)
        self.stacked_widget.addWidget(self.local_tab)
        self.stacked_widget.addWidget(self.stack_tab)

        self.stacked_widget.setCurrentIndex(0)
        self.update_header_crumb("Configuration")
        self.footer.setVisible(False)  # Hide footer on config tab

        self.settings = QSettings("YourOrganization", "ImmichGoGUI")
        self.update_binary()
        self.load_configuration()

        # Validation timer
        self.command_update_timer = QTimer(self)
        self.command_update_timer.timeout.connect(self.update_status)
        self.command_update_timer.start(300)

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
        self.btn_config.clicked.connect(
            lambda: self.switch_tab(0, "Configuration", self.btn_config)
        )
        sidebar_layout.addWidget(self.btn_config)

        lbl_upload = QLabel("UPLOAD")
        lbl_upload.setObjectName("NavTitle")
        sidebar_layout.addWidget(lbl_upload)

        self.btn_takeout = QPushButton(" 📦  Google Takeout")
        self.btn_takeout.setObjectName("NavBtn")
        self.btn_takeout.setCheckable(True)
        self.btn_takeout.clicked.connect(
            lambda: self.switch_tab(1, "upload · from-google-photos", self.btn_takeout)
        )
        sidebar_layout.addWidget(self.btn_takeout)

        self.btn_local = QPushButton(" 📁  Local Upload")
        self.btn_local.setObjectName("NavBtn")
        self.btn_local.setCheckable(True)
        self.btn_local.clicked.connect(
            lambda: self.switch_tab(2, "upload · from-folder", self.btn_local)
        )
        sidebar_layout.addWidget(self.btn_local)

        lbl_organize = QLabel("ORGANIZE")
        lbl_organize.setObjectName("NavTitle")
        sidebar_layout.addWidget(lbl_organize)

        self.btn_stack = QPushButton(" 📚  Stack Assets")
        self.btn_stack.setObjectName("NavBtn")
        self.btn_stack.setCheckable(True)
        self.btn_stack.clicked.connect(
            lambda: self.switch_tab(3, "stack", self.btn_stack)
        )
        sidebar_layout.addWidget(self.btn_stack)

        sidebar_layout.addStretch()

        # Status Frame
        status_frame = QFrame()
        status_frame.setObjectName("StatusFrame")
        status_layout = QVBoxLayout(status_frame)

        row1 = QHBoxLayout()
        self.lbl_binary_status = QLabel("🟢 Binary: Ready")
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
        btn_setup.clicked.connect(
            lambda: self.switch_tab(0, "Configuration", self.btn_config)
        )
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

    def switch_tab(self, index, crumb, btn):
        self.stacked_widget.setCurrentIndex(index)
        self.update_header_crumb(crumb)

        # Uncheck all nav buttons
        for w in [self.btn_config, self.btn_takeout, self.btn_local, self.btn_stack]:
            w.setChecked(False)
        btn.setChecked(True)

        # Hide footer on config tab
        self.footer.setVisible(index != 0)

    def update_header_crumb(self, text):
        self.lbl_crumb.setText(text)

    def toggle_advanced(self, checked):
        self.is_advanced = checked
        self.lbl_mode.setText("Advanced" if checked else "Simple")
        for w in self.advanced_widgets:
            w.setVisible(checked)

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

    # ==========================================
    # FORM CREATION
    # ==========================================
    def create_configuration_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)

        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        def create_info_icon(tooltip):
            label = QLabel("(i)")
            label.setToolTip(tooltip)
            label.setStyleSheet("color: #666; font-style: italic;")
            return label

        # Server Settings
        server_group = QGroupBox("Immich Server Connection")
        server_group.setObjectName("Card")
        server_form = QFormLayout()
        self.server_url_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.skip_ssl_checkbox = QCheckBox("Skip SSL Verification")

        server_url_row = QHBoxLayout()
        server_url_row.addWidget(self.server_url_edit)
        server_url_row.addWidget(
            create_info_icon("Immich server URL (e.g. http://your-server:2283)")
        )
        server_url_row.addStretch()

        server_form.addRow("Server URL *:", server_url_row)
        server_form.addRow("API Key *:", self.api_key_edit)
        server_form.addRow(self.skip_ssl_checkbox)
        server_group.setLayout(server_form)
        layout.addWidget(server_group)

        # Global Settings
        global_group = QGroupBox("Global Output Settings")
        global_group.setObjectName("Card")
        global_form = QFormLayout()
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["INFO", "DEBUG", "WARN", "ERROR"])
        self.log_type_combo = QComboBox()
        self.log_type_combo.addItems(["TEXT", "JSON"])
        self.no_ui_check = QCheckBox("Disable UI Output")

        global_form.addRow("Log Level:", self.log_level_combo)
        global_form.addRow("Log Type:", self.log_type_combo)
        global_form.addRow(self.no_ui_check)
        global_group.setLayout(global_form)
        layout.addWidget(global_group)

        # Advanced Config
        adv_group = QGroupBox("Advanced Configuration")
        adv_group.setObjectName("Card")
        adv_form = QFormLayout()

        self.client_timeout_spin = QSpinBox()
        self.client_timeout_spin.setRange(1, 1440)
        self.client_timeout_spin.setValue(20)
        self.client_timeout_spin.setSuffix(" minutes")

        self.concurrent_tasks_spin = QSpinBox()
        self.concurrent_tasks_spin.setRange(1, 20)
        self.concurrent_tasks_spin.setValue(2)

        self.device_uuid_edit = QLineEdit()
        self.pause_immich_jobs_check = QCheckBox("Pause Immich Jobs")
        self.pause_immich_jobs_check.setChecked(True)
        self.on_errors_combo = QComboBox()
        self.on_errors_combo.addItems(["stop", "continue"])

        adv_form.addRow("Client Timeout:", self.client_timeout_spin)
        adv_form.addRow("Concurrent Tasks:", self.concurrent_tasks_spin)
        adv_form.addRow("Device UUID:", self.device_uuid_edit)
        adv_form.addRow("On Errors:", self.on_errors_combo)
        adv_form.addRow(self.pause_immich_jobs_check)

        adv_group.setLayout(adv_form)
        layout.addWidget(adv_group)
        self.advanced_widgets.append(adv_group)
        adv_group.setVisible(False)  # Hidden by default

        layout.addStretch()
        return scroll

    def create_google_takeout_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)

        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        def create_info_icon(tooltip):
            label = QLabel("(i)")
            label.setToolTip(tooltip)
            label.setStyleSheet("color: #666; font-style: italic;")
            return label

        # Source Selection
        file_group = QGroupBox("Source Configuration")
        file_group.setObjectName("Card")
        file_layout = QFormLayout()
        self.source_path_edit = QLineEdit()
        self.browse_btn = QPushButton("Browse ZIPs")
        self.source_path_edit.setAcceptDrops(True)
        self.source_path_edit.dragEnterEvent = self.dragEnterEvent
        self.source_path_edit.dropEvent = self.dropEvent

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_path_edit)
        source_row.addWidget(
            create_info_icon("Path to Google Takeout ZIP files or extracted folder.")
        )
        source_row.addStretch()

        file_layout.addRow("Path:", source_row)
        file_layout.addRow(self.browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Core Options
        core_group = QGroupBox("Options")
        core_form = QFormLayout()

        self.sync_albums_check = QCheckBox("Sync Albums")
        self.sync_albums_check.setChecked(True)
        self.include_archived_check = QCheckBox("Include Archived Photos")
        self.include_archived_check.setChecked(True)
        self.include_partner_check = QCheckBox("Include Partner Photos")
        self.include_partner_check.setChecked(True)
        self.include_trashed_check = QCheckBox("Include Trashed")
        self.include_trashed_check.setChecked(False)
        self.run_takeout_button = QPushButton(
            "Run Google Takeout"
        )  # Kept for backend compatibility, hidden visually
        self.run_takeout_button.setVisible(False)

        def add_form_row(form, widget, tooltip):
            row = QHBoxLayout()
            row.addWidget(widget)
            row.addWidget(create_info_icon(tooltip))
            row.addStretch()
            form.addRow(row)

        add_form_row(
            core_form,
            self.sync_albums_check,
            "Auto-create Immich albums matching Google Photos albums.",
        )
        add_form_row(
            core_form,
            self.include_archived_check,
            "Import photos marked as archived in Google Photos.",
        )
        add_form_row(
            core_form, self.include_partner_check, "Import partner-shared photos."
        )
        add_form_row(core_form, self.include_trashed_check, "Import trashed photos.")

        core_group.setLayout(core_form)
        layout.addWidget(core_group)

        # Advanced Options
        adv_group = QGroupBox("Advanced Options")
        adv_group.setObjectName("Card")
        adv_form = QFormLayout()

        self.include_unmatched_check = QCheckBox("Include Unmatched (No JSON)")
        self.include_untitled_albums_check = QCheckBox("Include Untitled Albums")
        self.takeout_tag_check = QCheckBox("Add Takeout Tag")
        self.takeout_tag_check.setChecked(True)
        self.people_tag_check = QCheckBox("Add People Tag")
        self.people_tag_check.setChecked(True)
        self.from_album_name_edit = QLineEdit()

        add_form_row(
            adv_form,
            self.include_unmatched_check,
            "Import files that have no matching JSON metadata.",
        )
        add_form_row(
            adv_form,
            self.include_untitled_albums_check,
            "Include photos from untitled albums.",
        )
        add_form_row(
            adv_form,
            self.takeout_tag_check,
            "Tag assets with {takeout}/takeout-YYYYMMDD...",
        )
        add_form_row(
            adv_form,
            self.people_tag_check,
            "Tag assets with people/<name> from JSON data.",
        )

        album_name_row = QHBoxLayout()
        album_name_row.addWidget(self.from_album_name_edit)
        album_name_row.addWidget(
            create_info_icon("Only import photos from one specific Google Photos album")
        )
        album_name_row.addStretch()
        adv_form.addRow("From Album Only:", album_name_row)

        adv_group.setLayout(adv_form)
        layout.addWidget(adv_group)
        self.advanced_widgets.append(adv_group)
        adv_group.setVisible(False)

        layout.addStretch()

        self.browse_btn.clicked.connect(self.browse_takeout_source)

        return scroll

    def create_local_upload_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)

        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        def create_info_icon(tooltip):
            label = QLabel("(i)")
            label.setToolTip(tooltip)
            label.setStyleSheet("color: #666; font-style: italic;")
            return label

        # Source Folder
        source_group = QGroupBox("Source Configuration")
        source_group.setObjectName("Card")
        source_layout = QFormLayout()
        self.local_path_edit = QLineEdit()
        self.local_browse_btn = QPushButton("Browse")
        self.local_path_edit.setAcceptDrops(True)
        self.local_path_edit.dragEnterEvent = self.dragEnterEvent
        self.local_path_edit.dropEvent = self.dropEvent

        local_path_row = QHBoxLayout()
        local_path_row.addWidget(self.local_path_edit)
        local_path_row.addWidget(
            create_info_icon("Path to the local folder containing media to upload.")
        )
        local_path_row.addStretch()
        source_layout.addRow("Path:", local_path_row)
        source_layout.addRow(self.local_browse_btn)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # Upload Options
        upload_group = QGroupBox("Options")
        upload_group.setObjectName("Card")
        upload_form = QFormLayout()
        self.album_name_edit = QLineEdit()

        self.folder_as_album_combo = QComboBox()
        self.folder_as_album_combo.addItems(["NONE", "FOLDER", "PATH"])
        self.folder_as_tags_check = QCheckBox("Folder as Tags")

        self.manage_burst_combo = QComboBox()
        self.manage_burst_combo.addItems(
            ["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"]
        )

        self.manage_raw_jpeg_combo = QComboBox()
        self.manage_raw_jpeg_combo.addItems(
            ["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"]
        )

        self.manage_heic_jpeg_combo = QComboBox()
        self.manage_heic_jpeg_combo.addItems(
            ["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"]
        )

        self.run_local_button = QPushButton("Run Local Upload")
        self.run_local_button.setVisible(False)

        album_name_row = QHBoxLayout()
        album_name_row.addWidget(self.album_name_edit)
        album_name_row.addWidget(
            create_info_icon(
                "Specify an album name to upload all media into a single album."
            )
        )
        album_name_row.addStretch()
        upload_form.addRow("Into Album:", album_name_row)
        upload_form.addRow("Folder as Album:", self.folder_as_album_combo)
        upload_form.addRow(self.folder_as_tags_check)
        upload_form.addRow("Manage Burst:", self.manage_burst_combo)
        upload_form.addRow("Manage RAW+JPEG:", self.manage_raw_jpeg_combo)
        upload_form.addRow("Manage HEIC+JPEG:", self.manage_heic_jpeg_combo)

        upload_group.setLayout(upload_form)
        layout.addWidget(upload_group)

        # Advanced Options
        adv_group = QGroupBox("Advanced Options")
        adv_group.setObjectName("Card")
        adv_layout = QVBoxLayout()

        # Date Filter
        date_group = QGroupBox("Date Filter")
        date_layout = QVBoxLayout()
        self.date_check = QCheckBox("Enable Date Filter")
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.end_date.setDate(QDate.currentDate())
        self.start_date.setEnabled(False)
        self.end_date.setEnabled(False)

        date_check_row = QHBoxLayout()
        date_check_row.addWidget(self.date_check)
        date_check_row.addWidget(
            create_info_icon("Filter media files based on their EXIF date range.")
        )
        date_check_row.addStretch()
        date_layout.addLayout(date_check_row)
        date_layout.addWidget(QLabel("Start Date:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("End Date:"))
        date_layout.addWidget(self.end_date)
        date_group.setLayout(date_layout)
        adv_layout.addWidget(date_group)

        # File Type Filter
        type_group = QGroupBox("File Type Filter")
        type_layout = QVBoxLayout()
        self.type_check = QCheckBox("Filter by Extensions")
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText(".jpg,.png,.heic")
        self.type_edit.setEnabled(False)

        type_check_row = QHBoxLayout()
        type_check_row.addWidget(self.type_check)
        type_check_row.addWidget(
            create_info_icon("Filter media files by their file extensions.")
        )
        type_check_row.addStretch()
        type_layout.addLayout(type_check_row)
        type_edit_row = QHBoxLayout()
        type_edit_row.addWidget(self.type_edit)
        type_edit_row.addWidget(
            create_info_icon("Enter comma-separated file extensions (e.g., .jpg,.mp4).")
        )
        type_edit_row.addStretch()
        type_layout.addLayout(type_edit_row)
        type_group.setLayout(type_layout)
        adv_layout.addWidget(type_group)

        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)
        self.advanced_widgets.append(adv_group)
        adv_group.setVisible(False)

        layout.addStretch()

        self.date_check.toggled.connect(lambda checked: self.toggle_dates(checked))
        self.type_check.toggled.connect(
            lambda checked: self.type_edit.setEnabled(checked)
        )
        self.local_browse_btn.clicked.connect(self.browse_local_folder)

        return scroll

    def create_stack_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)

        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        def create_info_icon(tooltip):
            label = QLabel("(i)")
            label.setToolTip(tooltip)
            label.setStyleSheet("color: #666; font-style: italic;")
            return label

        stack_group = QGroupBox("Options")
        stack_group.setObjectName("Card")
        stack_form = QFormLayout()

        self.stack_manage_burst_combo = QComboBox()
        self.stack_manage_burst_combo.addItems(
            ["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"]
        )

        self.stack_manage_raw_jpeg_combo = QComboBox()
        self.stack_manage_raw_jpeg_combo.addItems(
            ["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"]
        )

        self.stack_manage_heic_jpeg_combo = QComboBox()
        self.stack_manage_heic_jpeg_combo.addItems(
            ["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"]
        )

        self.manage_epson_fastfoto_check = QCheckBox("Manage Epson FastFoto")
        self.stack_time_zone_edit = QLineEdit()
        self.run_stack_button = QPushButton("Run Stack")
        self.run_stack_button.setVisible(False)

        stack_form.addRow("Manage Burst:", self.stack_manage_burst_combo)
        stack_form.addRow("Manage RAW+JPEG:", self.stack_manage_raw_jpeg_combo)
        stack_form.addRow("Manage HEIC+JPEG:", self.stack_manage_heic_jpeg_combo)
        stack_form.addRow(self.manage_epson_fastfoto_check)
        stack_form.addRow("Time Zone:", self.stack_time_zone_edit)

        stack_group.setLayout(stack_form)
        layout.addWidget(stack_group)

        layout.addStretch()
        return scroll

    # ==========================================
    # LOGIC & BACKEND
    # ==========================================
    @staticmethod
    def get_latest_release_info():
        try:
            api_url = "https://api.github.com/repos/simulot/immich-go/releases/latest"
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()["tag_name"]
        except Exception as e:
            print(f"Failed to fetch release information: {e}")
            return None

    def get_download_url(self, version=None):
        os_name = sys.platform
        arch = platform.machine().lower()
        download_mapping = {
            ("win32", "amd64"): "immich-go_Windows_x86_64.zip",
            ("win32", "x86_64"): "immich-go_Windows_x86_64.zip",
            ("win32", "arm64"): "immich-go_Windows_arm64.zip",
            ("darwin", "x86_64"): "immich-go_Darwin_x86_64.tar.gz",
            ("darwin", "arm64"): "immich-go_Darwin_arm64.tar.gz",
            ("linux", "x86_64"): "immich-go_Linux_x86_64.tar.gz",
            ("linux", "arm64"): "immich-go_Linux_arm64.tar.gz",
            ("freebsd", "x86_64"): "immich-go_Freebsd_x86_64.tar.gz",
        }
        if arch in ["x64", "x86_64"]:
            arch = "x86_64"
        key = (os_name, arch)
        if key in download_mapping:
            if version is None:
                version = self.get_latest_release_info() or "0.22.1"
            filename = download_mapping[key]
            return f"https://github.com/simulot/immich-go/releases/download/{version}/{filename}"
        return None

    def update_binary(self):
        binary_folder = os.path.abspath(os.path.join(os.getcwd(), "immich-go"))
        if not os.path.exists(binary_folder):
            os.makedirs(binary_folder)

        binary_filename = (
            "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        )
        binary_path = os.path.join(binary_folder, binary_filename)
        self.binary_path = binary_path

        if os.path.exists(binary_path):
            self.lbl_binary_status.setText("🟢 Binary: Ready")
            return True

        # Download logic omitted for brevity, but would go here.
        # Refer to original file for download thread implementation.
        # For now, we just warn if missing.
        self.lbl_binary_status.setText("🔴 Binary: Missing")
        return False

    def run_command(self, command_parts=None):
        if command_parts is None:
            command_parts = []
        if not hasattr(self, "binary_path") or not os.path.exists(self.binary_path):
            if not self.update_binary():
                QMessageBox.critical(
                    self, "Error", "Immich-Go binary is missing or not executable."
                )
                return

        command = [self.binary_path] + command_parts

        try:
            self.btn_run.setDisabled(True)
            self.btn_dry_run.setDisabled(True)

            if sys.platform.startswith("win"):
                cmd_string = subprocess.list2cmdline(command)
                proc = subprocess.Popen(
                    ["cmd", "/c", "start", "cmd", "/k", cmd_string],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                self.running_process = proc.pid
            elif sys.platform.startswith("darwin"):
                apple_script = f'tell application "Terminal" to do script "{shlex.join(command)}; exec bash"'
                proc = subprocess.Popen(["osascript", "-e", apple_script])
                self.running_process = proc
            else:
                terminals = [
                    (
                        "gnome-terminal",
                        "--",
                        "bash",
                        "-c",
                        f"{shlex.join(command)}; exec bash",
                    ),
                    (
                        "konsole",
                        "-e",
                        "bash",
                        "-c",
                        f"{shlex.join(command)}; exec bash",
                    ),
                    (
                        "xfce4-terminal",
                        "-e",
                        "bash",
                        "-c",
                        f"{shlex.join(command)}; exec bash",
                    ),
                    ("xterm", "-hold", "-e", shlex.join(command)),
                ]
                for term in terminals:
                    try:
                        proc = subprocess.Popen(term)
                        self.running_process = proc
                        break
                    except FileNotFoundError:
                        continue
                else:
                    QMessageBox.critical(
                        self, "Error", "No suitable terminal emulator found."
                    )
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
            if psutil.pid_exists(self.running_process):
                still_running = True
        else:
            if (
                hasattr(self.running_process, "poll")
                and self.running_process.poll() is None
            ):
                still_running = True

        if still_running:
            self.status_indicator.setText("⚠️ Running... Close terminal to continue.")
        else:
            self.check_process_timer.stop()
            self.running_process = None
            self.btn_run.setDisabled(False)
            self.btn_dry_run.setDisabled(False)
            self.update_status()

    def validate_inputs(self):
        required = [(self.server_url_edit, r"^https?://.+"), (self.api_key_edit, r".+")]
        is_valid = True
        for field, pattern in required:
            if not re.match(pattern, field.text()):
                field.setStyleSheet("border: 1px solid red;")
                is_valid = False
            else:
                field.setStyleSheet("")
        return is_valid

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        target = self.sender() if self.sender() else event.widget()
        if isinstance(target, QLineEdit):
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            if target == self.source_path_edit:
                current_text = self.source_path_edit.text()
                separator = "; " if current_text else ""
                self.source_path_edit.setText(
                    current_text + separator + "; ".join(paths)
                )
            elif target == self.local_path_edit:
                self.local_path_edit.setText(paths[0])
            event.acceptProposedAction()

    def browse_takeout_source(self):
        # Simplified for this example
        folder = QFileDialog.getExistingDirectory(self, "Select Extracted Folder")
        if folder:
            self.source_path_edit.setText(folder)

    def toggle_dates(self, enabled):
        self.start_date.setEnabled(enabled)
        self.end_date.setEnabled(enabled)

    def browse_local_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Upload Folder")
        if folder:
            self.local_path_edit.setText(folder)

    def get_global_options(self):
        opts = []
        if self.log_level_combo.currentText() != "INFO":
            opts.append(f"--log-level={self.log_level_combo.currentText()}")
        if self.log_type_combo.currentText() != "TEXT":
            opts.append(f"--log-type={self.log_type_combo.currentText()}")
        if self.no_ui_check.isChecked():
            opts.append("--no-ui")
        return opts

    def get_server_options(self):
        opts = []
        if self.server_url_edit.text():
            opts.append(f"--server={self.server_url_edit.text()}")
        if self.api_key_edit.text():
            opts.append(f"--api-key={self.api_key_edit.text()}")
        if self.skip_ssl_checkbox.isChecked():
            opts.append("--skip-verify-ssl")
        if self.client_timeout_spin.value() != 20:
            opts.append(f"--client-timeout={self.client_timeout_spin.value()}m")
        if self.device_uuid_edit.text():
            opts.append(f"--device-uuid={self.device_uuid_edit.text()}")
        return opts

    def get_upload_behavior_options(self):
        opts = []
        if self.concurrent_tasks_spin.value() != 2:
            opts.append(f"--concurrent-tasks={self.concurrent_tasks_spin.value()}")
        if not self.pause_immich_jobs_check.isChecked():
            opts.append("--pause-immich-jobs=false")
        if self.on_errors_combo.currentText() != "stop":
            opts.append(f"--on-errors={self.on_errors_combo.currentText()}")
        return opts

    def get_command_and_tab_options(self):
        current_tab = self.stacked_widget.currentIndex()
        opts = []
        paths = []

        if current_tab == 1:  # Google Takeout
            opts += ["upload", "from-google-photos"]
            opts += self.get_server_options()
            opts += self.get_upload_behavior_options()

            if not self.sync_albums_check.isChecked():
                opts.append("--sync-albums=false")
            if not self.include_archived_check.isChecked():
                opts.append("--include-archived=false")
            if not self.include_partner_check.isChecked():
                opts.append("--include-partner=false")
            if self.include_trashed_check.isChecked():
                opts.append("--include-trashed=true")
            if self.include_unmatched_check.isChecked():
                opts.append("--include-unmatched=true")
            if self.include_untitled_albums_check.isChecked():
                opts.append("--include-untitled-albums=true")
            if not self.takeout_tag_check.isChecked():
                opts.append("--takeout-tag=false")
            if not self.people_tag_check.isChecked():
                opts.append("--people-tag=false")
            if self.from_album_name_edit.text():
                opts.append(f"--from-album-name={self.from_album_name_edit.text()}")

            source_path = self.source_path_edit.text()
            if source_path:
                paths = [source_path]

        elif current_tab == 2:  # Local Upload
            opts += ["upload", "from-folder"]
            opts += self.get_server_options()
            opts += self.get_upload_behavior_options()

            if self.date_check.isChecked():
                start = self.start_date.date().toString("yyyy-MM-dd")
                end = self.end_date.date().toString("yyyy-MM-dd")
                opts.append(f"--date-range={start},{end}")
            if self.type_check.isChecked() and self.type_edit.text():
                exts = self.type_edit.text().replace(" ", "").strip()
                if exts:
                    opts.append(f"--include-extensions={exts}")
            if self.album_name_edit.text():
                opts.append(f"--into-album={self.album_name_edit.text()}")
            if self.folder_as_album_combo.currentText() != "NONE":
                opts.append(
                    f"--folder-as-album={self.folder_as_album_combo.currentText()}"
                )
            if self.folder_as_tags_check.isChecked():
                opts.append("--folder-as-tags=true")
            if self.manage_burst_combo.currentText() != "NoStack":
                opts.append(f"--manage-burst={self.manage_burst_combo.currentText()}")
            if self.manage_raw_jpeg_combo.currentText() != "NoStack":
                opts.append(
                    f"--manage-raw-jpeg={self.manage_raw_jpeg_combo.currentText()}"
                )
            if self.manage_heic_jpeg_combo.currentText() != "NoStack":
                opts.append(
                    f"--manage-heic-jpeg={self.manage_heic_jpeg_combo.currentText()}"
                )

            if self.local_path_edit.text():
                paths = [self.local_path_edit.text()]

        elif current_tab == 3:  # Stack
            opts += ["stack"]
            opts += self.get_server_options()

            if self.stack_manage_burst_combo.currentText() != "NoStack":
                opts.append(
                    f"--manage-burst={self.stack_manage_burst_combo.currentText()}"
                )
            if self.stack_manage_raw_jpeg_combo.currentText() != "NoStack":
                opts.append(
                    f"--manage-raw-jpeg={self.stack_manage_raw_jpeg_combo.currentText()}"
                )
            if self.stack_manage_heic_jpeg_combo.currentText() != "NoStack":
                opts.append(
                    f"--manage-heic-jpeg={self.stack_manage_heic_jpeg_combo.currentText()}"
                )
            if self.manage_epson_fastfoto_check.isChecked():
                opts.append("--manage-epson-fastfoto=true")
            if self.stack_time_zone_edit.text():
                opts.append(f"--time-zone={self.stack_time_zone_edit.text()}")

        return opts + paths

    def show_confirm_dialog(self, is_dry_run):
        if self.stacked_widget.currentIndex() == 0:
            return

        parts = [self.binary_path] if hasattr(self, "binary_path") else ["./immich-go"]
        parts += self.get_global_options()
        parts += self.get_command_and_tab_options()

        if is_dry_run:
            if "--dry-run" not in parts:
                parts.append("--dry-run")
        else:
            if "--dry-run" in parts:
                parts.remove("--dry-run")

        cmd_str = " ".join(shlex.quote(p) for p in parts)

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

        desc = QLabel(
            "A dry run simulates the action. No files are changed."
            if is_dry_run
            else "This executes the real command."
        )
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
            self.run_command(parts[1:])  # Pass command without binary path

    def update_status(self):
        if self.validate_inputs():
            self.status_indicator.setText("🟢 Server: Ready")
            self.btn_run.setEnabled(True)
            self.btn_dry_run.setEnabled(True)
        else:
            self.status_indicator.setText("🔴 Server: Not Set")
            self.btn_run.setEnabled(False)
            self.btn_dry_run.setEnabled(False)

    def save_configuration(self):
        self.settings.setValue("server_url", self.server_url_edit.text())
        self.settings.setValue("api_key", self.api_key_edit.text())
        QMessageBox.information(self, "Saved", "Configuration saved successfully.")

    def load_configuration(self):
        self.server_url_edit.setText(self.settings.value("server_url", ""))
        self.api_key_edit.setText(self.settings.value("api_key", ""))

    def open_github_link(self):
        webbrowser.open("https://github.com/simulot/immich-go")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = ImmichGoGUI()
    window.show()
    sys.exit(app.exec())
