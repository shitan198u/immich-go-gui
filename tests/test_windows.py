import tempfile
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from core.process_tracker import (
    create_lock,
    is_lock_active,
    read_lock,
    release_lock,
    scan_locks,
)
from core.terminal_launcher import launch_external_terminal


def test_process_tracker_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))

    lock_path = create_lock(
        tab_key="upload-folder",
        command_summary="upload from-folder",
        binary_path="./immich-go",
    )
    assert lock_path.exists()

    lock = read_lock(lock_path)
    assert lock is not None
    assert lock.tab_key == "upload-folder"

    assert is_lock_active(lock_path) is True
    assert len(scan_locks()) == 1

    release_lock(lock_path)
    assert lock_path.exists() is False
    assert len(scan_locks()) == 0


def test_terminal_launcher_posix_script_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    lock_path = create_lock("upload-folder", "upload", "./immich-go")

    env = {
        "IMMICH_GO_UPLOAD_SERVER": "http://localhost:2283",
        "IMMICH_GO_UPLOAD_API_KEY": "secret_key_123",
    }
    cmd = ["./immich-go", "upload", "from-folder", "/photos"]

    with patch("subprocess.Popen") as mock_popen, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gnome-terminal"
        res = launch_external_terminal(cmd, env, lock_path, preferred_terminal="auto")
        assert res.ok is True
        assert mock_popen.called


def test_terminal_launcher_working_directory_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    monkeypatch.setattr("sys.platform", "linux")
    lock_path = create_lock("upload-folder", "upload", "./immich-go")

    env = {"IMMICH_GO_UPLOAD_SERVER": "http://localhost:2283"}
    cmd = ["./immich-go", "upload", "from-folder", "/photos"]

    with patch("subprocess.Popen"), patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gnome-terminal"
        res = launch_external_terminal(cmd, env, lock_path, preferred_terminal="auto")
        assert res.ok is True

    temp_dirs = list(
        set(
            list(Path(tempfile.gettempdir()).glob("immich-go-run-*"))
            + list(Path("/tmp").glob("immich-go-run-*"))
        )
    )
    assert temp_dirs, "Expected POSIX launcher to create a temp run directory"

    latest_temp = max(temp_dirs, key=lambda d: d.stat().st_mtime)
    run_sh = latest_temp / "run.sh"
    assert run_sh.exists()

    content = run_sh.read_text(encoding="utf-8")

    assert 'SAFE_DIR="$HOME"' in content
    assert 'cd "$SAFE_DIR"' in content
    assert "trap cleanup EXIT INT TERM HUP" in content
    assert f"cd '{latest_temp}'" not in content
    assert f"rm -rf '{latest_temp}'" not in content


def test_windows_stale_lock_on_closed_terminal(tmp_path, monkeypatch):
    """Regression test: closing the cmd window must mark the lock stale even when
    the orphan heartbeat subprocess keeps updating the .heartbeat file.

    Before the fix, is_lock_active() fell through to the heartbeat check after
    seeing terminal_pid dead, and the fresh heartbeat file returned True forever.
    """
    monkeypatch.setenv("IMMICH_GO_GUI_CONFIG", str(tmp_path / "config.toml"))
    monkeypatch.setattr("core.process_tracker.sys.platform", "win32")
    monkeypatch.setattr("core.process_tracker._is_process_alive", lambda pid: False)
    from core.process_tracker import (
        create_lock,
        is_lock_active,
        release_lock,
        update_lock,
    )

    l_path = create_lock("upload-folder", "upload", "./immich-go")

    # Simulate: cmd /k launched (terminal_pid set), started more than 60 s ago
    # (so grace period does not keep it alive), shell_pid not set.
    update_lock(
        l_path,
        terminal_pid=999999,  # dead PID — cmd window is "closed"
        started_at="2020-01-01T00:00:00+00:00",
    )

    # Create a fresh .heartbeat file (simulating the orphan heartbeat subprocess
    # that keeps running after the cmd window is closed).
    hb_path = l_path.with_suffix(".heartbeat")
    hb_path.write_text("", encoding="utf-8")
    # mtime is "now" by default — age < 60 s, so heartbeat looks fresh.

    # BEFORE fix: is_lock_active() would return True (heartbeat check wins).
    # AFTER fix: should return False because terminal_pid is dead on win32.
    assert is_lock_active(l_path) is False, (
        "Lock must be stale when cmd window PID is dead, even if heartbeat file is fresh"
    )

    release_lock(l_path)


