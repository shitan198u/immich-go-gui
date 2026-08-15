"""Application version definitions."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version

__version__ = "1.4.2"


def get_app_version() -> str:
    """Return the application version string.

    Prefers the static code-level `__version__` baked into the distribution,
    falling back to package metadata and finally 'dev'.
    """
    if __version__ and __version__ != "dev":
        return __version__
    try:
        return _pkg_version("immich-go-gui")
    except Exception:
        return "dev"
