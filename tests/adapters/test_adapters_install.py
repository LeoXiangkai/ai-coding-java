from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

from adapter_helpers import (CAPTURE_HOOK, EXECUTOR, LESSON, POLL_HOOK, RECALL_HOOK, REPO, run_hook)
from conftest import files_under, run_aicj

ORIGINAL_SETTINGS = {"theme": "dark", "hooks": {"PreToolUse": [{"matcher": "Read", "hooks": [{"type": "command", "command": "echo mine"}]}]}}
ADAPTER_FILES = [
    ".claude/refs/executor-contract.md",
    ".claude/skills/executor-handoff-ops/SKILL.md",
    ".claude/hooks/aicj/block-handoff-poll.py",
    ".claude/bin/aicj-worker",
    ".claude/refs/lesson-loop.md",
    ".claude/hooks/aicj/lesson-recall.py",
    ".claude/hooks/aicj/lesson-capture.py",
    ".claude/bin/aicj-lesson",
]


@pytest.fixture()
def seeded_home(home):
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps(ORIGINAL_SETTINGS, indent=2) + "\n", encoding="utf-8")
    return home


def adapter_commands(home):
    data = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    rows = []
    for event, groups in data["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                args = hook.get("args") or []
                locations = [hook.get("command", ""), *args]
                if any("/hooks/aicj/" in value.replace("\\", "/") for value in locations) and re.search(
                    r"(block-handoff-poll|lesson-)", " ".join(locations)
                ):
                    rows.append((event, group.get("matcher"), hook["command"], args))
    return rows


def test_install_places_files_and_registers_hooks(seeded_home):
    home = seeded_home
    result = run_aicj("install", "--adapters", "executor,lesson", home=home, source=None)
    assert result.returncode == 0, result.stdout + result.stderr
    for rel in ADAPTER_FILES:
        assert (home / rel).is_file(), rel
    rows = adapter_commands(home)
    assert sorted((event, matcher) for event, matcher, _, _ in rows) == [
        ("PreToolUse", "Bash"),
        ("PreToolUse", "Bash|Edit|Write|MultiEdit"),
        ("PreToolUse", "TaskOutput|BashOutput"),
        ("UserPromptSubmit", None),
    ]
    assert all(any("/hooks/aicj/" in value.replace("\\", "/") for value in [cmd, *args]) for _, _, cmd, args in rows)
    assert all(args and "/hooks/aicj/" in args[0].replace("\\", "/") for _, _, _, args in rows)
    assert "MISSING" not in run_aicj("doctor", home=home, source=None).stdout


def test_strict_prefixes_only_blocking_hooks(seeded_home):
    home = seeded_home
    assert run_aicj("install", "--adapters", "executor,lesson", "--strict", home=home, source=None).returncode == 0
    rows = adapter_commands(home)
    assert all(cmd == os.path.abspath(sys.executable) for _, _, cmd, _ in rows)
    assert json.loads((home / ".claude/aicj/config.json").read_text(encoding="utf-8")) == {"hook_mode": "block"}


def test_doctor_has_no_missing_and_default_install_excludes_adapters(home):
    assert run_aicj("install", home=home, source=None).returncode == 0
    assert not (home / ".claude" / "bin" / "aicj-worker").exists()
    assert run_aicj("install", "--adapters", "executor,lesson", home=home, source=None).returncode == 0
    doctor = run_aicj("doctor", home=home, source=None)
    assert doctor.returncode == 0 and "MISSING" not in doctor.stdout + doctor.stderr


def test_uninstall_removes_state_keeps_lessons_and_restores_settings(seeded_home):
    home = seeded_home
    claude = home / ".claude"
    before = (claude / "settings.json").read_bytes()
    assert run_aicj("install", "--adapters", "executor,lesson", home=home, source=None).returncode == 0

    # exercise the installed hooks so runtime state and lesson data appear
    cards = claude / "aicj" / "lessons" / "cards.jsonl"
    cards.parent.mkdir(parents=True, exist_ok=True)
    cards.write_text(json.dumps({"id": "c1", "scope": "global", "trigger": {"tools": ["Bash"], "cmd_regex": "rm"},
                                 "lesson": "l", "level": "hint", "status": "active", "created": "2026-01-01"}) + "\n",
                     encoding="utf-8")
    run_hook(RECALL_HOOK, {"tool_name": "Bash", "tool_input": {"command": "rm x"}, "session_id": "s"}, claude)
    run_hook(POLL_HOOK, {"tool_name": "TaskOutput", "tool_input": {"task_id": "t"}, "session_id": "s"}, claude)
    run_hook(CAPTURE_HOOK, {"prompt": "你刚才写的接口不对", "session_id": "s"}, claude)
    assert (claude / "aicj" / "state").is_dir()
    assert (claude / "aicj" / "lessons" / "corrections.jsonl").is_file()

    dry = run_aicj("uninstall", "--dry-run", home=home, source=None)
    assert dry.returncode == 0
    assert (claude / "aicj" / "state").is_dir(), "dry-run must not delete state"
    assert "保留的运行数据：.claude/aicj/lessons" in dry.stdout

    result = run_aicj("uninstall", home=home, source=None)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (claude / "aicj" / "state").exists()
    assert "保留的运行数据：.claude/aicj/lessons（可手动删除）" in result.stdout
    assert cards.is_file() and (claude / "aicj" / "lessons" / "corrections.jsonl").is_file()
    assert files_under(home) == [
        ".claude/aicj/lessons/cards.jsonl",
        ".claude/aicj/lessons/corrections.jsonl",
        ".claude/settings.json",
    ]
    assert (claude / "settings.json").read_bytes() == before


def test_uninstall_without_runtime_data_leaves_nothing_but_settings(seeded_home):
    home = seeded_home
    assert run_aicj("install", "--adapters", "executor,lesson", home=home, source=None).returncode == 0
    (home / ".claude" / "aicj" / "state").mkdir(parents=True, exist_ok=True)
    (home / ".claude" / "aicj" / "state" / "x").write_text("1", encoding="utf-8")
    result = run_aicj("uninstall", home=home, source=None)
    assert result.returncode == 0
    assert "保留的运行数据" not in result.stdout
    assert files_under(home) == [".claude/settings.json"]
    assert not (home / ".claude" / "aicj").exists()


FORBIDDEN = [
    ("personal path", re.compile(r"/Users/|~/\.claude|\.claude-worker|/home/\w+")),
    ("model name", re.compile(r"opus|sonnet|haiku|gpt-|claude-\d", re.I)),
    ("gateway/tool", re.compile(r"\bCPA\b|\bjq\b|127\.0\.0\.1|worker-cc|\bJEV\b", re.I)),
]


def adapter_text_files():
    return [p for root in (EXECUTOR, LESSON) for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]


def test_no_forbidden_terms_in_adapters():
    hits = []
    for path in adapter_text_files():
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN:
            for match in pattern.finditer(text):
                hits.append(f"{path.relative_to(REPO)}: {label}: {match.group(0)}")
    assert hits == []


def test_size_budgets_and_executable_bits():
    assert (EXECUTOR / "refs/executor-contract.md").stat().st_size <= 4096
    assert (LESSON / "refs/lesson-loop.md").stat().st_size <= 3072
    assert (EXECUTOR / "skills/executor-handoff-ops/SKILL.md").stat().st_size <= 12 * 1024
    for rel in ("executor/bin/aicj-worker", "lesson/bin/aicj-lesson"):
        path = REPO / "adapters" / rel
        assert path.stat().st_mode & 0o111
        assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")
    skill = (EXECUTOR / "skills/executor-handoff-ops/SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: executor-handoff-ops\ndescription: ")
