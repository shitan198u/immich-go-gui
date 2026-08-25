"""Packaging guardrails: enforce packaging configuration invariants to prevent
subpackage flattening, missing assets, and broken installer scripts.

These tests are intentionally Qt-free and pure-Python so they run fast in CI
and catch packaging regressions early.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGING_ROOT = REPO_ROOT / "packaging"
LINUX_PKG_ROOT = PACKAGING_ROOT / "linux"
WINDOWS_PKG_ROOT = PACKAGING_ROOT / "windows"


def test_nfpm_yaml_no_trailing_slash_on_directory_destinations():
    """nfpm 2.47.0+ flattens directory copies if dst ends with a trailing slash.

    This test enforces that directory mappings in packaging/linux/nfpm.yaml do
    not end with a trailing slash, preventing Qt and Shiboken shared object
    flattening.
    """
    nfpm_path = LINUX_PKG_ROOT / "nfpm.yaml"
    assert nfpm_path.is_file(), f"Missing {nfpm_path}"

    content = nfpm_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    in_contents = False
    current_entry = {}
    entries = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("contents:"):
            in_contents = True
            continue
        if in_contents:
            if stripped.startswith("- src:"):
                if current_entry:
                    entries.append(current_entry)
                current_entry = {"src": stripped.split(":", 1)[1].strip()}
            elif stripped.startswith("dst:") and current_entry:
                current_entry["dst"] = stripped.split(":", 1)[1].strip()
            elif (
                stripped and not stripped.startswith("#") and not line.startswith("  ")
            ):
                # End of contents block
                in_contents = False

    if current_entry:
        entries.append(current_entry)

    assert entries, "No entries parsed from nfpm.yaml contents block"

    for entry in entries:
        src = entry.get("src", "")
        dst = entry.get("dst", "")

        # Target destinations must not end with a trailing slash
        assert not dst.endswith("/"), (
            f"nfpm destination '{dst}' must not end with a trailing slash '/' "
            f"(causes silent directory flattening in nfpm for src '{src}')"
        )
        assert dst.startswith("/"), f"nfpm destination '{dst}' must be an absolute path"


def test_nfpm_referenced_static_files_exist():
    """Verify that static files referenced in nfpm.yaml actually exist in the repo."""
    nfpm_path = LINUX_PKG_ROOT / "nfpm.yaml"
    content = nfpm_path.read_text(encoding="utf-8")

    # Match static files (exclude app.dist which is generated at build time)
    for match in re.finditer(r"src:\s*(\S+)", content):
        src_path_str = match.group(1)
        if "app.dist" in src_path_str:
            continue
        # Resolve relative to packaging/linux/
        resolved = (LINUX_PKG_ROOT / src_path_str).resolve()
        assert resolved.exists(), (
            f"File referenced in nfpm.yaml does not exist: {src_path_str} -> {resolved}"
        )


def test_linux_desktop_file_validity():
    """Verify packaging/linux/immich-go-gui.desktop contains required Desktop Entry keys."""
    desktop_path = LINUX_PKG_ROOT / "immich-go-gui.desktop"
    assert desktop_path.is_file(), f"Missing {desktop_path}"

    content = desktop_path.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in content
    assert re.search(r"^Name\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^Exec\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^Icon\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^Type\s*=\s*Application$", content, re.MULTILINE)


def test_linux_appdata_xml_validity():
    """Verify packaging/linux/immich-go-gui.appdata.xml is well-formed XML with valid ID."""
    appdata_path = LINUX_PKG_ROOT / "immich-go-gui.appdata.xml"
    assert appdata_path.is_file(), f"Missing {appdata_path}"

    # Static repository-controlled AppStream metadata file
    tree = ET.parse(appdata_path)
    root = tree.getroot()
    assert root.tag == "component"
    id_elem = root.find("id")
    assert id_elem is not None and id_elem.text, "Missing or empty <id> in appdata.xml"


def test_nfpm_yaml_version_variable():
    """Verify nfpm.yaml uses ${VERSION} without bash parameter default syntax.

    Go os.ExpandEnv does not support ${VAR:-default} and will evaluate it to an
    empty string, causing packages to default to 0.0.0.
    """
    nfpm_path = LINUX_PKG_ROOT / "nfpm.yaml"
    content = nfpm_path.read_text(encoding="utf-8")
    match = re.search(r'^version:\s*"([^"]+)"', content, re.MULTILINE)
    assert match is not None, "Missing version in nfpm.yaml"
    ver_val = match.group(1)
    assert ver_val == "${VERSION}", (
        f"nfpm.yaml version must be strictly '${{VERSION}}', found '{ver_val}'"
    )
    assert ":-" not in ver_val, "nfpm.yaml version must not use ':-' default expansion"


def test_nfpm_yaml_metadata_complete():
    """Verify nfpm.yaml contains all required metadata fields for DEB and RPM."""
    nfpm_path = LINUX_PKG_ROOT / "nfpm.yaml"
    content = nfpm_path.read_text(encoding="utf-8")
    assert re.search(r'^maintainer:\s*"[^"]+"', content, re.MULTILINE)
    assert re.search(r'^vendor:\s*"[^"]+"', content, re.MULTILINE)
    assert re.search(r'^homepage:\s*"[^"]+"', content, re.MULTILINE)
    assert re.search(r'^license:\s*"[^"]+"', content, re.MULTILINE)
    assert re.search(r'^section:\s*"[^"]+"', content, re.MULTILINE)
    assert re.search(r'^priority:\s*"[^"]+"', content, re.MULTILINE)


def test_nfpm_yaml_contents_include_metainfo_and_licenses():
    """Verify nfpm.yaml includes AppStream metadata, desktop, icons, and licenses."""
    nfpm_path = LINUX_PKG_ROOT / "nfpm.yaml"
    content = nfpm_path.read_text(encoding="utf-8")

    expected_dsts = [
        "/opt/immich-go-gui",
        "/usr/share/pixmaps/immich-go-gui.png",
        "/usr/share/icons/hicolor/512x512/apps/immich-go-gui.png",
        "/usr/share/applications/immich-go-gui.desktop",
        "/usr/share/metainfo/immich-go-gui.metainfo.xml",
        "/usr/share/doc/immich-go-gui/copyright",
        "/usr/share/licenses/immich-go-gui/LICENSE",
    ]
    for dst in expected_dsts:
        assert f"dst: {dst}" in content, f"Missing destination in nfpm.yaml: {dst}"


def test_linux_metainfo_xml_validity_and_completeness():
    """Verify AppStream metainfo XML is well-formed and contains required metadata."""
    metainfo_path = LINUX_PKG_ROOT / "immich-go-gui.metainfo.xml"
    assert metainfo_path.is_file(), f"Missing {metainfo_path}"

    tree = ET.parse(metainfo_path)
    root = tree.getroot()
    assert root.tag == "component"

    id_elem = root.find("id")
    assert id_elem is not None and id_elem.text == "immich-go-gui"

    name_elem = root.find("name")
    assert name_elem is not None and name_elem.text == "Immich-Go GUI"

    summary_elem = root.find("summary")
    assert summary_elem is not None and summary_elem.text

    proj_license = root.find("project_license")
    assert proj_license is not None and proj_license.text == "MIT"

    meta_license = root.find("metadata_license")
    assert meta_license is not None and meta_license.text

    dev_elem = root.find("developer")
    assert dev_elem is not None, "Missing <developer> element in metainfo.xml"
    dev_name = dev_elem.find("name")
    assert dev_name is not None and dev_name.text, "Missing developer <name>"

    launchable = root.find("launchable")
    assert launchable is not None and launchable.text == "immich-go-gui.desktop"


def test_windows_installer_iss_preserves_subdirectories():
    """Verify Inno Setup script includes flags to recurse subdirectories."""
    iss_path = WINDOWS_PKG_ROOT / "installer.iss"
    assert iss_path.is_file(), f"Missing {iss_path}"

    content = iss_path.read_text(encoding="utf-8")
    match = re.search(
        r'Source:\s*"app\.dist\\?\*".*Flags:\s*(.*)', content, re.IGNORECASE
    )
    assert match, "Source directive for app.dist not found in installer.iss"
    flags = match.group(1).lower()
    assert "recursesubdirs" in flags, "Inno Setup must include 'recursesubdirs' flag"
    assert "createallsubdirs" in flags, (
        "Inno Setup must include 'createallsubdirs' flag"
    )


def test_windows_installer_iss_metadata():
    """Verify Inno Setup script contains publisher, URLs, icon, and version metadata."""
    iss_path = WINDOWS_PKG_ROOT / "installer.iss"
    content = iss_path.read_text(encoding="utf-8")

    assert re.search(r"^AppPublisher\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^AppPublisherURL\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^AppSupportURL\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^AppUpdatesURL\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^LicenseFile\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^SetupIconFile\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^VersionInfoVersion\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^VersionInfoProductName\s*=\s*.+$", content, re.MULTILINE)
    assert re.search(r"^VersionInfoCompany\s*=\s*.+$", content, re.MULTILINE)
