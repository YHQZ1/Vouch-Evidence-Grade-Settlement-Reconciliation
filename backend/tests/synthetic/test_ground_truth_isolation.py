from __future__ import annotations

import ast
from pathlib import Path

import app


def test_runtime_app_never_imports_generator_or_ground_truth() -> None:
    app_root = Path(app.__file__).parent
    forbidden = ("synthetic_data", "ground_truth", "ground-truth", "evaluation")
    violations: list[str] = []
    for path in sorted(app_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for name in imported:
                if name.startswith(forbidden):
                    violations.append(f"{path}: {name}")
    assert violations == []


def test_ground_truth_is_not_in_the_runtime_wheel_package_list() -> None:
    pyproject = Path(app.__file__).parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert 'packages = ["app"]' in text


def test_verifier_does_not_import_ground_truth_materiality_oracle() -> None:
    verifier = Path(__file__).parents[2] / "synthetic_data/verification.py"
    text = verifier.read_text(encoding="utf-8")
    assert "from synthetic_data.ground_truth import materiality_is_blocking" not in text
    assert "def _materiality_is_blocking(" in text
