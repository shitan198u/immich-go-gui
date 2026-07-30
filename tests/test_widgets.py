from unittest.mock import MagicMock, patch

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

from core.flag_registry import REGISTRY
from gui.widgets import DroppablePlainTextEdit
from gui.widgets.advanced_flag_row import AdvancedFlagRow
from gui.widgets.eliding_label import ElidingLabel


class _FixedWidthLabel(ElidingLabel):
    """ElidingLabel subclass exposing a settable width() for sizeHint tests."""

    _test_width = 0

    def width(self):
        return self._test_width


def test_advanced_flag_row_int_respects_flagdef_min_max(qtbot):
    """concurrent-tasks is 1-20 in flags.toml; UI must clamp, not 0-999999."""
    flag_def = next(
        f
        for f in REGISTRY.advanced_defs("upload-folder")
        if f.key == "concurrent-tasks"
    )
    assert flag_def.min_val == 1 and flag_def.max_val == 20
    row = AdvancedFlagRow(flag_def)
    qtbot.addWidget(row)
    spin = row.value_widget
    assert spin.minimum() == 1
    assert spin.maximum() == 20
    row.set_value(99)
    assert spin.value() == 20


def test_droppable_plain_text_edit_drop(qapp, qtbot):
    edit = DroppablePlainTextEdit()
    qtbot.addWidget(edit)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile("/path/a.zip"), QUrl.fromLocalFile("/path/b.zip")])
    event = QDropEvent(
        QPointF(0, 0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    edit.dropEvent(event)
    assert edit.toPlainText() == "/path/a.zip\n/path/b.zip"


def test_browse_takeout_zips(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(1)
    with patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=(["/path/a.zip", "/path/b.zip"], ""),
    ):
        gui.browse_takeout_zips()
        assert (
            gui.inputs["upload-gp"]["path"].toPlainText() == "/path/a.zip\n/path/b.zip"
        )


def test_browse_folder_upload(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    with patch(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
        return_value="/selected/folder",
    ):
        gui.browse_folder_upload()
        assert gui.inputs["upload-folder"]["path"].text() == "/selected/folder"


def test_native_dialog_options_passed(gui):
    with patch(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value="/test/path"
    ) as mock_get_dir:
        gui._browse_into(MagicMock(), "Test Caption")
        mock_get_dir.assert_called_once()
        from PySide6.QtWidgets import QFileDialog

        args, kwargs = mock_get_dir.call_args
        assert (
            args[3] == QFileDialog.Option.ShowDirsOnly
            or kwargs.get("options") == QFileDialog.Option.ShowDirsOnly
        )


def _expected_hint_width(full_w, widget_width):
    """Mirror ElidingLabel.sizeHint()'s width calculation."""
    if widget_width > 0:
        return min(full_w, max(widget_width, 200))
    return full_w


def test_eliding_label_size_hint_unsized_uses_full_text_width(qtbot):
    """When the widget has no width yet, sizeHint should not clamp at all."""
    label = _FixedWidthLabel("A moderately long label used for size hint testing")
    qtbot.addWidget(label)
    label._test_width = 0

    fm = label.fontMetrics()
    full_w = fm.horizontalAdvance(label.text()) + 2
    hint = label.sizeHint()

    assert hint.width() == full_w
    assert hint.height() == fm.lineSpacing()


def test_eliding_label_size_hint_clamps_to_200_when_narrow_and_long(qtbot):
    """Narrow widget (<200px) with long text should clamp the hint to 200."""
    label = _FixedWidthLabel(
        "A very long piece of text that will clearly exceed two hundred pixels"
    )
    qtbot.addWidget(label)

    fm = label.fontMetrics()
    full_w = fm.horizontalAdvance(label.text()) + 2
    assert full_w > 200  # sanity check on the fixture text

    label._test_width = 50
    hint = label.sizeHint()

    assert hint.width() == 200
    assert hint.width() == _expected_hint_width(full_w, 50)


def test_eliding_label_size_hint_uses_full_width_when_short_text_and_narrow(qtbot):
    """Narrow widget but short text: hint should not be padded up to the width."""
    label = _FixedWidthLabel("short")
    qtbot.addWidget(label)

    fm = label.fontMetrics()
    full_w = fm.horizontalAdvance(label.text()) + 2
    assert full_w < 200  # sanity check on the fixture text

    label._test_width = 50
    hint = label.sizeHint()

    assert hint.width() == full_w
    assert hint.width() == _expected_hint_width(full_w, 50)


def test_eliding_label_size_hint_caps_at_widget_width_when_wide(qtbot):
    """Wide widget (>=200px) should cap the hint at the widget's own width."""
    label = _FixedWidthLabel(
        "An extremely long label text intended to exceed three hundred pixels of width"
    )
    qtbot.addWidget(label)

    fm = label.fontMetrics()
    full_w = fm.horizontalAdvance(label.text()) + 2
    assert full_w > 300  # sanity check on the fixture text

    label._test_width = 300
    hint = label.sizeHint()

    assert hint.width() == 300
    assert hint.width() == _expected_hint_width(full_w, 300)


def test_eliding_label_size_hint_uses_full_width_when_less_than_widget_width(qtbot):
    """Short text inside a wide widget should report its own (smaller) full width."""
    label = _FixedWidthLabel("short")
    qtbot.addWidget(label)

    fm = label.fontMetrics()
    full_w = fm.horizontalAdvance(label.text()) + 2

    label._test_width = 300
    hint = label.sizeHint()

    assert hint.width() == full_w
    assert hint.width() == _expected_hint_width(full_w, 300)
