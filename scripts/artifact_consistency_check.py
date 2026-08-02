#!/usr/bin/env python3
from pathlib import Path
import argparse
import re
import sys


KNOWN_FILES = {
    "requirements-checklist.md": ["Scope Clarity", "Acceptance", "Enterprise Java Risk", "Verification"],
    "requirement-brief.md": ["Background", "Goal", "Non-goals", "Acceptance Criteria", "Data Boundary", "Dependencies"],
    "github-reference-analysis.md": ["Source", "Reference Summary", "Borrowed Ideas", "Rejected Ideas", "Local Decisions"],
    "domain-type-model.md": ["Source", "Core Types", "Status And Enums", "Commands", "Queries And Views", "Invariants", "Out Of Scope Types"],
    "architecture-review.md": ["Source", "Review Result", "Architecture Checks", "External Reference Conversion", "Risks And Decisions", "Required Changes Before Implementation"],
    "implementation-plan.md": ["Source", "Milestones", "Implementation Tasks", "Test Tasks", "Verification Commands", "Not Planned"],
    "design-brief.md": ["Source", "Design Gate", "New Project Macro Design", "Module Micro Design", "Existing Project Impact Design", "Scope", "Impact", "Data And Transaction Design", "SQL And Performance", "Rollback Or Fallback"],
    "test-plan.md": ["Source", "Requirement Coverage", "Test Layers", "Test Data", "Commands", "Risk-Based Coverage", "Not Covered"],
    "test-case-brief.md": ["Source", "Test Scope", "Cases", "Automation Plan", "Not Covered"],
    "release-impact.md": ["Change Summary", "Deployment Impact", "Verification Evidence", "Rollback", "Not-tested"],
    "handoff.md": ["Current Objective", "Completed", "Verification", "Open Risks", "Not Tested", "Next Step"],
}

PLACEHOLDER_VALUES = {"", "tbd", "todo", "draft", "unconfirmed", "n/a", "na", "none", "-"}

SOURCE_EXPECTATIONS = {
    "domain-type-model.md": [("Requirement brief:", "requirement-brief.md")],
    "architecture-review.md": [
        ("Requirement brief:", "requirement-brief.md"),
        ("Domain type model:", "domain-type-model.md"),
        ("Design brief:", "design-brief.md"),
    ],
    "implementation-plan.md": [
        ("Requirement brief:", "requirement-brief.md"),
        ("Domain type model:", "domain-type-model.md"),
        ("Architecture review:", "architecture-review.md"),
        ("Design brief:", "design-brief.md"),
    ],
    "design-brief.md": [
        ("Requirement brief:", "requirement-brief.md"),
        ("Domain type model:", "domain-type-model.md"),
    ],
    "test-plan.md": [
        ("Requirement brief:", "requirement-brief.md"),
        ("Domain type model:", "domain-type-model.md"),
        ("Architecture review:", "architecture-review.md"),
        ("Implementation plan:", "implementation-plan.md"),
        ("Design brief:", "design-brief.md"),
    ],
    "test-case-brief.md": [
        ("Requirement brief:", "requirement-brief.md"),
        ("Domain type model:", "domain-type-model.md"),
        ("Architecture review:", "architecture-review.md"),
        ("Implementation plan:", "implementation-plan.md"),
        ("Design brief:", "design-brief.md"),
        ("Test plan:", "test-plan.md"),
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only consistency check for ai-coding-java RD artifacts.")
    parser.add_argument("artifact_dir", help="Path to .ai-coding-java/artifacts/<work-id>")
    return parser.parse_args()


def ok(message: str) -> None:
    print(f"OK {message}")


def warn(message: str) -> None:
    print(f"WARN {message}")


def fail(message: str) -> None:
    print(f"FAIL {message}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).strip("` ")


def meaningful_line(line: str) -> bool:
    stripped = normalize(line)
    if not stripped:
        return False
    lowered = stripped.lower()
    if lowered in PLACEHOLDER_VALUES:
        return False
    if set(stripped) <= {"|", "-", " "}:
        return False
    if re.match(r"^(given|when|then|item|reason|risk|owner|evidence|decision|reviewer|date):\s*$", lowered):
        return False
    return True


def section_body(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?ims)^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)")
    match = pattern.search(text)
    return match.group("body").strip() if match else ""


def has_meaningful_section(text: str, heading: str) -> bool:
    body = section_body(text, heading)
    return any(meaningful_line(line) for line in body.splitlines())


def field_value(text: str, field: str) -> str:
    pattern = re.compile(rf"(?im)^{re.escape(field)}\s*(?P<value>.*)$")
    match = pattern.search(text)
    return normalize(match.group("value")) if match else ""


def work_id_from(text: str) -> str:
    for field in ["Work ID:", "Requirement / work ID:"]:
        value = field_value(text, field)
        if value and value.lower() not in PLACEHOLDER_VALUES:
            return value
    return ""


def file_reference_value(text: str, field: str) -> str:
    value = field_value(text, field)
    if value.lower() in PLACEHOLDER_VALUES:
        return ""
    return value


def main() -> int:
    args = parse_args()
    root = Path(args.artifact_dir).expanduser().resolve()
    if not root.is_dir():
        fail(f"artifact directory does not exist: {root}")
        return 1

    failed = 0
    warned = 0
    seen_any = False
    work_ids: dict[str, str] = {}
    texts: dict[str, str] = {}

    print(f"Checking RD artifacts: {root}")

    for filename, sections in KNOWN_FILES.items():
        path = root / filename
        if not path.is_file():
            warn(f"missing optional artifact {filename}")
            warned += 1
            continue
        seen_any = True
        text = read(path)
        texts[filename] = text
        ok(f"found {filename}")
        work_id = work_id_from(text)
        if work_id:
            work_ids[filename] = work_id
            ok(f"{filename} Work ID {work_id}")
        else:
            warn(f"{filename} missing Work ID")
            warned += 1
        for section in sections:
            if f"## {section}" not in text:
                warn(f"{filename} missing section {section}")
                warned += 1
            elif not has_meaningful_section(text, section):
                warn(f"{filename} section {section} has no meaningful content")
                warned += 1
            else:
                ok(f"{filename} section {section}")

    if not seen_any:
        fail("no known RD artifact files found")
        return 1

    distinct_ids = {value for value in work_ids.values()}
    if len(distinct_ids) > 1:
        fail(f"inconsistent Work ID values: {work_ids}")
        failed += 1
    elif distinct_ids:
        ok(f"consistent Work ID {next(iter(distinct_ids))}")

    for filename, expectations in SOURCE_EXPECTATIONS.items():
        artifact_text = texts.get(filename, "")
        if not artifact_text:
            continue
        for label, expected in expectations:
            value = file_reference_value(artifact_text, label)
            if not value:
                warn(f"{filename} missing source reference {label}")
                warned += 1
            elif expected not in value:
                warn(f"{filename} source {label} does not reference {expected}")
                warned += 1
            else:
                ok(f"{filename} source {label}")

    release_text = texts.get("release-impact.md", "")
    if release_text and "Verification Evidence" in release_text and not has_meaningful_section(release_text, "Verification Evidence"):
        warn("release-impact.md lacks verification evidence")
        warned += 1

    print(f"Summary: {failed} fail(s), {warned} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
