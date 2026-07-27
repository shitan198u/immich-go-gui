"""Helper script to bundle all documentation & website rendering files into a single text file for LLM analysis.

Usage:
    uv run python scripts/bundle_website_docs.py [output_path]

Defaults:
    output_path: immichgo_website_bundle.txt
"""

import sys
from pathlib import Path


def bundle_website(output_path: Path):
    repo_root = Path(__file__).resolve().parent.parent

    # Gather configuration & documentation source files
    files_to_bundle = []

    # 1. Root configuration files for MkDocs & GitHub Actions docs workflow
    for config_name in ["mkdocs.yml", ".github/workflows/docs.yml", "pyproject.toml"]:
        cfg_path = repo_root / config_name
        if cfg_path.exists():
            files_to_bundle.append(cfg_path)

    # 2. All text files inside docs/ directory
    docs_dir = repo_root / "docs"
    if docs_dir.exists():
        text_extensions = {".md", ".css", ".js", ".html", ".svg", ".yml", ".yaml", ".json", ".txt"}
        for p in sorted(docs_dir.rglob("*")):
            if p.is_file() and p.suffix.lower() in text_extensions:
                files_to_bundle.append(p)

    header = "=" * 80 + "\n"
    header += "IMMICH-GO GUI - WEBSITE RENDERING & DOCUMENTATION BUNDLE\n"
    header += "=" * 80 + "\n"
    header += "Generated for LLM Review & Analysis\n"
    header += "Files Included:\n"

    valid_files = []
    for idx, f in enumerate(files_to_bundle, 1):
        if f.exists():
            rel_path = f.relative_to(repo_root)
            lines_count = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
            header += f"  {idx:2d}. {rel_path} ({lines_count} lines)\n"
            valid_files.append((f, rel_path, lines_count))

    header += "=" * 80 + "\n\n"

    sections = [header]

    for idx, (f_path, rel_path, lines_count) in enumerate(valid_files, 1):
        content = f_path.read_text(encoding="utf-8", errors="replace")
        sec = f"{'=' * 80}\n"
        sec += f"FILE {idx} / {len(valid_files)}: {rel_path} (Lines 1-{lines_count})\n"
        sec += f"{'=' * 80}\n"
        sec += content + "\n\n"
        sections.append(sec)

    output_text = "\n".join(sections)
    output_path.write_text(output_text, encoding="utf-8")
    print(f"Successfully generated website docs bundle: {output_path} ({len(valid_files)} files, {len(output_text.splitlines())} lines)")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out_file = Path(sys.argv[1]) if len(sys.argv) > 1 else repo_root / "immichgo_website_bundle.txt"
    bundle_website(out_file)
