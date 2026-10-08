"""Coverage for skills shipped in core: frontmatter shape and reference integrity."""
from __future__ import annotations

import re
from pathlib import Path

from conftest import REPO

CORE = REPO / "core"
SKILLS = CORE / "skills"
# Categories whose markdown may cross-reference each other by rules/refs/agents paths.
LINK_DIRS = ("rules", "refs", "agents", "skills")
# Only core markdown files link by these relative paths; templates is checked by
# test_core_component.test_global_template_only_references_shipped_files.
LINK_RE = re.compile(r"(?<![\w/])((?:rules|refs|agents|skills)/[\w./-]+\.(?:md))\b")


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    out: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def test_every_core_skill_has_matching_name_and_description() -> None:
    skills = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    assert skills, "core ships no skills"
    for skill in skills:
        doc = skill / "SKILL.md"
        assert doc.is_file(), f"{skill.name}: missing SKILL.md"
        meta = _frontmatter(doc)
        assert meta.get("name") == skill.name, f"{doc}: name must equal directory name"
        assert meta.get("description"), f"{doc}: description must not be empty"


def test_core_markdown_internal_references_resolve() -> None:
    docs = [p for d in LINK_DIRS for p in (CORE / d).rglob("*.md")]
    assert docs, "core has no markdown to check"
    broken: list[str] = []
    for path in docs:
        text = path.read_text(encoding="utf-8")
        for ref in LINK_RE.findall(text):
            # resolve like a markdown reader: relative to the referencing file
            # first (skill-local rules/*.md), then against the core root.
            local = (path.parent / ref).resolve()
            if not local.is_file() and not (CORE / ref).is_file():
                broken.append(f"{path.relative_to(REPO)} -> {ref}")
    assert broken == [], "broken core references:\n" + "\n".join(broken)
