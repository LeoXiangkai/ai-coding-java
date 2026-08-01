# Agent Workflow

This workflow keeps AI Coding lightweight and evidence-based.

## Default Flow

```text
Intake -> Scope -> Context Load -> Impact Analysis -> Implement -> Verify -> Review -> Report
```

Small tasks may compress steps, but must still report verification and risk.

## Intake

Identify:

1. Task type: feature, bugfix, refactor, sql-change, ddl-change, config-change, release, review.
2. Allowed and forbidden modules.
3. Interfaces, tables, data boundaries, external systems, jobs, async flows, files, and caches.
4. Verification level: lightweight, standard, strict.
5. Whether the task needs lightweight RD artifacts under `.ai-coding-java/artifacts/<work-id>/`.

## Context Load

Load in order:

1. nearest `AGENTS.md`
2. user task
3. project memory/current notes
4. `docs/rule-index.md`
5. matched rules only
6. relevant code/tests/config/history

Runtime skills such as planning, TDD, review, release, commit, or deployment are owned by the global Codex, Claude Code, or OMX runtime. This workflow only defines project-side Java rule loading and delivery evidence.

## Implement

1. Keep diff small.
2. Follow existing project layers and naming.
3. Add no unrequested dependencies.
4. Preserve unrelated user changes.
5. Write no secrets.

## Verify

Use `docs/verification-matrix.md`.

If verification cannot run, report `Not-tested` rather than claiming success.

## Review

Use P0/P1/P2. Findings need file/line references when reviewing code.

## Report

Use `templates/delivery-report-template.md`.

For complex requirements, release-sensitive changes, or work that needs traceability, also use `docs/rd-integrated-workflow.md` and the brief templates. Do not create process artifacts for trivial tasks.
