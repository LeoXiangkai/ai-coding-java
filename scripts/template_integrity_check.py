#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "TOOL.md",
    "USAGE.md",
    "docs/ai-coding-java-standard-v1.md",
    "docs/rule-index.md",
    "docs/verification-matrix.md",
    "docs/design-first-policy.md",
    "docs/testing-workflow.md",
    "docs/tdd-policy.md",
    "docs/project-harness.md",
    "docs/structure-and-naming.md",
    "docs/documentation-tone-and-reuse.md",
    "docs/project-onboarding-template.md",
    "docs/review-output-template.md",
    "docs/project-integration-guide.md",
    "docs/auto-review-guide.md",
    "docs/git-policy.md",
    "docs/knowledge-guide.md",
    "docs/runtime-skill-boundary.md",
    "docs/rd-integrated-workflow.md",
    "docs/git-hooks-guide.md",
    "docs/remote-hosting-guide.md",
    "artifacts/README.md",
    "hooks/pre-commit",
    "hooks/pre-push",
    "knowledge/README.md",
    "knowledge/company-rules/java-layering.md",
    "knowledge/company-rules/verification-evidence.md",
    "knowledge/bug-roots/transaction-self-invocation.md",
    "knowledge/sql-transaction-cases/mybatis-dynamic-order.md",
    "knowledge/project-rule-examples/data-isolation-school-year.md",
    "rules/java8-springboot2-mybatis.md",
    "rules/sql-rule.md",
    "rules/transaction-rule.md",
    "rules/security-logging-rule.md",
    "rules/delivery-rule.md",
    "rules/review-level.md",
    "workflow/agent-workflow.md",
    "templates/coding-agent-template.md",
    "templates/ai-review-template.md",
    "templates/project-business-rule-template.md",
    "templates/delivery-report-template.md",
    "templates/adr-template.md",
    "templates/project-profile-template.md",
    "templates/agents-snippet-template.md",
    "templates/claude-snippet-template.md",
    "templates/knowledge-entry-template.md",
    "templates/requirement-brief-template.md",
    "templates/requirements-checklist-template.md",
    "templates/domain-type-model-template.md",
    "templates/architecture-review-template.md",
    "templates/implementation-plan-template.md",
    "templates/design-brief-template.md",
    "templates/test-plan-template.md",
    "templates/test-case-brief-template.md",
    "templates/release-impact-template.md",
    "templates/handoff-template.md",
    "examples/project-profile.example.md",
    "examples/AGENTS.ai-coding-java-snippet.example.md",
    "examples/CLAUDE.ai-coding-java-snippet.example.md",
    "examples/delivery-report.example.md",
    "examples/static-review-good/GoodMapper.xml",
    "examples/static-review-good/GoodService.java",
    "examples/static-review-bad/BadMapper.xml",
    "examples/static-review-bad/BadService.java",
    "scripts/init_target_project.py",
    "scripts/install_git_hooks.py",
    "scripts/check_target_project.py",
    "scripts/artifact_consistency_check.py",
    "scripts/structure_check.py",
    "scripts/docs_tone_check.py",
    "scripts/evidence_check.py",
    "scripts/generate_project_map.py",
    "scripts/refresh_target_project.py",
    "scripts/static_review_check.py",
    "scripts/extract_knowledge_candidate.py",
    ".omx/project-memory.json",
]


def main() -> int:
    failed = False
    for rel in REQUIRED:
        if (ROOT / rel).is_file():
            print(f"OK required {rel}")
        else:
            print(f"MISS required {rel}")
            failed = True

    try:
        json.loads((ROOT / ".omx/project-memory.json").read_text(encoding="utf-8"))
        print("OK project memory JSON")
    except Exception as exc:
        print(f"FAIL project memory JSON: {exc}")
        failed = True

    index = (ROOT / "docs/rule-index.md").read_text(encoding="utf-8")
    refs = sorted(set(re.findall(r"`((?:docs|rules|workflow|templates)/[^`]+?\.md)`", index)))
    for rel in refs:
        if (ROOT / rel).is_file():
            print(f"OK rule-index ref {rel}")
        else:
            print(f"MISS rule-index ref {rel}")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
