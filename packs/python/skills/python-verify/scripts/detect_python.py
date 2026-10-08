#!/usr/bin/env python3
"""Detect Python project conventions with only the standard library."""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - supported runtimes have tomllib
    tomllib = None


TOOLS = ("ruff", "mypy", "pyright", "pytest")
FRAMEWORKS = ("fastapi", "flask", "django")
ORM_ORDER = ("sqlalchemy", "django-orm", "tortoise", "peewee")


def empty_result() -> dict[str, Any]:
    return {
        "package_manager": "unknown",
        "python_requires": None,
        "frameworks": [],
        "orm": [],
        "migrations": None,
        "pydantic_major": None,
        "tools": {name: False for name in TOOLS},
        "entry": None,
        "commands": {"lint": "MISSING", "format_check": "MISSING", "type_check": "MISSING", "test": "MISSING", "start": "MISSING"},
    }


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def load_pyproject(path: Path) -> dict[str, Any]:
    if tomllib is None or not path.is_file():
        return {}
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def requirement_name(raw: str) -> tuple[str, str | None] | None:
    text = raw.strip()
    if not text or text.startswith(("#", "-r", "--", "-e", ".", "git+", "http:" , "https:")):
        return None
    text = text.split(";", 1)[0].strip()
    match = re.match(r"([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[^]]+\])?\s*(.*)$", text)
    if not match:
        return None
    return match.group(1).lower().replace("-", "_"), match.group(2).strip() or None


def dependency_data(root: Path, project: dict[str, Any]) -> tuple[set[str], dict[str, str | None], bool]:
    names: set[str] = set()
    versions: dict[str, str | None] = {}
    has_manifest = False

    def add(name: str, version: str | None = None) -> None:
        key = name.lower().replace("-", "_")
        names.add(key)
        if version is not None:
            versions[key] = str(version)

    section = project.get("project")
    if isinstance(section, dict):
        has_manifest = True
        reqs = section.get("dependencies", [])
        if isinstance(reqs, list):
            for raw in reqs:
                parsed = requirement_name(str(raw))
                if parsed:
                    add(parsed[0], parsed[1])
        optional = section.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for values in optional.values():
                if isinstance(values, list):
                    for raw in values:
                        parsed = requirement_name(str(raw))
                        if parsed:
                            add(parsed[0], parsed[1])
    tool = project.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            has_manifest = True
            deps = poetry.get("dependencies", {})
            if isinstance(deps, dict):
                for name, value in deps.items():
                    if name.lower() != "python":
                        add(str(name), str(value) if value is not None else None)
            groups = poetry.get("group", {})
            if isinstance(groups, dict):
                for group in groups.values():
                    if isinstance(group, dict) and isinstance(group.get("dependencies"), dict):
                        for name, value in group["dependencies"].items():
                            add(str(name), str(value) if value is not None else None)
        groups = project.get("dependency-groups")
        if isinstance(groups, dict):
            has_manifest = True
            for values in groups.values():
                if isinstance(values, list):
                    for raw in values:
                        parsed = requirement_name(str(raw))
                        if parsed:
                            add(parsed[0], parsed[1])
    for path in sorted(root.glob("requirements*.txt")):
        has_manifest = True
        for line in read(path).splitlines():
            parsed = requirement_name(line)
            if parsed:
                add(parsed[0], parsed[1])
    for filename in ("setup.py", "setup.cfg"):
        path = root / filename
        if path.is_file():
            has_manifest = True
            for raw in re.findall(r"['\"]([A-Za-z][A-Za-z0-9_.-]*(?:[<>=!~]=?[^'\", ]+)?)['\"]", read(path)):
                parsed = requirement_name(raw)
                if parsed:
                    add(parsed[0], parsed[1])
    return names, versions, has_manifest


def has_tool(name: str, root: Path, project: dict[str, Any], dependencies: set[str]) -> bool:
    if name in dependencies:
        return True
    tool = project.get("tool")
    if isinstance(tool, dict) and name in tool:
        return True
    config_files = {"ruff": ("ruff.toml", ".ruff.toml"), "mypy": ("mypy.ini",), "pyright": ("pyrightconfig.json",), "pytest": ("pytest.ini", "tox.ini", "setup.cfg")}
    return any((root / filename).is_file() for filename in config_files[name])


