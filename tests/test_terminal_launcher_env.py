"""Tests for POSIX terminal environment propagation via env.sh."""

from datetime import UTC
from pathlib import Path

import pytest

from core.process_tracker import create_lock
from core.terminal_launcher import _quote_sh_env_val, launch_external_terminal


@pytest.mark.skipif(
    __import__("sys").platform.startswith("win"),
    reason="POSIX terminal launcher tests",
)
def test_quote_sh_env_val_escapes_single_quotes():
    assert _quote_sh_env_val("a'b") == "'a'\"'\"'b'"


@pytest.mark.skipif(
    __import__("sys").platform.startswith("win"),
    reason="POSIX terminal launcher tests",
)
def test_posix_run_sh_sources_immich_go_env(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    lock_path = create_lock("upload-folder", "upload", "./immich-go")

    env = {
        "IMMICH_GO_UPLOAD_SERVER": "http://localhost:2283",
        "IMMICH_GO_UPLOAD_API_KEY": "secret_key_123",
        "PATH": "/usr/bin",
    }
    cmd = ["./immich-go", "upload", "from-folder", "/photos"]

    from unittest.mock import patch

    with patch("subprocess.Popen") as mock_popen, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gnome-terminal"
        mock_popen.return_value.pid = 4242
        res = launch_external_terminal(cmd, env, lock_path, preferred_terminal="auto")
        assert res.ok is True
        run_sh = Path(mock_popen.call_args[0][0][-1])

    env_sh = run_sh.parent / "env.sh"
    assert env_sh.exists()
    assert run_sh.exists()

    env_content = env_sh.read_text(encoding="utf-8")
    assert "export IMMICH_GO_UPLOAD_SERVER='http://localhost:2283'" in env_content
    assert "export IMMICH_GO_UPLOAD_API_KEY='secret_key_123'" in env_content
    assert "IMMICH_GO_GUI" not in env_content  # non IMMICH_GO_* vars excluded

    run_content = run_sh.read_text(encoding="utf-8")
    assert 'source "$ENV_FILE"' in run_content
    assert 'rm -f "$ENV_FILE"' in run_content
    assert "trap cleanup EXIT INT TERM HUP" in run_content
    assert "secret_key_123" not in run_content
    assert "IMMICH_GO_GUI_HEADLESS" in run_content
    assert "exec bash" in run_content


@pytest.mark.skipif(
    __import__("sys").platform.startswith("win"),
    reason="POSIX terminal launcher tests",
)
def test_posix_stale_lock_dead_shell_pid(tmp_path, monkeypatch):
    """Dead shell PID should not keep lock active via orphan heartbeat."""
    from datetime import datetime, timedelta

    from core.process_tracker import is_lock_active, update_lock

    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    lock_path = create_lock("upload-folder", "upload", "./immich-go")

    stale_start = (datetime.now(UTC) - timedelta(seconds=120)).isoformat()
    update_lock(lock_path, started_at=stale_start, shell_pid=999999)

    pid_file = lock_path.with_suffix(".pid")
    pid_file.write_text("999999", encoding="utf-8")
    assert is_lock_active(lock_path) is False


@pytest.mark.skipif(
    __import__("sys").platform.startswith("win"),
    reason="POSIX terminal launcher tests",
)
def test_posix_terminal_discovery_includes_alacritty_and_kitty(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    lock_path = create_lock("upload-folder", "upload", "./immich-go")
    cmd = ["./immich-go", "upload", "from-folder", "/photos"]

    from unittest.mock import patch

    # Test alacritty
    with patch("subprocess.Popen") as mock_popen, patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda term: (
            "/usr/bin/alacritty" if term == "alacritty" else None
        )
        mock_popen.return_value.pid = 5001
        res = launch_external_terminal(cmd, {}, lock_path, preferred_terminal="auto")
        assert res.ok is True
        assert mock_popen.call_args[0][0][0] == "alacritty"

    # Test kitty
    with patch("subprocess.Popen") as mock_popen, patch("shutil.which") as mock_which:
        mock_which.side_effect = lambda term: (
            "/usr/bin/kitty" if term == "kitty" else None
        )
        mock_popen.return_value.pid = 5002
        res = launch_external_terminal(cmd, {}, lock_path, preferred_terminal="auto")
        assert res.ok is True
        assert mock_popen.call_args[0][0][0] == "kitty"
