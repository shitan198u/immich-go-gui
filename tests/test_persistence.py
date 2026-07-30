import sys
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMessageBox

from core.config_manager import (
    SecretStore,
    get_secret_with_fallback,
    load_config,
    save_config,
    save_secret_with_fallback,
    save_server_url,
)
from core.models import AppConfig


def test_secret_store_save_load():
    with patch("core.config_manager.keyring") as mock_kr:
        mock_kr.get_password.return_value = "STORED"
        SecretStore.set_api_key("STORED")
        mock_kr.set_password.assert_called_once_with(
            "immich-go-gui", "default:api_key", "STORED"
        )
        assert SecretStore.get_api_key() == "STORED"


def test_secret_store_migration():
    with patch("core.config_manager.keyring") as mock_kr:
        mock_kr.get_password.return_value = "OLD_KEY"
        mock_settings = MagicMock()
        mock_settings.value.return_value = "OLD_KEY"
        SecretStore.migrate_from_qsettings(mock_settings)
        mock_kr.set_password.assert_called_once_with(
            "immich-go-gui", "default:api_key", "OLD_KEY"
        )
        mock_settings.remove.assert_called_once_with("api_key")


def test_has_unsaved_changes_detects_widget_edits(gui):
    gui._mark_configuration_clean()
    assert gui.has_unsaved_changes() is False
    gui.inputs["config"]["skip-ssl"].setChecked(True)
    assert gui.has_unsaved_changes() is True


def test_has_unsaved_changes_ignores_server_url(gui):
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["server"].setText("http://edited:2283")
    assert gui.has_unsaved_changes() is False
    assert gui.has_unsaved_server_details() is True


def test_has_unsaved_server_details_detects_api_key(gui):
    gui._mark_server_details_clean()
    gui.inputs["config"]["api_key"].setText("new-secret-key")
    assert gui.has_unsaved_server_details() is True


def test_save_server_details_marks_clean(gui, monkeypatch):
    gui._mark_server_details_clean()
    gui.inputs["config"]["server"].setText("http://edited:2283")
    assert gui.has_unsaved_server_details() is True
    gui.save_server_details(show_popup=False)
    assert gui.has_unsaved_server_details() is False


def test_unified_save_prompt_both_tracks_dirty(gui, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    captured = {}

    def fake_question(widget, title, body, buttons, default):
        captured["title"] = title
        captured["body"] = body
        return QMessageBox.StandardButton.Save

    monkeypatch.setattr("gui.mixins.persistence.QMessageBox.question", fake_question)
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["api_key"].setText("changed-key")
    gui.inputs["config"]["client_timeout_minutes"].setValue(120)

    reply = gui._prompt_save_pending_configuration("closing")
    assert reply == QMessageBox.StandardButton.Save
    assert captured["title"] == "Save configuration?"
    assert "Server connection and other settings" in captured["body"]


def test_save_server_details_preserves_other_server_fields(tmp_path, monkeypatch, gui):
    cfg_file = tmp_path / "config.toml"
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(cfg_file))
    cfg_file.write_text(
        """
schema_version = 3

[general]
theme = "system"

[server]
url = "http://original:2283"
skip_ssl = true
client_timeout_minutes = 90

[secrets]
provider = "keyring"
""".strip(),
        encoding="utf-8",
    )

    gui.load_configuration()
    gui._mark_server_details_clean()
    gui.inputs["config"]["client_timeout_minutes"].setValue(30)
    gui.inputs["config"]["skip-ssl"].setChecked(False)
    gui.inputs["config"]["api_key"].setText("new-api-key")

    gui.save_server_details(show_popup=False)

    loaded = load_config()
    assert loaded.server_url == gui.inputs["config"]["server"].text()
    assert loaded.skip_ssl is True
    assert loaded.client_timeout_minutes == 90


def test_save_server_url_merge_write(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(cfg_file))
    cfg_file.write_text(
        """
schema_version = 3

[server]
url = "http://old:2283"
skip_ssl = true
client_timeout_minutes = 75
""".strip(),
        encoding="utf-8",
    )

    save_server_url("http://new:2283", path=cfg_file)

    loaded = load_config()
    assert loaded.server_url == "http://new:2283"
    assert loaded.skip_ssl is True
    assert loaded.client_timeout_minutes == 75


