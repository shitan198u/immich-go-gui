from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core import default_secrets_path, load_binary_metadata
from gui.mixins.app_update import _gui_version
from gui.widgets import BasePage, Card, ElidingLabel, FormSection
from theme import THEME_DARK, THEME_LIGHT, THEME_SYSTEM


def build_config_tab(host) -> QWidget:
    page = BasePage()
    host.inputs["config"] = {}

    card = Card("Immich Server Connection", required=True)
    form = FormSection()

    host.server_url_edit = QLineEdit()
    host.server_url_edit.setPlaceholderText("http://localhost:2283")
    host.inputs["config"]["server"] = host.server_url_edit
    form.add_row(
        "Server URL",
        host._wrap_with_field_error("config", "server", host.server_url_edit),
    )

    host.api_key_edit = QLineEdit()
    host.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    host.api_key_edit.setPlaceholderText("Paste your Immich API key")
    host.inputs["config"]["api_key"] = host.api_key_edit
    form.add_row(
        "API Key",
        host._wrap_with_field_error("config", "api_key", host.api_key_edit),
        "You can generate an API key in Immich under Account Settings -> API Keys.",
    )

    host._conn_test_debounce = QTimer(host)
    host._conn_test_debounce.setSingleShot(True)
    host._conn_test_debounce.setInterval(1200)
    host._conn_test_debounce.timeout.connect(host._auto_test_connection)
    host.server_url_edit.textChanged.connect(host._reset_conn_test_state)
    host.api_key_edit.textChanged.connect(host._reset_conn_test_state)
    host.server_url_edit.textChanged.connect(lambda: host._conn_test_debounce.start())
    host.api_key_edit.textChanged.connect(lambda: host._conn_test_debounce.start())

    host._add_ssl_skip_row(form, host.inputs["config"])

    host.client_timeout_spin = QSpinBox()
    host.client_timeout_spin.setRange(5, 240)
    host.client_timeout_spin.setSuffix(" min")
    host.client_timeout_spin.setValue(60)
    host.inputs["config"]["client_timeout_minutes"] = host.client_timeout_spin
    form.add_row(
        "Client Timeout",
        host.client_timeout_spin,
        "Low values may cause long uploads or archives to fail. Increase if jobs time out.",
    )

    host.btn_test_connection = QPushButton("Test Connection")
    host.btn_test_connection.clicked.connect(host.on_test_connection_clicked)
    host.btn_save_server_details = QPushButton("Save Server Details")
    host.btn_save_server_details.clicked.connect(
        lambda: host.save_server_details(show_popup=True)
    )
    conn_btn_row = QHBoxLayout()
    conn_btn_row.setSpacing(8)
    conn_btn_row.addWidget(host.btn_test_connection)
    conn_btn_row.addWidget(host.btn_save_server_details)
    conn_btn_row.addStretch()
    form.add_row("", conn_btn_row)

    card.layout.addLayout(form)
    page.addWidget(card)

    card_sec = Card("Security & Secret Management")
    sec_form = FormSection()

    host.cmb_secret_provider = QComboBox()
    host.cmb_secret_provider.addItem("OS Keyring (recommended)", "keyring")
    host.cmb_secret_provider.addItem("Local secrets file", "config")
    host.inputs["config"]["secret_provider"] = host.cmb_secret_provider
    sec_form.add_row(
        "Secret Storage",
        host.cmb_secret_provider,
        "OS Keyring uses system credential store (Keychain/KWallet/Credential Manager).",
    )

    host.lbl_secret_status = QLabel("")
    host.lbl_secret_status.setObjectName("Hint")
    sec_form.add_row("", host.lbl_secret_status)

    host.admin_api_key_edit = QLineEdit()
    host.admin_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    host.admin_api_key_edit.setPlaceholderText("Optional Immich Admin API key")
    host.inputs["config"]["admin_api_key"] = host.admin_api_key_edit
    sec_form.add_row(
        "Admin API Key",
        host.admin_api_key_edit,
        "Required for administrative operations like partner shared albums or user management.",
    )

    host.lbl_secrets_path_hint = QLabel(f"Local secrets path: {default_secrets_path()}")
    host.lbl_secrets_path_hint.setObjectName("Hint")
    sec_form.add_row("", host.lbl_secrets_path_hint)

    card_sec.layout.addLayout(sec_form)
    page.addWidget(card_sec)

    card_app = Card("Application")
    app_row = QHBoxLayout()
    app_row.setSpacing(16)
    app_row.setAlignment(Qt.AlignmentFlag.AlignTop)
    app_info = QVBoxLayout()
    app_info.setSpacing(2)
    host.lbl_app_version = QLabel(f"Current Version: {_gui_version()}")
    host.lbl_app_version.setObjectName("FieldLabel")
    host.lbl_app_version.setWordWrap(True)
    host.lbl_app_update_status = QLabel("Check for updates to see status.")
    host.lbl_app_update_status.setObjectName("AppUpdateStatus")
    app_info.addWidget(host.lbl_app_version)
    app_info.addWidget(host.lbl_app_update_status)
    app_row.addLayout(app_info, 1)
    host.btn_check_app_updates = QPushButton("Check for Updates")
    host.btn_check_app_updates.clicked.connect(host.check_for_application_updates)
    app_row.addWidget(host.btn_check_app_updates, 0, Qt.AlignmentFlag.AlignTop)
    card_app.layout.addLayout(app_row)
    page.addWidget(card_app)

    card2 = Card("Binary Management")
    row = QHBoxLayout()
    row.setSpacing(16)
    row.setAlignment(Qt.AlignmentFlag.AlignTop)
    info = QVBoxLayout()
    info.setSpacing(2)
    host.lbl_binary_version = QLabel("Checking version…")
    host.lbl_binary_version.setObjectName("FieldLabel")
    host.lbl_binary_version.setWordWrap(True)
    host.lbl_binary_path = ElidingLabel("", Qt.TextElideMode.ElideMiddle)
    host.lbl_binary_path.setObjectName("Hint")
    info.addWidget(host.lbl_binary_version)
    info.addWidget(host.lbl_binary_path)
    row.addLayout(info, 1)
    btn_check = QPushButton("Check for Updates")
    host.btn_check_updates = btn_check
    btn_check.clicked.connect(host.check_for_updates)
    row.addWidget(btn_check, 0, Qt.AlignmentFlag.AlignTop)
    card2.layout.addLayout(row)

    manual_form = FormSection()
    host.manual_binary_edit = QLineEdit()
    host.manual_binary_edit.setPlaceholderText(
        "/usr/local/bin/immich-go  (leave empty to use managed binary)"
    )
    meta = load_binary_metadata()
    if meta.get("manual_path"):
        host.manual_binary_edit.setText(meta["manual_path"])
    host.binary_debounce = QTimer()
    host.binary_debounce.setSingleShot(True)
    host.binary_debounce.setInterval(400)
    host.binary_debounce.timeout.connect(host._on_manual_binary_changed)
    host.manual_binary_edit.textChanged.connect(
        lambda _text="": host.binary_debounce.start()
    )
    manual_form.add_row(
        "Manual Binary Path",
        host.manual_binary_edit,
        "If set, this path is used instead of the managed binary.",
    )
    card2.layout.addLayout(manual_form)
    page.addWidget(card2)

    card3 = Card("Appearance")
    theme_form = FormSection()
    host.theme_mode_combo = QComboBox()
    host.theme_mode_combo.addItems([THEME_SYSTEM, THEME_LIGHT, THEME_DARK])
    host.theme_mode_combo.setCurrentText(host.theme_mode)
    host.theme_mode_combo.currentTextChanged.connect(host.apply_theme)
    theme_form.add_row(
        "Theme",
        host.theme_mode_combo,
        "System follows your operating system theme when supported by Qt.",
    )
    card3.layout.addLayout(theme_form)
    page.addWidget(card3)

    adv_card = Card("Advanced Configuration")
    adv_form = FormSection()

    host.allow_untested_check = QCheckBox("Allow untested immich-go versions")
    host.allow_untested_check.setChecked(False)
    host.inputs["config"]["allow_untested_updates"] = host.allow_untested_check
    adv_form.addRow("", host.allow_untested_check)

    host.preferred_terminal_combo = QComboBox()
    host.preferred_terminal_combo.addItems(
        ["auto", "gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
    )
    host.inputs["config"]["preferred_terminal"] = host.preferred_terminal_combo
    adv_form.add_row("Preferred Terminal", host.preferred_terminal_combo)

    adv_card.layout.addLayout(adv_form)
    adv_card.setVisible(False)
    page.addWidget(adv_card)
    host.adv_frames.append(adv_card)

    if hasattr(host, "_init_app_update_ui"):
        host._init_app_update_ui()

    page.addStretch()
    return page
