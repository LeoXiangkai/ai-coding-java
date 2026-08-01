#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
COPY_DIRS = ["docs", "rules", "workflow", "templates", "knowledge", "artifacts", "hooks"]
COPY_FILES = ["README.md", "TOOL.md", "USAGE.md"]
TARGET_SCRIPTS = ["static_review_check.py", "extract_knowledge_candidate.py", "install_git_hooks.py"]
AGENTS_MARKER_START = "<!-- ai-coding-java:AGENTS:START -->"
AGENTS_MARKER_END = "<!-- ai-coding-java:AGENTS:END -->"
CLAUDE_MARKER_START = "<!-- ai-coding-java:CLAUDE:START -->"
CLAUDE_MARKER_END = "<!-- ai-coding-java:CLAUDE:END -->"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize a target project with a lightweight .ai-coding-java template package."
    )
    parser.add_argument("target", help="Target project directory")
    parser.add_argument("--project-type", default="unconfirmed", choices=["new", "legacy", "maintenance", "unconfirmed"])
    parser.add_argument("--stack", default="unconfirmed", help="Confirmed technology stack or preset name")
    parser.add_argument("--verification-level", default="standard", choices=["lightweight", "standard", "strict"])
    parser.add_argument("--template-policy", default="local-auxiliary", choices=["local-auxiliary", "committed"])
    parser.add_argument("--data-boundary", default="unconfirmed", help="Tenant/org/school/year/etc. data boundary")
    parser.add_argument("--force", action="store_true", help="Overwrite existing .ai-coding-java files")
    return parser.parse_args()


def copy_path(src: Path, dst: Path, force: bool) -> None:
    if dst.exists() and not force:
        print(f"SKIP exists {dst.relative_to(dst.parents[1])}")
        return
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"OK copied {src.relative_to(ROOT)} -> {dst}")


