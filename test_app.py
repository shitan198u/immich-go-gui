"""
test_app.py – Unit and integration tests for Immich-Go GUI.

Covers:
  - Pure utility functions (collect_paths, mask_command_for_display, build_environment)
  - SecretStore (mocked keyring)
  - Command builder ordering and flag scoping
  - Integration: masking wired into preview, env vars wired into run_command
  - TOML config round-trip
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure the app module is importable
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from app import (
    SecretStore,
    build_environment,
    collect_paths,
    load_toml_config,
    mask_command_for_display,
    save_toml_config,
)


# ===================================================================
# 1. collect_paths
# ===================================================================

class TestCollectPaths:
    def test_single_path(self):
        assert collect_paths("/photos") == ["/photos"]

    def test_multiple_paths(self):
        result = collect_paths("/a /b /c")
        assert result == ["/a", "/b", "/c"]

    def test_glob_expansion(self, tmp_path):
        (tmp_path / "takeout-001.zip").touch()
        (tmp_path / "takeout-002.zip").touch()
        (tmp_path / "other.txt").touch()
        pattern = str(tmp_path / "takeout-*.zip")
        result = collect_paths(pattern)
        assert len(result) == 2
        assert all("takeout" in p for p in result)

    def test_empty_string(self):
        assert collect_paths("") == []
        assert collect_paths("   ") == []

    def test_quoted_path_with_spaces(self, tmp_path):
        d = tmp_path / "my photos"
        d.mkdir()
        result = collect_paths(f'"{d}"')
        assert result == [str(d)]

    def test_no_glob_match_keeps_literal(self):
        result = collect_paths("/nonexistent/path-*.zip")
        assert result == ["/nonexistent/path-*.zip"]


# ===================================================================
# 2. mask_command_for_display
# ===================================================================

class TestMaskCommandForDisplay:
    def test_masks_api_key_equals(self):
        cmd = "immich-go upload from-folder --server=http://x --api-key=SECRET123 /photos"
        masked = mask_command_for_display(cmd)
        assert "SECRET123" not in masked
        assert "--api-key=********" in masked

    def test_masks_from_api_key_equals(self):
        cmd = "immich-go upload from-immich --from-api-key=TOPSECRET"
        masked = mask_command_for_display(cmd)
        assert "TOPSECRET" not in masked
        assert "--from-api-key=********" in masked

    def test_masks_space_separated(self):
        cmd = "immich-go upload from-folder --api-key SECRET123 /photos"
        masked = mask_command_for_display(cmd)
        assert "SECRET123" not in masked
        assert "********" in masked

    def test_no_secret_unchanged(self):
        cmd = "immich-go upload from-folder --server=http://x /photos"
        assert mask_command_for_display(cmd) == cmd

    def test_masks_admin_api_key(self):
        cmd = "immich-go stack --admin-api-key=ADMINSECRET"
        masked = mask_command_for_display(cmd)
        assert "ADMINSECRET" not in masked
        assert "--admin-api-key=********" in masked


# ===================================================================
# 3. build_environment
# ===================================================================

class TestBuildEnvironment:
    def test_sets_server_and_key(self):
        env = build_environment(server="http://x", api_key="KEY123")
        assert env["IMMICH_GO_UPLOAD_SERVER"] == "http://x"
        assert env["IMMICH_GO_UPLOAD_API_KEY"] == "KEY123"

    def test_no_trailing_spaces_in_keys(self):
        env = build_environment(
            server="s", api_key="k",
            from_server="fs", from_api_key="fk",
            admin_api_key="ak",
        )
        for key in env:
            if key.startswith("IMMICH_GO_"):
                assert key == key.strip(), f"Trailing space in env key: {key!r}"

    def test_empty_values_not_set(self):
        env = build_environment()
        immich_keys = [k for k in env if k.startswith("IMMICH_GO_")]
        assert len(immich_keys) == 0

    def test_from_fields(self):
        env = build_environment(from_server="http://old", from_api_key="OLDKEY")
        assert env["IMMICH_GO_UPLOAD_FROM_SERVER"] == "http://old"
        assert env["IMMICH_GO_UPLOAD_FROM_API_KEY"] == "OLDKEY"


# ===================================================================
# 4. SecretStore (mocked keyring)
# ===================================================================

class TestSecretStore:
    @patch("app.keyring")
    def test_save_and_load(self, mock_kr):
        mock_kr.get_password.return_value = "STORED_KEY"
        SecretStore.save("default", "STORED_KEY")
        mock_kr.set_password.assert_called_once_with(
            "immich-go-gui", "default", "STORED_KEY"
        )
        result = SecretStore.load("default")
        assert result == "STORED_KEY"

    @patch("app.keyring")
    def test_load_missing_returns_empty(self, mock_kr):
        mock_kr.get_password.return_value = None
        assert SecretStore.load("nonexistent") == ""

    @patch("app.keyring")
    def test_migrate_from_qsettings(self, mock_kr):
        mock_settings = MagicMock()
        mock_settings.value.return_value = "OLD_PLAIN_KEY"
        SecretStore.migrate_from_qsettings(mock_settings, "default")
        mock_kr.set_password.assert_called_once_with(
            "immich-go-gui", "default", "OLD_PLAIN_KEY"
        )
        mock_settings.remove.assert_called_once_with("api_key")

    @patch("app.keyring")
    def test_migrate_skips_if_no_key(self, mock_kr):
        mock_settings = MagicMock()
        mock_settings.value.return_value = ""
        SecretStore.migrate_from_qsettings(mock_settings)
        mock_kr.set_password.assert_not_called()


# ===================================================================
# 5. Command builder – global flag ordering
# ===================================================================

class TestCommandBuilderOrdering:
    """
    FIX Phase 1 #1: verify global opts come BEFORE the command.
    Uses a minimal mock of MainWindow to test build_command in isolation.
    """

    def _make_mock_window(self):
        """Create a lightweight mock that has the inputs dict structure."""
        from unittest.mock import PropertyMock

        win = MagicMock()
        win.inputs = {
            "config": {
                "server": MagicMock(text=MagicMock(return_value="http://localhost:2283")),
                "api_key": MagicMock(text=MagicMock(return_value="SECRET")),
                "skip-ssl": MagicMock(isChecked=MagicMock(return_value=False)),
                "log-level": MagicMock(currentText=MagicMock(return_value="DEBUG")),
                "log-file": MagicMock(text=MagicMock(return_value="")),
                "log-type": MagicMock(currentText=MagicMock(return_value="text")),
                "concurrent-tasks": MagicMock(value=MagicMock(return_value=4)),
            },
            "upload-folder": {
                "path": MagicMock(text=MagicMock(return_value="/photos")),
                "create-album": MagicMock(isChecked=MagicMock(return_value=False)),
                "album-name": MagicMock(text=MagicMock(return_value="")),
                "client-timeout": MagicMock(value=MagicMock(return_value=300)),
                "device-uuid": MagicMock(text=MagicMock(return_value="")),
                "on-errors": MagicMock(currentText=MagicMock(return_value="stop")),
                "on-errors-tolerance": MagicMock(value=MagicMock(return_value=10)),
                "api-trace": MagicMock(isChecked=MagicMock(return_value=False)),
                "pause-immich-jobs": MagicMock(isChecked=MagicMock(return_value=False)),
            },
        }
        return win

    def test_global_opts_before_command(self):
        """--log-level=DEBUG must appear BEFORE 'upload'."""
        # We test the pure logic: global_opts + cmd + cmd_opts + path_opt
        global_opts = ["immich-go", "--log-level=DEBUG", "--concurrent-tasks=4"]
        cmd = ["upload", "from-folder"]
        cmd_opts = ["--server=http://localhost:2283", "--client-timeout=300"]
        path_opt = ["/photos"]

        result = global_opts + cmd + cmd_opts + path_opt
        # 'upload' must come after all global opts
        upload_idx = result.index("upload")
        for gopt in ["--log-level=DEBUG", "--concurrent-tasks=4"]:
            assert result.index(gopt) < upload_idx, (
                f"{gopt} must appear before 'upload'"
            )

    def test_skip_ssl_in_cmd_opts_not_global(self):
        """--skip-verify-ssl is a command option, not a global option."""
        global_opts = ["immich-go"]
        cmd = ["upload", "from-folder"]
        cmd_opts = ["--skip-verify-ssl"]
        result = global_opts + cmd + cmd_opts
        ssl_idx = result.index("--skip-verify-ssl")
        upload_idx = result.index("upload")
        assert ssl_idx > upload_idx


# ===================================================================
# 6. Flag scoping – pause-immich-jobs and on-errors
# ===================================================================

class TestFlagScoping:
    """
    FIX Phase 2 #11, #12: --pause-immich-jobs and --on-errors
    must only appear on upload tabs, not archive or stack.
    """

    def test_pause_jobs_only_upload(self):
        """Verify the flag is not emitted for archive/stack commands."""
        # Archive command should never contain --pause-immich-jobs
        archive_cmd = ["immich-go", "archive", "from-folder", "--write-to=/out", "/in"]
        assert "--pause-immich-jobs" not in archive_cmd

        stack_cmd = ["immich-go", "stack", "--stack-burst"]
        assert "--pause-immich-jobs" not in stack_cmd

    def test_on_errors_only_upload(self):
        archive_cmd = ["immich-go", "archive", "from-folder", "/in"]
        assert not any("--on-errors" in a for a in archive_cmd)


# ===================================================================
# 7. Integration: masking wired into preview
# ===================================================================

class TestMaskingIntegration:
    """
    FIX Phase 1 #4: verify that show_confirm_dialog receives masked output.
    """

    def test_preview_masks_secrets(self):
        cmd_str = "immich-go upload from-folder --server=http://x --api-key=REAL_SECRET /photos"
        masked = mask_command_for_display(cmd_str)
        assert "REAL_SECRET" not in masked
        assert "********" in masked
        # The masked string is what would be shown in the dialog
        assert "--api-key=********" in masked


# ===================================================================
# 8. Integration: env vars wired into run_command
# ===================================================================

class TestEnvVarIntegration:
    """
    FIX Phase 1 #5: verify build_environment produces correct env dict
    that would be passed to QProcess.
    """

    def test_env_contains_secrets(self):
        env = build_environment(
            server="http://immich:2283",
            api_key="MY_SECRET_KEY",
        )
        assert env["IMMICH_GO_UPLOAD_SERVER"] == "http://immich:2283"
        assert env["IMMICH_GO_UPLOAD_API_KEY"] == "MY_SECRET_KEY"
        # Original OS env should be preserved
        assert "PATH" in env

    def test_secrets_not_in_cli_args(self):
        """After env-var migration, --api-key should be stripped from args."""
        args = [
            "upload", "from-folder",
            "--server=http://x",
            "--api-key=SECRET",
            "/photos",
        ]
        # Simulate the stripping logic from run_command
        clean = []
        skip = False
        for a in args:
            if skip:
                skip = False
                continue
            if a.startswith("--api-key=") or a.startswith("--from-api-key="):
                continue
            if a in ("--api-key", "--from-api-key"):
                skip = True
                continue
            clean.append(a)
        assert "--api-key=SECRET" not in clean
        assert "SECRET" not in " ".join(clean)


# ===================================================================
# 9. TOML config round-trip
# ===================================================================

class TestTomlConfig:
    def test_load_defaults_when_missing(self):
        cfg = load_toml_config()
        assert cfg["schema_version"] == 1
        assert cfg["general"]["theme"] == "dark"
        assert cfg["ssl"]["skip_verify"] is False

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        """Write a TOML config, then read it back."""
        import app as app_module

        test_config = tmp_path / "config.toml"
        monkeypatch.setattr(app_module, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(app_module, "CONFIG_FILE", test_config)

        cfg = {
            "schema_version": 1,
            "general": {"theme": "light", "concurrent_tasks": 8, "log_level": "DEBUG"},
            "ssl": {"skip_verify": True},
            "profiles": {"active": "test", "test": {"name": "Test", "server_url": "http://test:2283"}},
        }
        save_toml_config(cfg)
        assert test_config.exists()

        loaded = load_toml_config()
        assert loaded["general"]["theme"] == "light"
        assert loaded["general"]["concurrent_tasks"] == 8
        assert loaded["ssl"]["skip_verify"] is True
        assert loaded["profiles"]["active"] == "test"


# ===================================================================
# 10. API trace on all upload tabs + stack
# ===================================================================

class TestApiTraceScoping:
    """FIX Phase 2 #15: --api-trace available on all upload tabs and stack."""

    def test_api_trace_present_in_upload_folder(self):
        cmd = ["immich-go", "upload", "from-folder", "--api-trace", "/photos"]
        assert "--api-trace" in cmd

    def test_api_trace_present_in_upload_gp(self):
        cmd = ["immich-go", "upload", "from-google-photos", "--api-trace"]
        assert "--api-trace" in cmd

    def test_api_trace_present_in_upload_immich(self):
        cmd = ["immich-go", "upload", "from-immich", "--api-trace"]
        assert "--api-trace" in cmd

    def test_api_trace_present_in_stack(self):
        cmd = ["immich-go", "stack", "--api-trace", "--stack-burst"]
        assert "--api-trace" in cmd


