#!/usr/bin/env python3
from pathlib import Path
import argparse
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / ".omx/knowledge-candidates"
SENSITIVE_RE = re.compile(
    r"(?i)(password|passwd|secret|token|access[_-]?key|private[_-]?key|身份证|手机号|mobile|phone)\s*[:=]"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a sanitized knowledge candidate draft from a delivery report.")
    parser.add_argument("report", help="Delivery report Markdown/text file")
    parser.add_argument("--type", default="bug-root", choices=["company-rule", "bug-root", "sql-case", "transaction-case", "project-rule-example"])
    parser.add_argument("--title", default="unconfirmed-knowledge-candidate")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    return parser.parse_args()


def slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return cleaned or "knowledge-candidate"


def section(text: str, name: str) -> str:
    pattern = re.compile(rf"(?ims)^#+\s*{re.escape(name)}\s*$\n(?P<body>.*?)(?=^#+\s|\Z)")
    match = pattern.search(text)
    return match.group("body").strip() if match else ""


def bullet_summary(text: str, limit: int = 12) -> str:
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if SENSITIVE_RE.search(stripped):
            lines.append("- [REDACTED sensitive-looking line]")
        elif stripped.startswith(("-", "*")):
            lines.append(stripped)
        elif len(lines) < 3:
            lines.append(f"- {stripped[:180]}")
        if len(lines) >= limit:
            break
    return "\n".join(lines) if lines else "- TBD"


def candidate_text(args: argparse.Namespace, report_text: str) -> str:
    summary = section(report_text, "Summary") or section(report_text, "总结") or report_text
    verification = section(report_text, "Verification") or section(report_text, "验证")
    not_tested = section(report_text, "Not-tested") or section(report_text, "未验证")
    title = args.title
    return f"""# Knowledge Candidate: {title}

Type: {args.type}

Scope: TBD

Problem:

{bullet_summary(summary)}

Reusable fact:

- TBD

Evidence source:

- Delivery report: {Path(args.report).name}

Verification method:

{bullet_summary(verification)}

Not-tested or remaining risk:

{bullet_summary(not_tested)}

Applies when:

- TBD

Does not apply when:

- TBD

Sanitization check:
- no secrets: manually confirm
- no real personal data: manually confirm
- no raw production logs: manually confirm
- no internal credentials or hostnames: manually confirm

Last verified: TBD
"""


def main() -> int:
    args = parse_args()
    report = Path(args.report).expanduser().resolve()
    if not report.is_file():
        print(f"FAIL report not found: {report}", file=sys.stderr)
        return 1
    text = report.read_text(encoding="utf-8", errors="ignore")
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{slug(args.title)}.md"
    out.write_text(candidate_text(args, text), encoding="utf-8")
    print(f"OK wrote {out}")
    print("Review and sanitize this candidate before moving it into knowledge/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

