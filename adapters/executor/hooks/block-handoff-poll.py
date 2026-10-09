#!/usr/bin/env python3
"""Fail-open poll guard for repeated handoff status checks."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from hook_mode import hook_mode
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core" / "hooks"))
    from hook_mode import hook_mode

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def claude_dir() -> Path:
    value = os.environ.get("AICJ_CLAUDE_DIR")
    if value:
        return Path(value).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def mode() -> str:
    return hook_mode()


def warn(message: str) -> int:
    if mode() == "block":
        sys.stderr.write(message + "\n")
        return 2
    sys.stderr.write("[block-handoff-poll] AICJ_HOOK_MODE=warn，本次放行；请等待外部执行体自然回报。\n" + message + "\n")
    return 0


def payload() -> dict:
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:  # fail-open: unparsable input is allowed through
        return {}
    return data if isinstance(data, dict) else {}


def bash_poll(command: object) -> bool:
    if not isinstance(command, str):
        return False
    # sleep must be a standalone command; a quoted fragment or sleepiness in prose is ignored.
    sleep = re.compile(r"(?:^|[;&|()\n])\s*sleep\s+[0-9]+(?:\.[0-9]+)?[smhd]?(?=[\s;&|)]|$)")
    return bool(sleep.search(command) and "/tasks/" in command and ".output" in command)


def task_poll(data: dict) -> tuple[bool, str]:
    tool = str(data.get("tool_name", ""))
    if tool not in {"TaskOutput", "BashOutput"}:
        return False, ""
    inp = data.get("tool_input")
    if not isinstance(inp, dict):
        return False, ""
    task_id = inp.get("task_id") or inp.get("taskId") or inp.get("id")
    session = data.get("session_id") or data.get("sessionId") or "default"
    if not isinstance(task_id, str) or not task_id.strip():
        return False, ""
    return True, f"{session}:{task_id.strip()}"


def seen_twice(key: str) -> bool:
    directory = claude_dir() / "aicj" / "state" / "handoff-poll-seen"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for item in directory.iterdir():
            try:
                if datetime.fromtimestamp(item.stat().st_mtime, timezone.utc) < cutoff:
                    item.unlink()
            except OSError:
                continue
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
        path = directory / safe
        count = int(path.read_text(encoding="utf-8").strip() or "0") if path.exists() else 0
        path.write_text(str(count + 1), encoding="utf-8")
        return count >= 1
    except Exception:  # fail-open: state file problems must never block a tool call
        return False


def main() -> int:
    data = payload()
    tool = str(data.get("tool_name", ""))
    if tool == "Bash":
        inp = data.get("tool_input")
        command = inp.get("command") if isinstance(inp, dict) else None
        if bash_poll(command):
            return warn("检测到可能的轮询命令，请改为等待外部执行体回报或一次性确认状态。")
    is_task, key = task_poll(data)
    if is_task and seen_twice(key):
        return warn("同一会话对同一任务已重复查询，请停止轮询并等待回报。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # fail-open: never surface a traceback from the hook
        raise SystemExit(0)
