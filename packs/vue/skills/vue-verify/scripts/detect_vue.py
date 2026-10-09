#!/usr/bin/env python3
"""Detect Vue project conventions using only the Python standard library."""
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

STATIC_REVIEW = Path(__file__).resolve().with_name("static_review.py")


def static_command() -> str:
    if sys.platform == "win32":
        return f'"{Path(sys.executable).resolve()}" "{STATIC_REVIEW}" <paths>'
    return f"python3 {shlex.quote(str(STATIC_REVIEW))} <paths>"


def parse_major(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.startswith(("npm:", "workspace:")):
        return None
    match = re.fullmatch(r"[~^]?([0-9]+)(?:\.[0-9]+)?(?:\.[0-9]+)?(?:[-+][0-9A-Za-z.-]+)?", value)
    if not match:
        return None
    major = int(match.group(1))
    return major if major in (2, 3) else None


def read_package(project: Path) -> dict:
    path = project / "package.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def valid_package(project: Path) -> bool:
    try:
        data = json.loads((project / "package.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(data, dict)


def dependency_map(package: dict) -> dict:
    result = {}
    for key in ("dependencies", "devDependencies"):
        section = package.get(key)
        if isinstance(section, dict):
            result.update({name: value for name, value in section.items() if isinstance(name, str)})
    return result


def package_manager(project: Path) -> str:
    for filename, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
        ("bun.lockb", "bun"),
        ("bun.lock", "bun"),
    ):
        if (project / filename).is_file():
            return manager
    return "npm"


def find_script(scripts: dict, candidates: tuple[str, ...], manager: str) -> str:
    for name in candidates:
        value = scripts.get(name)
        if isinstance(value, str) and value.strip():
            return f"{manager} run {name}"
    return "MISSING"


def detect(project: Path) -> dict:
    package = read_package(project)
    deps = dependency_map(package)
    manager = package_manager(project)
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    scripts = {
        "lint": find_script(scripts, ("lint",), manager),
        "type_check": find_script(scripts, ("type-check", "typecheck"), manager),
        "test": find_script(scripts, ("test:unit", "test"), manager),
        "build": find_script(scripts, ("build",), manager),
        "dev": find_script(scripts, ("dev", "serve"), manager),
    }
    names = set(deps)
    vue_major = parse_major(deps.get("vue"))
    if "vite" in names or "@vitejs/plugin-vue" in names:
        build_tool = "vite"
    elif "@vue/cli-service" in names:
        build_tool = "vue-cli"
    elif "webpack" in names or "webpack-cli" in names:
        build_tool = "webpack"
    else:
        build_tool = "unknown"
    ui_lib = [name for name in ("element-plus", "element-ui", "ant-design-vue", "vant", "naive-ui") if name in names]
    state = [name for name in ("pinia", "vuex") if name in names]
    if "vitest" in names:
        test_runner = "vitest"
    elif "jest" in names:
        test_runner = "jest"
    else:
        test_runner = None
    result = {
        "vue_major": vue_major,
        "build_tool": build_tool,
        "typescript": "typescript" in names,
        "ui_lib": ui_lib,
        "state": state,
        "test_runner": test_runner,
        "package_manager": manager,
        "scripts": scripts,
        "playwright": "@playwright/test" in names or "playwright" in names,
    }
    if valid_package(project):
        result["static"] = static_command()
    return result


def main(argv: list[str] | None = None) -> int:
    project = Path((argv or sys.argv[1:] or ["."])[0]).expanduser().resolve()
    print(json.dumps(detect(project), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
