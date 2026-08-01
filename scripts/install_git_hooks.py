#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil
import stat
import subprocess
import sys
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
MARKER = "ai-coding-java pre-commit"


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


def wrapper_text(hook_path: Path, previous_path: Path | None) -> str:
    lines = [
        "#!/usr/bin/env sh",
        f"# {MARKER}",
        'ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"',
        'if [ -n "$ROOT" ] && [ -x "$ROOT/.ai-coding-java/hooks/pre-commit" ]; then',
        '  "$ROOT/.ai-coding-java/hooks/pre-commit"',
        f'elif [ -x "{hook_path}" ]; then',
        f'  "{hook_path}"',
        "else",
        "  exit 0",
        "fi",
        "  code=$?",
        "  if [ \"$code\" -ne 0 ]; then",
        "    exit \"$code\"",
        "  fi",
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


def install(root: Path, force: bool) -> int:
    git_dir = root / ".git"
    hooks_dir = git_dir / "hooks"
    source_hook = root / ".ai-coding-java" / "hooks" / "pre-commit"
    if not source_hook.is_file():
        source_hook = ROOT / "hooks" / "pre-commit"
    if not git_dir.exists():
        print(f"SKIP git hooks: {root} has no .git directory")
        return 0
    if not source_hook.is_file():
        print(f"FAIL missing ai-coding-java pre-commit hook under {root} or {ROOT}", file=sys.stderr)
        return 1

    hooks_dir.mkdir(parents=True, exist_ok=True)
    make_executable(source_hook)

    target_hook = hooks_dir / "pre-commit"
    previous_path: Path | None = None

    if target_hook.exists():
        text = target_hook.read_text(encoding="utf-8", errors="ignore")
        if MARKER in text:
            if not force:
                print(f"OK git hook already installed {target_hook}")
                return 0
            target_hook.unlink()
        else:
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            previous_path = hooks_dir / f"pre-commit.before-ai-coding-java.{stamp}"
            shutil.move(str(target_hook), str(previous_path))
            make_executable(previous_path)
            print(f"OK preserved existing pre-commit as {previous_path}")

    target_hook.write_text(wrapper_text(source_hook, previous_path), encoding="utf-8")
    make_executable(target_hook)
    print(f"OK installed ai-coding-java pre-commit hook {target_hook}")
    return 0


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
