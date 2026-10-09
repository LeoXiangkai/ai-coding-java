from __future__ import annotations

import json

import pytest

from adapter_helpers import LESSON_BIN, run_script


@pytest.fixture()
def claude(tmp_path):
    return tmp_path / ".claude"


def cli(claude, *args):
    return run_script(LESSON_BIN, *args, claude=claude)


def add(claude, cid="k1", *extra):
    return cli(claude, "add", "--id", cid, "--lesson", "先备份再删除", "--tools", "Bash", *(extra or ("--cmd-regex", r"rm\s")))


def test_add_then_list_and_search_hit(claude):
    result = add(claude)
    assert result.returncode == 0
    listed = cli(claude, "list")
    row = json.loads(listed.stdout.strip())
    assert row["id"] == "k1" and row["status"] == "active" and row["level"] == "hint"
    assert row["scope"] == "global" and row["trigger"] == {"tools": ["Bash"], "cmd_regex": r"rm\s"}
    assert row["created"]
    found = cli(claude, "search", "先备份")
    assert found.returncode == 0 and "k1" in found.stdout
    assert cli(claude, "search", "不存在的词").stdout == ""


def test_search_is_or_and_case_insensitive_and_covers_other_sources(claude, tmp_path):
    add(claude, "Alpha")
    corr = claude / "aicj" / "lessons" / "corrections.jsonl"
    corr.write_text(json.dumps({"ts": "2026-01-01T00:00:00Z", "prompt": "needle in corrections"}) + "\n", encoding="utf-8")
    mem = claude / "projects" / "p1" / "memory" / "MEMORY.md"
    mem.parent.mkdir(parents=True)
    mem.write_text("- memory NEEDLE entry\n", encoding="utf-8")
    out = cli(claude, "search", "zzz-none", "needle", "alpha").stdout
    assert "corrections.jsonl" in out and "MEMORY.md" in out and "cards.jsonl" in out


def test_search_blank_keyword_rejected(claude):
    assert cli(claude, "search", " ").returncode == 2


def test_duplicate_id_fails_and_keeps_single_card(claude):
    assert add(claude).returncode == 0
    dup = add(claude)
    assert dup.returncode != 0 and "duplicate" in dup.stderr
    assert len(cli(claude, "list", "--all").stdout.strip().splitlines()) == 1


def test_bad_regex_fails_and_writes_nothing(claude):
    result = cli(claude, "add", "--id", "b1", "--lesson", "x", "--tools", "Bash", "--cmd-regex", "(unclosed")
    assert result.returncode != 0
    assert not (claude / "aicj" / "lessons" / "cards.jsonl").exists()


@pytest.mark.parametrize("extra", [
    [],
    ["--cmd-regex", "a", "--path-glob", "*.x"],
])
def test_add_requires_exactly_one_trigger(claude, extra):
    result = cli(claude, "add", "--id", "t1", "--lesson", "x", "--tools", "Bash", *extra)
    assert result.returncode != 0


def test_add_rejects_blank_id_lesson_and_tools(claude):
    assert cli(claude, "add", "--id", " ", "--lesson", "x", "--tools", "Bash", "--cmd-regex", "a").returncode != 0
    assert cli(claude, "add", "--id", "i", "--lesson", " ", "--tools", "Bash", "--cmd-regex", "a").returncode != 0
    assert cli(claude, "add", "--id", "i", "--lesson", "x", "--tools", " , ", "--cmd-regex", "a").returncode != 0


def test_path_glob_card_and_scope_level_options(claude):
    result = cli(claude, "add", "--id", "p1", "--lesson", "x", "--tools", "Edit,Write", "--path-glob", "*.sql",
                 "--scope", "/work/a", "--level", "block")
    assert result.returncode == 0
    row = json.loads(cli(claude, "list").stdout.strip())
    assert row["trigger"] == {"tools": ["Edit", "Write"], "path_glob": "*.sql"}
    assert row["scope"] == "/work/a" and row["level"] == "block"


def test_set_retire_hides_from_default_list_and_can_reactivate(claude):
    add(claude)
    assert cli(claude, "set", "k1", "--status", "retired").returncode == 0
    assert cli(claude, "list").stdout == ""
    assert json.loads(cli(claude, "list", "--all").stdout.strip())["status"] == "retired"
    assert cli(claude, "set", "k1", "--status", "active", "--level", "warn").returncode == 0
    row = json.loads(cli(claude, "list").stdout.strip())
    assert row["status"] == "active" and row["level"] == "warn"


def test_set_unknown_id_fails(claude):
    assert cli(claude, "set", "nope", "--status", "retired").returncode != 0


def test_corrections_since_filters_by_age(claude):
    path = claude / "aicj" / "lessons" / "corrections.jsonl"
    path.parent.mkdir(parents=True)
    rows = [{"ts": "2020-01-01T00:00:00Z", "prompt": "old"}, {"ts": "2999-01-01T00:00:00Z", "prompt": "new"}]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\nbroken\n", encoding="utf-8")
    out = cli(claude, "corrections", "--since", "7d").stdout
    assert "new" in out and "old" not in out
    assert cli(claude, "corrections", "--since", "abc").returncode == 2


def test_bad_lines_in_cards_survive_set(claude):
    add(claude)
    path = claude / "aicj" / "lessons" / "cards.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "garbage\n", encoding="utf-8")
    assert cli(claude, "set", "k1", "--status", "retired").returncode == 0


def test_installed_layout_derives_claude_dir_from_script_location(tmp_path):
    import shutil
    import subprocess
    import sys

    claude = tmp_path / "home" / ".claude"
    (claude / "hooks" / "aicj").mkdir(parents=True)
    (claude / "bin").mkdir()
    shutil.copy(LESSON_BIN, claude / "bin" / "aicj-lesson")
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "elsewhere"), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, str(claude / "bin" / "aicj-lesson"), "add", "--id", "loc", "--lesson", "x",
         "--tools", "Bash", "--cmd-regex", "a"],
        capture_output=True, text=True, encoding="utf-8", env=env)
    assert result.returncode == 0, result.stderr
    assert (claude / "aicj" / "lessons" / "cards.jsonl").is_file()
