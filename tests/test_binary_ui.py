import os
from unittest.mock import MagicMock, patch

from core.binary_manager import BinaryManager, get_version_support
from core.cli_contract import check_binary_help
from core.models import VersionSupport


class TestBinaryManagerWindowsPathResolution:
    """Group B (extended): binary_manager.py Path.resolve() fix — issue #66."""

    def test_check_binary_uses_resolved_path(self, tmp_path):
        """Fix #66: check_binary resolves the binary path before subprocess.run."""
        bm = BinaryManager(base_dir=str(tmp_path), os_name="win32")

        fake_bin = tmp_path / "0.32.0" / "immich-go.exe"
        fake_bin.parent.mkdir(parents=True)
        fake_bin.write_bytes(b"fake")

        meta = {
            "schema_version": 2,
            "selected_version": "0.32.0",
            "manual_path": "",
            "versions": {
                "0.32.0": {
                    "path": str(fake_bin),
                    "gui_tested": True,
                    "support_status": "tested",
                    "sha256": "",
                    "release_url": "",
                }
            },
        }

        with (
            patch("core.binary_manager.subprocess.run") as mock_run,
            patch("core.binary_manager.load_binary_metadata", return_value=meta),
        ):
            mock_result = MagicMock()
            mock_result.stdout = "v0.32.0"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            _status = bm.check_binary()

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert os.path.isabs(call_args[0]), (
            f"Expected absolute resolved path in subprocess call, got: {call_args[0]!r}"
        )

    def test_verify_extracted_binary_uses_resolved_path(self, tmp_path):
        """Fix #66: verify_extracted_binary resolves path before subprocess.run."""
        bm = BinaryManager(os_name="win32")
        fake_bin = tmp_path / "immich-go.exe"
        fake_bin.write_bytes(b"fake")

        with patch("core.binary_manager.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "v0.32.0"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = bm.verify_extracted_binary(str(fake_bin))

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert os.path.isabs(call_args[0]), (
            f"Expected absolute resolved path, got: {call_args[0]!r}"
        )


def test_version_support_tested():
    assert get_version_support("0.32.0") == VersionSupport.TESTED
    assert get_version_support("v0.32.0") == VersionSupport.TESTED


def test_version_support_unsupported_old():
    assert get_version_support("0.31.0") == VersionSupport.UNSUPPORTED_OLD


def test_version_support_untested_new():
    assert get_version_support("0.33.0") == VersionSupport.UNTESTED_NEW


def test_update_decision_allows_tested_version():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.31.0",
        latest_version="0.32.0",
        allow_untested=False,
        release_notes="",
    )

    assert decision.allowed is True
    assert decision.requires_confirmation is True


def test_update_decision_blocks_untested_by_default():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.32.0",
        latest_version="0.33.0",
        allow_untested=False,
        release_notes="",
    )

    assert decision.allowed is False


def test_update_decision_allows_untested_when_enabled():
    manager = BinaryManager()

    decision = manager.evaluate_update(
        current_version="0.32.0",
        latest_version="0.33.0",
        allow_untested=True,
        release_notes="",
    )

    assert decision.allowed is True
    assert decision.requires_confirmation is True


def test_binary_manager_downgrade_prevention():
    from core.binary_manager import BinaryManager

    bm = BinaryManager()
    decision = bm.evaluate_update(current_version="0.33.0", latest_version="0.32.0")
    assert decision.allowed is False
    assert "newer version" in decision.message


def test_binary_manager_get_release_asset_url(monkeypatch):
    from core.binary_manager import BinaryManager

    bm = BinaryManager(os_name="linux", arch="x86_64")

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "assets": [
                    {
                        "name": "immich-go_0.32.0_linux_x86_64.tar.gz",
                        "browser_download_url": "https://github.com/simulot/immich-go/releases/download/v0.32.0/immich-go_0.32.0_linux_x86_64.tar.gz",
                    }
                ]
            }

    monkeypatch.setattr("requests.get", lambda url, timeout=10: MockResponse())
    url = bm.get_release_asset_url("0.32.0")
    assert "immich-go_0.32.0_linux_x86_64.tar.gz" in url


def test_binary_manager_verify_extracted_binary(tmp_path):
    from core.binary_manager import BinaryManager

    bm = BinaryManager()
    # Nonexistent file
    assert bm.verify_extracted_binary(str(tmp_path / "nonexistent")) is False


def test_binary_manager_download_and_install_cancellation(tmp_path):
    """Fix 1.3: download_and_install respects cancellation and cleans up temp files."""
    from core.binary_manager import BinaryManager

    bm = BinaryManager(base_dir=str(tmp_path))

    # Mock get_release_asset_url to return a dummy URL
    with patch.object(
        bm, "get_release_asset_url", return_value="https://example.com/immich-go.tar.gz"
    ):
        # Mock requests.get to return a streaming dummy response
        mock_res = MagicMock()
        mock_res.headers = {"content-length": "100"}
        mock_res.iter_content.return_value = [b"dummy data chunk"]
        mock_res.__enter__.return_value = mock_res

        with patch("requests.get", return_value=mock_res):
            success, msg = bm.download_and_install(
                version="0.32.0",
                cancel_check=lambda: True,  # cancel immediately
            )
            assert success is False
            assert "cancelled" in msg.lower()

    # Ensure no leftover temp archive or binary exists
    v_dir = tmp_path / "0.32.0"
    assert not (v_dir / "download.tmp").exists()
    assert not (v_dir / "immich-go.tmp").exists()


