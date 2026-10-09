from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def claude_dir() -> Path:
    value = os.environ.get("AICJ_CLAUDE_DIR")
    if value:
        return Path(value).expanduser().resolve()
    script = Path(os.path.abspath(sys.argv[0]))
    if script.parent.name == "aicj" and script.parent.parent.name == "hooks":
        return script.parents[2]
    return Path(__file__).resolve().parents[2]


def hook_mode() -> str:
    value = os.environ.get("AICJ_HOOK_MODE")
    if value is not None and value.strip():
        return value.strip().lower()
    try:
        data = json.loads((claude_dir() / "aicj" / "config.json").read_text(encoding="utf-8"))
        configured = data.get("hook_mode") if isinstance(data, dict) else None
        if isinstance(configured, str) and configured.strip():
            return configured.strip().lower()
    except (OSError, ValueError, TypeError):
        pass
    return "warn"
