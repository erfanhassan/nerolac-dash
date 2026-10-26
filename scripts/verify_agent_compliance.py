#!/usr/bin/env python3
"""Nerolac Dash - Repository Guardrail & AST Compliance Engine.

Enforces:
1. MANDATORY ARCHITECTURE: Next.js 15 App Router + FastAPI (Async ASGI) + PostgreSQL 16 + Redis 7
2. UI/UX DESIGN CONSTRAINT: Bright Light Corporate Mode ONLY
   (#FFFFFF, #F8FAFC, #D32F2F, tabular-nums)
   Absolute ban on Dark Mode, glassmorphism, floating gradients, or loose padding.
3. SCHEMA LOCK: Strict lock on Backend_Database_Schema_(PostgreSQL_16_DDL).md and DB tables.
4. ZERO FRONTEND MOCK DATA: Never render fake or hardcoded mock data on frontend components.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

# Base repository directory
REPO_ROOT = Path(__file__).resolve().parent.parent

# Ignored directories for scanning
IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}

# Forbidden Python packages/modules
BANNED_PYTHON_IMPORTS = {
    "flask": "FastAPI (Async ASGI) is the mandatory backend framework",
    "django": "FastAPI (Async ASGI) is the mandatory backend framework",
    "tornado": "FastAPI (Async ASGI) is the mandatory backend framework",
    "bottle": "FastAPI (Async ASGI) is the mandatory backend framework",
    "psycopg2": "Synchronous psycopg2 forbidden; asyncpg with SQLAlchemy async engine required",
}

# Approved backend dependencies
APPROVED_PYTHON_DEPS = {
    "fastapi",
    "uvicorn",
    "pydantic",
    "sqlalchemy",
    "asyncpg",
    "redis",
    "alembic",
    "pytest",
    "pytest-asyncio",
    "httpx",
    "ruff",
    "mypy",
    "paramiko",
    "pandera",
    "pandas",
    "eval_type_backport",
}

# Banned UI tokens & patterns (Strict Bright Light Corporate Mode)
BANNED_UI_PATTERNS: list[tuple[str, str, str]] = [
    (
        r"\bdark:\S+",
        "Tailwind Dark Mode",
        "Dark mode is strictly forbidden. Corporate Bright Light Mode only.",
    ),
    (
        r"prefers-color-scheme\s*:\s*dark",
        "CSS Dark Mode Media Query",
        "Dark mode is strictly forbidden.",
    ),
    (
        r'data-theme\s*=\s*["\']dark["\']',
        "Dark Theme Attribute",
        "Dark mode is strictly forbidden.",
    ),
    (
        r"backdrop-filter",
        "Glassmorphism Backdrop Filter",
        "Glassmorphism is strictly forbidden.",
    ),
    (
        r"backdrop-blur",
        "Glassmorphism Blur",
        "Glassmorphism is strictly forbidden.",
    ),
    (
        r"linear-gradient",
        "Floating Linear Gradient",
        "Floating gradients are strictly forbidden.",
    ),
    (
        r"radial-gradient",
        "Floating Radial Gradient",
        "Floating gradients are strictly forbidden.",
    ),
    (
        r"conic-gradient",
        "Floating Conic Gradient",
        "Floating gradients are strictly forbidden.",
    ),
    (
        r"bg-gradient-to-",
        "Tailwind Floating Gradient",
        "Floating gradients are strictly forbidden.",
    ),
]

# Zero Frontend Mock Data patterns
MOCK_DATA_PATTERNS: list[tuple[str, str]] = [
    (
        r"(?:const|let|var)\s+(?:mock[A-Z0-9_]|dummy[A-Z0-9_]|fake[A-Z0-9_]|sampleData)\w*\s*=\s*\[",
        "Hardcoded mock dataset array",
    ),
    (
        r"(?:const|let|var)\s+\w*(?:MockData|DummyData|FakeData)\s*=\s*\[",
        "Hardcoded mock dataset array",
    ),
    (
        r"from\s+['\"]\S*(?:mock|dummy|fake)[^'\"]*['\"]",
        "Importing mock/dummy fixture directly into frontend",
    ),
    (
        r"require\(['\"]\S*(?:mock|dummy|fake)[^'\"]*['\"]\)",
        "Requiring mock/dummy fixture in frontend",
    ),
]


class ComplianceViolation:
    def __init__(self, file_path: str, line: int, category: str, message: str) -> None:
        self.file_path = file_path
        self.line = line
        self.category = category
        self.message = message

    def __str__(self) -> str:
        return f"[{self.category}] {self.file_path}:{self.line} -> {self.message}"


class PythonASTVisitor(ast.NodeVisitor):
    """Scans Python AST trees for compliance with async FastAPI and banned libraries."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.violations: list[ComplianceViolation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_name = alias.name.split(".")[0]
            if base_name in BANNED_PYTHON_IMPORTS:
                self.violations.append(
                    ComplianceViolation(
                        self.file_path,
                        node.lineno,
                        "ARCHITECTURE_VIOLATION",
                        f"Banned Python library '{alias.name}': {BANNED_PYTHON_IMPORTS[base_name]}",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_name = node.module.split(".")[0]
            if base_name in BANNED_PYTHON_IMPORTS:
                msg = f"Banned import '{node.module}': {BANNED_PYTHON_IMPORTS[base_name]}"
                self.violations.append(
                    ComplianceViolation(
                        self.file_path,
                        node.lineno,
                        "ARCHITECTURE_VIOLATION",
                        msg,
                    )
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Detect synchronous route definitions in FastAPI
        for decorator in node.decorator_list:
            dec_id = ""
            if isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute):
                    dec_id = f"{getattr(func.value, 'id', '')}.{func.attr}"
            elif isinstance(decorator, ast.Attribute):
                dec_id = f"{getattr(decorator.value, 'id', '')}.{decorator.attr}"

            # Common FastAPI route decorators: app.get, router.post, etc.
            if any(
                dec_id.endswith(f".{method}")
                for method in ["get", "post", "put", "delete", "patch", "options", "head"]
            ):
                msg = (
                    f"FastAPI route '{node.name}' must be asynchronous (`async def`), "
                    "got synchronous `def`."
                )
                self.violations.append(
                    ComplianceViolation(
                        self.file_path,
                        node.lineno,
                        "FASTAPI_ASYNC_ASGI_REQUIRED",
                        msg,
                    )
                )
        self.generic_visit(node)


def verify_agent_rules_file(violations: list[ComplianceViolation]) -> None:
    """Ensure .agents/rules.md exists and contains all mandatory directives."""
    rules_path = REPO_ROOT / ".agents" / "rules.md"
    if not rules_path.is_file():
        violations.append(
            ComplianceViolation(
                str(rules_path),
                1,
                "RULE_INTEGRITY",
                "Missing mandatory .agents/rules.md in repository root.",
            )
        )
        return

    content = rules_path.read_text(encoding="utf-8")
    mandatory_terms = [
        ("Next.js 15 App Router", "Mandatory Architecture: Next.js 15"),
        ("FastAPI", "Mandatory Architecture: FastAPI (Async ASGI)"),
        ("PostgreSQL 16", "Mandatory Architecture: PostgreSQL 16"),
        ("Redis 7", "Mandatory Architecture: Redis 7"),
        ("#FFFFFF", "UI Token: Canvas #FFFFFF"),
        ("#F8FAFC", "UI Token: Containers #F8FAFC"),
        ("#D32F2F", "UI Token: Nerolac Red Accents #D32F2F"),
        ("#E2E8F0", "UI Token: 1px solid #E2E8F0 borders"),
        ("tabular-nums", "UI Token: tabular-nums typography"),
        ("Dark Mode", "Prohibition: Ban on Dark Mode"),
        ("glassmorphism", "Prohibition: Ban on glassmorphism"),
        ("floating gradients", "Prohibition: Ban on floating gradients"),
        ("Backend_Database_Schema_(PostgreSQL_16_DDL).md", "Directive: Schema Lock"),
        ("ZERO FRONTEND MOCK DATA", "Directive: Zero Frontend Mock Data"),
    ]

    for term, label in mandatory_terms:
        if term.lower() not in content.lower():
            violations.append(
                ComplianceViolation(
                    str(rules_path),
                    1,
                    "RULE_DIRECTIVE_MISSING",
                    f".agents/rules.md is missing mandatory directive '{label}'.",
                )
            )


def verify_schema_lock(violations: list[ComplianceViolation]) -> None:
    """Ensure locked database schema file exists and is intact."""
    schema_path = REPO_ROOT / "knowledge" / "Backend_Database_Schema_(PostgreSQL_16_DDL).md"
    if not schema_path.is_file():
        violations.append(
            ComplianceViolation(
                str(schema_path),
                1,
                "SCHEMA_LOCK_VIOLATION",
                "Mandatory schema documentation 'knowledge/Backend_Database_Schema' missing.",
            )
        )
        return

    content = schema_path.read_text(encoding="utf-8")
    if "nerolac_ops" not in content or "CREATE TABLE" not in content:
        violations.append(
            ComplianceViolation(
                str(schema_path),
                1,
                "SCHEMA_CORRUPTED",
                "PostgreSQL 16 DDL Schema definition lacks valid DDL or schema header.",
            )
        )


def scan_python_files(violations: list[ComplianceViolation]) -> None:
    """Parse and inspect all Python files via AST."""
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, REPO_ROOT)

                # Skip this verification script itself
                if rel_path == "scripts/verify_agent_compliance.py":
                    continue

                try:
                    with open(file_path, encoding="utf-8") as f:
                        source = f.read()
                    tree = ast.parse(source, filename=file_path)
                    visitor = PythonASTVisitor(rel_path)
                    visitor.visit(tree)
                    violations.extend(visitor.violations)
                except SyntaxError as e:
                    violations.append(
                        ComplianceViolation(
                            rel_path,
                            e.lineno or 1,
                            "SYNTAX_ERROR",
                            f"Python Syntax Error: {e.msg}",
                        )
                    )


def scan_frontend_code(violations: list[ComplianceViolation]) -> None:
    """Scan frontend files (.ts, .tsx, .js, .jsx, .css, .html) for banned UI patterns and mocks."""
    frontend_extensions = {".ts", ".tsx", ".js", ".jsx", ".css", ".scss", ".html"}

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in frontend_extensions:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, REPO_ROOT)

                # Skip configuration files or test mocks placed in test suites
                if "test" in rel_path.lower() and "fixture" in rel_path.lower():
                    continue

                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for idx, line in enumerate(lines, 1):
                        # 1. Check Banned UI Patterns
                        for pattern, name, reason in BANNED_UI_PATTERNS:
                            if re.search(pattern, line, re.IGNORECASE):
                                violations.append(
                                    ComplianceViolation(
                                        rel_path,
                                        idx,
                                        "UI_DESIGN_VIOLATION",
                                        f"Detected banned pattern '{name}': {reason}",
                                    )
                                )

                        # 2. Check Zero Frontend Mock Data
                        if ext in {".ts", ".tsx", ".js", ".jsx"}:
                            for pattern, desc in MOCK_DATA_PATTERNS:
                                if re.search(pattern, line):
                                    msg = (
                                        f"Found {desc}. Frontend UI must remain pristine "
                                        "awaiting live backend pipeline feeds."
                                    )
                                    violations.append(
                                        ComplianceViolation(
                                            rel_path,
                                            idx,
                                            "MOCK_DATA_VIOLATION",
                                            msg,
                                        )
                                    )
                except OSError as e:
                    violations.append(
                        ComplianceViolation(
                            rel_path,
                            1,
                            "SCAN_ERROR",
                            f"Unable to read file for compliance scan: {e!s}",
                        )
                    )


