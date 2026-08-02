#!/usr/bin/env python3
from pathlib import Path
import argparse
import re
import sys


PLACEHOLDER_VALUES = {"", "tbd", "todo", "draft", "unconfirmed", "n/a", "na", "none", "-"}
SECTION_NAMES = ["Summary", "Verification", "RD artifacts", "Review", "Not-tested", "Delivery decision"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check delivery evidence in a Markdown delivery report.")
    parser.add_argument("report", help="Delivery report Markdown file")
    parser.add_argument("--warn-only", action="store_true", help="Return success even when evidence is incomplete")
    return parser.parse_args()


def ok(message: str) -> None:
    print(f"OK {message}")


def warn(message: str) -> None:
    print(f"WARN {message}")


def fail(message: str) -> None:
    print(f"FAIL {message}")


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
    if re.match(r"^-?\s*(command|result|item|reason|remaining risk):\s*$", lowered):
        return False
    return True


def section_body(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?ims)^#+\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^#+\s+|\Z)")
    match = pattern.search(text)
    if match:
        return match.group("body").strip()
    labels = "|".join(re.escape(name) for name in SECTION_NAMES if name != heading)
    label_pattern = re.compile(
        rf"(?ims)^{re.escape(heading)}:\s*$\n(?P<body>.*?)(?=^(?:{labels}):\s*$|\Z)"
    )
    label_match = label_pattern.search(text)
    return label_match.group("body").strip() if label_match else ""


def has_heading(text: str, heading: str) -> bool:
    return bool(re.search(rf"(?im)^#+\s+{re.escape(heading)}\s*$", text)) or bool(
        re.search(rf"(?im)^{re.escape(heading)}:\s*$", text)
    )


def has_meaningful_section(text: str, heading: str) -> bool:
    body = section_body(text, heading)
    return any(meaningful_line(line) for line in body.splitlines())


def has_meaningful_not_tested(text: str) -> bool:
    body = section_body(text, "Not-tested")
    if not body:
        return False
    if re.search(r"(?im)\b(none|no skipped checks|all relevant checks ran)\b", body):
        return True
    return any(meaningful_line(line) for line in body.splitlines())


def has_verification_pair(text: str) -> bool:
    body = section_body(text, "Verification")
    if not body:
        return False
    has_command = bool(re.search(r"(?im)\b(command|mvn|gradle|curl|npm|python3?|pytest|test|compile)\b", body))
    has_result = bool(re.search(r"(?im)\b(result|passed|success|ok|green|failed|not-tested)\b", body))
    return has_command and has_result and any(meaningful_line(line) for line in body.splitlines())


def main() -> int:
    args = parse_args()
    path = Path(args.report).expanduser().resolve()
    if not path.is_file():
        fail(f"delivery report does not exist: {path}")
        return 0 if args.warn_only else 1

    text = path.read_text(encoding="utf-8", errors="ignore")
    failed = 0
    warned = 0
    print(f"Checking delivery evidence: {path}")

    for heading in ["Summary", "Verification", "Not-tested"]:
        if not has_heading(text, heading):
            fail(f"missing section {heading}")
            failed += 1
        elif heading == "Not-tested" and not has_meaningful_not_tested(text):
            warn(f"section {heading} has no meaningful content")
            warned += 1
        elif heading != "Not-tested" and not has_meaningful_section(text, heading):
            warn(f"section {heading} has no meaningful content")
            warned += 1
        else:
            ok(f"section {heading}")

    if has_heading(text, "Verification") and not has_verification_pair(text):
        fail("Verification section must include command-like evidence and result")
        failed += 1

    print(f"Summary: {failed} fail(s), {warned} warning(s)")
    if args.warn_only:
        return 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
