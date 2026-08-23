"""Architecture guard for the framework-independent Phase 2 domain."""

import ast
from pathlib import Path

import app.domain

FORBIDDEN_IMPORT_PREFIXES = (
    "app.api",
    "app.application",
    "app.infrastructure",
    "app.main",
    "fastapi",
    "sqlalchemy",
    "httpx",
    "requests",
    "ollama",
    "openai",
    "langchain",
    "crewai",
    "app.evaluation",
    "app.ground_truth",
    "pydantic_settings",
    "uvicorn",
    "ground_truth",
    "evaluation",
)


def test_domain_modules_have_no_framework_or_runtime_integration_imports() -> None:
    domain_root = Path(app.domain.__file__).parent
    violations: list[str] = []

    for source_path in sorted(domain_root.glob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported_names: list[str] = []
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names = [node.module]
            for imported_name in imported_names:
                if imported_name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(f"{source_path.name}: {imported_name}")

    assert violations == []
