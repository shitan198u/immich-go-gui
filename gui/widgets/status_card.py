from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from gui.widgets.eliding_label import ElidingLabel


class StatusCard(QFrame):
    _DOT: ClassVar[dict[str, str]] = {
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
        txt = ElidingLabel(text, Qt.TextElideMode.ElideMiddle)
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
        self.txt_b.setToolTip(text)

    def set_server(self, state, text):
        self._paint(self.dot_s, state)
        self.txt_s.setText(text)
        self.txt_s.setToolTip(text)
