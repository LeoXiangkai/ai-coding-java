#!/usr/bin/env python3
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

README_FORBIDDEN = [
    "不支持：",
    "不负责：",
    "不能：",
    "不会：",
    "无：",
]

GLOBAL_PATTERNS = [
    (re.compile(r"\|\s*[^|]+\s*\|\s*不支持\s*\|"), "Use 范围外 or 由 X 负责 instead of table status 不支持"),
    (re.compile(r"(?m)^##\s+.*不支持"), "Use 边界 or 范围外 heading instead of 不支持 heading"),
]

REQUIRED_README_STATUS = ["已落地", "边界清晰", "后续增强"]


def fail(message: str) -> None:
    print(f"FAIL {message}")


def ok(message: str) -> None:
    print(f"OK {message}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def markdown_files() -> list[Path]:
    roots = [ROOT / "README.md", ROOT / "docs", ROOT / "rules", ROOT / "workflow", ROOT / "templates", ROOT / "artifacts", ROOT / "knowledge"]
    files: list[Path] = []
    for item in roots:
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            files.extend(sorted(item.rglob("*.md")))
    return files


def check_readme() -> int:
    path = ROOT / "README.md"
    text = read(path)
    failed = 0
    for token in README_FORBIDDEN:
        if token in text:
            fail(f"README.md contains reverse capability wording: {token}")
            failed += 1
    for token in REQUIRED_README_STATUS:
        if token not in text:
            fail(f"README.md missing positive status token: {token}")
            failed += 1
    if failed == 0:
        ok("README tone")
    return failed


def check_global_patterns() -> int:
    failed = 0
    for path in markdown_files():
        rel = path.relative_to(ROOT)
        text = read(path)
        for pattern, message in GLOBAL_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text[: match.start()].count("\n") + 1
                fail(f"{rel}:{line_no} {message}")
                failed += 1
    if failed == 0:
        ok("global tone patterns")
    return failed


def main() -> int:
    failed = 0
    failed += check_readme()
    failed += check_global_patterns()
    print(f"Summary: {failed} tone issue(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
