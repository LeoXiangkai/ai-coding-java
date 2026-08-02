#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone


REQUIRED_FILES = [
    ".ai-coding-java/docs/rule-index.md",
    ".ai-coding-java/docs/verification-matrix.md",
    ".ai-coding-java/docs/design-first-policy.md",
    ".ai-coding-java/docs/testing-workflow.md",
    ".ai-coding-java/docs/tdd-policy.md",
    ".ai-coding-java/docs/project-harness.md",
    ".ai-coding-java/docs/runtime-skill-boundary.md",
    ".ai-coding-java/workflow/agent-workflow.md",
    ".ai-coding-java/templates/delivery-report-template.md",
    ".ai-coding-java/templates/requirement-brief-template.md",
    ".ai-coding-java/templates/requirements-checklist-template.md",
    ".ai-coding-java/templates/domain-type-model-template.md",
    ".ai-coding-java/templates/architecture-review-template.md",
    ".ai-coding-java/templates/implementation-plan-template.md",
    ".ai-coding-java/templates/design-brief-template.md",
    ".ai-coding-java/templates/test-plan-template.md",
    ".ai-coding-java/templates/test-case-brief-template.md",
    ".ai-coding-java/templates/release-impact-template.md",
    ".ai-coding-java/templates/handoff-template.md",
    ".ai-coding-java/scripts/static_review_check.py",
    ".ai-coding-java/scripts/install_git_hooks.py",
    ".ai-coding-java/scripts/check_target_project.py",
    ".ai-coding-java/scripts/artifact_consistency_check.py",
    ".ai-coding-java/scripts/docs_tone_check.py",
    ".ai-coding-java/scripts/evidence_check.py",
    ".ai-coding-java/scripts/generate_project_map.py",
    ".ai-coding-java/scripts/refresh_target_project.py",
    ".ai-coding-java/project-profile.md",
]

AGENTS_MARKER_START = "<!-- ai-coding-java:AGENTS:START -->"
AGENTS_MARKER_END = "<!-- ai-coding-java:AGENTS:END -->"
CLAUDE_MARKER_START = "<!-- ai-coding-java:CLAUDE:START -->"
CLAUDE_MARKER_END = "<!-- ai-coding-java:CLAUDE:END -->"
RULE_INDEX_REF = ".ai-coding-java/docs/rule-index.md"

PROFILE_REQUIRED_FIELDS = [
    "Project type:",
    "Technology stack:",
    "Verification level:",
    "Template policy:",
    "Data boundary:",
    "- Hook mode:",
]

PROFILE_RECOMMENDED_FIELDS = [
    "- Build command:",
    "- Test command:",
    "- Start command:",
    "- New project macro modules:",
    "- New project core flows:",
    "- Module micro design entry:",
    "- Legacy module entry points:",
    "- Legacy reuse points:",
    "- Legacy forbidden change scope:",
    "- Secondary development impact check:",
    "- API verification method:",
    "- Delivery report path:",
]

RECORDS: list[dict[str, str]] = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only ai-coding-java target project check.")
    parser.add_argument("target", nargs="?", default=".", help="Target project directory")
    parser.add_argument("--report", choices=["markdown", "json"], help="Write a structured doctor report")
    parser.add_argument("--report-path", help="Report output path; defaults under .ai-coding-java/reports/")
    return parser.parse_args()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def print_ok(message: str) -> None:
    RECORDS.append({"status": "OK", "message": message})
    print(f"OK {message}")


def print_warn(message: str) -> None:
    RECORDS.append({"status": "WARN", "message": message})
    print(f"WARN {message}")


def print_info(message: str) -> None:
    RECORDS.append({"status": "INFO", "message": message})
    print(f"INFO {message}")