def test_is_process_alive_win32_still_active(monkeypatch):
    """Cover win32 ctypes OpenProcess / GetExitCodeProcess path in _is_process_alive."""
    monkeypatch.setattr("core.process_tracker.sys.platform", "win32")

    class FakeKernel32:
        STILL_ACTIVE = 259

        def OpenProcess(self, access, inherit, pid):
            return 42 if pid == 1234 else 0

        def GetExitCodeProcess(self, handle, exit_code_ref):
            exit_code_ref._obj.value = self.STILL_ACTIVE
            return 1

        def CloseHandle(self, handle):
            return 1

    fake_kernel32 = FakeKernel32()
    import ctypes

    fake_windll = type("windll", (), {})()
    fake_windll.kernel32 = fake_kernel32
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)

    from core.process_tracker import _is_process_alive

    assert _is_process_alive(1234) is True
    assert _is_process_alive(9999) is False
    assert _is_process_alive(None) is False


def test_forward_all_immich_go_env_vars(tmp_path, monkeypatch):
    from core.terminal_launcher import launch_external_terminal

    dummy_lock = tmp_path / "test.lock"
    dummy_lock.write_text("{}", encoding="utf-8")

    test_env = {
        "IMMICH_GO_CUSTOM_VAR": "custom_val",
        "IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER": "http://srv:2283",
        "OTHER_VAR": "ignored",
    }

    with (
        patch("subprocess.Popen") as mock_popen,
        patch("shutil.which", return_value="/usr/bin/gnome-terminal"),
    ):
        launch_external_terminal(
            command=["./immich-go", "archive", "from-immich"],
            env=test_env,
            lock_path=dummy_lock,
        )
        assert mock_popen.called
        call_args = mock_popen.call_args
        _args, kwargs = call_args
        env_used = kwargs.get("env", {})
        assert env_used.get("IMMICH_GO_CUSTOM_VAR") == "custom_val"
        assert (
            env_used.get("IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_SERVER")
            == "http://srv:2283"
        )


def test_windows_bat_heartbeat_generation(tmp_path, monkeypatch):
    """Fix 1.4: Windows terminal launch generates a .bat file with background heartbeat loop."""
    from core.terminal_launcher import launch_external_terminal

    monkeypatch.setattr("sys.platform", "win32")

    lock_file = tmp_path / "run_test.lock"
    lock_file.write_text('{"run_id": "test"}', encoding="utf-8")

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value.pid = 1234
        res = launch_external_terminal(["immich-go", "stack"], {}, lock_file)
        assert res.ok

    bat_file = lock_file.with_suffix(".bat")
    assert bat_file.exists()
    bat_content = bat_file.read_text(encoding="utf-8")

    assert "HB_FILE=" in bat_content
    assert ".heartbeat" in bat_content
    assert "start /b cmd /c" in bat_content
    assert 'del /f "%HB_FILE%"' in bat_content
    # Fix #67b: bat file must NOT delete itself — self-deletion under cmd /k
    # causes 'The batch file cannot be found' after immich-go exits.
    # release_lock() cleans up the .bat sidecar instead.
    assert 'del /f "' + str(lock_file.with_suffix(".bat")) + '"' not in bat_content
    assert 'del /f "%BAT_FILE%"' not in bat_content


