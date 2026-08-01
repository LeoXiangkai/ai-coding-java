#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil
import stat
import subprocess
import sys
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ["pre-commit", "pre-push"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install ai-coding-java lightweight git hooks into a target repository.")
    parser.add_argument("target", nargs="?", default=".", help="Target project directory")
    parser.add_argument("--force", action="store_true", help="Reinstall even when an ai-coding-java hook exists")
    return parser.parse_args()


def git_root(target: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def marker(hook_name: str) -> str:
    return f"ai-coding-java {hook_name}"


def wrapper_text(hook_name: str, hook_path: Path, previous_path: Path | None) -> str:
    lines = [
        "#!/usr/bin/env sh",
        f"# {marker(hook_name)}",
        'ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"',
        "code=0",
        f'if [ -n "$ROOT" ] && [ -x "$ROOT/.ai-coding-java/hooks/{hook_name}" ]; then',
        f'  "$ROOT/.ai-coding-java/hooks/{hook_name}"',
        "  code=$?",
        f'elif [ -x "{hook_path}" ]; then',
        f'  "{hook_path}"',
        "  code=$?",
        "else",
        f'  echo "ai-coding-java {hook_name}: source hook not found, skip" >&2',
        "fi",
        'if [ "$code" -ne 0 ]; then',
        '  exit "$code"',
        "fi",
    ]
    if previous_path is not None:
        lines.extend(
            [
                f'PREV="{previous_path}"',
                'if [ -x "$PREV" ]; then',
                '  "$PREV"',
                "  exit $?",
                "fi",
            ]
        )
    lines.append("exit 0")
    lines.append("")
    return "\n".join(lines)


def install_one(root: Path, hooks_dir: Path, hook_name: str, force: bool) -> int:
    source_hook = root / ".ai-coding-java" / "hooks" / hook_name
    if not source_hook.is_file():
        source_hook = ROOT / "hooks" / hook_name
    if not source_hook.is_file():
        print(f"FAIL missing ai-coding-java {hook_name} hook under {root} or {ROOT}", file=sys.stderr)
        return 1

    make_executable(source_hook)
    target_hook = hooks_dir / hook_name
    previous_path: Path | None = None

    if target_hook.exists():
        text = target_hook.read_text(encoding="utf-8", errors="ignore")
        if marker(hook_name) in text:
            if not force:
                print(f"OK git hook already installed {target_hook}")
                return 0
            target_hook.unlink()
        else:
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            previous_path = hooks_dir / f"{hook_name}.before-ai-coding-java.{stamp}"
            shutil.move(str(target_hook), str(previous_path))
            make_executable(previous_path)
            print(f"OK preserved existing {hook_name} as {previous_path}")

    target_hook.write_text(wrapper_text(hook_name, source_hook, previous_path), encoding="utf-8")
    make_executable(target_hook)
    print(f"OK installed ai-coding-java {hook_name} hook {target_hook}")
    return 0


def install(root: Path, force: bool) -> int:
    git_dir = root / ".git"
    if not git_dir.exists():
        print(f"SKIP git hooks: {root} has no .git directory")
        return 0

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    for hook_name in HOOKS:
        if install_one(root, hooks_dir, hook_name, force) != 0:
            failed = True
    return 1 if failed else 0


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    root = git_root(target)
    if root is None:
        print(f"SKIP git hooks: {target} is not inside a git repository")
        return 0
    return install(root, args.force)


if __name__ == "__main__":
    sys.exit(main())
