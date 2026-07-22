"""Validation and input normalization helpers for Immich-Go GUI.

Pure Python module, Qt-free.
"""

from datetime import datetime
import glob
import os
from pathlib import Path
import re


def clean_date_range(text: str) -> str:
    """Normalize date range input.

    - strip outer whitespace
    - remove spaces around comma
    - return empty string if blank
    """
    if not text:
        return ""
    text = text.strip()
    if not text:
        return ""
    parts = [p.strip() for p in text.split(",")]
    return ",".join(parts)


def _parse_partial_date(date_str: str) -> tuple[datetime | None, str | None]:
    """Helper to parse YYYY, YYYY-MM, YYYY-MM-DD.

    Returns (datetime_obj, error_message).
    """
    s = date_str.strip()
    if not s:
        return None, "Empty date segment"

    if re.match(r"^\d{4}$", s):
        try:
            return datetime(int(s), 1, 1), None
        except ValueError as e:
            return None, str(e)
    elif re.match(r"^\d{4}-\d{2}$", s):
        try:
            parts = s.split("-")
            return datetime(int(parts[0]), int(parts[1]), 1), None
        except ValueError as e:
            return None, str(e)
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        try:
            parts = [int(x) for x in s.split("-")]
            return datetime(parts[0], parts[1], parts[2]), None
        except ValueError as e:
            return None, str(e)
    else:
        return None, f"Invalid date format: '{s}'. Expected YYYY, YYYY-MM, or YYYY-MM-DD"


def validate_date_range(text: str) -> tuple[bool, str | None]:
    """Validate date range input.

    Return (is_valid, error_message).
    Accept:
      - YYYY
      - YYYY-MM
      - YYYY-MM-DD
      - start,end (with optional spaces after comma)
    Reject:
      - invalid months
      - invalid days
      - impossible dates
      - start > end when comparable
    """
    cleaned = clean_date_range(text)
    if not cleaned:
        return True, None

    parts = cleaned.split(",")
    if len(parts) > 2:
        return False, "Date range can have at most one start and one end date separated by comma"

    if len(parts) == 1:
        dt, err = _parse_partial_date(parts[0])
        if err:
            return False, err
        return True, None

    dt_start, err_start = _parse_partial_date(parts[0])
    if err_start:
        return False, f"Start date error: {err_start}"

    dt_end, err_end = _parse_partial_date(parts[1])
    if err_end:
        return False, f"End date error: {err_end}"

    if dt_start and dt_end and dt_start > dt_end:
        return False, f"Start date ({parts[0]}) cannot be after end date ({parts[1]})"

    return True, None


def normalize_extensions_csv(value: str) -> str:
    """Normalize extension lists.

    - split on comma
    - trim whitespace
    - lowercase
    - ensure leading dot
    - remove empties
    - deduplicate while preserving order
    - rejoin with commas
    """
    if not value:
        return ""
    seen = set()
    result = []
    for item in value.split(","):
        ext = item.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        if ext not in seen:
            seen.add(ext)
            result.append(ext)
    return ",".join(result)


def normalize_list_csv(value: str) -> list[str]:
    """Normalize generic comma-separated lists:

    - tags
    - albums
    - people
    Do not lowercase. Preserve hierarchy separators like '/'.
    """
    if not value:
        return []
    result = []
    for item in value.split(","):
        trimmed = item.strip()
        if trimmed:
            result.append(trimmed)
    return result


def has_glob_pattern(text: str) -> bool:
    """Return True if text contains *, ?, [, or ]."""
    return any(c in text for c in ("*", "?", "[", "]"))


def expand_source_paths(raw_text: str) -> tuple[list[str], list[str]]:
    """For multi-line path input:

    - split lines
    - strip lines
    - expand globs
    - return (expanded_paths, warnings)

    Warnings:
    - non-glob line that does not exist
    - glob line that matches nothing
    """
    if not raw_text:
        return [], []

    expanded_paths: list[str] = []
    warnings: list[str] = []

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    for line in lines:
        if has_glob_pattern(line):
            matches = glob.glob(line, recursive=True)
            if not matches:
                warnings.append(f"Glob pattern '{line}' matched no files or directories.")
            else:
                expanded_paths.extend(matches)
        else:
            p = Path(line)
            if not p.exists():
                warnings.append(f"Source path '{line}' does not exist.")
            expanded_paths.append(line)

    return expanded_paths, warnings


def validate_destination_folder(
    write_to: str,
    source_paths: list[str],
) -> list[str]:
    """Return warnings/errors for destination folder.

    - warn if destination is inside a source path
    - warn if destination exists but is not a directory
    - warn if destination exists and is not writable
    """
    if not write_to:
        return []

    warnings: list[str] = []
    dest_path = Path(write_to).resolve()

    if dest_path.exists():
        if not dest_path.is_dir():
            warnings.append(f"Destination '{write_to}' exists but is not a directory.")
        elif not os.access(dest_path, os.W_OK):
            warnings.append(f"Destination folder '{write_to}' exists but is not writable.")

    for src in source_paths:
        if not src:
            continue
        try:
            src_path = Path(src).resolve()
            if dest_path == src_path or src_path in dest_path.parents:
                warnings.append(
                    f"Destination folder '{write_to}' is inside the source path '{src}'. "
                    "Future runs may include archived output."
                )
        except Exception:
            pass

    return warnings
