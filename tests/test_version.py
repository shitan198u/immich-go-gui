"""Unit tests for core.version resolution and synchronization."""

import re
from pathlib import Path
from unittest.mock import patch

from core.app_update import is_parseable_semver
from core.version import __version__, get_app_version

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_version_matches_pyproject():
    pyproject_text = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.MULTILINE)
    assert match is not None
    assert __version__ == match.group(1)


def test_get_app_version_returns_valid_semver():
    ver = get_app_version()
    assert ver == __version__
    assert is_parseable_semver(ver) is True


def test_get_app_version_fallback():
    with patch("core.version.__version__", "dev"):
        with patch("core.version._pkg_version", return_value="2.0.0"):
            assert get_app_version() == "2.0.0"

    with patch("core.version.__version__", ""):
        with patch("core.version._pkg_version", side_effect=Exception("not found")):
            assert get_app_version() == "dev"