def _make_tar_gz_archive(content: bytes = b"#!/bin/sh\necho 0.32.0\n") -> bytes:
    import io
    import tarfile

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = content
        info = tarfile.TarInfo(name="immich-go")
        info.size = len(data)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_binary_manager_checksum_verification_pass(tmp_path):
    from core.binary_manager import BinaryManager, calculate_sha256

    archive_bytes = _make_tar_gz_archive()
    archive_name = "immich-go_0.32.0_linux_x86_64.tar.gz"
    url = f"https://example.com/{archive_name}"
    checksums = {archive_name: calculate_sha256(archive_bytes)}

    bm = BinaryManager(base_dir=str(tmp_path), os_name="linux", arch="x86_64")

    mock_res = MagicMock()
    mock_res.headers = {"content-length": str(len(archive_bytes))}
    mock_res.iter_content.return_value = [archive_bytes]
    mock_res.__enter__.return_value = mock_res

    with (
        patch.object(bm, "get_release_asset_url", return_value=url),
        patch.object(bm, "fetch_checksums", return_value=checksums),
        patch("requests.get", return_value=mock_res),
        patch.object(bm, "verify_extracted_binary", return_value=True),
    ):
        success, msg = bm.download_and_install(version="0.32.0")
        assert success is True
        assert "Successfully installed" in msg


def test_binary_manager_checksum_verification_fail(tmp_path):
    from core.binary_manager import BinaryManager

    archive_bytes = _make_tar_gz_archive()
    archive_name = "immich-go_0.32.0_linux_x86_64.tar.gz"
    url = f"https://example.com/{archive_name}"
    checksums = {
        archive_name: "0000000000000000000000000000000000000000000000000000000000000000"
    }

    bm = BinaryManager(base_dir=str(tmp_path), os_name="linux", arch="x86_64")

    mock_res = MagicMock()
    mock_res.headers = {"content-length": str(len(archive_bytes))}
    mock_res.iter_content.return_value = [archive_bytes]
    mock_res.__enter__.return_value = mock_res

    with (
        patch.object(bm, "get_release_asset_url", return_value=url),
        patch.object(bm, "fetch_checksums", return_value=checksums),
        patch("requests.get", return_value=mock_res),
    ):
        success, msg = bm.download_and_install(version="0.32.0")
        assert success is False
        assert "checksum verification failed" in msg.lower()


def test_binary_manager_checksum_missing_checksums_txt(tmp_path):
    from core.binary_manager import BinaryManager

    archive_bytes = _make_tar_gz_archive()
    archive_name = "immich-go_0.32.0_linux_x86_64.tar.gz"
    url = f"https://example.com/{archive_name}"

    bm = BinaryManager(base_dir=str(tmp_path), os_name="linux", arch="x86_64")

    mock_res = MagicMock()
    mock_res.headers = {"content-length": str(len(archive_bytes))}
    mock_res.iter_content.return_value = [archive_bytes]
    mock_res.__enter__.return_value = mock_res

    with (
        patch.object(bm, "get_release_asset_url", return_value=url),
        patch.object(bm, "fetch_checksums", return_value={}),
        patch("requests.get", return_value=mock_res),
    ):
        success, msg = bm.download_and_install(version="0.32.0")
        assert success is False
        assert "checksums.txt" in msg.lower()


def test_binary_manager_checksum_tampered_archive(tmp_path):
    from core.binary_manager import BinaryManager, calculate_sha256

    good_bytes = _make_tar_gz_archive(b"good binary")
    tampered_bytes = _make_tar_gz_archive(b"tampered binary")
    archive_name = "immich-go_0.32.0_linux_x86_64.tar.gz"
    url = f"https://example.com/{archive_name}"
    checksums = {archive_name: calculate_sha256(good_bytes)}

    bm = BinaryManager(base_dir=str(tmp_path), os_name="linux", arch="x86_64")

    mock_res = MagicMock()
    mock_res.headers = {"content-length": str(len(tampered_bytes))}
    mock_res.iter_content.return_value = [tampered_bytes]
    mock_res.__enter__.return_value = mock_res

    with (
        patch.object(bm, "get_release_asset_url", return_value=url),
        patch.object(bm, "fetch_checksums", return_value=checksums),
        patch("requests.get", return_value=mock_res),
    ):
        success, msg = bm.download_and_install(version="0.32.0")
        assert success is False
        assert "checksum verification failed" in msg.lower()


def test_check_binary_help_all_11_tabs(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stdout = "Flags:\n      --dry-run\n      --server string\n"
        result.stderr = ""
        return result

    monkeypatch.setattr("core.cli_contract.subprocess.run", fake_run)
    check_binary_help(tmp_path / "immich-go")
    assert len(calls) == 11


def test_load_binary_metadata_migration_non_dict_record(tmp_path):
    """Regression test: load_binary_metadata handles non-dict version entries during migration."""
    import json

    from core.binary_manager import load_binary_metadata

    metadata_path = tmp_path / "metadata.json"

    # Create a metadata file with schema_version 1 (or missing)
    # where 'versions' contains both a dict record and a non-dict (string) record
    corrupt_meta = {
        "schema_version": 1,
        "selected_version": "0.32.0",
        "manual_path": "",
        "versions": {
            "0.32.0": {
                "path": "/some/path/immich-go",
                "downloaded_at": "2024-01-01T00:00:00Z",
            },
            "0.31.0": "some-string-value",  # Non-dict entry
        },
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(corrupt_meta, f)

    # This should not raise AttributeError
    result = load_binary_metadata(str(metadata_path))

    # Verify migration completed
    assert result["schema_version"] == 2

    # Verify dict record got defaults applied
    assert "gui_tested" in result["versions"]["0.32.0"]
    assert "support_status" in result["versions"]["0.32.0"]
    assert "sha256" in result["versions"]["0.32.0"]
    assert "release_url" in result["versions"]["0.32.0"]

    # Verify non-dict entry was left as-is (not modified, no crash)
    assert result["versions"]["0.31.0"] == "some-string-value"
