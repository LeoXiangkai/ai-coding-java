#!/usr/bin/env python3
"""Fixture hook: honours AICJ_HOOK_MODE / aicj/config.json and always allows the action."""
import json
import os
import sys
from pathlib import Path


def main() -> int:
    mode = os.environ.get("AICJ_HOOK_MODE", "").strip().lower()
    if not mode:
        config = Path(__file__).resolve().parents[2] / "aicj" / "config.json"
        try:
            mode = str(json.loads(config.read_text(encoding="utf-8")).get("hook_mode", "warn")).strip().lower()
        except (OSError, ValueError, AttributeError):
            mode = "warn"
    if mode == "block":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
