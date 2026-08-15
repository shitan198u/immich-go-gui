"""Unit tests for core.version resolution and environment detection."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

from core.app_update import is_parseable_semver
from core.version import __version__, get_app_version, is_development_build

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_version_matches_pyproject():
    pyproject_text = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.MULTILINE)
    assert match is not None
    assert __version__ == match.group(1)


def test_is_development_build_env_override(monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_DEV", "1")
    assert is_development_build() is True

    monkeypatch.setenv("IMMICH_GO_GUI_DEV", "0")
    assert is_development_build() is False


def test_is_development_build_compiled_flag(monkeypatch):
    monkeypatch.delenv("IMMICH_GO_GUI_DEV", raising=False)
    monkeypatch.setattr("sys.__compiled__", True, raising=False)
    assert is_development_build() is False


def test_get_app_version_dev_mode(monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_DEV", "1")
    ver = get_app_version()
    assert ver == f"{__version__}-dev"
    assert is_parseable_semver(ver) is True


def test_get_app_version_release_mode(monkeypatch):
    monkeypatch.setenv("IMMICH_GO_GUI_DEV", "0")
    ver = get_app_version()
    assert ver == __version__
    assert not ver.endswith("-dev")
    assert is_parseable_semver(ver) is True


def test_get_app_version_fallback():
    with (
        patch("core.version.__version__", "dev"),
        patch("core.version.is_development_build", return_value=False),
    ):
        with patch("core.version._pkg_version", return_value="2.0.0"):
            assert get_app_version() == "2.0.0"

    with (
        patch("core.version.__version__", ""),
        patch("core.version.is_development_build", return_value=False),
    ):
        with patch("core.version._pkg_version", side_effect=Exception("not found")):
            assert get_app_version() == "dev"
