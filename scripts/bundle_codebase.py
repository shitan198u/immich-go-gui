"""Bundle project source/config/test files into one text file for LLM code review.

Lean AI review profile: core/, tests/, scripts/, packaging/, CI — without full docs/
or editor config. Use bundle_website_docs.py for documentation review.

Usage:
    uv run scripts/bundle_codebase.py [output_path]
    uv run scripts/bundle_codebase.py --full [output_path]

Defaults:
    output_path: immichgo_modules_bundle.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path

# Directory names skipped anywhere in a path.
_SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".cache",
    "site",
    "dist",
    "build",
    "wheels",
    "node_modules",
    ".kilo",
    ".agents",
    "canvases",
    "AppDir",
    "immich-go",
}

# Lean profile: root files included in code review bundle.
_ROOT_FILES_LEAN = (
    "app.py",
    "theme.py",
    "pyproject.toml",
    "README.md",
    ".gitignore",
    ".pre-commit-config.yaml",
)

# Full profile adds meta/docs-adjacent root files.
_ROOT_FILES_FULL_EXTRA = (
    "mkdocs.yml",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "LICENSE.txt",
)

# Extensions treated as text source/config for the project.
_TEXT_EXTENSIONS = {
    ".py",
    ".toml",
    ".qss",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".txt",
    ".svg",
    ".cfg",
    ".ini",
    ".sh",
    ".bat",
    ".ps1",
    ".desktop",
    ".service",
}

# Generated / personal artifacts never bundled.
_SKIP_FILE_NAMES = {
    "immichgo_modules_bundle.txt",
    "immichgo_website_bundle.txt",
    "GitReadme.md",
    "TODO.md",
    "uv.lock",
}

_SKIP_NAME_PREFIXES = (
    "Refinement",
    "immichgo_",
)

_SKIP_NAME_SUFFIXES = (
    "_bundle.txt",
    ".egg-info",
)

# Lean profile: path prefixes excluded from glob collection.
_LEAN_EXCLUDE_PREFIXES = (
    "docs/",
    ".vscode/",
    "assets/icons/",
)

# Lean profile: individual root-relative paths excluded.
_LEAN_EXCLUDE_REL = frozenset(
    {
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE.txt",
        "mkdocs.yml",
        "uv.lock",
    }
)


def _is_under_skipped_dir(path: Path, repo_root: Path) -> bool:
    try:
        parts = path.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        return True
    return any(part in _SKIP_DIR_NAMES for part in parts)


def _should_skip_file(path: Path) -> bool:
    name = path.name
    if name in _SKIP_FILE_NAMES:
        return True
    if name.startswith(_SKIP_NAME_PREFIXES):
        return True
    if name.endswith(_SKIP_NAME_SUFFIXES):
        return True
    return bool(
        name.endswith(
            (
                ".pyc",
                ".pyo",
                ".png",
                ".ico",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webp",
                ".bin",
                ".exe",
                ".dmg",
                ".AppImage",
            )
        )
    )


def _is_text_file(path: Path) -> bool:
    if path.suffix.lower() in _TEXT_EXTENSIONS:
        return True
    return path.name in {".gitignore", "Dockerfile", "Makefile"}


def _lean_exclude(rel_posix: str) -> bool:
    if rel_posix in _LEAN_EXCLUDE_REL:
        return True
    return any(rel_posix.startswith(prefix) for prefix in _LEAN_EXCLUDE_PREFIXES)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return None


def collect_project_files(repo_root: Path, full: bool = False) -> list[Path]:
    """Return sorted unique project files for the codebase bundle."""
    found: set[Path] = set()

    def add(path: Path, lean_ok: bool = True) -> None:
        if not path.is_file():
            return
        if _is_under_skipped_dir(path, repo_root):
            return
        if _should_skip_file(path):
            return
        if not _is_text_file(path):
            return
        rel = path.relative_to(repo_root).as_posix()
        if not full and lean_ok and _lean_exclude(rel):
            return
        found.add(path.resolve())

    root_files = list(_ROOT_FILES_LEAN)
    if full:
        root_files.extend(_ROOT_FILES_FULL_EXTRA)

    for rel in root_files:
        add(repo_root / rel, lean_ok=False)

    glob_patterns = (
        "core/**/*",
        "gui/**/*",
        "tests/**/*",
        "scripts/**/*",
        "packaging/**/*",
        ".github/**/*",
    )
    if full:
        glob_patterns = (
            *glob_patterns,
            "docs/**/*",
            ".vscode/**/*",
        )

    for pattern in glob_patterns:
        for path in repo_root.glob(pattern):
            add(path)

    # Lean: theme.qss only from assets (skip icons/*.svg)
    if full:
        for path in repo_root.glob("assets/**/*"):
            add(path)
    else:
        add(repo_root / "assets/theme.qss", lean_ok=False)

    def sort_key(p: Path) -> tuple:
        rel = p.relative_to(repo_root).as_posix()
        rank = 50
        if rel in root_files or rel == ".gitignore":
            rank = 0
        elif rel.startswith("core/"):
            rank = 10
        elif rel.startswith("gui/"):
            rank = 15
        elif rel.startswith("assets/"):
            rank = 20
        elif rel.startswith("tests/"):
            rank = 30
        elif rel.startswith("scripts/"):
            rank = 40
        elif rel.startswith("packaging/"):
            rank = 45
        elif rel.startswith("docs/"):
            rank = 60
        elif rel.startswith(".github/"):
            rank = 70
        elif rel.startswith(".vscode/"):
            rank = 80
        return (rank, rel)

    return sorted(found, key=sort_key)


def _build_header(
    repo_root: Path,
    valid: list[tuple[Path, Path, int, str]],
    full: bool,
    skipped_binary: int,
) -> str:
    profile = "FULL" if full else "LEAN CODE REVIEW"
    lines = [
        "=" * 80,
        f"IMMICH-GO GUI — {profile} BUNDLE",
        "=" * 80,
        "Generated for LLM code review & prompting",
        f"Repo root: {repo_root}",
        f"Files included: {len(valid)}",
        "",
        "Project summary:",
        "  PySide6 desktop GUI for immich-go (v0.32.0 tested). Users configure",
        "  upload/archive/stack workflows via forms, preview argv, launch in an",
        "  external terminal. core/ is Qt-free; flags.toml is the SSOT for CLI",
        "  parity (loaded by flag_registry.py). Secrets via OS keyring + env vars",
        "  (never argv). 11 workflow tabs; serverless archive tabs never emit server",
        "  flags. Binary manager downloads versioned immich-go with SHA256 checks.",
        "",
        "For user/docs review use: immichgo_website_bundle.txt",
        "",
        "Coverage:",
        "  - Root app entrypoints (app.py, theme.py)",
        "  - core/ (including flags.toml, command_builder, binary_manager)",
        "  - gui/ (widgets, tabs, mixins, main_window)",
        "  - tests/ (suite + fixtures)",
        "  - scripts/, packaging/, .github/workflows",
        "  - assets/theme.qss",
    ]
    if full:
        lines.extend(
            [
                "  - docs/, .vscode/, CHANGELOG/CONTRIBUTING/LICENSE/mkdocs",
                "  - assets/icons/*.svg",
            ]
        )
    else:
        lines.append(
            "  - Excluded: docs/, .vscode/, icons/*.svg, uv.lock, meta docs files"
        )

    lines.append("")
    lines.append("Files:")
    for idx, (_, rel, line_count, _) in enumerate(valid, 1):
        lines.append(f"  {idx:3d}. {rel.as_posix()} ({line_count} lines)")

    if skipped_binary:
        lines.append(f"\nSkipped unreadable/binary files: {skipped_binary}")

    lines.extend(["=" * 80, ""])
    return "\n".join(lines)


def bundle_codebase(output_path: Path, full: bool = False) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    files = collect_project_files(repo_root, full=full)

    valid: list[tuple[Path, Path, int, str]] = []
    skipped_binary = 0
    for path in files:
        content = _read_text(path)
        if content is None:
            skipped_binary += 1
            continue
        rel = path.relative_to(repo_root)
        lines = len(content.splitlines())
        valid.append((path, rel, lines, content))

    sections = [_build_header(repo_root, valid, full, skipped_binary)]

    for idx, (_, rel, lines, content) in enumerate(valid, 1):
        sections.append(
            f"{'=' * 80}\n"
            f"FILE {idx} / {len(valid)}: {rel.as_posix()} (Lines 1-{lines})\n"
            f"{'=' * 80}\n"
            f"{content}\n"
        )

    output_text = "\n".join(sections)
    output_path.write_text(output_text, encoding="utf-8")
    profile = "full" if full else "lean"
    print(
        f"Successfully generated {profile} codebase bundle: {output_path} "
        f"({len(valid)} files, {len(output_text.splitlines())} lines)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundle codebase for LLM review")
    parser.add_argument("output_path", nargs="?", help="Output file path")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include docs/, .vscode/, meta files, and all assets (legacy all-inclusive dump)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    out_file = (
        Path(args.output_path)
        if args.output_path
        else repo_root / "immichgo_modules_bundle.txt"
    )
    bundle_codebase(out_file, full=args.full)


if __name__ == "__main__":
    main()
