"""CLI Help parsing and fixture loading module for Immich-Go GUI.

Pure Python module, Qt-free.
"""

from pathlib import Path
import re

_FLAG_PATTERN = re.compile(r"(?:^|\s)--([a-zA-Z0-9-]+)(?:[=[\s]|$)")


def parse_help_flags(help_text: str) -> set[str]:
    """Extracts flag names (without leading --) from immich-go CLI --help text.

    Filters out standard help flag 'help'.
    """
    flags = set()
    for line in help_text.splitlines():
        # Match all occurrences of --flag-name in the line
        matches = _FLAG_PATTERN.findall(line)
        for flag in matches:
            if flag and flag != "help":
                flags.add(flag)
    return flags


def help_name_for_tab(tab_key: str) -> str:
    """Maps a GUI tab key to its corresponding captured help fixture basename."""
    mapping = {
        "upload-folder": "upload_from-folder",
        "upload-gp": "upload_from-google-photos",
        "upload-immich": "upload_from-immich",
        "archive-folder": "archive_from-folder",
        "archive-immich": "archive_from-immich",
        "stack": "stack",
    }
    return mapping.get(tab_key, tab_key.replace("-", "_"))


def load_help_fixture(version: str = "0.32.0", help_name: str = "root") -> set[str]:
    """Loads a captured help text fixture and returns its set of parsed flag names."""
    base_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "cli_help" / version
    fixture_file = base_dir / f"{help_name}.txt"

    if not fixture_file.exists():
        return set()

    try:
        text = fixture_file.read_text(encoding="utf-8")
        return parse_help_flags(text)
    except Exception:
        return set()
