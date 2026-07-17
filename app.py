import sys
import os
import re  # For input validation
import psutil
import requests
import io
import subprocess  # For running external commands
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QCheckBox, QComboBox, QPushButton, QFileDialog,
    QTextEdit, QTabWidget, QGroupBox, QSpinBox, QDateEdit, QSizePolicy,
    QScrollArea, QRadioButton, QMessageBox, QDialog, QProgressBar
)
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QDesktopServices, QIcon
from PySide6.QtCore import Qt, QDate, QTimer, QUrl, QSettings, QThread, Signal
import shlex # For proper command quoting
import platform
import webbrowser

class ImmichGoGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immich-Go GUI")
        self.setGeometry(100, 100, 900, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Improved margins and spacing for a clean layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabBar::tab {
                background: #546E7A;
                padding: 10px 24px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                color: white;
                font-weight: 500;
                margin-right: 2px;
                border: none;
            }
            QTabBar::tab:selected {
                background: #37474F;
                color: white;
                border-bottom: 2px solid #263238;
            }
            QTabBar::tab:hover:!selected {
                background: #455A64;
            }
            QPushButton {
                background: #546E7A;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #455A64;
            }
            QPushButton:pressed {
                background: #37474F;
            }
            QPushButton:disabled {
                background: #B0BEC5;
                color: #90A4AE;
            }
        """)
        # Add the tab widget to the main layout
        self.main_layout.addWidget(self.tab_widget)

        self.create_menu_bar()
        self.create_configuration_tab()
        self.create_google_takeout_tab()
        self.create_local_upload_tab()
        self.create_stack_tab()

        # Command Preview Section with refined size policy
        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(80)
        self.command_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout.addWidget(QLabel("Command Preview:"))
        self.main_layout.addWidget(self.command_preview)

        # Status Indicator
        self.status_indicator = QLabel()
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.status_indicator)

        # Timer for command preview update
        self.command_update_timer = QTimer(self)
        self.command_update_timer.timeout.connect(self.update_command_preview)
        self.command_update_timer.start(300)

        self.settings = QSettings("YourOrganization", "ImmichGoGUI")

        # Check for and update (or download) the immich-go binary
        self.update_binary()

        self.load_configuration()
        
        self.tab_widget.currentChanged.connect(self.update_command_preview)

    @staticmethod
    def get_latest_release_info():
        """Fetch the latest release information from GitHub."""
        try:
            # GitHub API to get the latest release
            api_url = "https://api.github.com/repos/simulot/immich-go/releases/latest"
            response = requests.get(api_url)
            response.raise_for_status()
            release_data = response.json()

            # Get the release tag (version)
            latest_version = release_data['tag_name']

            return latest_version
        except Exception as e:
            print(f"Failed to fetch release information: {e}")
            return None

    def get_download_url(self, version=None):
        """Generate the appropriate download URL based on the system."""
        os_name = sys.platform
        arch = platform.machine().lower()

        # Mapping of OS and architecture to download filename
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

        # Normalize some variations
        if arch in ['x64', 'x86_64']:
            arch = 'x86_64'

        key = (os_name, arch)
        if key in download_mapping:
            # Use provided version or fetch latest
            if version is None:
                version = self.get_latest_release_info() or '0.22.1'

            filename = download_mapping[key]
            return f'https://github.com/simulot/immich-go/releases/download/{version}/{filename}'

        return None

    def update_binary(self):
        binary_folder = os.path.abspath(os.path.join(os.getcwd(), "immich-go"))
        if not os.path.exists(binary_folder):
            os.makedirs(binary_folder)

        # Determine correct binary name for OS
        binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"
        binary_path = os.path.join(binary_folder, binary_filename)
        self.binary_path = binary_path

        # Check if binary exists
        if not os.path.exists(binary_path):
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

                        # Set executable permissions for non-Windows systems
                        if not sys.platform.startswith("win"):
                            os.chmod(binary_path, 0o755)

                    except Exception as extraction_error:
                        QMessageBox.critical(self, "Extraction Error",
                            f"Failed to extract binary: {str(extraction_error)}\n\n"
                            "Please download manually from GitHub.")

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
                        "Please download the binary manually:\n\n"
                        f"1. Visit: {download_url}\n"
                        f"2. Download the appropriate binary for your system\n"
                        f"3. Place it in: {binary_folder}\n"
                        "4. Rename to 'immich-go' (or 'immich-go.exe' on Windows)\n"
                        "5. Ensure it has executable permissions"
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
                    f"Failed to initiate download: {str(e)}\n\n"
                    "Please download manually from GitHub.")
                return False

        return True

    def run_command(self, command_parts=None):
        if command_parts is None:
            command_parts = []

        # Ensure binary path is correctly referenced
        if not hasattr(self, 'binary_path') or not os.path.exists(self.binary_path):
            if not self.update_binary():  # Check and update binary path
                QMessageBox.critical(self, "Error", "Immich-Go binary is missing or not executable.")
                return

        # Command structure is strictly generated in update_command_preview and passed via command_parts
        command = [self.binary_path] + command_parts

        try:
            self.run_local_button.setDisabled(True)
            self.run_takeout_button.setDisabled(True)
            if hasattr(self, 'run_stack_button'):
                self.run_stack_button.setDisabled(True)

            if sys.platform.startswith("win"):
                # Properly format the command line for Windows
                cmd_string = subprocess.list2cmdline(command)
                proc = subprocess.Popen(
                    ['cmd', '/c', 'start', 'cmd', '/k', cmd_string],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                self.running_process = proc.pid

            elif sys.platform.startswith("darwin"):
                # MacOS handling (unchanged)
                apple_script = f'tell application "Terminal" to do script "{shlex.join(command)}; exec bash"'
                proc = subprocess.Popen(["osascript", "-e", apple_script])
                self.running_process = proc

            else:  # Linux
                # Linux handling (unchanged)
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
                    except FileNotFoundError:
                        continue
                else:
                    QMessageBox.critical(self, "Error", "No suitable terminal emulator found.")
                    self.run_local_button.setDisabled(False)
                    self.run_takeout_button.setDisabled(False)
                    if hasattr(self, 'run_stack_button'):
                        self.run_stack_button.setDisabled(False)
                    return

            # Start timer to monitor process
            self.check_process_timer = QTimer()
            self.check_process_timer.timeout.connect(self.check_if_process_running)
            self.check_process_timer.start(1000)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run command: {e}")
            self.run_local_button.setDisabled(False)
            self.run_takeout_button.setDisabled(False)
            if hasattr(self, 'run_stack_button'):
                self.run_stack_button.setDisabled(False)
            self.running_process = None


    def check_if_process_running(self):
        still_running = False

        if sys.platform.startswith("win"):
            # On Windows, check if the stored PID is still running
            if psutil.pid_exists(self.running_process):
                still_running = True

        else:
            # On Linux/macOS, use the Popen object to check process status
            if hasattr(self.running_process, "poll") and self.running_process.poll() is None:
                still_running = True

        if still_running:
            self.status_indicator.setText("⚠️ Please close the Immich-Go terminal window to process more.")
            self.status_indicator.setStyleSheet("color: orange; font-weight: bold;")
        else:
            # Process has finished
            self.check_process_timer.stop()
            self.running_process = None
            self.run_local_button.setDisabled(False)
            self.run_takeout_button.setDisabled(False)
            if hasattr(self, 'run_stack_button'):
                self.run_stack_button.setDisabled(False)
            self.status_indicator.setText("✓ Ready to go!")
            self.status_indicator.setStyleSheet("color: green; font-weight: bold;")


    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        save_action = QAction(QIcon("icons/save.png"), "Save Configuration", self)
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
    def create_configuration_tab(self):
        config_tab = QWidget()
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setWidget(config_tab)

        layout = QVBoxLayout(config_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        def create_info_icon(tooltip):
            label = QLabel("(i)")
            label.setToolTip(tooltip)
            label.setStyleSheet("color: #666; font-style: italic;")
            return label

        server_group = QGroupBox("Server Settings")
        server_form = QFormLayout()
        self.server_url_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.skip_ssl_checkbox = QCheckBox("Skip SSL Verification")

        server_url_row = QHBoxLayout()
        server_url_row.addWidget(self.server_url_edit)
        server_url_row.addWidget(create_info_icon("Immich server URL (e.g. http://your-server:2283)"))
        server_url_row.addStretch()

        server_form.addRow("Server URL *:", server_url_row)
        server_form.addRow("API Key *:", self.api_key_edit)
        server_form.addRow(self.skip_ssl_checkbox)
        server_group.setLayout(server_form)
        layout.addWidget(server_group)

        global_group = QGroupBox("Global Output Settings")
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

        adv_group = QGroupBox("Advanced Configuration")
        adv_group.setObjectName("Advanced Configuration")
        adv_group.setCheckable(True)
        adv_group.setChecked(False)
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

        layout.addStretch()
        self.tab_widget.addTab(config_scroll, "Configuration")

        self.server_url_edit.textChanged.connect(self.validate_inputs)
        self.api_key_edit.textChanged.connect(self.validate_inputs)
        self.server_url_edit.textChanged.connect(self.update_status)
        self.api_key_edit.textChanged.connect(self.update_status)
        
        self.log_level_combo.currentIndexChanged.connect(self.update_command_preview)
        self.log_type_combo.currentIndexChanged.connect(self.update_command_preview)
        self.no_ui_check.toggled.connect(self.update_command_preview)
        self.client_timeout_spin.valueChanged.connect(self.update_command_preview)
        self.concurrent_tasks_spin.valueChanged.connect(self.update_command_preview)
        self.device_uuid_edit.textChanged.connect(self.update_command_preview)
        self.on_errors_combo.currentIndexChanged.connect(self.update_command_preview)
        self.pause_immich_jobs_check.toggled.connect(self.update_command_preview)
        self.skip_ssl_checkbox.toggled.connect(self.update_command_preview)
    def create_google_takeout_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)

        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        def create_info_icon(tooltip):
            label = QLabel("(i)")
            label.setToolTip(tooltip)
            label.setStyleSheet("color: #666; font-style: italic;")
            return label

        file_group = QGroupBox("Source Selection")
        file_layout = QFormLayout()
        self.source_path_edit = QLineEdit()
        self.browse_btn = QPushButton("Browse ZIPs")
        self.source_path_edit.setAcceptDrops(True)
        self.source_path_edit.dragEnterEvent = self.dragEnterEvent
        self.source_path_edit.dropEvent = self.dropEvent

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_path_edit)
        source_row.addWidget(create_info_icon("Path to Google Takeout ZIP files or extracted folder."))
        source_row.addStretch()

        file_layout.addRow("Path:", source_row)
        file_layout.addRow(self.browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        source_group = QGroupBox("Source Type")
        source_layout = QVBoxLayout()
        self.zip_radio = QRadioButton("Process ZIP archives")
        self.folder_radio = QRadioButton("Process extracted folder")
        self.zip_radio.setChecked(True)

        source_layout.addWidget(self.zip_radio)
        source_layout.addWidget(self.folder_radio)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        core_group = QGroupBox("Processing Options")
        core_form = QFormLayout()
        
        self.sync_albums_check = QCheckBox("Sync Albums")
        self.sync_albums_check.setChecked(True)
        self.include_archived_check = QCheckBox("Include Archived Photos")
        self.include_archived_check.setChecked(True)
        self.include_partner_check = QCheckBox("Include Partner Photos")
        self.include_partner_check.setChecked(True)
        self.include_trashed_check = QCheckBox("Include Trashed")
        self.include_trashed_check.setChecked(False)
        self.takeout_dry_run_check = QCheckBox("Dry Run Mode")
        self.run_takeout_button = QPushButton("Run Google Takeout")
        self.run_takeout_button.setEnabled(False) # Initially disabled

        def add_form_row(form, widget, tooltip):
            row = QHBoxLayout()
            row.addWidget(widget)
            row.addWidget(create_info_icon(tooltip))
            row.addStretch()
            form.addRow(row)

        add_form_row(core_form, self.sync_albums_check, "Auto-create Immich albums matching Google Photos albums.")
        add_form_row(core_form, self.include_archived_check, "Import photos marked as archived in Google Photos.")
        add_form_row(core_form, self.include_partner_check, "Import partner-shared photos.")
        add_form_row(core_form, self.include_trashed_check, "Import trashed photos.")
        add_form_row(core_form, self.takeout_dry_run_check, "Simulate the upload without transferring files.")
        
        core_group.setLayout(core_form)
        layout.addWidget(core_group)

        adv_group = QGroupBox("Advanced Options")
        adv_group.setObjectName("Advanced Options")
        adv_group.setCheckable(True)
        adv_group.setChecked(False)
        adv_form = QFormLayout()

        self.include_unmatched_check = QCheckBox("Include Unmatched (No JSON)")
        self.include_untitled_albums_check = QCheckBox("Include Untitled Albums")
        self.takeout_tag_check = QCheckBox("Add Takeout Tag")
        self.takeout_tag_check.setChecked(True)
        self.people_tag_check = QCheckBox("Add People Tag")
        self.people_tag_check.setChecked(True)
        
        self.from_album_name_edit = QLineEdit()

        add_form_row(adv_form, self.include_unmatched_check, "Import files that have no matching JSON metadata.")
        add_form_row(adv_form, self.include_untitled_albums_check, "Include photos from untitled albums.")
        add_form_row(adv_form, self.takeout_tag_check, "Tag assets with {takeout}/takeout-YYYYMMDD...")
        add_form_row(adv_form, self.people_tag_check, "Tag assets with people/<name> from JSON data.")
        
        album_name_row = QHBoxLayout()
        album_name_row.addWidget(self.from_album_name_edit)
        album_name_row.addWidget(create_info_icon("Only import photos from one specific Google Photos album"))
        album_name_row.addStretch()
        adv_form.addRow("From Album Only:", album_name_row)
        
        adv_group.setLayout(adv_form)
        layout.addWidget(adv_group)
        layout.addWidget(self.run_takeout_button)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Google Takeout")

        self.browse_btn.clicked.connect(self.browse_takeout_source)
        self.zip_radio.toggled.connect(self.update_browse_mode)
        self.folder_radio.toggled.connect(self.update_browse_mode)
        self.run_takeout_button.clicked.connect(lambda: self.run_command(self.get_command_and_tab_options()))
        
        self.source_path_edit.textChanged.connect(self.update_command_preview)
        self.sync_albums_check.toggled.connect(self.update_command_preview)
        self.include_archived_check.toggled.connect(self.update_command_preview)
        self.include_partner_check.toggled.connect(self.update_command_preview)
        self.include_trashed_check.toggled.connect(self.update_command_preview)
        self.takeout_dry_run_check.toggled.connect(self.update_command_preview)
        self.include_unmatched_check.toggled.connect(self.update_command_preview)
        self.include_untitled_albums_check.toggled.connect(self.update_command_preview)
        self.takeout_tag_check.toggled.connect(self.update_command_preview)
        self.people_tag_check.toggled.connect(self.update_command_preview)
        self.from_album_name_edit.textChanged.connect(self.update_command_preview)
    def create_local_upload_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)

        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        def create_info_icon(tooltip):
            label = QLabel("(i)")
            label.setToolTip(tooltip)
            label.setStyleSheet("color: #666; font-style: italic;")
            return label

        source_group = QGroupBox("Source Folder")
        source_layout = QFormLayout()
        self.local_path_edit = QLineEdit()
        self.local_browse_btn = QPushButton("Browse")
        self.local_path_edit.setAcceptDrops(True)
        self.local_path_edit.dragEnterEvent = self.dragEnterEvent
        self.local_path_edit.dropEvent = self.dropEvent

        local_path_row = QHBoxLayout()
        local_path_row.addWidget(self.local_path_edit)
        local_path_row.addWidget(create_info_icon("Path to the local folder containing media to upload."))
        local_path_row.addStretch()
        source_layout.addRow("Path:", local_path_row)
        source_layout.addRow(self.local_browse_btn)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

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
        date_check_row.addWidget(create_info_icon("Filter media files based on their EXIF date range."))
        date_check_row.addStretch()
        date_layout.addLayout(date_check_row)
        date_layout.addWidget(QLabel("Start Date:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("End Date:"))
        date_layout.addWidget(self.end_date)
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        type_group = QGroupBox("File Type Filter")
        type_layout = QVBoxLayout()
        self.type_check = QCheckBox("Filter by Extensions")
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText(".jpg,.png,.heic")
        self.type_edit.setEnabled(False)

        type_check_row = QHBoxLayout()
        type_check_row.addWidget(self.type_check)
        type_check_row.addWidget(create_info_icon("Filter media files by their file extensions."))
        type_check_row.addStretch()
        type_layout.addLayout(type_check_row)
        type_edit_row = QHBoxLayout()
        type_edit_row.addWidget(self.type_edit)
        type_edit_row.addWidget(create_info_icon("Enter comma-separated file extensions (e.g., .jpg,.mp4)."))
        type_edit_row.addStretch()
        type_layout.addLayout(type_edit_row)
        type_preset_layout = QHBoxLayout()
        photo_preset = QPushButton("Photos")
        photo_preset.clicked.connect(lambda: self.type_edit.setText(".jpg,.jpeg,.png,.heic"))
        video_preset = QPushButton("Videos")
        video_preset.clicked.connect(lambda: self.type_edit.setText(".mp4,.mov,.avi"))
        type_preset_layout.addWidget(photo_preset)
        type_preset_layout.addWidget(video_preset)
        type_layout.addLayout(type_preset_layout)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        upload_group = QGroupBox("Upload Options")
        upload_form = QFormLayout()
        self.album_name_edit = QLineEdit()
        
        self.folder_as_album_combo = QComboBox()
        self.folder_as_album_combo.addItems(["NONE", "FOLDER", "PATH"])
        self.folder_as_tags_check = QCheckBox("Folder as Tags")

        self.manage_burst_combo = QComboBox()
        self.manage_burst_combo.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        
        self.manage_raw_jpeg_combo = QComboBox()
        self.manage_raw_jpeg_combo.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        
        self.manage_heic_jpeg_combo = QComboBox()
        self.manage_heic_jpeg_combo.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])

        self.dry_run_check = QCheckBox("Dry Run Mode")
        self.run_local_button = QPushButton("Run Local Upload")
        self.run_local_button.setEnabled(False) # Initially disabled

        album_name_row = QHBoxLayout()
        album_name_row.addWidget(self.album_name_edit)
        album_name_row.addWidget(create_info_icon("Specify an album name to upload all media into a single album."))
        album_name_row.addStretch()
        upload_form.addRow("Into Album:", album_name_row)
        upload_form.addRow("Folder as Album:", self.folder_as_album_combo)
        upload_form.addRow(self.folder_as_tags_check)
        upload_form.addRow("Manage Burst:", self.manage_burst_combo)
        upload_form.addRow("Manage RAW+JPEG:", self.manage_raw_jpeg_combo)
        upload_form.addRow("Manage HEIC+JPEG:", self.manage_heic_jpeg_combo)

        dry_run_row = QHBoxLayout()
        dry_run_row.addWidget(self.dry_run_check)
        dry_run_row.addWidget(create_info_icon("Simulate the upload without actually transferring files."))
        dry_run_row.addStretch()
        upload_form.addRow(dry_run_row)

        upload_group.setLayout(upload_form)
        layout.addWidget(upload_group)
        layout.addWidget(self.run_local_button)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Local Upload")

        self.date_check.toggled.connect(lambda checked: self.toggle_dates(checked))
        self.type_check.toggled.connect(lambda checked: self.type_edit.setEnabled(checked))
        self.local_browse_btn.clicked.connect(self.browse_local_folder)
        self.run_local_button.clicked.connect(lambda: self.run_command(self.get_command_and_tab_options()))
        
        self.local_path_edit.textChanged.connect(self.update_command_preview)
        self.date_check.toggled.connect(self.update_command_preview)
        self.start_date.dateChanged.connect(self.update_command_preview)
        self.end_date.dateChanged.connect(self.update_command_preview)
        self.type_check.toggled.connect(self.update_command_preview)
        self.type_edit.textChanged.connect(self.update_command_preview)
        self.album_name_edit.textChanged.connect(self.update_command_preview)
        self.folder_as_album_combo.currentIndexChanged.connect(self.update_command_preview)
        self.folder_as_tags_check.toggled.connect(self.update_command_preview)
        self.manage_burst_combo.currentIndexChanged.connect(self.update_command_preview)
        self.manage_raw_jpeg_combo.currentIndexChanged.connect(self.update_command_preview)
        self.manage_heic_jpeg_combo.currentIndexChanged.connect(self.update_command_preview)
        self.dry_run_check.toggled.connect(self.update_command_preview)
    def create_stack_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)

        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        def create_info_icon(tooltip):
            label = QLabel("(i)")
            label.setToolTip(tooltip)
            label.setStyleSheet("color: #666; font-style: italic;")
            return label

        stack_group = QGroupBox("Stack Configuration")
        stack_form = QFormLayout()

        self.stack_manage_burst_combo = QComboBox()
        self.stack_manage_burst_combo.addItems(["NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"])
        
        self.stack_manage_raw_jpeg_combo = QComboBox()
        self.stack_manage_raw_jpeg_combo.addItems(["NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"])
        
        self.stack_manage_heic_jpeg_combo = QComboBox()
        self.stack_manage_heic_jpeg_combo.addItems(["NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"])

        self.manage_epson_fastfoto_check = QCheckBox("Manage Epson FastFoto")
        self.stack_time_zone_edit = QLineEdit()
        self.stack_dry_run_check = QCheckBox("Dry Run Mode")

        stack_form.addRow("Manage Burst:", self.stack_manage_burst_combo)
        stack_form.addRow("Manage RAW+JPEG:", self.stack_manage_raw_jpeg_combo)
        stack_form.addRow("Manage HEIC+JPEG:", self.stack_manage_heic_jpeg_combo)
        stack_form.addRow(self.manage_epson_fastfoto_check)
        stack_form.addRow("Time Zone:", self.stack_time_zone_edit)
        stack_form.addRow(self.stack_dry_run_check)

        self.run_stack_button = QPushButton("Run Stack")
        self.run_stack_button.setEnabled(False) # Initially disabled

        stack_group.setLayout(stack_form)
        layout.addWidget(stack_group)
        layout.addWidget(self.run_stack_button)

        layout.addStretch()
        self.tab_widget.addTab(scroll, "Stack")

        self.run_stack_button.clicked.connect(lambda: self.run_command(self.get_command_and_tab_options()))
        
        self.stack_manage_burst_combo.currentIndexChanged.connect(self.update_command_preview)
        self.stack_manage_raw_jpeg_combo.currentIndexChanged.connect(self.update_command_preview)
        self.stack_manage_heic_jpeg_combo.currentIndexChanged.connect(self.update_command_preview)
        self.manage_epson_fastfoto_check.toggled.connect(self.update_command_preview)
        self.stack_time_zone_edit.textChanged.connect(self.update_command_preview)
        self.stack_dry_run_check.toggled.connect(self.update_command_preview)

    def validate_inputs(self):
        required = [
            (self.server_url_edit, r"^https?://.+"),
            (self.api_key_edit, r".+")
        ]
        is_valid_config = True # Assume valid initially
        for field, pattern in required:
            if not re.match(pattern, field.text()):
                field.setStyleSheet("border: 1px solid red;")
                is_valid_config = False # Config is invalid if any field fails validation
            else:
                field.setStyleSheet("")
        return is_valid_config # Return validation status

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
                self.source_path_edit.setText(current_text + separator + "; ".join(paths))
            elif target == self.local_path_edit:
                self.local_path_edit.setText(paths[0])
            event.acceptProposedAction()

    def browse_takeout_source(self):
        if self.zip_radio.isChecked():
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select Google Takeout ZIPs", "", "ZIP Files (*.zip)"
            )
            if files:
                self.source_path_edit.setText("; ".join(files))
                self.update_command_preview()
        else:
            folder = QFileDialog.getExistingDirectory(self, "Select Extracted Folder")
            if folder:
                self.source_path_edit.setText(folder)
                self.update_command_preview()

    def update_browse_mode(self, checked):
        self.source_path_edit.clear()
        self.browse_btn.setText("Browse ZIPs" if checked else "Browse Folder")
        self.update_command_preview()

    def toggle_dates(self, enabled):
        self.start_date.setEnabled(enabled)
        self.end_date.setEnabled(enabled)
        self.update_command_preview()

    def browse_local_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Upload Folder")
        if folder:
            self.local_path_edit.setText(folder)
            self.update_command_preview()
    def update_command_preview(self):
        # Build command strictly in order: [binary] [global] command [subcmd] [server] [upload_opts] [tab_opts] [path]
        parts = [self.binary_path] if hasattr(self, "binary_path") else ["./immich-go"]
        
        parts += self.get_global_options()
        parts += self.get_command_and_tab_options()

        quoted_parts = [shlex.quote(part) for part in parts]
        command_text = " ".join(quoted_parts)

        if not self.server_url_edit.text():
            command_text += "\\n\\n⚠️ MISSING SERVER URL"
        if not self.api_key_edit.text():
            command_text += "\\n⚠️ MISSING API KEY"

        self.command_preview.setPlainText(command_text)

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
        current_tab = self.tab_widget.tabText(self.tab_widget.currentIndex())
        opts = []
        paths = []
        
        if current_tab == "Google Takeout":
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
                opts.append(f'--from-album-name={self.from_album_name_edit.text()}')
            if self.takeout_dry_run_check.isChecked():
                opts.append("--dry-run")
                
            source_path = self.source_path_edit.text()
            if self.zip_radio.isChecked() and source_path:
                paths = [path.strip() for path in source_path.split(";") if path.strip()]
            elif source_path:
                paths = [source_path]

        elif current_tab == "Local Upload":
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
                    opts.append(f'--include-extensions={exts}')
            if self.album_name_edit.text():
                opts.append(f'--into-album={self.album_name_edit.text()}')
            if self.folder_as_album_combo.currentText() != "NONE":
                opts.append(f'--folder-as-album={self.folder_as_album_combo.currentText()}')
            if self.folder_as_tags_check.isChecked():
                opts.append("--folder-as-tags=true")
            if self.manage_burst_combo.currentText() != "NoStack":
                opts.append(f'--manage-burst={self.manage_burst_combo.currentText()}')
            if self.manage_raw_jpeg_combo.currentText() != "NoStack":
                opts.append(f'--manage-raw-jpeg={self.manage_raw_jpeg_combo.currentText()}')
            if self.manage_heic_jpeg_combo.currentText() != "NoStack":
                opts.append(f'--manage-heic-jpeg={self.manage_heic_jpeg_combo.currentText()}')
            if self.dry_run_check.isChecked():
                opts.append("--dry-run")
                
            if self.local_path_edit.text():
                paths = [self.local_path_edit.text()]
                
        elif current_tab == "Stack":
            opts += ["stack"]
            opts += self.get_server_options()
            
            if self.stack_manage_burst_combo.currentText() != "NoStack":
                opts.append(f'--manage-burst={self.stack_manage_burst_combo.currentText()}')
            if self.stack_manage_raw_jpeg_combo.currentText() != "NoStack":
                opts.append(f'--manage-raw-jpeg={self.stack_manage_raw_jpeg_combo.currentText()}')
            if self.stack_manage_heic_jpeg_combo.currentText() != "NoStack":
                opts.append(f'--manage-heic-jpeg={self.stack_manage_heic_jpeg_combo.currentText()}')
            if self.manage_epson_fastfoto_check.isChecked():
                opts.append("--manage-epson-fastfoto=true")
            if self.stack_time_zone_edit.text():
                opts.append(f'--time-zone={self.stack_time_zone_edit.text()}')
            if self.stack_dry_run_check.isChecked():
                opts.append("--dry-run")

        return opts + paths
    def update_status(self):
        is_valid_config = self.validate_inputs() # Validate config and get status
        errors = []
        if not self.server_url_edit.text():
            errors.append("Server URL required")
        if not self.api_key_edit.text():
            errors.append("API Key required")

        if errors:
            self.status_indicator.setText("❌ " + ", ".join(errors))
            self.status_indicator.setStyleSheet("color: red;")
        else:
            self.status_indicator.setText("✓ Ready to go!")
            self.status_indicator.setStyleSheet("color: green;")

        # Enable/Disable Run Buttons based on config validity
        self.run_takeout_button.setEnabled(is_valid_config)
        self.run_local_button.setEnabled(is_valid_config)
        if hasattr(self, 'run_stack_button'):
            self.run_stack_button.setEnabled(is_valid_config)

    def open_github_link(self):
        url = QUrl("https://github.com/simulot/immich-go")
        QDesktopServices.openUrl(url)

    def save_configuration(self):
        self.settings.setValue("server_url", self.server_url_edit.text())
        self.settings.setValue("api_key", self.api_key_edit.text())
        self.settings.setValue("skip_ssl", self.skip_ssl_checkbox.isChecked())
        
        self.settings.setValue("log_level", self.log_level_combo.currentText())
        self.settings.setValue("log_type", self.log_type_combo.currentText())
        self.settings.setValue("no_ui", self.no_ui_check.isChecked())
        
        self.settings.setValue("client_timeout", self.client_timeout_spin.value())
        self.settings.setValue("concurrent_tasks", self.concurrent_tasks_spin.value())
        self.settings.setValue("device_uuid", self.device_uuid_edit.text())
        self.settings.setValue("on_errors", self.on_errors_combo.currentText())
        self.settings.setValue("pause_immich_jobs", self.pause_immich_jobs_check.isChecked())

        self.settings.setValue("google_takeout_zip_radio", self.zip_radio.isChecked())
        self.settings.setValue("google_takeout_folder_radio", self.folder_radio.isChecked())
        self.settings.setValue("google_takeout_source_path", self.source_path_edit.text())
        
        self.settings.setValue("google_takeout_sync_albums", self.sync_albums_check.isChecked())
        self.settings.setValue("google_takeout_include_archived", self.include_archived_check.isChecked())
        self.settings.setValue("google_takeout_include_partner", self.include_partner_check.isChecked())
        self.settings.setValue("google_takeout_include_trashed", self.include_trashed_check.isChecked())
        self.settings.setValue("google_takeout_dry_run", self.takeout_dry_run_check.isChecked())
        
        self.settings.setValue("google_takeout_include_unmatched", self.include_unmatched_check.isChecked())
        self.settings.setValue("google_takeout_include_untitled_albums", self.include_untitled_albums_check.isChecked())
        self.settings.setValue("google_takeout_takeout_tag", self.takeout_tag_check.isChecked())
        self.settings.setValue("google_takeout_people_tag", self.people_tag_check.isChecked())
        self.settings.setValue("google_takeout_from_album_name", self.from_album_name_edit.text())
        
        adv_group_config = self.tab_widget.widget(0).widget().findChild(QGroupBox, "Advanced Configuration")
        if adv_group_config is not None:
            self.settings.setValue("config_adv_group_checked", adv_group_config.isChecked())
        adv_group_google_takeout = self.tab_widget.widget(1).widget().findChild(QGroupBox, "Advanced Options")
        if adv_group_google_takeout is not None:
            self.settings.setValue("google_takeout_adv_group_checked", adv_group_google_takeout.isChecked())

        self.settings.setValue("local_upload_path", self.local_path_edit.text())
        self.settings.setValue("local_upload_date_check", self.date_check.isChecked())
        self.settings.setValue("local_upload_start_date", self.start_date.date())
        self.settings.setValue("local_upload_end_date", self.end_date.date())
        self.settings.setValue("local_upload_type_check", self.type_check.isChecked())
        self.settings.setValue("local_upload_type_edit", self.type_edit.text())
        
        self.settings.setValue("local_upload_album_name", self.album_name_edit.text())
        self.settings.setValue("local_upload_folder_as_album", self.folder_as_album_combo.currentText())
        self.settings.setValue("local_upload_folder_as_tags", self.folder_as_tags_check.isChecked())
        self.settings.setValue("local_upload_manage_burst", self.manage_burst_combo.currentText())
        self.settings.setValue("local_upload_manage_raw_jpeg", self.manage_raw_jpeg_combo.currentText())
        self.settings.setValue("local_upload_manage_heic_jpeg", self.manage_heic_jpeg_combo.currentText())
        self.settings.setValue("local_upload_dry_run_check", self.dry_run_check.isChecked())
        
        self.settings.setValue("stack_manage_burst", self.stack_manage_burst_combo.currentText())
        self.settings.setValue("stack_manage_raw_jpeg", self.stack_manage_raw_jpeg_combo.currentText())
        self.settings.setValue("stack_manage_heic_jpeg", self.stack_manage_heic_jpeg_combo.currentText())
        self.settings.setValue("stack_manage_epson_fastfoto", self.manage_epson_fastfoto_check.isChecked())
        self.settings.setValue("stack_time_zone", self.stack_time_zone_edit.text())
        self.settings.setValue("stack_dry_run", self.stack_dry_run_check.isChecked())

    def load_configuration(self):
        self.server_url_edit.setText(self.settings.value("server_url", ""))
        self.api_key_edit.setText(self.settings.value("api_key", ""))
        self.skip_ssl_checkbox.setChecked(self.settings.value("skip_ssl", False, type=bool))
        
        self.log_level_combo.setCurrentText(self.settings.value("log_level", "INFO"))
        self.log_type_combo.setCurrentText(self.settings.value("log_type", "TEXT"))
        self.no_ui_check.setChecked(self.settings.value("no_ui", False, type=bool))
        
        self.client_timeout_spin.setValue(self.settings.value("client_timeout", 20, type=int))
        self.concurrent_tasks_spin.setValue(self.settings.value("concurrent_tasks", 2, type=int))
        self.device_uuid_edit.setText(self.settings.value("device_uuid", ""))
        self.on_errors_combo.setCurrentText(self.settings.value("on_errors", "stop"))
        self.pause_immich_jobs_check.setChecked(self.settings.value("pause_immich_jobs", True, type=bool))

        self.zip_radio.setChecked(self.settings.value("google_takeout_zip_radio", True, type=bool))
        self.folder_radio.setChecked(self.settings.value("google_takeout_folder_radio", False, type=bool))
        self.update_browse_mode(self.zip_radio.isChecked())
        self.source_path_edit.setText(self.settings.value("google_takeout_source_path", ""))
        
        self.sync_albums_check.setChecked(self.settings.value("google_takeout_sync_albums", True, type=bool))
        self.include_archived_check.setChecked(self.settings.value("google_takeout_include_archived", True, type=bool))
        self.include_partner_check.setChecked(self.settings.value("google_takeout_include_partner", True, type=bool))
        self.include_trashed_check.setChecked(self.settings.value("google_takeout_include_trashed", False, type=bool))
        self.takeout_dry_run_check.setChecked(self.settings.value("google_takeout_dry_run", False, type=bool))
        
        self.include_unmatched_check.setChecked(self.settings.value("google_takeout_include_unmatched", False, type=bool))
        self.include_untitled_albums_check.setChecked(self.settings.value("google_takeout_include_untitled_albums", False, type=bool))
        self.takeout_tag_check.setChecked(self.settings.value("google_takeout_takeout_tag", True, type=bool))
        self.people_tag_check.setChecked(self.settings.value("google_takeout_people_tag", True, type=bool))
        self.from_album_name_edit.setText(self.settings.value("google_takeout_from_album_name", ""))
        
        adv_group_google_takeout = self.tab_widget.widget(1).widget().findChild(QGroupBox, "Advanced Options")
        if adv_group_google_takeout is not None:
            adv_group_google_takeout.setChecked(self.settings.value("google_takeout_adv_group_checked", False, type=bool))

        self.local_path_edit.setText(self.settings.value("local_upload_path", ""))
        self.date_check.setChecked(self.settings.value("local_upload_date_check", False, type=bool))
        self.toggle_dates(self.date_check.isChecked())
        self.start_date.setDate(self.settings.value("local_upload_start_date", QDate.currentDate().addYears(-1)))
        self.end_date.setDate(self.settings.value("local_upload_end_date", QDate.currentDate()))
        self.type_check.setChecked(self.settings.value("local_upload_type_check", False, type=bool))
        self.type_edit.setEnabled(self.type_check.isChecked())
        self.type_edit.setText(self.settings.value("local_upload_type_edit", ""))
        
        self.album_name_edit.setText(self.settings.value("local_upload_album_name", ""))
        self.folder_as_album_combo.setCurrentText(self.settings.value("local_upload_folder_as_album", "NONE"))
        self.folder_as_tags_check.setChecked(self.settings.value("local_upload_folder_as_tags", False, type=bool))
        self.manage_burst_combo.setCurrentText(self.settings.value("local_upload_manage_burst", "NoStack"))
        self.manage_raw_jpeg_combo.setCurrentText(self.settings.value("local_upload_manage_raw_jpeg", "NoStack"))
        self.manage_heic_jpeg_combo.setCurrentText(self.settings.value("local_upload_manage_heic_jpeg", "NoStack"))
        self.dry_run_check.setChecked(self.settings.value("local_upload_dry_run_check", False, type=bool))
        
        self.stack_manage_burst_combo.setCurrentText(self.settings.value("stack_manage_burst", "NoStack"))
        self.stack_manage_raw_jpeg_combo.setCurrentText(self.settings.value("stack_manage_raw_jpeg", "NoStack"))
        self.stack_manage_heic_jpeg_combo.setCurrentText(self.settings.value("stack_manage_heic_jpeg", "NoStack"))
        self.manage_epson_fastfoto_check.setChecked(self.settings.value("stack_manage_epson_fastfoto", False, type=bool))
        self.stack_time_zone_edit.setText(self.settings.value("stack_time_zone", ""))
        self.stack_dry_run_check.setChecked(self.settings.value("stack_dry_run", False, type=bool))
        
        adv_group_config = self.tab_widget.widget(0).widget().findChild(QGroupBox, "Advanced Configuration")
        if adv_group_config is not None:
            adv_group_config.setChecked(self.settings.value("config_adv_group_checked", False, type=bool))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    from PySide6.QtGui import QFont
    app.setFont(QFont("Segoe UI", 10))
    window = ImmichGoGUI()
    window.show()
    window.update_status()
    sys.exit(app.exec())