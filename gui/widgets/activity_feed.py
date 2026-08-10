"""Live activity feed widget for the Monitor tab.

Shows a scrolling list of recent upload events: file names, folder progress,
errors, and summaries. Supports color-coded log levels.
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ActivityEntry:
    """A single log entry in the activity feed."""

    def __init__(self, folder: str, message: str, level: str = "info"):
        self.folder = folder
        self.message = message
        self.level = level  # info, warn, error, success, progress


class ActivityFeed(QFrame):
    """Scrolling activity log for monitor operations."""

    max_entries = 500

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ActivityFeed")

        self._pending: list[ActivityEntry] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(100)
        self._flush_timer.timeout.connect(self._flush)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        title = QLabel("Activity")
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(60)
        btn_clear.clicked.connect(self.clear)
        header.addWidget(btn_clear)
        layout.addLayout(header)

        # Text area
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        # QTextEdit does not expose setMaximumBlockCount directly, while its
        # document does.  Using the document API also keeps this widget
        # compatible with QPlainTextEdit and older packaged builds that used
        # QTextEdit here.
        self._text.document().setMaximumBlockCount(self.max_entries)
        font = QFont("Consolas, Courier New, monospace", 9)
        self._text.setFont(font)
        layout.addWidget(self._text)

    def add_entry(self, folder: str, message: str, level: str = "info") -> None:
        """Queue an entry to be appended to the feed."""
        self._pending.append(ActivityEntry(folder, message, level))
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def _flush(self) -> None:
        """Flush pending entries to the text widget (batched for performance)."""
        if not self._pending:
            return

        entries = self._pending
        self._pending = []

        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        for entry in entries:
            fmt = QTextCharFormat()
            fmt.setFontFamily("Consolas")

            if entry.level == "error":
                fmt.setForeground(QColor("#ef4444"))
            elif entry.level == "warn":
                fmt.setForeground(QColor("#f59e0b"))
            elif entry.level == "success":
                fmt.setForeground(QColor("#22c55e"))
            elif entry.level == "progress":
                fmt.setForeground(QColor("#3b82f6"))
            elif entry.level == "summary":
                fmt.setForeground(QColor("#a855f7"))
                fmt.setFontWeight(QFont.Weight.Bold)
            else:
                fmt.setForeground(QColor("#d1d5db"))

            folder_text = f"[{entry.folder}] " if entry.folder else ""
            line = f"{folder_text}{entry.message}"

            cursor.insertText(line + "\n", fmt)

        # Auto-scroll to bottom
        self._text.setTextCursor(cursor)
        sb = self._text.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def clear(self) -> None:
        """Clear all entries."""
        self._pending.clear()
        self._text.clear()


class ProgressCard(QFrame):
    """Card showing overall upload progress across all folders."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ProgressCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Status line
        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #94a3b8;"
        )
        layout.addWidget(self.status_label)

        # Folders progress
        self.folders_label = QLabel("No active uploads")
        self.folders_label.setStyleSheet("font-size: 12px; color: #64748b;")
        layout.addWidget(self.folders_label)

        # Current file
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("font-size: 11px; color: #475569;")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)

        # Stats row
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(self.stats_label)

    def set_idle(self) -> None:
        self.status_label.setText("Idle")
        self.status_label.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #94a3b8;"
        )
        self.folders_label.setText("Waiting for changes or scheduled run...")
        self.file_label.setText("")
        self.stats_label.setText("")

    def set_running(
        self,
        folder: str,
        completed: int,
        total: int,
        current_file: str = "",
        uploaded: int = 0,
        skipped: int = 0,
        failed: int = 0,
    ) -> None:
        self.status_label.setText("Running")
        self.status_label.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #3b82f6;"
        )
        self.folders_label.setText(f"Folder {completed} of {total}: {folder}")
        if current_file:
            self.file_label.setText(f"Uploading: {current_file}")
        else:
            self.file_label.setText("")
        parts = [f"{uploaded} uploaded"]
        if skipped:
            parts.append(f"{skipped} skipped")
        if failed:
            parts.append(f"{failed} failed")
        self.stats_label.setText(" · ".join(parts))

    def set_paused(self, reason: str = "") -> None:
        self.status_label.setText("Paused")
        self.status_label.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #f59e0b;"
        )
        self.folders_label.setText(reason or "Uploads paused")

    def set_complete(self, success: int, fail: int) -> None:
        if fail == 0:
            self.status_label.setText("Complete")
            self.status_label.setStyleSheet(
                "font-size: 14px; font-weight: 700; color: #22c55e;"
            )
        else:
            self.status_label.setText("Complete (with errors)")
            self.status_label.setStyleSheet(
                "font-size: 14px; font-weight: 700; color: #f59e0b;"
            )
        self.folders_label.setText(f"{success} succeeded, {fail} failed")
        self.file_label.setText("")
        self.stats_label.setText("")
