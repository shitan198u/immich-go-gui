from unittest.mock import MagicMock, patch

import requests

from core.network import check_preflight_server_connection
from core.network import test_immich_connection as run_test_immich_connection


def test_network_connection_success():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"version": "v1.100.0"}
        mock_get.return_value = mock_resp

        res = run_test_immich_connection("http://localhost:2283", "secret_key")
        assert res.ok is True
        assert res.status_code == 200
        assert "v1.100.0" in res.message
        assert res.server_version == "v1.100.0"


def test_network_connection_auth_failure():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        res = run_test_immich_connection("http://localhost:2283", "bad_key")
        assert res.ok is False
        assert res.status_code == 401
        assert "Authentication failed" in res.message


def test_network_connection_ssl_error():
    with patch("requests.get", side_effect=requests.exceptions.SSLError):
        res = run_test_immich_connection("https://localhost:2283", "secret_key")
        assert res.ok is False
        assert "SSL certificate verification failed" in res.message


def test_network_connection_timeout():
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        res = run_test_immich_connection("http://localhost:2283", "secret_key")
        assert res.ok is False
        assert "timed out" in res.message


def test_check_preflight_server_connection_serverless():
    res = check_preflight_server_connection(
        "archive-folder", {"server": "http://localhost:2283"}
    )
    assert res.ok is True
    assert "Serverless" in res.message


def test_check_preflight_server_connection_success():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"version": "v1.100.0"}
        mock_get.return_value = mock_resp

        res = check_preflight_server_connection(
            "upload-folder", {"server": "http://localhost:2283", "api_key": "key"}
        )
        assert res.ok is True


def test_check_preflight_server_connection_unreachable():
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        res = check_preflight_server_connection(
            "upload-folder", {"server": "http://localhost:2283", "api_key": "key"}
        )
        assert res.ok is False
        assert "Failed to connect to server" in res.message


def test_status_card_reflects_connection_test_failure(gui):
    gui.stacked_widget.setCurrentIndex(0)
    gui.inputs["config"]["server"].setText("http://localhost:2283")
    gui.inputs["config"]["api_key"].setText("key")

    with (
        patch("requests.get", side_effect=requests.exceptions.ConnectionError),
        patch("PySide6.QtWidgets.QMessageBox.warning"),
    ):
        gui.on_test_connection_clicked()
        assert gui._last_conn_test_ok is False
        assert "Connection Failed" in gui.status_card.txt_s.text()


def test_serverless_tab_run_enabled_after_connection_failure(gui):
    gui._last_conn_test_ok = False
    gui.stacked_widget.setCurrentIndex(2)
    gui.archive_tabs.setCurrentIndex(0)
    gui.inputs["archive-folder"]["path"].setText("/src")
    gui.inputs["archive-folder"]["write-to"].setText("/dst")
    gui.update_status()
    assert gui.btn_run.isEnabled() is True
    assert gui.btn_dry_run.isEnabled() is True