class TestWindowsPathParsing:
    """Group A: Pure path logic tests — no filesystem access, run on any OS."""

    def test_bat_sibling_derived_from_lock_path(self):
        lock = PureWindowsPath(
            r"C:\Users\Shsrra\AppData\Roaming\immich-go-gui\locks\run_89d244f3.lock"
        )
        bat = lock.with_suffix(".bat")
        hb = lock.with_suffix(".heartbeat")
        assert bat.name == "run_89d244f3.bat"
        assert hb.name == "run_89d244f3.heartbeat"
        assert bat.parent == lock.parent

    def test_path_with_spaces_in_username(self):
        import subprocess as _sp

        p = PureWindowsPath(
            r"C:\Users\John Doe\AppData\Roaming\immich-go-gui\locks\run_abc.bat"
        )
        assert " " in str(p)
        assert p.suffix == ".bat"
        cmdline = _sp.list2cmdline(["cmd", "/k", str(p)])
        assert '"' in cmdline, f"Expected quoted path in: {cmdline!r}"
        assert str(p) in cmdline

    def test_path_without_spaces_list2cmdline(self):
        import subprocess as _sp

        p = PureWindowsPath(
            r"C:\Users\Shsrra\AppData\Roaming\immich-go-gui\locks\run_x.bat"
        )
        assert " " not in str(p)
        cmdline = _sp.list2cmdline(["cmd", "/k", str(p)])
        assert str(p) in cmdline

    def test_binary_filename_win32(self):
        win_p = PureWindowsPath(r"C:\Users\me\.immich-go-gui\bin\0.32.0\immich-go.exe")
        assert win_p.name == "immich-go.exe"
        assert win_p.stem == "immich-go"
        assert win_p.suffix == ".exe"

    def test_lock_path_drive_letter_preserved(self):
        lock = PureWindowsPath(r"C:\immich-go-gui\locks\run_001.lock")
        assert lock.with_suffix(".bat").drive == "C:"
        assert lock.with_suffix(".heartbeat").drive == "C:"


class TestWindowsBatFileCreation:
    """Group B: Windows FS simulation tests."""

    def test_bat_written_with_heartbeat_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")
        lock_path = tmp_path / "run_test.lock"
        lock_path.write_text('{"run_id": "test"}', encoding="utf-8")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 9999
            res = launch_external_terminal(
                ["immich-go.exe", "upload", "from-folder"], {}, lock_path
            )

        assert res.ok
        bat = lock_path.with_suffix(".bat")
        assert bat.exists(), "Expected .bat file to be created alongside lock"
        content = bat.read_text(encoding="utf-8")
        assert "HB_FILE=" in content
        assert ".heartbeat" in content
        assert "start /b cmd /c" in content
        assert 'del /f "%HB_FILE%"' in content
        bat_path_str = str(lock_path.with_suffix(".bat"))
        assert f'del /f "{bat_path_str}"' not in content

    def test_popen_uses_list_form_not_shell(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")

        spaced_dir = tmp_path / "John Doe" / "locks"
        spaced_dir.mkdir(parents=True)
        lock_path = spaced_dir / "run_spaced.lock"
        lock_path.write_text('{"run_id": "spaced"}', encoding="utf-8")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 1234
            res = launch_external_terminal(["immich-go.exe", "stack"], {}, lock_path)

        assert res.ok
        assert mock_popen.called
        call_args = mock_popen.call_args
        cmd_arg = call_args[0][0]

        assert isinstance(cmd_arg, list)
        assert cmd_arg[0] == "cmd"
        assert cmd_arg[1] == "/k"
        assert str(lock_path.with_suffix(".bat")) == cmd_arg[2]
        kwargs = call_args[1]
        assert not kwargs.get("shell")
        assert kwargs.get("creationflags", 0) & 0x00000010

    def test_popen_list_form_without_spaces(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")
        lock_path = tmp_path / "run_nospace.lock"
        lock_path.write_text('{"run_id": "nospace"}', encoding="utf-8")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 5678
            launch_external_terminal(
                ["immich-go.exe", "upload", "from-folder"], {}, lock_path
            )

        cmd_arg = mock_popen.call_args[0][0]
        assert isinstance(cmd_arg, list)
        assert cmd_arg[0] == "cmd"
        assert not mock_popen.call_args[1].get("shell")
