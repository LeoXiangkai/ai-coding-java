from __future__ import annotations

import json
import re
from pathlib import Path

from conftest import REPO, files_under, run_aicj

CORE = REPO / "core"
MD_DIRS = ("rules", "refs", "agents", "templates")

# Personal environment names that must not leak into distributable core files.
BANNED = re.compile(
    r"worker-cc|\bCPA\b|127\.0\.0\.1|claude-worker|enrollment|\bjev\b|jev-|\brtk\b|lessons-index"
    r"|haiku|sonnet|opus|block-handoff-poll|pre-warn|feedback-capture|rule-archive|Keychain",
    re.IGNORECASE,
)


def core_markdown() -> list[Path]:
    return sorted(p for d in MD_DIRS for p in (CORE / d).rglob("*.md"))


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    assert end != -1, f"{path}: unterminated frontmatter"
    out: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def test_manifest_registers_every_core_markdown_file() -> None:
    data = json.loads((CORE / "manifest.json").read_text(encoding="utf-8"))
    registered = {row["source"] for d in MD_DIRS for row in data["entries"][d]}
    on_disk = {p.relative_to(CORE).as_posix() for p in core_markdown()}
    assert on_disk, "core has no markdown files"
    assert registered == on_disk


def test_agents_have_required_frontmatter_and_no_model() -> None:
    agents = sorted((CORE / "agents").glob("*.md"))
    assert {p.stem for p in agents} == {"pm", "sa", "dev", "qa", "scanner"}
    for path in agents:
        meta = frontmatter(path)
        assert meta.get("name") == path.stem, path
        assert meta.get("description"), path
        assert meta.get("tools"), path
        assert "model" not in meta, path


def test_rules_have_description_frontmatter() -> None:
    for path in sorted((CORE / "rules").glob("*.md")):
        assert frontmatter(path).get("description"), path


def test_core_markdown_has_no_personal_environment_names() -> None:
    hits = []
    for path in core_markdown():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if BANNED.search(line):
                hits.append(f"{path.relative_to(REPO)}:{number}: {line.strip()[:100]}")
    assert hits == []


def test_global_template_within_size_budget() -> None:
    assert (CORE / "templates" / "CLAUDE.global.md").stat().st_size <= 9 * 1024


def test_global_template_only_references_shipped_files() -> None:
    text = (CORE / "templates" / "CLAUDE.global.md").read_text(encoding="utf-8")
    refs = set(re.findall(r"`((?:rules|refs)/[\w.-]+\.md)", text))
    assert refs
    missing = sorted(ref for ref in refs if not (CORE / ref).is_file())
    assert missing == []


def test_real_core_install_doctor_uninstall_leaves_no_residue(home: Path) -> None:
    result = run_aicj("install", home=home, source=REPO)
    assert result.returncode == 0, result.stdout + result.stderr
    for rel in (
        ".claude/rules/executor-handoff.md",
        ".claude/refs/git-policy.md",
        ".claude/agents/scanner.md",
        ".claude/aicj/CLAUDE.global.md",
        ".claude/skills/req-intake/SKILL.md",
        ".claude/skills/flow/SKILL.md",
    ):
        assert (home / rel).is_file(), rel
    assert "@aicj/CLAUDE.global.md" in (home / ".claude/CLAUDE.md").read_text(encoding="utf-8")

    result = run_aicj("doctor", home=home, source=None)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "MISSING" not in result.stdout

    result = run_aicj("uninstall", home=home, source=None)
    assert result.returncode == 0, result.stdout + result.stderr
    assert files_under(home) == []