def test_save_marks_configuration_clean(gui, monkeypatch):
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["skip-ssl"].setChecked(True)
    assert gui.has_unsaved_changes() is True
    gui.save_configuration(show_popup=False)
    assert gui.has_unsaved_changes() is False


def test_save_configuration_preserves_server_credentials_when_widgets_empty(
    tmp_path, monkeypatch, gui
):
    """Regression: app-settings save must not wipe URL/API key from empty widgets."""
    cfg_file = tmp_path / "config.toml"
    secrets_file = tmp_path / "secrets.toml"
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(cfg_file))
    monkeypatch.setattr(
        "core.config_manager.default_secrets_path", lambda *_a, **_k: secrets_file
    )

    cfg = AppConfig()
    cfg.server_url = "http://persisted:2283"
    save_config(cfg, path=cfg_file)
    save_secret_with_fallback(
        profile_name="default",
        key="api_key",
        value="persisted-key",
        provider="keyring",
        secrets_path=secrets_file,
    )

    gui.app_config = load_config()
    gui.inputs["config"]["server"].clear()
    gui.inputs["config"]["api_key"].clear()
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["skip-ssl"].setChecked(True)

    gui.save_configuration(show_popup=False)

    loaded = load_config()
    assert loaded.server_url == "http://persisted:2283"
    assert loaded.skip_ssl is True
    assert (
        get_secret_with_fallback(
            profile_name="default",
            key="api_key",
            provider="keyring",
            secrets_path=secrets_file,
        )
        == "persisted-key"
    )


