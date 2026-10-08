#!/usr/bin/env python3
"""Deterministic Python static checks using the standard library."""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".idea", ".vscode", ".omx", "__pycache__", ".venv", "venv", "dist", "build"}
SECRET_NAME = re.compile(r"(?:password|passwd|secret|token|api[_-]?key)", re.I)


def add(findings, level, path, line, message):
    findings.append((level, str(path), line, message))


def line_no(text: str, node_or_index) -> int:
    index = node_or_index if isinstance(node_or_index, int) else getattr(node_or_index, "lineno", 1)
    return text.count("\n", 0, index) + 1 if isinstance(index, int) and index > len(text) else (index if isinstance(index, int) else 1)


def files(paths):
    seen = set()
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            continue
        candidates = [path] if path.is_file() else path.rglob("*.py")
        for item in candidates:
            if item.is_file() and item.suffix == ".py" and not any(part in SKIP_DIRS for part in item.parts) and item not in seen:
                seen.add(item)
                yield item


def source_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def only_noop(body) -> bool:
    return all(isinstance(node, (ast.Pass, ast.Expr)) and (isinstance(node, ast.Pass) or isinstance(getattr(node, "value", None), (ast.Constant, ast.Ellipsis))) for node in body)


def is_suspicious_sql(node: ast.AST, tainted: set[str]) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return True
    if isinstance(node, ast.Name) and node.id in tainted:
        return True
    return any(is_suspicious_sql(child, tainted) for child in ast.iter_child_nodes(node))


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def inside_with_open(tree: ast.AST) -> set[int]:
    protected: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.With):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and call_name(child) == "open":
                protected.add(id(child))
    return protected


def is_test_file(path: Path) -> bool:
    if path.name.startswith("test_"):
        return True
    if "tests" in path.parts:
        marker = next((parent / ".static-review-fixture" for parent in [path.parent, *path.parents]), None)
        return not marker or not marker.is_file()
    return False


def check(path: Path, findings) -> None:
    text = source_text(path)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        add(findings, "P1", path, exc.lineno or 1, "parse failed")
        return
    tainted: set[str] = set()
    protected = inside_with_open(tree)
    # Collect SQL-bearing assignments before checking calls so source order
    # cannot make an equivalent execute(query) form escape review.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not is_suspicious_sql(value, set()):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        tainted.update(target.id for target in targets if isinstance(target, ast.Name))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                names = [target.id] if isinstance(target, ast.Name) else []
                if any(SECRET_NAME.search(name) for name in names) and isinstance(value, ast.Constant) and isinstance(value.value, str) and len(value.value) >= 8:
                    add(findings, "P0", path, node.lineno, "possible plaintext secret")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_defaults = [*node.args.defaults, *(value for value in node.args.kw_defaults if value is not None)]
            for default in all_defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    add(findings, "P1", path, default.lineno, "mutable default argument")
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                add(findings, "P1", path, node.lineno, "bare except")
            elif isinstance(node.type, (ast.Name, ast.Tuple)):
                names = {item.id for item in (node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]) if isinstance(item, ast.Name)}
                if names & {"Exception", "BaseException"} and only_noop(node.body):
                    add(findings, "P1", path, node.lineno, "exception handler swallows")
        if isinstance(node, ast.Call):
            name = call_name(node)
            if name in {"execute", "executemany", "text"} and any(is_suspicious_sql(arg, tainted) for arg in node.args):
                add(findings, "P0", path, node.lineno, "SQL string construction")
            if name == "open" and id(node) not in protected:
                add(findings, "P1", path, node.lineno, "open() should be used inside with")
            if name == "print" and not is_test_file(path):
                add(findings, "P1", path, node.lineno, "print() in non-test code")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Python static review")
    parser.add_argument("paths", nargs="*", default=["."])
    args = parser.parse_args(argv)
    selected = list(files(args.paths))
    findings = []
    for path in selected:
        check(path, findings)
    findings.sort(key=lambda row: (row[1], row[2], row[0], row[3]))
    print(f"Scanned files: {len(selected)}")
    if not findings:
        print("No P0/P1 deterministic findings.")
        return 0
    for level, path, line, message in findings:
        print(f"{level} {path}:{line} {message}")
    print(f"Findings: {len(findings)} (P0={sum(level == 'P0' for level, *_ in findings)}, P1={sum(level == 'P1' for level, *_ in findings)})")
    return 1 if any(level == "P0" for level, *_ in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
