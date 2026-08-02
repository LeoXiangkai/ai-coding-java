#!/usr/bin/env python3
from pathlib import Path
import argparse
import re
import sys


KNOWN_FILES = {
    "requirements-checklist.md": ["Scope Clarity", "Acceptance", "Enterprise Java Risk", "Verification"],
    "requirement-brief.md": ["Background", "Goal", "Non-goals", "Acceptance Criteria", "Data Boundary", "Dependencies"],
    "design-brief.md": ["Scope", "Impact", "Data And Transaction Design", "SQL And Performance", "Rollback Or Fallback"],
    "test-case-brief.md": ["Source", "Test Scope", "Cases", "Automation Plan", "Not Covered"],
    "release-impact.md": ["Change Summary", "Deployment Impact", "Verification Evidence", "Rollback", "Not-tested"],
    "handoff.md": ["Current Objective", "Completed", "Verification", "Open Risks", "Not Tested", "Next Step"],
}

PLACEHOLDER_VALUES = {"", "tbd", "todo", "draft", "unconfirmed", "n/a", "na", "none", "-"}


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

    test_text = texts.get("test-case-brief.md", "")
    if test_text:
        for label, expected in [("Requirement brief:", "requirement-brief.md"), ("Design brief:", "design-brief.md")]:
            value = file_reference_value(test_text, label)
            if not value:
                warn(f"test-case-brief.md missing source reference {label}")
                warned += 1
            elif expected not in value:
                warn(f"test-case-brief.md source {label} does not reference {expected}")
                warned += 1
            else:
                ok(f"test-case-brief.md source {label}")

    release_text = texts.get("release-impact.md", "")
    if release_text and "Verification Evidence" in release_text and not has_meaningful_section(release_text, "Verification Evidence"):
        warn("release-impact.md lacks verification evidence")
        warned += 1

    print(f"Summary: {failed} fail(s), {warned} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
