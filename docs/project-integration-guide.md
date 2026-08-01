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
  scripts/
    static_review_check.py
    extract_knowledge_candidate.py
```

## Required Manual Review

1. Fill missing build, test, start, database, cache, and endpoint verification commands in `project-profile.md`.
2. Review the generated marker blocks in root `AGENTS.md` and `CLAUDE.md`.
3. Keep `AGENTS.ai-coding-java-snippet.md` and `CLAUDE.ai-coding-java-snippet.md` as review copies.
5. Confirm whether `.ai-coding-java/` stays local-only or is committed.
6. Run a small real task through `rule-index -> matched rules -> verification -> delivery report`.

## Acceptance Criteria

1. Target `AGENTS.md` points to `.ai-coding-java/docs/rule-index.md`.
2. Target `CLAUDE.md` points to `.ai-coding-java/docs/rule-index.md`, or explicitly delegates to `AGENTS.md`.
3. Project profile records technology stack, verification level, data boundary, and template policy.
4. Codex and Claude Code can route Controller, Service, Mapper SQL, security/logging, and review tasks to matched files.
5. Delivery reports include verification evidence and `Not-tested` when needed.
6. Reusable sanitized knowledge entries are available under `.ai-coding-java/knowledge/` and loaded only when matched.
7. Target-safe helper scripts live under `.ai-coding-java/scripts/`; no helper script should be written to the target business root by default.
8. Lightweight RD process records, when useful, live under `.ai-coding-java/artifacts/<work-id>/` and are not generated as a mandatory gate.
