from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXECUTOR = REPO / "adapters" / "executor"
LESSON = REPO / "adapters" / "lesson"
POLL_HOOK = EXECUTOR / "hooks" / "block-handoff-poll.py"
WORKER = EXECUTOR / "bin" / "aicj-worker"
RECALL_HOOK = LESSON / "hooks" / "lesson-recall.py"
CAPTURE_HOOK = LESSON / "hooks" / "lesson-capture.py"
LESSON_BIN = LESSON / "bin" / "aicj-lesson"


def fake_command(directory: Path, name: str, body: str) -> Path:
    """Create a PATH command that works with both POSIX shebangs and Windows .cmd."""
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        script = directory / f"{name}.py"
        script.write_text(body, encoding="utf-8")
        command = directory / f"{name}.cmd"
        command.write_text(f'@"{sys.executable}" "%~dp0{name}.py" %*\r\n', encoding="utf-8")
        return command
    command = directory / name
    command.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    command.chmod(0o755)
    return command


def run_script(script: Path, *args: str, stdin: str | None = None, claude: Path, mode: str | None = None,
               env_extra: dict[str, str] | None = None, path: str | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICJ_")}
    env["AICJ_CLAUDE_DIR"] = str(claude)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if mode:
        env["AICJ_HOOK_MODE"] = mode
    if path is not None:
        env["PATH"] = path
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(script), *args], input=stdin, capture_output=True, text=True, encoding="utf-8", env=env)


def run_hook(script: Path, payload: object, claude: Path, mode: str | None = None) -> subprocess.CompletedProcess:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return run_script(script, stdin=text, claude=claude, mode=mode)
