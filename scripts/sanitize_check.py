#!/usr/bin/env python3
"""Scan distributable component directories for personal or secret material.

Extra banned regexes come from the file named by AICJ_SANITIZE_EXTRA (one regex
per line; blank lines and lines starting with '#' are ignored).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("core", "packs", "adapters", "installer")

BUILTIN_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("personal-abs-path", re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home)/[A-Za-z0-9._-]+(?:/|\b)")),
    ("personal-win-path", re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9._-]+")),
    # ~/.claude and ~/.codex style config dirs are documented on purpose; a visible ~/<workspace>/ is personal
    (
        "personal-home-dir",
        re.compile(
            r"(?<![A-Za-z0-9_.~])~/(?!(?:path|dir|project|projects|workspace|repo|code|src|your[A-Za-z0-9_-]*)/)"
            r"[A-Za-z0-9][A-Za-z0-9_-]*/"
        ),
    ),
    ("loopback-port", re.compile(r"127\.0\.0\.1:\d+")),
    ("private-executor", re.compile(r"worker-cc")),
    ("secret-key-sk", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("secret-key-ghp", re.compile(r"\bghp_[A-Za-z0-9]{20,}")),
    ("secret-key-akia", re.compile(r"\bAKIA[0-9A-Z]{12,}")),
    (
        "secret-token-assign",
        re.compile(
            r"\b[A-Za-z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY)[\"']?\s*[=:]\s*[\"']?(?![$<{\[(])[^\s\"',;}]{8,}"
        ),
    ),
    ("secret-private-key", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
]

PATH_EXEMPTIONS: dict[str, set[str]] = {
    "adapters/executor/examples/": {"private-executor"},
}


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    name: str
    text: str


def load_extra(path: str | None) -> list[tuple[str, re.Pattern]]:
    if not path:
        return []
    file = Path(os.path.expanduser(path))
    try:
        raw = file.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot read AICJ_SANITIZE_EXTRA {file}: {exc}")
    out: list[tuple[str, re.Pattern]] = []
    for number, line in enumerate(raw.splitlines(), start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            out.append((f"extra:{number}", re.compile(text)))
        except re.error as exc:
            raise SystemExit(f"invalid regex in {file} line {number}: {exc}")
    return out


def is_exempt(rel: str, name: str, exemptions: dict[str, set[str]]) -> bool:
    return any(rel.startswith(prefix) and name in names for prefix, names in exemptions.items())


def scan(
    root: Path, patterns: list[tuple[str, re.Pattern]], exemptions: dict[str, set[str]]
) -> tuple[list[Hit], list[str]]:
    hits: list[Hit] = []
    warnings: list[str] = []
    for base in SCAN_DIRS:
        directory = root / base
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(root).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                warnings.append(f"{rel}: not valid UTF-8, not scanned")
                continue
            except OSError as exc:
                warnings.append(f"{rel}: unreadable ({exc}), not scanned")
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                for name, pattern in patterns:
                    if is_exempt(rel, name, exemptions):
                        continue
                    if pattern.search(line):
                        hits.append(Hit(rel, number, name, line.strip()[:120]))
    return hits, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="scan component dirs for personal or secret material")
    parser.add_argument("--root", default=str(ROOT), help="repository root to scan")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    patterns = BUILTIN_PATTERNS + load_extra(os.environ.get("AICJ_SANITIZE_EXTRA"))
    hits, warnings = scan(root, patterns, PATH_EXEMPTIONS)
    for warning in warnings:
        print(f"WARN {warning}")
    for hit in hits:
        print(f"FAIL {hit.path}:{hit.line}: {hit.name}: {hit.text}")
    print(f"Summary: {len(hits)} sanitize issue(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
