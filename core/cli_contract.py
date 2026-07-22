"""Runtime CLI Compatibility Checker module for Immich-Go GUI.

Pure Python, Qt-free module.
"""

from dataclasses import dataclass, field
from pathlib import Path
import subprocess

from .binary_manager import TESTED_IMMICH_GO_VERSION
from .cli_help import load_help_fixture, parse_help_flags, help_name_for_tab
from .cli_schema import TAB_ALLOWED_FLAGS, TAB_KEYS, COMPATIBILITY_MATRIX


@dataclass
class CompatibilityReport:
    version: str
    supported: bool = True
    missing_flags_by_tab: dict[str, set[str]] = field(default_factory=dict)
    unknown_flags_by_tab: dict[str, set[str]] = field(default_factory=dict)
    notes: str = ""

    def is_fully_compatible(self) -> bool:
        return not any(self.missing_flags_by_tab.values())


def check_fixtures(version: str = TESTED_IMMICH_GO_VERSION) -> CompatibilityReport:
    """Evaluates GUI flag allowlists against captured help fixtures for a version."""
    report = CompatibilityReport(version=version)
    matrix_entry = COMPATIBILITY_MATRIX.get(version, {})
    report.notes = matrix_entry.get("notes", "")

    fixtures_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "cli_help" / version
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
        unknown = fixture_flags - set(gui_allowed)

        if missing:
            report.missing_flags_by_tab[tab_key] = missing
            report.supported = False
        if unknown:
            report.unknown_flags_by_tab[tab_key] = unknown

    return report


def check_binary_help(binary_path: Path, version: str = TESTED_IMMICH_GO_VERSION) -> CompatibilityReport:
    """Runs --help on target subcommands of live binary and compares against GUI allowlists."""
    report = CompatibilityReport(version=version)
    matrix_entry = COMPATIBILITY_MATRIX.get(version, {})
    report.notes = matrix_entry.get("notes", "")

    subcommands = {
        "upload-folder": ["upload", "from-folder"],
        "upload-gp": ["upload", "from-google-photos"],
        "upload-immich": ["upload", "from-immich"],
        "archive-folder": ["archive", "from-folder"],
        "archive-immich": ["archive", "from-immich"],
        "stack": ["stack"],
    }

    for tab_key, args in subcommands.items():
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
        unknown = binary_flags - set(gui_allowed)

        if missing:
            report.missing_flags_by_tab[tab_key] = missing
            report.supported = False
        if unknown:
            report.unknown_flags_by_tab[tab_key] = unknown

    return report
