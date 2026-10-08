from __future__ import annotations

import json

import pytest

from adapter_helpers import CAPTURE_HOOK, RECALL_HOOK, run_hook


@pytest.fixture()
def claude(tmp_path):
    return tmp_path / ".claude"


def write_cards(claude, *cards, raw=()):
    path = claude / "aicj" / "lessons" / "cards.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(c, ensure_ascii=False) for c in cards] + list(raw)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def card(cid="c1", **over):
    base = {"id": cid, "scope": "global", "trigger": {"tools": ["Bash"], "cmd_regex": r"rm\s+-rf"},
            "lesson": "不要递归强删", "level": "hint", "status": "active", "created": "2026-01-01"}
    base.update(over)
    return base


def bash(cmd, session="s1", cwd="/work/proj"):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "session_id": session, "cwd": cwd}


def context(result):
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


# ---- lesson-recall ----

def test_cmd_regex_match_injects_json(claude):
    write_cards(claude, card())
    result = run_hook(RECALL_HOOK, bash("rm -rf build"), claude)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert context(result) == "[lesson:c1] 不要递归强删"


def test_no_match_no_output(claude):
    write_cards(claude, card())
    result = run_hook(RECALL_HOOK, bash("ls -la"), claude)
    assert result.returncode == 0 and result.stdout == ""


def test_missing_cards_file_is_silent(claude):
    result = run_hook(RECALL_HOOK, bash("rm -rf x"), claude)
    assert result.returncode == 0 and result.stdout == ""


def test_same_session_injects_once_other_session_again(claude):
    write_cards(claude, card())
    assert "[lesson:c1]" in run_hook(RECALL_HOOK, bash("rm -rf a", session="s1"), claude).stdout
    assert run_hook(RECALL_HOOK, bash("rm -rf b", session="s1"), claude).stdout == ""
    assert "[lesson:c1]" in run_hook(RECALL_HOOK, bash("rm -rf c", session="s2"), claude).stdout
    assert (claude / "aicj" / "state" / "lesson-recall").is_dir()


def test_scope_mismatch_not_injected_and_match_injected(claude):
    write_cards(claude, card(scope="/work/other"))
    assert run_hook(RECALL_HOOK, bash("rm -rf a", cwd="/work/proj"), claude).stdout == ""
    assert "[lesson:c1]" in run_hook(RECALL_HOOK, bash("rm -rf a", cwd="/work/other/sub", session="s9"), claude).stdout


def test_retired_card_not_injected(claude):
    write_cards(claude, card(status="retired"))
    assert run_hook(RECALL_HOOK, bash("rm -rf a"), claude).stdout == ""


def test_path_glob_for_edit_tools(claude):
    write_cards(claude, card("g1", trigger={"tools": ["Edit", "Write"], "path_glob": "*.sql"}, lesson="SQL 需评审"))
    hit = {"tool_name": "Edit", "tool_input": {"file_path": "/p/db/a.sql"}, "session_id": "s1", "cwd": "/p"}
    miss = {"tool_name": "Edit", "tool_input": {"file_path": "/p/db/a.py"}, "session_id": "s1", "cwd": "/p"}
    assert context(run_hook(RECALL_HOOK, hit, claude)) == "[lesson:g1] SQL 需评审"
    assert run_hook(RECALL_HOOK, miss, claude).stdout == ""


def test_tool_not_in_trigger_not_injected(claude):
    write_cards(claude, card())
    payload = {"tool_name": "Write", "tool_input": {"file_path": "rm -rf"}, "session_id": "s1"}
    assert run_hook(RECALL_HOOK, payload, claude).stdout == ""


def test_block_level_in_block_mode_exits_2_with_lesson(claude):
    write_cards(claude, card(level="block"))
    result = run_hook(RECALL_HOOK, bash("rm -rf a"), claude, mode="block")
    assert result.returncode == 2
    assert "[lesson:c1] 不要递归强删" in result.stderr
    assert result.stdout == ""


def test_block_level_in_warn_mode_downgrades_to_injection(claude):
    write_cards(claude, card(level="block"))
    result = run_hook(RECALL_HOOK, bash("rm -rf a"), claude, mode="warn")
    assert result.returncode == 0
    assert "[lesson:c1]" in context(result)


def test_bad_lines_and_bad_regex_do_not_crash_and_good_card_still_fires(claude):
    bad_regex = card("bad", trigger={"tools": ["Bash"], "cmd_regex": "(unclosed"})
    write_cards(claude, bad_regex, card("good"), raw=["{not json", "5", '{"id": "x", "trigger": 3}', ""])
    result = run_hook(RECALL_HOOK, bash("rm -rf a"), claude, mode="block")
    assert result.returncode == 0
    assert context(result) == "[lesson:good] 不要递归强删"
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("bad", ["", "not json", "[]", '{"tool_name": "Bash", "tool_input": 1}'])
def test_bad_event_fails_open(claude, bad):
    write_cards(claude, card())
    result = run_hook(RECALL_HOOK, bad, claude, mode="block")
    assert result.returncode == 0 and "Traceback" not in result.stderr


# ---- lesson-capture ----

def corrections(claude):
    path = claude / "aicj" / "lessons" / "corrections.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def submit(claude, prompt, session="s1"):
    return run_hook(CAPTURE_HOOK, {"prompt": prompt, "session_id": session, "cwd": "/work/proj"}, claude)


def test_correction_sentence_recorded(claude):
    result = submit(claude, "你刚才写的字段名不对，应该是 userId 而不是 uid")
    assert result.returncode == 0 and result.stdout == ""
    rows = corrections(claude)
    assert len(rows) == 1
    assert rows[0]["session_id"] == "s1" and rows[0]["cwd"] == "/work/proj"
    assert "userId" in rows[0]["prompt"] and rows[0]["ts"].endswith("Z")


def test_long_correction_truncated_to_2000(claude):
    submit(claude, "你刚才写的接口不对" + "x" * 3000)
    assert len(corrections(claude)[0]["prompt"]) == 2000


def test_worry_sentence_not_recorded(claude):
    submit(claude, "你直接改，我怕改错了")
    assert corrections(claude) == []


def test_worry_with_explicit_blame_still_recorded(claude):
    submit(claude, "我怕改错了，而且你刚才改错了接口")
    assert len(corrections(claude)) == 1


def test_ordinary_sentence_not_recorded(claude):
    submit(claude, "请帮我写一个分页查询")
    assert corrections(claude) == []


@pytest.mark.parametrize("prompt", [
    "<task-notification>子代理回报：接口不对</task-notification>",
    "子代理回报：刚才的接口不对，应该是 A 而不是 B",
    "Task: 你刚才写的字段不对",
    "你刚才的结论不对" + "。" * 5000,
])
def test_machine_generated_prompts_not_recorded(claude, prompt):
    submit(claude, prompt)
    assert corrections(claude) == []


@pytest.mark.parametrize("bad", ["", "not json", "[]", '{"prompt": 5}'])
def test_capture_bad_input_exits_0_silently(claude, bad):
    result = run_hook(CAPTURE_HOOK, bad, claude)
    assert result.returncode == 0 and result.stdout == "" and "Traceback" not in result.stderr


def test_appends_without_truncating(claude):
    submit(claude, "你刚才写的接口不对")
    submit(claude, "你刚才写的字段不对")
    assert len(corrections(claude)) == 2
