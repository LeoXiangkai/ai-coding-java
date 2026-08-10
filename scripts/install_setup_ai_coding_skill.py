#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "setup-ai-coding"
SOURCE_DIR = ROOT / "skills" / SKILL_NAME
SOURCE = SOURCE_DIR / "SKILL.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Link the project-bundled setup-ai-coding skill into global skill directories."
    )
    parser.add_argument("--agents-skills-dir", default="~/.agents/skills", help="Codex/agents skill root")
    parser.add_argument("--claude-skills-dir", default="~/.claude/skills", help="Claude Code skill root")
    parser.add_argument("--skip-claude-link", action="store_true", help="Do not create the Claude Code skill symlink")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing different skill file or link")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files")
    return parser.parse_args()


def link_skill(skill_root: Path, force: bool, dry_run: bool) -> None:
    link_path = skill_root / SKILL_NAME
    if link_path.is_symlink() and link_path.readlink() == SOURCE_DIR:
        print(f"OK existing skill link {link_path} -> {SOURCE_DIR}")
        return
    if link_path.exists() or link_path.is_symlink():
        if not force:
            raise SystemExit(f"FAIL existing skill path: {link_path}; rerun with --force to replace")
        if dry_run:
            print(f"DRY-RUN replace {link_path} with symlink to {SOURCE_DIR}")
            return
        if link_path.is_dir() and not link_path.is_symlink():
            shutil.rmtree(link_path)
        else:
            link_path.unlink()
    if dry_run:
        print(f"DRY-RUN symlink {link_path} -> {SOURCE_DIR}")
        return
    skill_root.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(SOURCE_DIR, target_is_directory=True)
    print(f"OK linked {link_path} -> {SOURCE_DIR}")


def main() -> int:
    args = parse_args()
    if not SOURCE.is_file():
        print(f"FAIL missing bundled skill source: {SOURCE}", file=sys.stderr)
        return 1
    agents_dir = Path(args.agents_skills_dir).expanduser().resolve()
    claude_dir = Path(args.claude_skills_dir).expanduser().resolve()
    link_skill(agents_dir, args.force, args.dry_run)
    if not args.skip_claude_link:
        link_skill(claude_dir, args.force, args.dry_run)
    print("OK setup-ai-coding global entries point to the project-bundled source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
