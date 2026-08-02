# Agent Workflow

This workflow keeps AI Coding lightweight and evidence-based.

## Default Flow

```text
Intake -> Scope -> Context Load -> Design Gate -> Impact Analysis -> Test Plan -> Implement -> Verify -> Review -> Report
```

Small tasks may compress steps, but must still report verification and risk.

## Intake

Identify:

1. Task type: feature, bugfix, refactor, sql-change, ddl-change, config-change, release, review.
2. Allowed and forbidden modules.
3. Interfaces, tables, data boundaries, external systems, jobs, async flows, files, and caches.
4. Verification level: lightweight, standard, strict.
    5. Whether the task needs lightweight RD artifacts under `.ai-coding-java/artifacts/<work-id>/`.

## Design Gate

Before implementation, use `docs/design-first-policy.md` when the task is a new project, complete module, legacy change, cross-module change, or any behavior change with unclear impact.

Implementation must not start until the agent can state:

1. project mode: new project, complete module, legacy change, small fix, or documentation-only;
2. macro/module design for new projects, or module/impact design for legacy changes;
3. modules, files, APIs, tables, config, jobs, cache, files, and external systems likely affected;
4. modules explicitly not changed;
5. design gaps that block implementation.

If the design is incomplete, update `design-brief.md` or the task note first. Do not compensate with a narrow local implementation.

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
6. Implement the real target capability according to the design gate, including tests and integration points. Do not reduce scope to an easier fallback when the requested function is clear.

## Test Plan

Before or during implementation, use `docs/testing-workflow.md` and `docs/tdd-policy.md` when the change affects business behavior. Map acceptance criteria to unit, integration, API, SQL, regression, or manual verification, and choose L0-L3 TDD level before claiming the work is ready.

## Drift And Churn

Pause and refresh the lightweight requirement/design record before more code edits when any trigger appears:

1. User feedback changes the original acceptance criteria.
2. The same defect or requirement is being reworked for a second time.
3. The same file receives repeated patch-only edits without a clearer design decision.
4. Test expectations no longer match the current business rule.

For small tasks, update the delivery report or task note. For complex tasks, update `.ai-coding-java/artifacts/<work-id>/requirement-brief.md`, `domain-type-model.md`, `design-brief.md`, `architecture-review.md`, `implementation-plan.md`, or an ADR before continuing.

## Verify

Use `docs/verification-matrix.md`.

If verification cannot run, report `Not-tested` rather than claiming success.

## Review

Use P0/P1/P2. Findings need file/line references when reviewing code.

## Report

Use `templates/delivery-report-template.md`.

For complex requirements, release-sensitive changes, or work that needs traceability, also use `docs/rd-integrated-workflow.md` and the brief templates. Do not create process artifacts for trivial tasks.

When evidence quality matters, run:

```bash
python3 .ai-coding-java/scripts/evidence_check.py <delivery-report.md>
```
