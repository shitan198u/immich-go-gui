"""Helper script to bundle Python modules into a single text file for LLM analysis.

Usage:
    uv run python scripts/bundle_codebase.py [output_path]

Defaults:
    output_path: immichgo_modules_bundle.txt
"""

import sys
from pathlib import Path

def bundle_codebase(output_path: Path):
    repo_root = Path(__file__).resolve().parent.parent

    # Target python files to include in bundle
    files_to_bundle = [
        repo_root / "core" / "models.py",
        repo_root / "core" / "cli_schema.py",
        repo_root / "core" / "config_manager.py",
        repo_root / "core" / "binary_manager.py",
        repo_root / "core" / "command_builder.py",
        repo_root / "app.py",
        repo_root / "test_app.py",
    ]

    header = "=" * 80 + "\n"
    header += "IMMICH-GO GUI - PYTHON BACKEND & CORE BUNDLE\n"
    header += "=" * 80 + "\n"
    header += "Generated for LLM Review & Prompting\n"
    header += "Files Included:\n"

    valid_files = []
    for idx, f in enumerate(files_to_bundle, 1):
        if f.exists():
            rel_path = f.relative_to(repo_root)
            lines_count = len(f.read_text(encoding="utf-8").splitlines())
            header += f"  {idx}. {rel_path} ({lines_count} lines)\n"
            valid_files.append((f, rel_path, lines_count))

    header += "=" * 80 + "\n\n"

    sections = [header]

    for idx, (f_path, rel_path, lines_count) in enumerate(valid_files, 1):
        content = f_path.read_text(encoding="utf-8")
        sec = f"{'=' * 80}\n"
        sec += f"FILE {idx} / {len(valid_files)}: {rel_path} (Lines 1-{lines_count})\n"
        sec += f"{'=' * 80}\n"
        sec += content + "\n\n"
        sections.append(sec)

    output_text = "\n".join(sections)
    output_path.write_text(output_text, encoding="utf-8")
    print(f"Successfully generated codebase bundle: {output_path} ({len(valid_files)} files, {len(output_text.splitlines())} lines)")

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out_file = Path(sys.argv[1]) if len(sys.argv) > 1 else repo_root / "immichgo_modules_bundle.txt"
    bundle_codebase(out_file)
