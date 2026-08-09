"""Monitor tab — folder watching, scheduling, and backup controls.

Provides the full UI for the backup monitoring system: watched folder list,
schedule configuration, file watcher status, manual controls, and activity feed.
"""

from typing import ClassVar

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.activity_feed import ActivityFeed, ProgressCard


class FolderListWidget(QFrame):
    """Widget for managing the list of watched folders."""

    folder_added = Signal(str)
    folder_removed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FolderListWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Add folder row
        add_row = QHBoxLayout()
        self._folder_input = QLineEdit()
        self._folder_input.setPlaceholderText(
            "C:\\Users\\You\\Pictures or /home/you/photos"
        )
        add_row.addWidget(self._folder_input)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_folder)
        add_row.addWidget(btn_browse)

        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self._add_current)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        # Folder list
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list)

        # Remove button
        btn_row = QHBoxLayout()
        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(btn_remove)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _browse_folder(self) -> None:
        """Open folder browser dialog."""
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Watch")
        if folder:
            self._folder_input.setText(folder)

    def _add_current(self) -> None:
        """Add the current input path to the watched list."""
        path = self._folder_input.text().strip()
        if not path:
            return

        # Check not duplicate
        for i in range(self._list.count()):
            if self._list.item(i).text() == path:
                return

        item = QListWidgetItem(path)
        self._list.addItem(item)
        self._folder_input.clear()
        self.folder_added.emit(path)

    def _remove_selected(self) -> None:
        """Remove selected folders from the list."""
        for item in self._list.selectedItems():
            self.folder_removed.emit(item.text())
            row = self._list.row(item)
            self._list.takeItem(row)

    def set_folders(self, folders: list[str]) -> None:
        """Replace all folders in the list."""
        self._list.clear()
        for f in folders:
            self._list.addItem(QListWidgetItem(f))

    def get_folders(self) -> list[str]:
        """Get all folders currently in the list."""
        return [self._list.item(i).text() for i in range(self._list.count())]

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self._folder_input.setEnabled(enabled)
        self._list.setEnabled(enabled)


class ScheduleGroup(QGroupBox):
    """Schedule configuration for weekly and monthly full scans."""

    schedule_changed = Signal()

    DAYS_OF_WEEK: ClassVar[list[str]] = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Schedule", parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Weekly
        weekly_box = QGroupBox("Weekly Incremental Scan")
        weekly_layout = QVBoxLayout(weekly_box)
        weekly_row = QHBoxLayout()

        self._weekly_enabled = QCheckBox("Enabled")
        self._weekly_enabled.setChecked(True)
        self._weekly_enabled.toggled.connect(lambda: self.schedule_changed.emit())
        weekly_row.addWidget(self._weekly_enabled)

        weekly_row.addWidget(QLabel("Day:"))
        self._weekly_day = QComboBox()
        self._weekly_day.addItems(self.DAYS_OF_WEEK)
        self._weekly_day.setCurrentIndex(6)  # Sunday
        self._weekly_day.currentIndexChanged.connect(
            lambda: self.schedule_changed.emit()
        )
        weekly_row.addWidget(self._weekly_day)

        weekly_row.addWidget(QLabel("Hour:"))
        self._weekly_hour = QSpinBox()
        self._weekly_hour.setRange(0, 23)
        self._weekly_hour.setValue(3)
        self._weekly_hour.valueChanged.connect(lambda: self.schedule_changed.emit())
        weekly_row.addWidget(self._weekly_hour)

        weekly_row.addWidget(QLabel("Min:"))
        self._weekly_minute = QSpinBox()
        self._weekly_minute.setRange(0, 59)
        self._weekly_minute.setValue(0)
        self._weekly_minute.valueChanged.connect(lambda: self.schedule_changed.emit())
        weekly_row.addWidget(self._weekly_minute)
        weekly_row.addStretch()

        weekly_layout.addLayout(weekly_row)
        layout.addWidget(weekly_box)

        # Monthly
        monthly_box = QGroupBox("Monthly Full Rescan")
        monthly_layout = QVBoxLayout(monthly_box)
        monthly_row = QHBoxLayout()

        self._monthly_enabled = QCheckBox("Enabled")
        self._monthly_enabled.setChecked(True)
        self._monthly_enabled.toggled.connect(lambda: self.schedule_changed.emit())
        monthly_row.addWidget(self._monthly_enabled)

        monthly_row.addWidget(QLabel("Day:"))
        self._monthly_day = QSpinBox()
        self._monthly_day.setRange(1, 28)
        self._monthly_day.setValue(1)
        self._monthly_day.valueChanged.connect(lambda: self.schedule_changed.emit())
        monthly_row.addWidget(self._monthly_day)

        monthly_row.addWidget(QLabel("Hour:"))
        self._monthly_hour = QSpinBox()
        self._monthly_hour.setRange(0, 23)
        self._monthly_hour.setValue(4)
        self._monthly_hour.valueChanged.connect(lambda: self.schedule_changed.emit())
        monthly_row.addWidget(self._monthly_hour)

        monthly_row.addWidget(QLabel("Min:"))
        self._monthly_minute = QSpinBox()
        self._monthly_minute.setRange(0, 59)
        self._monthly_minute.setValue(0)
        self._monthly_minute.valueChanged.connect(lambda: self.schedule_changed.emit())
        monthly_row.addWidget(self._monthly_minute)
        monthly_row.addStretch()

        monthly_layout.addLayout(monthly_row)
        layout.addWidget(monthly_box)

    def get_values(self) -> dict:
        return {
            "weekly_enabled": self._weekly_enabled.isChecked(),
            "weekly_day": self._weekly_day.currentIndex(),
            "weekly_hour": self._weekly_hour.value(),
            "weekly_minute": self._weekly_minute.value(),
            "monthly_enabled": self._monthly_enabled.isChecked(),
            "monthly_day": self._monthly_day.value(),
            "monthly_hour": self._monthly_hour.value(),
            "monthly_minute": self._monthly_minute.value(),
        }

    def set_values(self, values: dict) -> None:
        if "weekly_enabled" in values:
            self._weekly_enabled.setChecked(values["weekly_enabled"])
        if "weekly_day" in values:
            self._weekly_day.setCurrentIndex(values["weekly_day"])
        if "weekly_hour" in values:
            self._weekly_hour.setValue(values["weekly_hour"])
        if "weekly_minute" in values:
            self._weekly_minute.setValue(values["weekly_minute"])
        if "monthly_enabled" in values:
            self._monthly_enabled.setChecked(values["monthly_enabled"])
        if "monthly_day" in values:
            self._monthly_day.setValue(values["monthly_day"])
        if "monthly_hour" in values:
            self._monthly_hour.setValue(values["monthly_hour"])
        if "monthly_minute" in values:
            self._monthly_minute.setValue(values["monthly_minute"])


