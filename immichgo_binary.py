"""Binary management, version detection, tested version policies, and extraction logic.

This module manages immich-go CLI binaries, version compatibility checks, GitHub update
evaluations, and archive extractions without any PySide6 or Qt dependencies.
"""

import hashlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests
from packaging.version import InvalidVersion, Version

from immichgo_models import (
    BinaryStatus,
    UpdateDecision,
    UpdateSeverity,
    VersionSupport,
)


BINARY_BASE_DIR = os.path.join(os.path.expanduser("~"), ".immich-go-gui", "bin")
METADATA_PATH = os.path.join(BINARY_BASE_DIR, "metadata.json")

# The GUI is built and tested against immich-go v0.32.0.
RECOMMENDED_IMMICH_GO_VERSION = "0.32.0"
TESTED_IMMICH_GO_VERSION = RECOMMENDED_IMMICH_GO_VERSION

TESTED_IMMICH_GO_VERSIONS = frozenset({
    "0.32.0",
})

MIN_SUPPORTED_IMMICH_GO_VERSION = "0.32.0"
MAX_KNOWN_COMPATIBLE_IMMICH_GO_VERSION = "0.32.0"

VERSION_NOTES = {
    "0.32.0": (
        "GUI-tested version. Upstream removed the ReplaceAsset API. "
        "The asset.replace API-key permission is no longer required. "
        "No known immich-go CLI flag breakage for this GUI."
    ),
}

BREAKING_INDICATORS = [
    r"\bbreaking\s+change",
    r"\bbreaking\b",
    r"\bBREAKING\b",
    r"\bremoved\b.*\bflag\b",
    r"\brenamed\b.*\bflag\b",
    r"\bincompatible\b",
    r"\bdeprecat(ed|ion)\b",
]

_BREAKING_RE = re.compile(
    "|".join(BREAKING_INDICATORS),
    re.IGNORECASE,
)


def clean_version(version: str) -> str:
    """Normalize version string by removing leading 'v', build info, and whitespace."""
    version = version.strip()
    if not version:
        return ""
    if version.startswith("v") or version.startswith("V"):
        version = version[1:]
    # Handle version string like "0.32.0, built with..."
    version = version.split(",")[0].strip().split()[0].strip()
    return version


