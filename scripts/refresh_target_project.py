#!/usr/bin/env python3
from pathlib import Path
import argparse
import filecmp
import shutil
import sys


DEFAULT_SOURCE = Path(__file__).resolve().parents[1]
COPY_DIRS = ["docs", "rules", "workflow", "templates", "knowledge", "artifacts", "hooks"]
COPY_FILES = ["README.md", "TOOL.md", "USAGE.md"]
TARGET_SCRIPTS = [
    "static_review_check.py",
    "extract_knowledge_candidate.py",
    "install_git_hooks.py",
    "check_target_project.py",
    "artifact_consistency_check.py",
    "docs_tone_check.py",
    "evidence_check.py",
    "generate_project_map.py",
    "refresh_target_project.py",
]
IGNORED_NAMES = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
GENERATED_TARGET_FILES = {
    Path("project-profile.md"),
    Path("AGENTS.ai-coding-java-snippet.md"),
    Path("CLAUDE.ai-coding-java-snippet.md"),
    Path("project-map.md"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare or refresh a target project's .ai-coding-java files without touching business code."
    )
    parser.add_argument("target", help="Target project directory")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="ai-coding-java source component directory")
    parser.add_argument("--apply", action="store_true", help="Copy missing/changed component files into the target")
    parser.add_argument("--list-extra", action="store_true", help="List target files that are not present in this component")
    return parser.parse_args()


def iter_sources(source: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for directory in COPY_DIRS:
        base = source / directory
        for path in sorted(base.rglob("*")):
            if any(part in IGNORED_NAMES for part in path.parts) or path.suffix in IGNORED_SUFFIXES:
                continue
            if path.is_file():
                pairs.append((path, Path(directory) / path.relative_to(base)))
    for filename in COPY_FILES:
        pairs.append((source / filename, Path(filename)))
    for filename in TARGET_SCRIPTS:
        pairs.append((source / "scripts" / filename, Path("scripts") / filename))
    return pairs


def same_file(src: Path, dst: Path) -> bool:
    return dst.is_file() and filecmp.cmp(src, dst, shallow=False)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def list_extra_files(target_component: Path, expected: set[Path]) -> int:
    count = 0
    for path in sorted(target_component.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(target_component)
        if rel.parts and rel.parts[0] == "reports":
            continue
        if rel in GENERATED_TARGET_FILES:
            continue
        if rel not in expected:
            print(f"EXTRA target-only .ai-coding-java/{rel}")
            count += 1
    return count


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"FAIL target directory does not exist: {target}", file=sys.stderr)
        return 1
    source = Path(args.source).expanduser().resolve()
    if not (source / "docs" / "rule-index.md").is_file():
        print(f"FAIL source does not look like ai-coding-java: {source}", file=sys.stderr)
        return 1

    target_component = target / ".ai-coding-java"
    if not target_component.is_dir():
        print(f"FAIL missing target component directory: {target_component}", file=sys.stderr)
        return 1

    changed = 0
    missing = 0
    copied = 0
    expected: set[Path] = set()

    print(f"Checking refresh plan: {target_component}")
    print(f"Source: {source}")
    print("Mode: apply" if args.apply else "Mode: dry-run")

    for src, rel in iter_sources(source):
        expected.add(rel)
        dst = target_component / rel
        if not dst.exists():
            missing += 1
            print(f"MISS .ai-coding-java/{rel}")
            if args.apply:
                copy_file(src, dst)
                copied += 1
            continue
        if not same_file(src, dst):
            changed += 1
            print(f"DIFF .ai-coding-java/{rel}")
            if args.apply:
                copy_file(src, dst)
                copied += 1
            continue
        print(f"OK .ai-coding-java/{rel}")

    extra = list_extra_files(target_component, expected) if args.list_extra else 0
    print(f"Summary: {missing} missing, {changed} changed, {extra} extra, {copied} copied")
    if missing or changed:
        return 0 if args.apply else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