def write_text(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"SKIP exists {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"OK wrote {path}")


def upsert_marked_block(path: Path, start: str, end: str, body: str) -> None:
    block = f"{start}\n{body.rstrip()}\n{end}\n"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        start_index = text.find(start)
        end_index = text.find(end)
        if start_index >= 0 and end_index >= start_index:
            replacement_end = end_index + len(end)
            new_text = text[:start_index] + block.rstrip() + text[replacement_end:]
            if not new_text.endswith("\n"):
                new_text += "\n"
            path.write_text(new_text, encoding="utf-8")
            print(f"OK updated marker block {path}")
            return
        separator = "" if text.endswith("\n") else "\n"
        path.write_text(f"{text}{separator}\n{block}", encoding="utf-8")
        print(f"OK appended marker block {path}")
        return
    path.write_text(f"# {path.name.replace('.md', '')}\n\n{block}", encoding="utf-8")
    print(f"OK created {path}")


def install_git_hooks(target: Path) -> None:
    installer = target / ".ai-coding-java" / "scripts" / "install_git_hooks.py"
    if not installer.is_file():
        print(f"SKIP git hooks missing installer {installer}")
        return
    result = subprocess.run([sys.executable, str(installer), str(target)], text=True, capture_output=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)


def profile_text(args: argparse.Namespace) -> str:
    return f"""# ai-coding-java Project Profile

Project type: {args.project_type}
Technology stack: {args.stack}
Verification level: {args.verification_level}
Template policy: {args.template_policy}
Data boundary: {args.data_boundary}

## Required Confirmation

- Build command:
- Test command:
- Start command:
- Database:
- Cache:
- External systems:
- API verification method:
- P1 waiver owner and record path:
- RD artifact policy: local-only / committed-after-review / not-used
- Hook mode: warn / strict

## Notes

- Project `AGENTS.md` and business rules override generic ai-coding-java suggestions.
- Keep this profile free of secrets and long logs.
"""


def agents_snippet(args: argparse.Namespace) -> str:
    return f"""## ai-coding-java

Use `.ai-coding-java/docs/rule-index.md` as the first ai-coding-java routing file.

Project profile: `.ai-coding-java/project-profile.md`

Global runtime skills remain owned by Codex, Claude Code, or OMX. ai-coding-java provides project-side Java rules, verification, review, and delivery templates.

Confirmed setup:

- Project type: {args.project_type}
- Technology stack: {args.stack}
- Verification level: {args.verification_level}
- Template policy: {args.template_policy}
- Data boundary: {args.data_boundary}

Loading order:

1. This `AGENTS.md`
2. User task
3. Project memory/current task notes
4. `.ai-coding-java/docs/rule-index.md`
5. Only matched `.ai-coding-java/rules/`, `workflow/`, `templates/`, `knowledge/`, or `artifacts/` files
6. Relevant code, tests, config, and history

Project business rules, data isolation, environment commands, and API contracts in this `AGENTS.md` override generic ai-coding-java suggestions.

Target-safe helper scripts are under `.ai-coding-java/scripts/`.
"""


def claude_snippet(args: argparse.Namespace) -> str:
    return f"""## ai-coding-java

Use `.ai-coding-java/docs/rule-index.md` as the first ai-coding-java routing file for Java development rules.

Project profile: `.ai-coding-java/project-profile.md`

Global runtime skills remain owned by Codex, Claude Code, or OMX. ai-coding-java provides project-side Java rules, verification, review, and delivery templates.

Confirmed setup:

- Project type: {args.project_type}
- Technology stack: {args.stack}
- Verification level: {args.verification_level}
- Template policy: {args.template_policy}
- Data boundary: {args.data_boundary}

Claude Code loading guidance:

1. Read this `CLAUDE.md`.
2. Read the nearest `AGENTS.md` for Codex-compatible project execution rules when present.
3. Read `.ai-coding-java/docs/rule-index.md`.
4. Load only matched `.ai-coding-java/rules/`, `workflow/`, `templates/`, `knowledge/`, or `artifacts/` files.
5. Use `.ai-coding-java/docs/verification-matrix.md` before claiming completion.

Project business rules, data isolation, environment commands, and API contracts in this `CLAUDE.md` or `AGENTS.md` override generic ai-coding-java suggestions.

Target-safe helper scripts are under `.ai-coding-java/scripts/`.
"""


def agents_pointer() -> str:
    return """## ai-coding-java

Use `.ai-coding-java/docs/rule-index.md` as the first ai-coding-java routing file.
Project profile: `.ai-coding-java/project-profile.md`.
Global runtime skills remain owned by Codex, Claude Code, or OMX.

Load only matched `.ai-coding-java/rules/`, `workflow/`, `templates/`, `knowledge/`, or `artifacts/` files. Project rules in this `AGENTS.md` override generic ai-coding-java suggestions.
"""


def claude_pointer() -> str:
    return """## ai-coding-java

Use `.ai-coding-java/docs/rule-index.md` as the first ai-coding-java routing file for Java development rules.
Read `AGENTS.md` for Codex-compatible execution rules when present.
Use `.ai-coding-java/docs/verification-matrix.md` before claiming completion.
Global runtime skills remain owned by Codex, Claude Code, or OMX.
"""


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        print(f"FAIL target directory does not exist: {target}", file=sys.stderr)
        return 1

    dest = target / ".ai-coding-java"
    dest.mkdir(exist_ok=True)

    for rel in COPY_DIRS:
        copy_path(ROOT / rel, dest / rel, args.force)
    for rel in COPY_FILES:
        copy_path(ROOT / rel, dest / rel, args.force)
    for rel in TARGET_SCRIPTS:
        copy_path(ROOT / "scripts" / rel, dest / "scripts" / rel, args.force)

    write_text(dest / "project-profile.md", profile_text(args), args.force)
    write_text(dest / "AGENTS.ai-coding-java-snippet.md", agents_snippet(args), args.force)
    write_text(dest / "CLAUDE.ai-coding-java-snippet.md", claude_snippet(args), args.force)

    upsert_marked_block(target / "AGENTS.md", AGENTS_MARKER_START, AGENTS_MARKER_END, agents_pointer())
    upsert_marked_block(target / "CLAUDE.md", CLAUDE_MARKER_START, CLAUDE_MARKER_END, claude_pointer())
    install_git_hooks(target)

    print("\nNext steps:")
    print("1. Review .ai-coding-java/project-profile.md and fill missing commands.")
    print("2. Review the marker blocks added to AGENTS.md and CLAUDE.md.")
    print("3. Confirm .git/hooks/pre-commit and .git/hooks/pre-push were installed when the target is a git repository.")
    print("4. Run .ai-coding-java/scripts/static_review_check.py when deterministic review is needed outside commit flow.")
    print("5. Use .ai-coding-java/artifacts/<work-id>/ only when RD process records are useful.")
    print("6. Decide whether .ai-coding-java/ stays local-only or is committed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
