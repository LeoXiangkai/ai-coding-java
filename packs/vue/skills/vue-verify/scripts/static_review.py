#!/usr/bin/env python3
"""Deterministic Vue/TypeScript static checks using the standard library."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

EXTENSIONS = {".vue", ".ts", ".tsx", ".js", ".jsx"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", "coverage"}
FIXTURE_MARKER = ".static-review-fixture"
SECRET_NAME = r"(?:password|secret|token|apiKey|api_key)"
SECRET_RE = re.compile(
    rf"(?i)(?:\b{SECRET_NAME}\b|[.\[]\s*['\"]?{SECRET_NAME}['\"]?\s*[])]?)\s*[:=]\s*(['\"])(?P<value>.*?)\1"
)
TAG_RE = re.compile(r"<(?P<tag>[A-Za-z][\w:.-]*)(?P<attrs>[^<>]*?)>", re.S)


def add(findings, level, path, line, message):
    findings.append((level, str(path), line, message))


def line_no(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def fixture_dir(path: Path) -> bool:
    return (path / FIXTURE_MARKER).is_file()


def files(paths):
    seen = set()
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            continue
        if path.is_file():
            candidates = [path]
        else:
            candidates = []
            for root, dirs, names in os.walk(path):
                root_path = Path(root)
                dirs[:] = [
                    name
                    for name in dirs
                    if name not in SKIP_DIRS and not fixture_dir(root_path / name)
                ]
                if fixture_dir(root_path):
                    dirs[:] = []
                    continue
                candidates.extend(root_path / name for name in names)
        for item in candidates:
            if (
                item.is_file()
                and item.suffix in EXTENSIONS
                and not any(part in SKIP_DIRS for part in item.parts)
                and item not in seen
            ):
                seen.add(item)
                yield item


def source_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def check(path: Path, findings) -> None:
    text = source_text(path)
    for match in SECRET_RE.finditer(text):
        value = match.group("value")
        if value and "import.meta.env" not in value and "process.env" not in value:
            add(findings, "P0", path, line_no(text, match.start()), "possible plaintext secret")

    for match in re.finditer(r"\bv-html\b", text):
        add(findings, "P1", path, line_no(text, match.start()), "v-html may create an XSS risk")
    for match in re.finditer(r"\beval\s*\(|\bnew\s+Function\s*\(", text):
        add(findings, "P1", path, line_no(text, match.start()), "dynamic code execution")

    for tag in TAG_RE.finditer(text):
        attrs = tag.group("attrs")
        if re.search(r"\bv-for\s*=", attrs) and not re.search(r"(?::key|v-bind:key)\s*=", attrs):
            add(findings, "P1", path, line_no(text, tag.start()), "v-for should define a key")
        if re.search(r"\bv-if\s*=", attrs) and re.search(r"\bv-for\s*=", attrs):
            add(findings, "P2", path, line_no(text, tag.start()), "v-if and v-for should not share a tag")

    for match in re.finditer(r"\bconsole\.log\s*\(|\bdebugger\b", text):
        add(findings, "P2", path, line_no(text, match.start()), "debug output or debugger statement")
    for match in re.finditer(r"(?::\s*any\b|\bas\s+any\b|<any>)", text):
        add(findings, "P2", path, line_no(text, match.start()), "explicit TypeScript any")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Vue static review")
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
    print(
        f"Findings: {len(findings)} "
        f"(P0={sum(level == 'P0' for level, *_ in findings)}, "
        f"P1={sum(level == 'P1' for level, *_ in findings)}, "
        f"P2={sum(level == 'P2' for level, *_ in findings)})"
    )
    return 2 if any(level == "P0" for level, *_ in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