def print_fail(message: str) -> None:
    RECORDS.append({"status": "FAIL", "message": message})
    print(f"FAIL {message}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_files(root: Path) -> tuple[int, int]:
    failed = 0
    warned = 0
    for item in REQUIRED_FILES:
        path = root / item
        if path.is_file():
            print_ok(f"required file {item}")
        else:
            print_fail(f"missing required file {item}")
            failed += 1
    artifacts = root / ".ai-coding-java/artifacts"
    if artifacts.is_dir():
        print_ok("artifacts directory .ai-coding-java/artifacts")
    else:
        print_warn("missing artifacts directory .ai-coding-java/artifacts")
        warned += 1
    return failed, warned


def check_marker_file(path: Path, start: str, end: str, root: Path) -> tuple[int, int]:
    if not path.is_file():
        print_fail(f"missing root entry {rel(path, root)}")
        return 1, 0
    text = read_text(path)
    failed = 0
    warned = 0
    if start in text and end in text and text.find(start) < text.find(end):
        print_ok(f"marker block {rel(path, root)}")
    else:
        print_fail(f"missing marker block {rel(path, root)}")
        failed += 1
    if RULE_INDEX_REF in text:
        print_ok(f"rule-index reference {rel(path, root)}")
    else:
        print_fail(f"missing rule-index reference {rel(path, root)}")
        failed += 1
    if ".ai-coding-java/project-profile.md" in text:
        print_ok(f"project-profile reference {rel(path, root)}")
    else:
        print_warn(f"missing project-profile reference {rel(path, root)}")
        warned += 1
    return failed, warned


def value_after_colon(line: str) -> str:
    if ":" not in line:
        return ""
    return line.split(":", 1)[1].strip()


def check_profile(root: Path) -> tuple[int, int]:
    path = root / ".ai-coding-java/project-profile.md"
    if not path.is_file():
        print_fail("missing .ai-coding-java/project-profile.md")
        return 1, 0
    text = read_text(path)
    failed = 0
    warned = 0
    for field in PROFILE_REQUIRED_FIELDS:
        matching = [line for line in text.splitlines() if line.startswith(field)]
        if not matching:
            print_fail(f"project-profile missing field {field}")
            failed += 1
            continue
        value = value_after_colon(matching[0])
        if not value or value == "unconfirmed":
            print_warn(f"project-profile unconfirmed field {field}")
            warned += 1
        else:
            print_ok(f"project-profile field {field}")
    for field in PROFILE_RECOMMENDED_FIELDS:
        matching = [line for line in text.splitlines() if line.startswith(field)]
        if not matching:
            print_info(f"project-profile missing recommended field {field}")
            continue
        value = value_after_colon(matching[0])
        if not value or value == "unconfirmed":
            print_info(f"project-profile unconfirmed recommended field {field}")
        else:
            print_ok(f"project-profile recommended field {field}")
    return failed, warned


def git_path(root: Path, name: str) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", name],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path


def check_hooks(root: Path) -> tuple[int, int]:
    hooks_dir = git_path(root, "hooks")
    if hooks_dir is None:
        print_warn("target is not a git repository; hooks skipped")
        return 0, 1
    failed = 0
    warned = 0
    for hook in ["pre-commit", "pre-push"]:
        path = hooks_dir / hook
        if not path.is_file():
            print_warn(f"missing git hook {path}")
            warned += 1
            continue
        text = read_text(path)
        if ".ai-coding-java/hooks/" in text:
            print_ok(f"git hook installed {path}")
        else:
            print_warn(f"git hook does not reference ai-coding-java {path}")
            warned += 1
    return failed, warned


def default_report_path(root: Path, report_type: str) -> Path:
    filename = "harness-doctor.md" if report_type == "markdown" else "harness-doctor.json"
    return root / ".ai-coding-java" / "reports" / filename


def markdown_report(root: Path, failed: int, warned: int) -> str:
    lines = [
        "# ai-coding-java Harness Doctor",
        "",
        f"Target: {root}",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Summary: {failed} fail(s), {warned} warning(s)",
        "",
        "| Status | Item |",
        "|---|---|",
    ]
    for item in RECORDS:
        message = item["message"].replace("|", "\\|")
        lines.append(f"| {item['status']} | {message} |")
    lines.append("")
    return "\n".join(lines)


def json_report(root: Path, failed: int, warned: int) -> str:
    payload = {
        "target": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"failures": failed, "warnings": warned},
        "items": RECORDS,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_report(root: Path, args: argparse.Namespace, failed: int, warned: int) -> None:
    if not args.report:
        return
    path = Path(args.report_path).expanduser().resolve() if args.report_path else default_report_path(root, args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.report == "markdown":
        content = markdown_report(root, failed, warned)
    else:
        content = json_report(root, failed, warned)
    path.write_text(content, encoding="utf-8")
    print(f"OK wrote report {path}")


def main() -> int:
    args = parse_args()
    root = Path(args.target).expanduser().resolve()
    if not root.is_dir():
        print_fail(f"target directory does not exist: {root}")
        return 1

    failed = 0
    warned = 0
    print(f"Checking ai-coding-java target: {root}")

    f, w = check_required_files(root)
    failed += f
    warned += w

    f, w = check_marker_file(root / "AGENTS.md", AGENTS_MARKER_START, AGENTS_MARKER_END, root)
    failed += f
    warned += w

    f, w = check_marker_file(root / "CLAUDE.md", CLAUDE_MARKER_START, CLAUDE_MARKER_END, root)
    failed += f
    warned += w

    f, w = check_profile(root)
    failed += f
    warned += w

    f, w = check_hooks(root)
    failed += f
    warned += w

    write_report(root, args, failed, warned)
    print(f"Summary: {failed} fail(s), {warned} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
