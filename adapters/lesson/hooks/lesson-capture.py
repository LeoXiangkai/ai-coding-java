#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

SIGNAL = re.compile(r"(?:刚才|这里|你|前面|上面|之前|接口|字段|文档|代码|结论|提示语|返回|message).*(?:不对|错了|写错|搞错|弄错|偏差|不正确|风格不对|拼写错|名字错)|(?:应该是|应改为|应当是).*(?:不是|而不是|而非)|你(?:说|写|做|加|改|提)的?.*(?:不对|错|偏差|应该)|纠正(?:一下|下)?[:：，,]?|(?:再核|再查|重新核对|重新检查).*(?:不对|错|偏差)", re.I)
WORRY = re.compile(r"(?:怕|别|不要|担心|万一|以免|防止|避免)[^，。,.!?！？\n]{0,6}错")
BLAME = re.compile(r"(?:刚才|你)(?:已经)?.{0,4}(?:改|写|弄|搞|做|说)错")
MACHINE_PREFIXES = ("Task:", "You are analyzing", "You are running as", "子代理回报", "任务回报", "外部执行体回报", "摘要模板", "跨会话消息")
MACHINE_MAX_LEN = 4000


def is_machine_prompt(prompt: str) -> bool:
    """Tool-generated text (summary templates, sub-agent reports, cross-session messages) is not a user correction."""
    text = prompt.strip()
    return text.startswith("<") or len(text) > MACHINE_MAX_LEN or text.startswith(MACHINE_PREFIXES)


def root() -> Path:
    value = os.environ.get("AICJ_CLAUDE_DIR")
    if value:
        return Path(value).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def main() -> int:
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(data, dict):
            return 0
        prompt = data.get("prompt") or data.get("user_prompt") or ""
        if not isinstance(prompt, str) or not prompt or not SIGNAL.search(prompt):
            return 0
        if WORRY.search(prompt) and not BLAME.search(prompt):
            return 0
        if is_machine_prompt(prompt):
            return 0
        target = root() / "aicj" / "lessons" / "corrections.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "session_id": str(data.get("session_id") or data.get("sessionId") or ""), "cwd": str(data.get("cwd") or os.getcwd()), "prompt": prompt[:2000]}
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # never block or disturb a prompt submission; a lost capture is acceptable
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
