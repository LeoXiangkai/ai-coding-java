#!/usr/bin/env python3
"""Fixture hook: honours AICJ_HOOK_MODE and always allows the action."""
import os
import sys


def main() -> int:
    mode = os.environ.get("AICJ_HOOK_MODE", "warn").strip().lower()
    if mode == "block":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