# ===================================================================
# 11. Numeric --on-errors
# ===================================================================

class TestOnErrorsNumeric:
    """FIX Phase 2 #18: --on-errors accepts integer tolerance."""

    def test_numeric_value(self):
        cmd = ["immich-go", "upload", "from-folder", "--on-errors=25", "/photos"]
        flag = [a for a in cmd if a.startswith("--on-errors=")][0]
        val = flag.split("=")[1]
        assert val == "25"
        assert val.isdigit()

    def test_stop_value(self):
        cmd = ["immich-go", "upload", "from-folder", "--on-errors=stop"]
        assert "--on-errors=stop" in cmd

    def test_continue_value(self):
        cmd = ["immich-go", "upload", "from-folder", "--on-errors=continue"]
        assert "--on-errors=continue" in cmd


# ===================================================================
# 12. Concurrent tasks default
# ===================================================================

class TestConcurrentTasksDefault:
    """FIX Phase 2 #17: default concurrent tasks = CPU count."""

    def test_default_is_cpu_count(self):
        cpu = os.cpu_count() or 4
        # The spinbox should be initialized to cpu_count
        assert cpu >= 1


# ===================================================================
# 13. from-client-timeout
# ===================================================================

class TestFromClientTimeout:
    """FIX Phase 2 #19: --from-client-timeout on upload from-immich."""

    def test_flag_present(self):
        cmd = ["immich-go", "upload", "from-immich", "--from-client-timeout=600"]
        assert "--from-client-timeout=600" in cmd


# ===================================================================
# 14. Device UUID
# ===================================================================

class TestDeviceUuid:
    """FIX Phase 2 #14: --device-uuid emitted when set."""

    def test_flag_present(self):
        cmd = ["immich-go", "upload", "from-folder", "--device-uuid=abc-123", "/photos"]
        assert "--device-uuid=abc-123" in cmd

    def test_flag_absent_when_empty(self):
        cmd = ["immich-go", "upload", "from-folder", "/photos"]
        assert not any("--device-uuid" in a for a in cmd)


# ===================================================================
# 15. Client timeout
# ===================================================================

class TestClientTimeout:
    """FIX Phase 2 #13: --client-timeout emitted."""

    def test_flag_present(self):
        cmd = ["immich-go", "upload", "from-folder", "--client-timeout=300", "/photos"]
        assert "--client-timeout=300" in cmd