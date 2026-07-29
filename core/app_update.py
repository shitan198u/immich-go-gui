"""GitHub release lookup for the Immich-Go GUI application itself."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from packaging.version import InvalidVersion, Version

from core.binary_manager import clean_version

_log = logging.getLogger(__name__)

GITHUB_REPO = "shitan198u/immich-go-gui"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class GuiReleaseInfo:
    tag: str
    version: str
    html_url: str


def get_latest_gui_release() -> GuiReleaseInfo | None:
    """Fetch the latest GUI release from GitHub."""
    try:
        res = requests.get(LATEST_RELEASE_URL, timeout=15)
        res.raise_for_status()
        data = res.json()
        tag = str(data.get("tag_name", "")).strip()
        html_url = str(data.get("html_url", "")).strip()
        if not tag:
            return None
        version = clean_version(tag)
        if not version:
            return None
        if not html_url:
            html_url = f"https://github.com/{GITHUB_REPO}/releases/latest"
        return GuiReleaseInfo(tag=tag, version=version, html_url=html_url)
    except Exception as exc:
        _log.warning("Failed to fetch latest GUI release: %s", exc)
        return None


def is_update_available(installed_version: str, latest_version: str) -> bool:
    """Return True when latest_version is newer than installed_version."""
    installed = clean_version(installed_version)
    latest = clean_version(latest_version)
    if not installed or not latest:
        return False
    try:
        return Version(latest) > Version(installed)
    except InvalidVersion:
        return latest != installed
