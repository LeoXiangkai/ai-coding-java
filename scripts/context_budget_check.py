#!/usr/bin/env python3
from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
LIMITS = {
    "AGENTS.md": 5 * 1024,
    "CLAUDE.md": 8 * 1024,
    ".omx/notepad.md": 5 * 1024,
    ".omx/project-memory.json": 10 * 1024,
}


def size(path: Path) -> int:
    return path.stat().st_size if path.exists() else -1


def main() -> int:
    failed = False
    for rel, limit in LIMITS.items():
        path = ROOT / rel
        actual = size(path)
        if actual < 0:
            print(f"MISS {rel}")
            failed = True
            continue
        status = "OK" if actual <= limit else "OVER"
        print(f"{status} {rel} {actual}/{limit} bytes")
        failed = failed or status == "OVER"

    memory_path = ROOT / ".omx/project-memory.json"
    try:
        json.loads(memory_path.read_text(encoding="utf-8"))
        print("OK .omx/project-memory.json valid JSON")
    except Exception as exc:
        print(f"FAIL .omx/project-memory.json invalid JSON: {exc}")
        failed = True

    logs_path = ROOT / ".omx/logs"
    if logs_path.exists():
        total = sum(p.stat().st_size for p in logs_path.rglob("*") if p.is_file())
        print(f"INFO .omx/logs {total} bytes, excluded from startup context")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

