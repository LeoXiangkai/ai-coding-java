# Project Integration Guide

This guide covers Phase 2: injecting `ai-coding-java` into a real Java project.

## Default Command

```bash
python3 /path/to/ai-coding-java/scripts/init_target_project.py /path/to/target-project \
  --project-type legacy \
  --stack "Java 8 + Spring Boot 2.x + Maven + MyBatis + MySQL + Redis" \
  --verification-level standard \
  --template-policy local-auxiliary \
  --data-boundary "school + school_year"
```

The script writes `.ai-coding-java/` in the target project and adds small marker blocks to the target root `AGENTS.md` and `CLAUDE.md` so Codex and Claude Code can discover the rules immediately after initialization.

## Generated Target Files

```text
.ai-coding-java/
  README.md
  TOOL.md
  USAGE.md
  project-profile.md
  AGENTS.ai-coding-java-snippet.md
  CLAUDE.ai-coding-java-snippet.md
  docs/
  rules/
  workflow/
  templates/
  knowledge/
  artifacts/
  hooks/
  scripts/
    check_target_project.py
    artifact_consistency_check.py
    docs_tone_check.py
    evidence_check.py
    generate_project_map.py
    refresh_target_project.py
    install_git_hooks.py
    static_review_check.py
    extract_knowledge_candidate.py
```

## Required Manual Review

1. Fill missing build, test, start, database, cache, and endpoint verification commands in `project-profile.md`.
2. Review the generated marker blocks in root `AGENTS.md` and `CLAUDE.md`.
3. Keep `AGENTS.ai-coding-java-snippet.md` and `CLAUDE.ai-coding-java-snippet.md` as review copies.
4. Confirm whether `.ai-coding-java/` stays local-only or is committed.
5. Run a small real task through `rule-index -> matched rules -> verification -> delivery report`.
6. Run the read-only target check:

```bash
python3 .ai-coding-java/scripts/check_target_project.py .
```

Generate a doctor report when onboarding needs a reviewable record:

```bash
python3 .ai-coding-java/scripts/check_target_project.py . --report markdown
```

Generate a lightweight code map for old projects or unfamiliar modules:

```bash
python3 .ai-coding-java/scripts/generate_project_map.py .
```

Preview template refresh before updating an existing target:

```bash
python3 /path/to/ai-coding-java/scripts/refresh_target_project.py . --list-extra
```

## Acceptance Criteria

1. Target `AGENTS.md` points to `.ai-coding-java/docs/rule-index.md`.
2. Target `CLAUDE.md` points to `.ai-coding-java/docs/rule-index.md`, or explicitly delegates to `AGENTS.md`.
3. Project profile records technology stack, verification level, data boundary, and template policy.
4. Codex and Claude Code can route Controller, Service, Mapper SQL, security/logging, and review tasks to matched files.
5. Delivery reports include test and verification evidence, with `Not-tested` when needed.
6. Reusable sanitized knowledge entries are available under `.ai-coding-java/knowledge/` and loaded only when matched.
7. Target-safe helper scripts live under `.ai-coding-java/scripts/`; no helper script should be written to the target business root by default.
8. Lightweight RD process records, when useful, live under `.ai-coding-java/artifacts/<work-id>/` and are not generated as a mandatory gate.
9. Git targets get auto-installed local `pre-commit` and `pre-push` wrappers in the repository hook directory.
10. `check_target_project.py` reports zero failures. Warnings are acceptable only when they reflect deliberate local policy, such as missing build/test commands during early onboarding.
11. Complex tasks can run `artifact_consistency_check.py` against `.ai-coding-java/artifacts/<work-id>` before review or release.
12. Complex tasks can use `testing-workflow.md` and `test-plan-template.md` to map requirements to unit, integration, API, SQL, regression, and manual verification.
13. Delivery reports can run `evidence_check.py` before handoff or push when evidence quality matters.
14. Existing targets can run `refresh_target_project.py` in dry-run mode before applying template updates.