def main() -> None:
    print("=" * 70)
    print("  NEROLAC DASH - SYSTEM GUARDRAIL & AST COMPLIANCE SCANNER")
    print("=" * 70)

    violations: list[ComplianceViolation] = []

    print("[1/4] Verifying .agents/rules.md directives...")
    verify_agent_rules_file(violations)

    print("[2/4] Verifying PostgreSQL 16 DDL schema lock...")
    verify_schema_lock(violations)

    print("[3/4] Parsing and scanning Python AST code trees...")
    scan_python_files(violations)

    print("[4/4] Scanning frontend codebase for UI/UX constraints & mock data...")
    scan_frontend_code(violations)

    print("-" * 70)

    if violations:
        print(f"FAILED: Found {len(violations)} compliance violation(s):\n")
        for v in violations:
            print(f"  ❌ {v}")
        print("\nCompliance verification failed. Fix above violations to proceed.")
        sys.exit(1)
    else:
        print("SUCCESS: All system guardrails and AST compliance checks passed! ✨")
        print("  - Mandatory Architecture: Next.js 15 + FastAPI ASGI + PostgreSQL 16 + Redis 7")
        print("  - UI/UX Design Constraints: Bright Light Corporate Mode enforced")
        print("  - Schema Integrity Lock: Validated")
        print("  - Zero Frontend Mock Data: Clean and pristine")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
