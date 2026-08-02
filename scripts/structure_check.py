#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRS = ["docs", "rules", "workflow", "templates", "scripts", "hooks", "artifacts", "knowledge", "examples"]
ROOT_FILES = {"README.md", "AGENTS.md", "CLAUDE.md", "TOOL.md", "USAGE.md"}
KEBAB_MD = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
SNAKE_PY = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*\.py$")
HOOK_NAMES = {"pre-commit", "pre-push"}
IGNORED_TRACKED_PREFIXES = (
    ".omx/logs/",
    ".omx/state/",
    ".omx/knowledge-candidates/",
    ".Codex/",
)
IGNORED_TRACKED_FILES = {".omx/notepad.md", ".omx/metrics.json"}


def ok(message: str) -> None:
    print(f"OK {message}")


def fail(message: str) -> None:
    print(f"FAIL {message}")


def warn(message: str) -> None:
    print(f"WARN {message}")


def git_source_files() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        warn("not a git repository; source-file checks skipped")
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_kebab_md(path: Path) -> bool:
    return bool(KEBAB_MD.match(path.name))


def check_docs_like(rel: str, path: Path) -> int:
    if path.name == "README.md":
        return 0
    if path.suffix != ".md":
        fail(f"{rel} should be Markdown")
        return 1
    if not is_kebab_md(path):
        fail(f"{rel} should use kebab-case Markdown naming")
        return 1
    ok(f"name {rel}")
    return 0


def main() -> int:
    failed = 0

    for directory in REQUIRED_DIRS:
        if (ROOT / directory).is_dir():
            ok(f"directory {directory}/")
        else:
            fail(f"missing directory {directory}/")
            failed += 1

    for rel in git_source_files():
        path = ROOT / rel
        if any(rel.startswith(prefix) for prefix in IGNORED_TRACKED_PREFIXES) or rel in IGNORED_TRACKED_FILES:
            fail(f"tracked runtime artifact {rel}")
            failed += 1
            continue

        parts = Path(rel).parts
        if len(parts) == 1:
            if path.name in ROOT_FILES or path.name in {".gitignore", ".claudeignore", ".gitattributes"}:
                ok(f"root file {rel}")
            continue

        top = parts[0]
        if top == "docs":
            failed += check_docs_like(rel, path)
        elif top == "rules":
            failed += check_docs_like(rel, path)
        elif top == "workflow":
            failed += check_docs_like(rel, path)
        elif top == "templates":
            if not path.name.endswith("-template.md"):
                fail(f"{rel} should end with -template.md")
                failed += 1
            elif not is_kebab_md(path):
                fail(f"{rel} should use kebab-case Markdown naming")
                failed += 1
            else:
                ok(f"name {rel}")
        elif top == "scripts":
            if not SNAKE_PY.match(path.name):
                fail(f"{rel} should use snake_case .py naming")
                failed += 1
            else:
                ok(f"name {rel}")
        elif top == "hooks":
            if path.name not in HOOK_NAMES:
                fail(f"{rel} should use a known Git hook name")
                failed += 1
            else:
                ok(f"name {rel}")
        elif top == "artifacts":
            if path.name != "README.md":
                failed += check_docs_like(rel, path)
            else:
                ok(f"name {rel}")
        elif top == "knowledge":
            if path.name != "README.md":
                failed += check_docs_like(rel, path)
            else:
                ok(f"name {rel}")

    print(f"Summary: {failed} structure issue(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