def parse_version_output(text: str) -> str:
    """Parses output from `immich-go version`."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    for line in lines:
        match = re.search(r"v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?)\b", line)
        if match:
            return clean_version(match.group(1))
    return clean_version(lines[0])


def get_version_support(version: str) -> VersionSupport:
    """Return support classification for a given version string."""
    cleaned = clean_version(version)
    if not cleaned:
        return VersionSupport.UNKNOWN

    try:
        v = Version(cleaned)
    except InvalidVersion:
        return VersionSupport.UNKNOWN

    try:
        min_v = Version(MIN_SUPPORTED_IMMICH_GO_VERSION)
        max_v = Version(MAX_KNOWN_COMPATIBLE_IMMICH_GO_VERSION)
    except InvalidVersion:
        return VersionSupport.UNKNOWN

    if v < min_v:
        return VersionSupport.UNSUPPORTED_OLD

    if cleaned in TESTED_IMMICH_GO_VERSIONS:
        return VersionSupport.TESTED

    if v > max_v:
        return VersionSupport.UNTESTED_NEW

    return VersionSupport.UNTESTED_BUT_MAY_WORK


def calculate_sha256(data: bytes) -> str:
    """Calculate hex digest SHA256 of byte array."""
    return hashlib.sha256(data).hexdigest()


def load_binary_metadata(metadata_path: str = METADATA_PATH) -> dict:
    """Loads binary metadata JSON from disk, migrating schema if needed."""
    meta = {
        "schema_version": 2,
        "selected_version": "",
        "manual_path": "",
        "versions": {},
    }

    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    meta.update(loaded)
        except (json.JSONDecodeError, OSError):
            pass

    # Schema version migration
    if meta.get("schema_version", 1) < 2:
        for version, record in meta.get("versions", {}).items():
            if isinstance(record, dict):
                record.setdefault("gui_tested", version in TESTED_IMMICH_GO_VERSIONS)
                record.setdefault(
                    "support_status",
                    get_version_support(version).value,
                )
                record.setdefault("sha256", "")
                record.setdefault("release_url", "")
        meta["schema_version"] = 2

    return meta


def save_binary_metadata(meta: dict, metadata_path: str = METADATA_PATH) -> None:
    """Saves binary metadata JSON to disk atomically."""
    base_dir = os.path.dirname(metadata_path)
    os.makedirs(base_dir, exist_ok=True)

    tmp_path = metadata_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    os.replace(tmp_path, metadata_path)


def get_binary_path(meta: dict | None = None, base_dir: str = BINARY_BASE_DIR) -> str:
    """Resolve effective executable binary path from metadata or standard directory."""
    if meta is None:
        meta = load_binary_metadata()

    manual = meta.get("manual_path", "").strip()
    if manual and os.path.exists(manual):
        return manual

    selected = meta.get("selected_version", "")
    if selected and selected in meta.get("versions", {}):
        v_record = meta["versions"][selected]
        if isinstance(v_record, dict) and "path" in v_record:
            path = v_record["path"]
            if os.path.exists(path):
                return path

    binary_filename = "immich-go.exe" if sys.platform.startswith("win") else "immich-go"

    # Check selected version directory fallback
    if selected:
        version_path = os.path.join(base_dir, selected, binary_filename)
        if os.path.exists(version_path):
            return version_path

    # Check legacy base directory
    legacy = os.path.join(base_dir, binary_filename)
    if os.path.exists(legacy):
        return legacy

    return ""


class BinaryManager:
    """Encapsulates binary inspection, GitHub release checking, and extraction."""

    def __init__(
        self,
        base_dir: str | None = None,
        metadata_path: str | None = None,
        os_name: str | None = None,
        arch: str | None = None,
    ):
        self.base_dir = base_dir or BINARY_BASE_DIR
        self.metadata_path = metadata_path or os.path.join(self.base_dir, "metadata.json")
        self.os_name = os_name or sys.platform
        self.arch = arch or platform.machine().lower()

    def load_metadata(self) -> dict:
        return load_binary_metadata(self.metadata_path)

    def save_metadata(self, meta: dict) -> None:
        save_binary_metadata(meta, self.metadata_path)

    def resolve_binary_path(self, meta: dict | None = None) -> str:
        return get_binary_path(meta, self.base_dir)

    def check_binary(self) -> BinaryStatus:
        """Inspects the local binary and returns a BinaryStatus."""
        binary_path = self.resolve_binary_path()
        if not binary_path or not os.path.exists(binary_path):
            return BinaryStatus(
                state="err",
                card_text="Binary: Missing",
                version_text="Not found",
                support=VersionSupport.UNKNOWN,
                message="Immich-Go binary not found.",
            )

        if not self.os_name.startswith("win") and not os.access(binary_path, os.X_OK):
            try:
                os.chmod(binary_path, 0o755)
            except OSError:
                return BinaryStatus(
                    state="err",
                    card_text="Binary: Permission Denied",
                    version_text="Not executable",
                    support=VersionSupport.UNKNOWN,
                    message="Binary exists but is not executable.",
                )

        try:
            res = subprocess.run(
                [binary_path, "version"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            version_text = parse_version_output(res.stdout or res.stderr)
            if not version_text:
                version_text = "Unknown"
        except Exception as e:
            return BinaryStatus(
                state="warn",
                card_text="Binary: Error",
                version_text="Error running binary",
                support=VersionSupport.UNKNOWN,
                message=f"Failed to execute binary version command: {e}",
            )

        support = get_version_support(version_text)

        if support == VersionSupport.TESTED:
            return BinaryStatus(
                state="ok",
                card_text=f"Binary: {version_text} (tested)",
                version_text=version_text,
                support=support,
                message=VERSION_NOTES.get(version_text, "Tested and supported version."),
            )
        elif support == VersionSupport.UNTESTED_BUT_MAY_WORK:
            return BinaryStatus(
                state="warn",
                card_text=f"Binary: {version_text} (untested)",
                version_text=version_text,
                support=support,
                message=f"Version {version_text} is untested but within expected range.",
            )
        elif support == VersionSupport.UNTESTED_NEW:
            return BinaryStatus(
                state="warn",
                card_text=f"Binary: {version_text} (newer than tested)",
                version_text=version_text,
                support=support,
                message=f"Version {version_text} is newer than tested version ({RECOMMENDED_IMMICH_GO_VERSION}).",
            )
        elif support == VersionSupport.UNSUPPORTED_OLD:
            return BinaryStatus(
                state="warn",
                card_text=f"Binary: {version_text} (older than supported)",
                version_text=version_text,
                support=support,
                message=f"Version {version_text} is older than minimum supported version ({MIN_SUPPORTED_IMMICH_GO_VERSION}).",
            )

        return BinaryStatus(
            state="warn",
            card_text=f"Binary: {version_text}",
            version_text=version_text,
            support=support,
            message=f"Unknown support status for version {version_text}.",
        )

    def get_latest_version(self) -> str | None:
        """Fetch latest release tag from GitHub."""
        try:
            url = "https://api.github.com/repos/simulot/immich-go/releases/latest"
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            data = res.json()
            tag = data.get("tag_name", "")
            return clean_version(tag) if tag else None
        except Exception:
            return None

    def get_release_notes(self, version: str) -> str:
        """Fetch release notes for a given version tag."""
        try:
            url = f"https://api.github.com/repos/simulot/immich-go/releases/tags/v{clean_version(version)}"
            res = requests.get(url, timeout=15)
            if res.status_code == 404:
                url = f"https://api.github.com/repos/simulot/immich-go/releases/tags/{clean_version(version)}"
                res = requests.get(url, timeout=15)
            res.raise_for_status()
            data = res.json()
            return data.get("body", "") or ""
        except Exception:
            return ""

    def get_download_url(self, version: str | None = None) -> str | None:
        """Determine download URL for current OS/arch and target version."""
        if not version:
            version = self.get_latest_version()
        if not version:
            return None

        clean_v = clean_version(version)

        # OS detection
        if self.os_name.startswith("win"):
            target_os = "Windows"
            ext = ".zip"
        elif self.os_name.startswith("darwin"):
            target_os = "Darwin"
            ext = ".tar.gz"
        else:
            target_os = "Linux"
            ext = ".tar.gz"

        # Arch detection
        arch_map = {
            "x86_64": "x86_64",
            "amd64": "x86_64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "i386": "i386",
            "i686": "i386",
        }
        target_arch = arch_map.get(self.arch, "x86_64")

        filename = f"immich-go_{clean_v}_{target_os}_{target_arch}{ext}"
        return f"https://github.com/simulot/immich-go/releases/download/v{clean_v}/{filename}"

    def evaluate_update(
        self,
        current_version: str,
        latest_version: str,
        allow_untested: bool = False,
        release_notes: str = "",
    ) -> UpdateDecision:
        """Evaluates whether an update to latest_version should be allowed."""
        latest_clean = clean_version(latest_version)
        current_clean = clean_version(current_version)

        # 1. If latest_version is explicitly tested
        if latest_clean in TESTED_IMMICH_GO_VERSIONS:
            return UpdateDecision(
                allowed=True,
                requires_confirmation=True,
                severity=UpdateSeverity.INFO,
                message="This version has been tested with this GUI.",
                latest_version=latest_clean,
                current_version=current_clean,
            )

        has_breaking = bool(_BREAKING_RE.search(release_notes)) if release_notes else False

        # 2. If latest_version is newer than tested
        if not allow_untested:
            msg = (
                f"immich-go {latest_clean} is newer than the tested version ({RECOMMENDED_IMMICH_GO_VERSION}). "
                "Automatic update is disabled for untested versions. "
                "Review release notes or enable untested updates in settings."
            )
            if has_breaking:
                msg += " (Release notes indicate possible breaking CLI changes)."

            return UpdateDecision(
                allowed=False,
                requires_confirmation=False,
                severity=UpdateSeverity.WARNING,
                message=msg,
                latest_version=latest_clean,
                current_version=current_clean,
            )

        msg = (
            f"immich-go {latest_clean} has not been tested with this GUI. "
            "Review release notes before continuing."
        )
        if has_breaking:
            msg += "\n\nWarning: Release notes contain breaking change indicators."

        return UpdateDecision(
            allowed=True,
            requires_confirmation=True,
            severity=UpdateSeverity.WARNING,
            message=msg,
            latest_version=latest_clean,
            current_version=current_clean,
        )

    def download_archive(
        self,
        url: str,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> bytes:
        """Downloads the binary archive and returns raw bytes."""
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024
        downloaded_size = 0
        content = io.BytesIO()

        for data in response.iter_content(block_size):
            downloaded_size += len(data)
            content.write(data)
            if total_size > 0 and progress_cb:
                progress = int((downloaded_size / total_size) * 100)
                progress_cb(progress)

        return content.getvalue()

    def extract_binary(
        self,
        archive_bytes: bytes,
        download_url: str,
        version: str,
    ) -> str:
        """Extracts immich-go binary from archive bytes into version directory."""
        v_clean = clean_version(version)
        target_dir = os.path.join(self.base_dir, v_clean)
        os.makedirs(target_dir, exist_ok=True)

        binary_filename = "immich-go.exe" if self.os_name.startswith("win") else "immich-go"
        binary_path = os.path.join(target_dir, binary_filename)

        if download_url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
                for filename in z.namelist():
                    base = os.path.basename(filename)
                    if base in ("immich-go", "immich-go.exe"):
                        with z.open(filename) as source, open(binary_path, "wb") as target:
                            target.write(source.read())
                        break
        elif download_url.endswith(".tar.gz") or download_url.endswith(".tgz"):
            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
                for member in tar.getmembers():
                    base = os.path.basename(member.name)
                    if base in ("immich-go", "immich-go.exe"):
                        source = tar.extractfile(member)
                        if source:
                            with open(binary_path, "wb") as target:
                                target.write(source.read())
                        break
        else:
            raise ValueError(f"Unsupported archive extension in URL: {download_url}")

        if not self.os_name.startswith("win") and os.path.exists(binary_path):
            os.chmod(binary_path, 0o755)

        return binary_path

    def select_version(
        self,
        version: str,
        binary_path: str,
        sha256: str = "",
        release_url: str = "",
    ) -> None:
        """Updates selected version record in metadata and saves to disk."""
        v_clean = clean_version(version)
        meta = self.load_metadata()

        meta["selected_version"] = v_clean
        if "versions" not in meta or not isinstance(meta["versions"], dict):
            meta["versions"] = {}

        if not sha256 and os.path.exists(binary_path):
            try:
                with open(binary_path, "rb") as f:
                    sha256 = calculate_sha256(f.read())
            except OSError:
                pass

        meta["versions"][v_clean] = {
            "path": binary_path,
            "downloaded_at": meta["versions"].get(v_clean, {}).get("downloaded_at", ""),
            "gui_tested": v_clean in TESTED_IMMICH_GO_VERSIONS,
            "support_status": get_version_support(v_clean).value,
            "sha256": sha256,
            "release_url": release_url or f"https://github.com/simulot/immich-go/releases/tag/v{v_clean}",
        }

        self.save_metadata(meta)
