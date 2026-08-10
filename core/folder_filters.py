"""Shared file-filtering and path-containment helpers for the Monitor subsystem.

Used by both the real-time folder watcher and the hidden upload runner so
that filter behavior stays consistent. No Qt dependencies.
"""

import fnmatch
import os
from pathlib import Path

from .monitor_config import FolderFilter


def should_skip_file(file_path: str, filter_rules: FolderFilter) -> bool:
    """Apply folder filter rules to decide if a file should be skipped."""
    name = os.path.basename(file_path)
    ext = os.path.splitext(name)[1].lower()

    if filter_rules.skip_hidden and name.startswith("."):
        return True

    if filter_rules.skip_system_files:
        if name.startswith("~$") or name.lower() in ("thumbs.db", "desktop.ini"):
            return True

    if filter_rules.include_extensions:
        if ext not in [e.lower() for e in filter_rules.include_extensions]:
            return True

    if ext in [e.lower() for e in filter_rules.exclude_extensions]:
        return True

    try:
        size_bytes = os.path.getsize(file_path)
    except OSError:
        return True

    if (
        filter_rules.max_file_size_mb > 0
        and size_bytes > filter_rules.max_file_size_mb * 1024 * 1024
    ):
        return True
    if (
        filter_rules.min_file_size_kb > 0
        and size_bytes < filter_rules.min_file_size_kb * 1024
    ):
        return True

    normalized = file_path.replace("\\", "/")
    for pattern in filter_rules.exclude_patterns:
        if fnmatch.fnmatch(normalized, pattern):
            return True

    return False


def is_within_folder(base_path: str, candidate_path: str) -> bool:
    """Boundary-safe containment check for event paths.

    Avoids the classic ``str.startswith`` false positive where a sibling
    folder such as ``photos_backup`` matches a watch on ``photos``. Both
    paths are resolved first so case and separator differences on Windows
    do not reject valid events.
    """
    try:
        Path(candidate_path).resolve().relative_to(Path(base_path).resolve())
    except (ValueError, OSError, RuntimeError):
        return False
    return True