class WatcherStatusWidget(QFrame):
    """Status display for the file watcher."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("WatcherStatus")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet("color: #22c55e; font-size: 16px;")
        self._status_dot.setFixedWidth(24)
        layout.addWidget(self._status_dot)

        self._status_text = QLabel("File watcher active — monitoring for changes")
        self._status_text.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self._status_text)
        layout.addStretch()

    def set_active(self, folder_count: int) -> None:
        self._status_dot.setStyleSheet("color: #22c55e; font-size: 16px;")
        self._status_text.setText(
            f"File watcher active — monitoring {folder_count} folder(s)"
        )

    def set_inactive(self, reason: str = "") -> None:
        self._status_dot.setStyleSheet("color: #64748b; font-size: 16px;")
        self._status_text.setText(reason or "File watcher inactive")

    def set_error(self, message: str) -> None:
        self._status_dot.setStyleSheet("color: #ef4444; font-size: 16px;")
        self._status_text.setText(message)


def build_monitor_tab(host) -> QWidget:
    """Build the Monitor tab with all sub-components.

    Args:
        host: The ImmichGoGUI main window instance.

    Returns:
        The fully constructed monitor tab widget.
    """

    page = QWidget()
    page.setObjectName("MonitorTab")

    # Outer scroll area for the entire tab
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)

    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(24, 16, 24, 16)
    layout.setSpacing(16)

    host.inputs["monitor"] = {}

    # ── Progress Card ──────────────────────────────────────
    host.progress_card = ProgressCard()
    layout.addWidget(host.progress_card)

    # ── Controls ───────────────────────────────────────────
    master_row = QHBoxLayout()
    host.monitor_enabled_check = QCheckBox("Enable Backup Monitor")
    host.monitor_enabled_check.setToolTip(
        "Master switch for scheduled backups and background monitoring. "
        "When enabled, the application remains available for system tray operation."
    )
    host.inputs["monitor"]["monitor_enabled"] = host.monitor_enabled_check
    master_row.addWidget(host.monitor_enabled_check)
    master_row.addStretch()
    layout.addLayout(master_row)

    controls = QHBoxLayout()
    controls.setSpacing(8)

    host.btn_monitor_run = QPushButton("Run Now")
    host.btn_monitor_run.setObjectName("BtnRun")
    host.btn_monitor_run.setCursor(Qt.CursorShape.PointingHandCursor)
    controls.addWidget(host.btn_monitor_run)

    host.btn_monitor_full = QPushButton("Full Rescan Now")
    host.btn_monitor_full.setCursor(Qt.CursorShape.PointingHandCursor)
    controls.addWidget(host.btn_monitor_full)

    host.btn_monitor_pause = QPushButton("Pause")
    host.btn_monitor_pause.setCursor(Qt.CursorShape.PointingHandCursor)
    host.btn_monitor_pause.setEnabled(False)
    controls.addWidget(host.btn_monitor_pause)

    host.btn_monitor_cancel = QPushButton("Cancel")
    host.btn_monitor_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
    host.btn_monitor_cancel.setEnabled(False)
    controls.addWidget(host.btn_monitor_cancel)

    controls.addStretch()
    layout.addLayout(controls)

    # ── Folder List ────────────────────────────────────────
    host.folder_list = FolderListWidget()
    layout.addWidget(host.folder_list)

    # ── Watcher Status ─────────────────────────────────────
    host.watcher_status = WatcherStatusWidget()
    layout.addWidget(host.watcher_status)

    # ── Schedule ───────────────────────────────────────────
    host.schedule_group = ScheduleGroup()
    layout.addWidget(host.schedule_group)

    # ── Network Policy ─────────────────────────────────────
    net_group = QGroupBox("Network")
    net_layout = QVBoxLayout(net_group)
    net_row = QHBoxLayout()
    net_row.addWidget(QLabel("Upload policy:"))

    host.network_policy_combo = QComboBox()
    host.network_policy_combo.addItems(
        [
            "Always (any network)",
            "No metered connections",
            "Only specific Wi-Fi",
        ]
    )
    host.inputs["monitor"]["network_policy"] = host.network_policy_combo
    net_row.addWidget(host.network_policy_combo)
    net_row.addStretch()
    net_layout.addLayout(net_row)

    # SSID input (shown when SSID_ONLY selected)
    ssid_row = QHBoxLayout()
    ssid_row.addWidget(QLabel("Allowed SSIDs:"))
    host.ssid_input = QLineEdit()
    host.ssid_input.setPlaceholderText("MyHomeWiFi, OfficeWiFi")
    host.inputs["monitor"]["allowed_ssids"] = host.ssid_input
    ssid_row.addWidget(host.ssid_input)
    ssid_row.addStretch()
    net_layout.addLayout(ssid_row)

    layout.addWidget(net_group)

    # ── Options ────────────────────────────────────────────
    opts_group = QGroupBox("Options")
    opts_layout = QVBoxLayout(opts_group)
    opts_row1 = QHBoxLayout()

    opts_row1.addWidget(QLabel("Concurrency:"))
    host.concurrency_spin = QSpinBox()
    host.concurrency_spin.setRange(1, 16)
    host.concurrency_spin.setValue(4)
    host.inputs["monitor"]["concurrency"] = host.concurrency_spin
    opts_row1.addWidget(host.concurrency_spin)

    opts_row1.addWidget(QLabel("Days back:"))
    host.days_back_spin = QSpinBox()
    host.days_back_spin.setRange(1, 365)
    host.days_back_spin.setValue(7)
    host.inputs["monitor"]["days_back"] = host.days_back_spin
    opts_row1.addWidget(host.days_back_spin)

    opts_row1.addWidget(QLabel("Watcher debounce (s):"))
    host.debounce_spin = QSpinBox()
    host.debounce_spin.setRange(5, 300)
    host.debounce_spin.setValue(30)
    host.inputs["monitor"]["debounce"] = host.debounce_spin
    opts_row1.addWidget(host.debounce_spin)

    opts_row1.addStretch()
    opts_layout.addLayout(opts_row1)

    # File watcher toggle
    host.file_watcher_check = QCheckBox("Enable real-time file watching")
    host.file_watcher_check.setToolTip(
        "Watch configured folders for changes and start incremental uploads. "
        "This is separate from scheduled backups and only operates while the backup monitor is enabled."
    )
    host.file_watcher_check.setChecked(True)
    host.inputs["monitor"]["file_watcher_enabled"] = host.file_watcher_check
    opts_layout.addWidget(host.file_watcher_check)

    host.minimize_to_tray_check = QCheckBox(
        "Close to system tray when monitor is enabled"
    )
    host.minimize_to_tray_check.setChecked(True)
    host.inputs["monitor"]["minimize_to_tray"] = host.minimize_to_tray_check
    opts_layout.addWidget(host.minimize_to_tray_check)

    host.launch_on_startup_check = QCheckBox("Start monitor with Windows")
    host.inputs["monitor"]["launch_on_startup"] = host.launch_on_startup_check
    opts_layout.addWidget(host.launch_on_startup_check)

    layout.addWidget(opts_group)

    # ── Advanced Flags (reuses upload-folder schema) ──────
    adv_card = host._build_advanced_flags_card("upload-folder")
    layout.addWidget(adv_card)

    # ── Activity Feed ──────────────────────────────────────
    host.activity_feed = ActivityFeed()
    host.activity_feed.setMinimumHeight(180)
    layout.addWidget(host.activity_feed)

    layout.addStretch()

    scroll.setWidget(content)

    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.addWidget(scroll)

    return page