def version_major(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(?<!\d)([12])(?:\.\d+)?", value)
    return int(match.group(1)) if match else None


def guess_entry(root: Path, frameworks: list[str]) -> str | None:
    candidates: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*.py")):
        relative_parts = path.relative_to(root).parts
        if any(part in {".git", ".venv", "venv", "__pycache__", "tests", "test"} for part in relative_parts):
            continue
        source = read(path)
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imported.update(alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module for alias in [ast.alias(name=node.module)])
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call) or not isinstance(node.value.func, ast.Name):
                continue
            kind = node.value.func.id.lower()
            if kind not in {"fastapi", "flask"}:
                continue
            if kind == "fastapi" and "fastapi" not in imported:
                continue
            if kind == "flask" and "flask" not in imported:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module = path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
                    candidates.append((module, target.id, kind))
    for preferred in frameworks:
        for module, variable, kind in candidates:
            if kind == preferred:
                return f"{module}:{variable}"
    return None


def main(argv: list[str] | None = None) -> int:
    root = Path((argv or sys.argv[1:] or ["."])[0]).expanduser().resolve()
    result = empty_result()
    project_path = root / "pyproject.toml"
    project = load_pyproject(project_path)
    dependencies, versions, has_manifest = dependency_data(root, project)
    # A pyproject with only tool configuration still selects the pip-style
    # command prefix when no lockfile or Poetry metadata is present.
    has_manifest = has_manifest or project_path.is_file()
    if (root / "uv.lock").is_file():
        result["package_manager"] = "uv"
    elif (root / "poetry.lock").is_file() or isinstance(project.get("tool"), dict) and isinstance(project["tool"].get("poetry"), dict):
        result["package_manager"] = "poetry"
    elif has_manifest:
        result["package_manager"] = "pip"

    section = project.get("project")
    if isinstance(section, dict) and isinstance(section.get("requires-python"), str):
        result["python_requires"] = section["requires-python"]
    else:
        poetry = project.get("tool", {}).get("poetry", {}) if isinstance(project.get("tool"), dict) else {}
        py_req = poetry.get("dependencies", {}).get("python") if isinstance(poetry, dict) and isinstance(poetry.get("dependencies"), dict) else None
        result["python_requires"] = str(py_req) if py_req else None

    result["frameworks"] = [name for name in FRAMEWORKS if name in dependencies]
    if "django" in dependencies:
        result["orm"].append("django-orm")
    result["orm"].extend(name for name in ORM_ORDER if name != "django-orm" and name in dependencies)
    if "alembic" in dependencies:
        result["migrations"] = "alembic"
    elif "django" in dependencies:
        result["migrations"] = "django"
    result["pydantic_major"] = version_major(versions.get("pydantic"))
    result["tools"] = {name: has_tool(name, root, project, dependencies) for name in TOOLS}
    result["entry"] = guess_entry(root, result["frameworks"])

    manager = result["package_manager"]
    prefix = {"uv": "uv run", "poetry": "poetry run", "pip": "python -m"}.get(manager)
    if prefix:
        if result["tools"]["ruff"]:
            result["commands"]["lint"] = f"{prefix} ruff check ."
            result["commands"]["format_check"] = f"{prefix} ruff format --check ."
        if result["tools"]["mypy"]:
            result["commands"]["type_check"] = f"{prefix} mypy ."
        elif result["tools"]["pyright"]:
            result["commands"]["type_check"] = f"{prefix} pyright"
        if result["tools"]["pytest"]:
            result["commands"]["test"] = f"{prefix} pytest"
        entry = result["entry"]
        if entry and "fastapi" in result["frameworks"]:
            result["commands"]["start"] = f"{prefix} uvicorn {entry}"
        elif entry and "flask" in result["frameworks"]:
            result["commands"]["start"] = f"{prefix} flask --app {entry} run"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
