from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import QLabel


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
        super().setText(
            fm.elidedText(self._full, self._elide, w) if w > 0 else self._full
        )

    def sizeHint(self):
        """
        Return the preferred size for displaying the label's full text.
        
        Returns:
        	QSize: A size whose width is based on the full text width and current widget width, and whose height matches the font's line spacing.
        """
        fm = self.fontMetrics()
        full_w = fm.horizontalAdvance(self._full) + 2
        w = min(full_w, max(self.width(), 200)) if self.width() > 0 else full_w
        return QSize(w, fm.lineSpacing())

    def minimumSizeHint(self):
        """
        Return the minimum size needed to display an ellipsis.
        
        Returns:
        	QSize: A size based on the ellipsis width and current font line spacing.
        """
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
