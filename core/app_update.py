"""GitHub release lookup for the Immich-Go GUI application itself."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import requests
from packaging.version import InvalidVersion, Version

from core.binary_manager import clean_version

_log = logging.getLogger(__name__)

_GUI_RELEASE_PREFIXES = ("immich-go-gui-v", "immich-go-gui-", "v")
_SEMVER_PATTERN = re.compile(r"(\d+\.\d+\.\d+(?:[-+][\w.]+)?)")


def clean_gui_release_version(tag: str) -> str:
    """Extract semver from Release Please tags like ``immich-go-gui-v1.2.0``."""
    tag = tag.strip()
    if not tag:
        return ""
    lowered = tag.lower()
    for prefix in _GUI_RELEASE_PREFIXES:
        if lowered.startswith(prefix):
            tag = tag[len(prefix) :]
            break
    match = _SEMVER_PATTERN.search(tag)
    if match:
        return match.group(1)
    return clean_version(tag)


def is_parseable_semver(version: str) -> bool:
    """Return True when *version* is a valid PEP 440 semver after GUI tag cleanup."""
    cleaned = clean_gui_release_version(version)
    if not cleaned:
        return False
    try:
        Version(cleaned)
    except InvalidVersion:
        return False
    return True

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
        version = clean_gui_release_version(tag)
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
    if not is_parseable_semver(installed_version):
        return False
    installed = clean_gui_release_version(installed_version)
    latest = clean_gui_release_version(latest_version)
    if not installed or not latest:
        return False
    try:
        return Version(latest) > Version(installed)
    except InvalidVersion:
        return False
