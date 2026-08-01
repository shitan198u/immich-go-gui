"""Architecture guardrails: enforce structural invariants that protect the
long-term design of the codebase.

These tests are intentionally Qt-free and pure-Python so they run fast and
catch AI-agent-introduced architecture violations (e.g. importing PySide6
into ``core/``, which must remain Qt-free and testable without a GUI).
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = REPO_ROOT / "core"
GUI_ROOT = REPO_ROOT / "gui"

# Qt bindings that must never appear in core/.
FORBIDDEN_TOP_LEVELS = {"PySide6", "PyQt6", "PyQt5"}


def _iter_py(root: Path):
    """Yield every .py file under *root*, skipping bytecode caches."""
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _imported_top_levels(path: Path):
    """
    Extract top-level module names from imports in a Python file.

    Parameters:
        path (Path): Python file to inspect.

    Yields:
        tuple[Path, str]: The file path and the imported top-level module name.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield path, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod:
                yield path, mod


def test_core_is_qt_free():
    """core/ must never import PySide6 or any Qt binding."""
    offenders = [
        (p.name, top)
        for p in _iter_py(CORE_ROOT)
        for _, top in _imported_top_levels(p)
        if top in FORBIDDEN_TOP_LEVELS
    ]
    assert not offenders, f"Qt imports found in core/: {offenders}"


def test_core_does_not_import_gui():
    """core/ must not depend on the gui/ package (no circular dependency)."""
    offenders = [
        (p.name, top)
        for p in _iter_py(CORE_ROOT)
        for _, top in _imported_top_levels(p)
        if top == "gui"
    ]
    assert not offenders, f"core/ imports gui/: {offenders}"


def test_core_models_is_qt_free_by_import():
    """Importing core.models must succeed without PySide6 installed concept.

    A smoke test that the pure-data module imports cleanly and exposes the
    expected dataclasses used across the codebase.
    """
    from core.models import (
        AppConfig,
        CommandPlan,
        ValidationResult,
    )

    plan = CommandPlan()
    assert plan.argv == []
    assert plan.env == {}
    assert ValidationResult().is_valid is True
    assert AppConfig().schema_version == 3
