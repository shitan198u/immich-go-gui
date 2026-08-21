"""Application version definitions and environment detection."""

from __future__ import annotations

import os
import sys
from importlib.metadata import version as _pkg_version
from pathlib import Path

__version__ = "1.4.3"


def is_development_build() -> bool:
    """Return True if running directly from a source tree / git clone rather than a compiled binary.

    Compiled standalone releases (Nuitka, PyInstaller, etc.) set `sys.frozen` or
    `__compiled__` and do not include a `.git` working tree.
    """
    if os.environ.get("IMMICH_GO_GUI_DEV") == "1":
        return True
    if os.environ.get("IMMICH_GO_GUI_DEV") == "0":
        return False
    # If compiled with Nuitka or frozen binary, it is a release/standalone build
    if hasattr(sys, "__compiled__") or getattr(sys, "frozen", False):
        return False
    # If running from a directory with a .git repository, it is a developer git checkout
    try:
        repo_root = Path(__file__).resolve().parent.parent
        if (repo_root / ".git").exists():
            return True
    except Exception:
        pass
    return False


def get_app_version() -> str:
    """Return the application version string.

    In release / compiled standalone builds (e.g. .deb, .rpm, AppImage, DMG, EXE),
    returns the static version string (e.g. '1.4.2').
    In a git clone / developer source tree, appends the '-dev' suffix (e.g. '1.4.2-dev').
    """
    base_version = __version__
    if not base_version or base_version == "dev":
        try:
            base_version = _pkg_version("immich-go-gui")
        except Exception:
            return "dev"

    if is_development_build():
        return (
            f"{base_version}-dev" if not base_version.endswith("-dev") else base_version
        )
    return base_version
