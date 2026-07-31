"""Runtime CLI Compatibility Checker module for Immich-Go GUI.

Pure Python, Qt-free module.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .binary_manager import TESTED_IMMICH_GO_VERSION
from .cli_help import (
    help_name_for_tab,
    load_help_fixture,
    parse_help_bool_defaults,
    parse_help_flags,
)
from .cli_schema import COMPATIBILITY_MATRIX, TAB_ALLOWED_FLAGS

IGNORED_UPSTREAM_FLAGS = frozenset(
    {
        "api-key",
        "admin-api-key",
        "from-api-key",
        "from-admin-api-key",
        "config",
        "save-config",
        "log-file",
        "log-type",
        "help",
        "no-ui",
    }
)


@dataclass
class CompatibilityReport:
    version: str
    supported: bool = True
    missing_flags_by_tab: dict[str, set[str]] = field(default_factory=dict)
    unknown_flags_by_tab: dict[str, set[str]] = field(default_factory=dict)
    notes: str = ""

    def is_fully_compatible(self) -> bool:
        return self.supported and not any(self.missing_flags_by_tab.values())


def check_fixtures(version: str = TESTED_IMMICH_GO_VERSION) -> CompatibilityReport:
    """
    Evaluate GUI flag allowlists against captured CLI help fixtures for a version.
    
    Parameters:
        version (str): Immich-Go version whose help fixtures are checked.
    
    Returns:
        CompatibilityReport: Compatibility results, including missing and unknown flags and any fixture-related notes.
    """
    report = CompatibilityReport(version=version)
    matrix_entry = COMPATIBILITY_MATRIX.get(version, {})
    notes_val = matrix_entry.get("notes", "")
    report.notes = str(notes_val) if notes_val else ""

    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "cli_help" / version
    if not fixtures_dir.exists():
        report.supported = False
        report.notes += f"\n[Error] CLI help fixtures directory for version {version} does not exist."
        return report

    for tab_key, gui_allowed in TAB_ALLOWED_FLAGS.items():
        fixture_name = help_name_for_tab(tab_key)
        fixture_flags = load_help_fixture(version, fixture_name)

        if not fixture_flags:
            report.supported = False
            report.missing_flags_by_tab[tab_key] = {"[MISSING_HELP_FIXTURE]"}
            report.notes += f"\n[Warning] Missing or empty help fixture for tab '{tab_key}' ({fixture_name}.txt)"
            continue

        missing = set(gui_allowed) - fixture_flags
        unknown = fixture_flags - set(gui_allowed) - IGNORED_UPSTREAM_FLAGS

        if missing:
            report.missing_flags_by_tab[tab_key] = missing
            report.supported = False
        if unknown:
            report.unknown_flags_by_tab[tab_key] = unknown

    return report


_TAB_SUBCOMMANDS: dict[str, list[str]] = {
    "upload-folder": ["upload", "from-folder"],
    "upload-gp": ["upload", "from-google-photos"],
    "upload-icloud": ["upload", "from-icloud"],
    "upload-picasa": ["upload", "from-picasa"],
    "upload-immich": ["upload", "from-immich"],
    "archive-folder": ["archive", "from-folder"],
    "archive-gp": ["archive", "from-google-photos"],
    "archive-icloud": ["archive", "from-icloud"],
    "archive-picasa": ["archive", "from-picasa"],
    "archive-immich": ["archive", "from-immich"],
    "stack": ["stack"],
}


def collect_bool_defaults_from_binary(binary_path: Path) -> dict[str, dict[str, bool]]:
    """Run --help on each tab subcommand and parse bool flag defaults."""
    result: dict[str, dict[str, bool]] = {}
    for tab_key, args in _TAB_SUBCOMMANDS.items():
        cmd = [str(binary_path)] + args + ["--help"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            text = res.stdout if res.stdout else res.stderr
            result[tab_key] = parse_help_bool_defaults(text)
        except Exception:
            result[tab_key] = {}
    return result


def check_binary_help(
    binary_path: Path, version: str = TESTED_IMMICH_GO_VERSION
) -> CompatibilityReport:
    """
    Compare a live Immich-Go binary's subcommand help flags with the GUI allowlists.
    
    Parameters:
    	binary_path (Path): Path to the Immich-Go binary.
    	version (str): Version whose compatibility notes should be included in the report.
    
    Returns:
    	CompatibilityReport: Compatibility results, including missing and unknown flags by tab.
    """
    report = CompatibilityReport(version=version)
    matrix_entry = COMPATIBILITY_MATRIX.get(version, {})
    notes_val = matrix_entry.get("notes", "")
    report.notes = str(notes_val) if notes_val else ""

    for tab_key, args in _TAB_SUBCOMMANDS.items():
        gui_allowed = TAB_ALLOWED_FLAGS.get(tab_key, set())
        cmd = [str(binary_path)] + args + ["--help"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            text = res.stdout if res.stdout else res.stderr
            binary_flags = parse_help_flags(text)
        except Exception as e:
            report.notes += f"\nError checking {tab_key}: {e}"
            continue

        missing = set(gui_allowed) - binary_flags
        unknown = binary_flags - set(gui_allowed) - IGNORED_UPSTREAM_FLAGS

        if missing:
            report.missing_flags_by_tab[tab_key] = missing
            report.supported = False
        if unknown:
            report.unknown_flags_by_tab[tab_key] = unknown

    return report
