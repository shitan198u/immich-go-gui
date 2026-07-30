from unittest.mock import MagicMock, patch

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

from core.flag_registry import REGISTRY
from gui.widgets import DroppablePlainTextEdit
from gui.widgets.advanced_flag_row import AdvancedFlagRow


def test_advanced_flag_row_duration_minutes_uses_static_unit_label(qtbot):
    flag_def = next(
        d
        for defs in REGISTRY.flags.values()
        for d in defs
        if d.kind == "duration_minutes"
    )
    row = AdvancedFlagRow(flag_def)
    qtbot.addWidget(row)
    assert row.value_widget.suffix() == ""


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
