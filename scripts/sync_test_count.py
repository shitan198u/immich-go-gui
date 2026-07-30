#!/usr/bin/env python3
"""Synchronize and verify pytest test counts in developer documentation."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT_DIR / "tests"


def count_test_modules() -> int:
    """Count test modules matching tests/test_*.py."""
    return len(list(TESTS_DIR.glob("test_*.py")))


def collect_pytest_count() -> int:
    """Return number of tests reported by pytest --collect-only -q."""
    res = subprocess.run(
        ["uv", "run", "pytest", "--collect-only", "-q"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print(res.stdout, file=sys.stderr)
        print(res.stderr, file=sys.stderr)
        raise RuntimeError("pytest --collect-only failed")

    for line in reversed(res.stdout.splitlines()):
        match = re.search(r"(\d+)\s+tests?\s+collected", line)
        if match:
            return int(match.group(1))

    raise RuntimeError("Could not parse test count from pytest output")


def check_or_update_file(
    file_path: Path, pattern: str, replacement: str, check_only: bool
) -> bool:
    """Check or update a file matching regex pattern with a fixed replacement string."""
    if not file_path.is_file():
        print(f"Warning: {file_path} does not exist", file=sys.stderr)
        return True

    content = file_path.read_text(encoding="utf-8")
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        print(
            f"Error: Pattern '{pattern}' not found in {file_path.relative_to(ROOT_DIR)}",
            file=sys.stderr,
        )
        return False

    current_found = match.group(0)
    if current_found == replacement:
        return True

    if check_only:
        print(
            f"Test count mismatch in {file_path.relative_to(ROOT_DIR)}:\n"
            f"  Found:    {current_found}\n"
            f"  Expected: {replacement}",
            file=sys.stderr,
        )
        return False

    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    file_path.write_text(new_content, encoding="utf-8")
    print(f"Updated {file_path.relative_to(ROOT_DIR)} -> {replacement}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize or check pytest test counts in documentation."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--sync", action="store_true", help="Update documentation to match pytest (default)."
    )
    group.add_argument(
        "--check", action="store_true", help="Verify documentation matches pytest without writing."
    )
    args = parser.parse_args()

    check_only = args.check
    test_count = collect_pytest_count()
    module_count = count_test_modules()
    print(f"Collected {test_count} tests across {module_count} modules")

    targets = [
        (
            ROOT_DIR / "docs" / "developer-guide" / "testing.md",
            r"\d+\s+tests(?:\s+across\s+\d+\s+modules)?",
            f"{test_count} tests across {module_count} modules",
        ),
        (
            ROOT_DIR / "docs" / "developer-guide" / "architecture.md",
            r"~\d+\s+tests",
            f"~{test_count} tests",
        ),
    ]

    all_ok = True
    for path, pattern, replacement in targets:
        ok = check_or_update_file(path, pattern, replacement, check_only)
        if not ok:
            all_ok = False

    if not all_ok:
        if check_only:
            print(
                "\nTest count synchronization check failed! "
                "Run `uv run python scripts/sync_test_count.py --sync` to fix.",
                file=sys.stderr,
            )
        return 1

    print("Test count synchronization check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
