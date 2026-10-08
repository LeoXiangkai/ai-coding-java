from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "USAGE.md",
    ROOT / "TOOL.md",
    ROOT / "docs/runtime-skill-boundary.md",
    ROOT / "skills/setup-ai-coding/SKILL.md",
]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PATH_RE = re.compile(r"`((?:core|packs|adapters|installer|docs|scripts|templates)/[^`]+)`")


def _relative_target(raw: str) -> str | None:
    target = raw.strip().split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    return target


def test_entry_document_markdown_links_resolve() -> None:
    failures: list[str] = []
    for document in DOCS:
        text = document.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            target = _relative_target(raw)
            if target is None:
                continue
            if not (document.parent / target).is_file():
                failures.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not failures, "missing markdown links: " + "; ".join(failures)


def test_entry_document_repo_paths_exist() -> None:
    failures: list[str] = []
    for document in DOCS:
        text = document.read_text(encoding="utf-8")
        for raw in PATH_RE.findall(text):
            if any(token in raw for token in ("<", ">", "*")):
                continue
            if not (ROOT / raw).exists():
                failures.append(f"{document.relative_to(ROOT)} -> {raw}")
    assert not failures, "missing repository paths: " + "; ".join(failures)


def test_readme_documents_required_install_flags() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for flag in ("--dry-run", "--home", "--link", "--strict", "--codex"):
        assert flag in text
