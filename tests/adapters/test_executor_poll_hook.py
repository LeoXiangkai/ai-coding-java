from __future__ import annotations

import pytest

from adapter_helpers import POLL_HOOK, run_hook


@pytest.fixture()
def claude(tmp_path):
    return tmp_path / ".claude"


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "session_id": "s1"}


def task(task_id, session="s1", tool="TaskOutput"):
    return {"tool_name": tool, "tool_input": {"task_id": task_id}, "session_id": session}


# hook input text only; nothing here ever sleeps
POLL_CMD = "sleep 30 && cat /tmp/x/tasks/abc123.output"


def test_sleep_plus_task_output_warns_in_warn_mode(claude):
    result = run_hook(POLL_HOOK, bash(POLL_CMD), claude, mode="warn")
    assert result.returncode == 0
    assert "轮询" in result.stderr
    assert "Traceback" not in result.stderr


def test_default_mode_is_warn(claude):
    assert run_hook(POLL_HOOK, bash(POLL_CMD), claude).returncode == 0


def test_sleep_plus_task_output_blocks_in_block_mode(claude):
    result = run_hook(POLL_HOOK, bash(POLL_CMD), claude, mode="block")
    assert result.returncode == 2
    assert "轮询" in result.stderr


def test_plain_sleep_is_allowed(claude):
    for mode in ("warn", "block"):
        result = run_hook(POLL_HOOK, bash("sleep 5 && echo done"), claude, mode=mode)
        assert result.returncode == 0 and result.stderr == ""


def test_reading_output_without_sleep_is_allowed(claude):
    result = run_hook(POLL_HOOK, bash("tail -n 20 /tmp/x/tasks/abc.output"), claude, mode="block")
    assert result.returncode == 0 and result.stderr == ""


def test_sleep_inside_prose_is_not_a_sleep_command(claude):
    result = run_hook(POLL_HOOK, bash("echo please sleep 5 now /tasks/ .output"), claude, mode="block")
    assert result.returncode == 0


def test_task_output_first_query_allowed_second_flagged(claude):
    assert run_hook(POLL_HOOK, task("t1"), claude, mode="block").returncode == 0
    second = run_hook(POLL_HOOK, task("t1"), claude, mode="block")
    assert second.returncode == 2
    assert "重复查询" in second.stderr
    assert (claude / "aicj" / "state" / "handoff-poll-seen").is_dir()


def test_second_query_warn_mode_allows_with_hint(claude):
    run_hook(POLL_HOOK, task("t1", tool="BashOutput"), claude, mode="warn")
    second = run_hook(POLL_HOOK, task("t1", tool="BashOutput"), claude, mode="warn")
    assert second.returncode == 0
    assert "重复查询" in second.stderr


def test_other_session_or_other_task_is_allowed(claude):
    run_hook(POLL_HOOK, task("t1", session="s1"), claude, mode="block")
    assert run_hook(POLL_HOOK, task("t1", session="s2"), claude, mode="block").returncode == 0
    assert run_hook(POLL_HOOK, task("t2", session="s1"), claude, mode="block").returncode == 0


@pytest.mark.parametrize("bad", ["not json", "", "[]", "null", '{"tool_name": "Bash", "tool_input": "x"}'])
def test_bad_input_fails_open_without_traceback(claude, bad):
    result = run_hook(POLL_HOOK, bad, claude, mode="block")
    assert result.returncode == 0
    assert "Traceback" not in result.stderr


def test_sleep_followed_by_separator_without_space_blocks(claude):
    for cmd in ("sleep 30; tail /tmp/x/tasks/abc.output", "sleep 5m&&cat /tmp/x/tasks/a.output", "(sleep 2)|cat /tmp/x/tasks/a.output"):
        result = run_hook(POLL_HOOK, bash(cmd), claude, mode="block")
        assert result.returncode == 2, cmd
