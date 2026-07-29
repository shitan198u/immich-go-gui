from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox

from core.command_builder import validate_state_light
from gui.widgets.status_card import StatusCard


def test_status_card_elides_and_sets_tooltip(qtbot):
    card = StatusCard()
    qtbot.addWidget(card)
    card.resize(120, 80)
    qtbot.waitExposed(card)
    long_text = "Server: " + "x" * 200
    card.set_server("ok", long_text)
    assert card.txt_s.toolTip() == long_text
    assert card.txt_s.text() == long_text
    w = card.txt_s.contentsRect().width() or card.txt_s.width()
    if w > 0:
        elided = card.txt_s.fontMetrics().elidedText(
            long_text, card.txt_s._elide, w
        )
        assert len(elided) < len(long_text)
        assert "…" in elided


def test_running_process_boolean_state(gui):
    gui.active_lock_path = None
    gui.running_process = False
    gui.update_status()
    assert gui.lbl_running_warning.isHidden() is True

    gui.running_process = True
    gui.update_status()
    assert gui.lbl_running_warning.isHidden() is False

    with patch(
        "PySide6.QtWidgets.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        gui.on_reset_run_state_clicked()
        assert gui.running_process is False
        assert gui.active_lock_path is None
        assert gui.lbl_running_warning.isHidden() is True


def test_close_event_save_prompt(gui, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    calls = {"pending": 0, "prompt": 0}

    def fake_prompt(context):
        calls["prompt"] += 1
        return QMessageBox.StandardButton.Save

    monkeypatch.setattr(gui, "_prompt_save_pending_configuration", fake_prompt)
    monkeypatch.setattr(
        gui,
        "_save_pending_configuration",
        lambda show_popup=False: calls.__setitem__(
            "pending", calls["pending"] + 1
        ),
    )
    monkeypatch.setattr("gui.main_window.scan_locks", list)
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["server"].setText("http://changed:2283")
    event = QCloseEvent()
    gui.closeEvent(event)
    assert calls["prompt"] == 1
    assert calls["pending"] == 1
    assert event.isAccepted()


def test_close_event_both_tracks_dirty_single_prompt(gui, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    calls = {"pending": 0, "prompt": 0}

    def fake_prompt(context):
        calls["prompt"] += 1
        return QMessageBox.StandardButton.Save

    monkeypatch.setattr(gui, "_prompt_save_pending_configuration", fake_prompt)
    monkeypatch.setattr(
        gui,
        "_save_pending_configuration",
        lambda show_popup=False: calls.__setitem__(
            "pending", calls["pending"] + 1
        ),
    )
    monkeypatch.setattr("gui.main_window.scan_locks", list)
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["api_key"].setText("new-key")
    gui.inputs["config"]["skip-ssl"].setChecked(not gui.inputs["config"]["skip-ssl"].isChecked())
    event = QCloseEvent()
    gui.closeEvent(event)
    assert calls["prompt"] == 1
    assert calls["pending"] == 1
    assert event.isAccepted()


def test_close_event_cancel_ignores(gui, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    monkeypatch.setattr(
        gui,
        "_prompt_save_pending_configuration",
        lambda context: QMessageBox.StandardButton.Cancel,
    )
    monkeypatch.setattr(
        gui,
        "_save_pending_configuration",
        lambda show_popup=False: (_ for _ in ()).throw(AssertionError("save")),
    )
    monkeypatch.setattr("gui.main_window.scan_locks", list)
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["server"].setText("http://changed:2283")
    event = QCloseEvent()
    gui.closeEvent(event)
    assert not event.isAccepted()


def test_close_event_discard_no_save(gui, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    calls = {"pending": 0, "prompt": 0}

    def fake_prompt(context):
        calls["prompt"] += 1
        return QMessageBox.StandardButton.Discard

    monkeypatch.setattr(gui, "_prompt_save_pending_configuration", fake_prompt)
    monkeypatch.setattr(
        gui,
        "_save_pending_configuration",
        lambda show_popup=False: calls.__setitem__(
            "pending", calls["pending"] + 1
        ),
    )
    monkeypatch.setattr("gui.main_window.scan_locks", list)
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["server"].setText("http://changed:2283")
    event = QCloseEvent()
    gui.closeEvent(event)
    assert calls["prompt"] == 1
    assert calls["pending"] == 0
    assert event.isAccepted()


def test_close_event_clean_skips_save_prompt(gui, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    calls = {"question": 0}

    def fake_question(*args, **kwargs):
        calls["question"] += 1
        return kwargs.get("defaultButton")

    monkeypatch.setattr("gui.mixins.persistence.QMessageBox.question", fake_question)
    monkeypatch.setattr("gui.main_window.scan_locks", list)
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    event = QCloseEvent()
    gui.closeEvent(event)
    assert calls["question"] == 0
    assert event.isAccepted()


def test_icon_cache_cleared_on_theme_switch(gui, monkeypatch):
    cleared = {"n": 0}

    def fake_clear():
        cleared["n"] += 1

    monkeypatch.setattr("gui.mixins.theme_mixin.clear_icon_cache", fake_clear)
    monkeypatch.setattr(
        "gui.mixins.theme_mixin.apply_application_theme", lambda mode: "dark"
    )
    monkeypatch.setattr(gui, "findChildren", lambda *a, **k: [])
    monkeypatch.setattr(gui, "refresh_sidebar_icons", lambda *_: None)
    gui.apply_theme("Dark")
    assert cleared["n"] == 1


def test_theme_switch_light_dark_system(gui, monkeypatch):
    # Avoid full QSS re-apply / widget walk — this test only checks mode state.
    monkeypatch.setattr(
        "gui.mixins.theme_mixin.apply_application_theme", lambda mode: "dark"
    )
    monkeypatch.setattr(gui, "findChildren", lambda *a, **k: [])
    monkeypatch.setattr(gui, "refresh_sidebar_icons", lambda *_: None)
    gui.apply_theme("Light")
    assert gui.theme_mode == "Light"
    gui.apply_theme("Dark")
    assert gui.theme_mode == "Dark"
    gui.apply_theme("System")
    assert gui.theme_mode == "System"


def test_validate_state_light_does_not_call_glob(monkeypatch):
    called = {"n": 0}

    def fake_glob(*_args, **_kwargs):
        called["n"] += 1
        return []

    monkeypatch.setattr("core.command_builder.glob.glob", fake_glob)
    res = validate_state_light(
        "upload-folder",
        {"server": "http://localhost:2283", "api_key": "key"},
        {"path": "/tmp/*.jpg"},
    )
    assert res.is_valid
    assert called["n"] == 0


def test_binary_debounce_and_ban_file_lines_repeat(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].setText("/photos")

    fired = {"n": 0}
    original = gui._on_manual_binary_changed

    def counting_handler():
        fired["n"] += 1
        original()

    gui._on_manual_binary_changed = counting_handler
    gui.binary_debounce.timeout.emit()

    ban_row = gui.adv_rows["upload-folder"]["ban-file"]
    ban_row.enable.setChecked(True)
    ban_row.value_widget.setPlainText("*.tmp\n*.bak")
    gui._do_update_status()


def test_inline_field_errors_shown_on_validation(gui):
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")
    gui.inputs["upload-folder"]["path"].clear()
    gui.update_status()
    lbl = gui._field_error_labels[("upload-folder", "path")]
    assert lbl.text()
    assert "required" in lbl.text().lower()