def test_close_event_server_dirty_calls_save_server_details(gui, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    calls = {"server": 0, "config": 0}

    monkeypatch.setattr(
        gui,
        "_prompt_save_pending_configuration",
        lambda context: QMessageBox.StandardButton.Save,
    )
    monkeypatch.setattr(
        gui,
        "save_server_details",
        lambda show_popup=True: calls.__setitem__("server", calls["server"] + 1),
    )
    monkeypatch.setattr(
        gui,
        "save_configuration",
        lambda show_popup=True: calls.__setitem__("config", calls["config"] + 1),
    )
    monkeypatch.setattr("gui.main_window.scan_locks", list)
    gui._mark_configuration_clean()
    gui._mark_server_details_clean()
    gui.inputs["config"]["server"].setText("http://changed:2283")

    event = QCloseEvent()
    gui.closeEvent(event)

    assert calls["server"] == 1
    assert calls["config"] == 0
    assert event.isAccepted()


def test_config_roundtrip(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(cfg_file))

    cfg = AppConfig()
    cfg.server_url = "http://localhost:2283"
    cfg.skip_ssl = True
    cfg.allow_untested_updates = True

    save_config(cfg)
    loaded = load_config()

    assert loaded.server_url == "http://localhost:2283"
    assert loaded.skip_ssl is True
    assert loaded.allow_untested_updates is True


def test_secret_store_profile_scoped(monkeypatch):
    store = {}

    def mock_set(service, username, password):
        store[username] = password

    def mock_get(service, username):
        return store.get(username, None)

    def mock_delete(service, username):
        store.pop(username, None)

    monkeypatch.setattr("core.config_manager.keyring.set_password", mock_set)
    monkeypatch.setattr("core.config_manager.keyring.get_password", mock_get)
    monkeypatch.setattr("core.config_manager.keyring.delete_password", mock_delete)

    assert SecretStore.set_secret("default", "api_key", "key_default") is True
    assert SecretStore.set_secret("work", "api_key", "key_work") is True
    assert SecretStore.set_secret("work", "admin_api_key", "admin_work") is True

    assert SecretStore.get_secret("default", "api_key") == "key_default"
    assert SecretStore.get_secret("work", "api_key") == "key_work"
    assert SecretStore.get_secret("work", "admin_api_key") == "admin_work"

    SecretStore.clear_secret("work", "api_key")
    assert SecretStore.get_secret("work", "api_key") == ""
    assert SecretStore.get_secret("default", "api_key") == "key_default"


def test_secret_keyring_failure_fallback(tmp_path, monkeypatch):
    secrets_file = tmp_path / "secrets.toml"

    def mock_failing_set(service, username, password):
        raise RuntimeError("Keyring unavailable")

    def mock_failing_get(service, username):
        return ""

    monkeypatch.setattr("core.config_manager.keyring.set_password", mock_failing_set)
    monkeypatch.setattr("core.config_manager.keyring.get_password", mock_failing_get)

    res = save_secret_with_fallback(
        profile_name="default",
        key="api_key",
        value="fallback_secret",
        provider="keyring",
        secrets_path=secrets_file,
    )

    assert res.ok is True
    assert res.provider_used == "config"
    assert "keyring is unavailable" in res.message.lower()

    val = get_secret_with_fallback(
        profile_name="default",
        key="api_key",
        provider="keyring",
        secrets_path=secrets_file,
    )
    assert val == "fallback_secret"


def test_collect_form_state_excludes_secrets(gui):
    state = gui.collect_form_state()
    for tab_name, tab_dict in state.items():
        for secret_key in ("api_key", "from-api-key", "admin_api_key"):
            assert secret_key not in tab_dict


def test_secret_copy_success_verification(monkeypatch):
    from core.config_manager import SecretStore

    secrets_db = {}

    def mock_set(profile, key, val):
        secrets_db[(profile, key)] = val
        return True

    def mock_get(profile, key):
        return secrets_db.get((profile, key), "")

    monkeypatch.setattr(SecretStore, "set_secret", mock_set)
    monkeypatch.setattr(SecretStore, "get_secret", mock_get)

    secrets_db[("src", "api_key")] = "my-secret-key"
    res = SecretStore.copy_secrets("src", "dst")
    assert res is True
    assert secrets_db.get(("dst", "api_key")) == "my-secret-key"


def test_advanced_secret_value_not_persisted(gui):
    gui.toggle_advanced(True)
    gui.adv_rows["upload-immich"]["from-admin-api-key"].set_state(
        {
            "enabled": True,
            "value": "super-secret-admin-key",
        }
    )

    state = gui.collect_form_state()
    saved = state["advanced"]["upload-immich"]["from-admin-api-key"]
    assert saved["enabled"] is False
    assert saved["value"] == ""


def test_secret_status_label_keyring(gui, monkeypatch):
    gui.app_config.secrets_provider = "keyring"
    monkeypatch.setattr(
        SecretStore, "get_secret", staticmethod(lambda *_: "secret-key")
    )
    monkeypatch.setattr(gui, "_secrets_file_has_key", lambda: False)
    gui._update_secret_status()
    assert "keyring" in gui.lbl_secret_status.text().lower()


def test_secret_status_label_file_fallback(gui, monkeypatch):
    gui.app_config.secrets_provider = "config"
    monkeypatch.setattr(SecretStore, "get_secret", staticmethod(lambda *_: ""))
    monkeypatch.setattr(gui, "_secrets_file_has_key", lambda: True)
    gui._update_secret_status()
    assert "secrets.toml" in gui.lbl_secret_status.text()


def test_profile_index_cached(tmp_path, monkeypatch):
    from core import profile_manager as pm

    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    pm.clear_profiles_cache()
    (tmp_path / "profiles.toml").write_text(
        'schema_version = 1\nactive_profile = "default"\n[[profiles]]\nname = "default"\n',
        encoding="utf-8",
    )
    # Point profiles path
    monkeypatch.setattr(pm, "global_profiles_path", lambda: tmp_path / "profiles.toml")
    pm.clear_profiles_cache()
    first = pm._load_profiles_index()
    (tmp_path / "profiles.toml").write_text(
        'schema_version = 1\nactive_profile = "other"\n[[profiles]]\nname = "other"\n',
        encoding="utf-8",
    )
    second = pm._load_profiles_index()
    assert first is second
    assert second.get("active_profile") == "default"
    pm.clear_profiles_cache()
    third = pm._load_profiles_index()
    assert third.get("active_profile") == "other"


def test_legacy_root_config_migrated_when_profiles_dir_exists(tmp_path, monkeypatch):
    """Regression: profiles/ may exist before default/config.toml is populated."""
    from core.profile_manager import (
        clear_profiles_cache,
        migrate_single_config_to_default,
        profile_config_path,
    )

    base = tmp_path / "immich-go-gui"
    base.mkdir()
    legacy = base / "config.toml"
    legacy.write_text(
        '[server]\nurl = "http://legacy:2283"\n',
        encoding="utf-8",
    )
    (base / "profiles" / "default").mkdir(parents=True)

    monkeypatch.setattr("core.config_manager.default_config_dir", lambda: base)
    clear_profiles_cache()

    migrate_single_config_to_default()

    migrated = profile_config_path("default")
    assert migrated.exists()
    loaded = load_config(migrated)
    assert loaded.server_url == "http://legacy:2283"
    assert not legacy.exists()


def test_save_config_uses_profile_path_without_env_override(tmp_path, monkeypatch):
    """Save must land in profiles/{name}/config.toml, not the config root."""
    from core.profile_manager import clear_profiles_cache, profile_config_path

    base = tmp_path / "immich-go-gui"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.delenv("IMMICH_GO_GUI_CONFIG", raising=False)
    monkeypatch.setattr("core.config_manager.default_config_dir", lambda: base)
    clear_profiles_cache()

    cfg = AppConfig()
    cfg.server_url = "http://saved:2283"
    cfg.profile_name = "default"
    save_config(cfg)

    path = profile_config_path("default")
    assert path == base / "profiles" / "default" / "config.toml"
    assert path.exists()
    loaded = load_config(path)
    assert loaded.server_url == "http://saved:2283"


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="XDG_CONFIG_HOME is honored only on Linux",
)
def test_linux_xdg_save_server_details_roundtrip(tmp_path, monkeypatch):
    """Regression: GUI save must persist server URL under Linux XDG profile paths."""
    from unittest.mock import patch

    from core.profile_manager import profile_config_path
    from gui import ImmichGoGUI

    xdg = tmp_path / "xdg-config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("IMMICH_GO_GUI_CONFIG", raising=False)

    with (
        patch.object(ImmichGoGUI, "check_binary_version"),
        patch.object(ImmichGoGUI, "_probe_keyring", return_value=True),
        patch("PySide6.QtWidgets.QMessageBox.warning"),
        patch(
            "gui.mixins.persistence.get_secret_with_fallback",
            return_value="roundtrip-key",
        ),
    ):
        gui = ImmichGoGUI()
        gui.inputs["config"]["server"].setText("http://linux-host:2283")
        gui.inputs["config"]["api_key"].setText("roundtrip-key")
        gui.save_server_details(show_popup=False)

        cfg_path = profile_config_path("default")
        assert cfg_path == xdg / "immich-go-gui" / "profiles" / "default" / "config.toml"
        assert load_config(cfg_path).server_url == "http://linux-host:2283"

        gui.inputs["config"]["server"].clear()
        gui.inputs["config"]["api_key"].clear()
        gui.load_configuration()

        assert gui.inputs["config"]["server"].text() == "http://linux-host:2283"
        assert gui.inputs["config"]["api_key"].text() == "roundtrip-key"


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="XDG_CONFIG_HOME is honored only on Linux",
)
def test_linux_xdg_save_configuration_roundtrip(tmp_path, monkeypatch):
    """Regression: File → Save persists server URL via save_server_details when dirty."""
    from unittest.mock import patch

    from core.profile_manager import clear_profiles_cache, profile_config_path
    from gui import ImmichGoGUI

    xdg = tmp_path / "xdg-config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("IMMICH_GO_GUI_CONFIG", raising=False)
    clear_profiles_cache()

    with (
        patch.object(ImmichGoGUI, "check_binary_version"),
        patch.object(ImmichGoGUI, "_probe_keyring", return_value=True),
        patch("PySide6.QtWidgets.QMessageBox.warning"),
        patch("PySide6.QtWidgets.QMessageBox.information"),
    ):
        gui = ImmichGoGUI()
        gui._mark_configuration_clean()
        gui._mark_server_details_clean()
        gui.inputs["config"]["server"].setText("http://linux-save-config:2283")
        gui._save_from_menu()
        gui._force_close = True
        gui.close()

    cfg_path = profile_config_path("default")
    assert load_config(cfg_path).server_url == "http://linux-save-config:2283"
