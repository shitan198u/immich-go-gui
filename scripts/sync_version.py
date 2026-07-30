#!/usr/bin/env python3
"""Synchronize and verify application version across configuration and documentation files.

Version source priority:
1. Max semver of latest semver git release tag (`v<major>.<minor>.<patch>`) vs `pyproject.toml`.
   Ignores test tags (`test-*`), binary tags (`Immich-Go_*`), or non-semver tags.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from packaging.version import Version, InvalidVersion

ROOT_DIR = Path(__file__).resolve().parent.parent
SEMVER_TAG_PATTERN = re.compile(r"^v(\d+\.\d+\.\d+)$")


def get_latest_git_release_version() -> str | None:
    """Retrieve the version from the latest semver git release tag matching v<major>.<minor>.<patch>."""
    try:
        res = subprocess.run(
            ["git", "tag", "-l", "v[0-9]*", "--sort=-v:refname"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        tags = [t.strip() for t in res.stdout.splitlines() if t.strip()]
        for tag in tags:
            match = SEMVER_TAG_PATTERN.match(tag)
            if match:
                return match.group(1)
    except subprocess.CalledProcessError:
        pass
    return None


def get_pyproject_version() -> str:
    """Read version string from pyproject.toml."""
    pyproject_path = ROOT_DIR / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find version in {pyproject_path}")
    return match.group(1)


def resolve_target_version() -> str:
    """Resolve active version taking max of latest git release tag and pyproject.toml."""
    pyproject_ver = get_pyproject_version()
    git_ver = get_latest_git_release_version()
    if not git_ver:
        return pyproject_ver

    try:
        v_py = Version(pyproject_ver)
        v_git = Version(git_ver)
        return pyproject_ver if v_py >= v_git else git_ver
    except InvalidVersion:
        return pyproject_ver


def check_or_update_file(
    file_path: Path,
    pattern: str,
    replacement_fmt: str,
    target_ver: str,
    check_only: bool,
) -> bool:
    """Check or update a file matching regex pattern with replacement_fmt.format(version=target_ver)."""
    if not file_path.is_file():
        print(f"Warning: {file_path} does not exist", file=sys.stderr)
        return True

    content = file_path.read_text(encoding="utf-8")
    expected_str = replacement_fmt.format(version=target_ver)

    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        print(
            f"Error: Pattern '{pattern}' not found in {file_path.relative_to(ROOT_DIR)}",
            file=sys.stderr,
        )
        return False

    current_found = match.group(0)
    if current_found == expected_str:
        return True

    if check_only:
        print(
            f"Version mismatch in {file_path.relative_to(ROOT_DIR)}:\n"
            f"  Found:    {current_found}\n"
            f"  Expected: {expected_str}",
            file=sys.stderr,
        )
        return False

    new_content = re.sub(pattern, expected_str, content, flags=re.MULTILINE)
    file_path.write_text(new_content, encoding="utf-8")
    print(f"Updated {file_path.relative_to(ROOT_DIR)} -> {expected_str}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize or check version across codebase files."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--sync",
        action="store_true",
        help="Update all files to target version (default).",
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="Verify all files match target version without writing.",
    )
    args = parser.parse_args()

    check_only = args.check
    target_ver = resolve_target_version()
    print(f"Resolved release target version: {target_ver}")

    targets = [
        (
            ROOT_DIR / "pyproject.toml",
            r'^version\s*=\s*"[^"]+"',
            'version = "{version}"',
        ),
        (
            ROOT_DIR / ".github" / ".release-please-manifest.json",
            r'"\."\s*:\s*"[^"]+"',
            '".": "{version}"',
        ),
        (
            ROOT_DIR / "docs" / "README.md",
            r"Docs track the application as of <strong>v[^<]+</strong>",
            "Docs track the application as of <strong>v{version}</strong>",
        ),
        (
            ROOT_DIR / "docs" / "developer-guide" / "ci-cd-and-releases.md",
            r"Current version is defined in `pyproject.toml` \(e\.g\. `[^`]+`\)\.",
            "Current version is defined in `pyproject.toml` (e.g. `{version}`).",
        ),
        (
            ROOT_DIR / "docs" / "developer-guide" / "ci-cd-and-releases.md",
            r"Tag `v[^`]+` or manual",
            "Tag `v[0-9]*` or manual",
        ),
    ]

    all_ok = True
    for path, pattern, fmt in targets:
        ok = check_or_update_file(path, pattern, fmt, target_ver, check_only)
        if not ok:
            all_ok = False

    if not all_ok:
        if check_only:
            print(
                "\nVersion synchronization check failed! Run `uv run python scripts/sync_version.py --sync` to fix.",
                file=sys.stderr,
            )
        return 1

    print("Version synchronization check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
