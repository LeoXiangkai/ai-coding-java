# Knowledge Guide

This guide covers reusable knowledge capture and feedback into Agent context.

## Goal

Capture stable, sanitized knowledge so future Coding Agent runs can load less context and still avoid repeated mistakes.

## Layers

```text
Company reusable knowledge:
  knowledge/

Target project stable facts:
  target AGENTS.md
  target .omx/project-memory.json
  target project docs or ADR

Current task notes:
  target .omx/notepad.md
```

## Capture Candidates

Capture a knowledge entry when a completed task reveals:

1. A reusable Java engineering rule.
2. A recurring bug root cause.
3. A SQL, transaction, async, cache, or idempotency lesson.
4. A reusable example of how project business rules should be recorded.

Do not capture:

1. Temporary logs.
2. Raw command output.
3. Project-only private business facts.
4. Secrets or sensitive data.
5. Unverified guesses.

## Feedback Into Agent Loading

1. Start with project `AGENTS.md`.
2. Route with `docs/rule-index.md`.
3. If the task matches a recurring topic, load the smallest matching `knowledge/` entry.
4. Do not load the whole knowledge directory by default.

## Required Fields

Use `templates/knowledge-entry-template.md`.

To draft a candidate from a delivery report:

```bash
python3 scripts/extract_knowledge_candidate.py examples/delivery-report.example.md --title transaction-rollback-example
```

The generated file goes to `.omx/knowledge-candidates/` and is ignored by Git until manually reviewed and sanitized.

Every entry must include:

1. Scope.
2. Reusable fact.
3. Evidence source.
4. Verification method.
5. Applicability boundary.
6. Sanitization check.
