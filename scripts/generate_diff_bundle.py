"""Helper script to generate structured git diff review bundles for code analysis.

Usage:
    uv run python scripts/generate_diff_bundle.py [start_ref] [output_path] [end_ref]

Defaults:
    start_ref: 9dbbc54
    output_path: phase2_review_changes.txt
    end_ref: HEAD
"""

import sys
import subprocess
from pathlib import Path


def generate_diff_bundle(start_ref: str = "9dbbc54", output_path: Path = None, end_ref: str = "HEAD"):
    repo_root = Path(__file__).resolve().parent.parent
    if output_path is None:
        output_path = repo_root / "phase2_review_changes.txt"

    rev_spec = f"{start_ref}..{end_ref}"

    try:
        diff = subprocess.check_output(["git", "diff", rev_spec], cwd=repo_root).decode("utf-8")
        log = subprocess.check_output(["git", "log", rev_spec, "--oneline"], cwd=repo_root).decode("utf-8")
        stat = subprocess.check_output(["git", "diff", rev_spec, "--stat"], cwd=repo_root).decode("utf-8")
    except subprocess.CalledProcessError as e:
        print(f"Error executing git command for {rev_spec}: {e}")
        sys.exit(1)

    header = "=" * 80 + "\n"
    header += f"IMMICH-GO GUI - REVIEW & CHANGES BUNDLE ({rev_spec})\n"
    header += "=" * 80 + "\n\n"
    header += "COMMITS IN RANGE:\n"
    header += log + "\n"
    header += "SUMMARY OF CHANGED FILES:\n"
    header += stat + "\n"
    header += "=" * 80 + "\n"
    header += "FULL GIT DIFF:\n"
    header += "=" * 80 + "\n\n"

    full_content = header + diff
    output_path.write_text(full_content, encoding="utf-8")
    print(f"Successfully generated git diff bundle: {output_path} ({len(full_content.splitlines())} lines)")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    start = sys.argv[1] if len(sys.argv) > 1 else "9dbbc54"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else repo_root / "phase2_review_changes.txt"
    end = sys.argv[3] if len(sys.argv) > 3 else "HEAD"

    generate_diff_bundle(start_ref=start, output_path=out, end_ref=end)
