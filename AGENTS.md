# ai-coding-java Project Contract

## Project Purpose

`ai-coding-java` is a personal reusable enterprise Java AI Coding component for new development projects. It standardizes project onboarding, rule routing, verification evidence, review output, and lightweight pre-commit protection without extra lifecycle hooks, CLI gates, or long mandatory workflows by default.

This component itself is intended to be versioned in Git. Target Java projects may inject `.ai-coding-java/` as local AI development assistance or choose to commit it after project review.

## Runtime Entry Points

- Codex reads this `AGENTS.md` as the project contract.
- Claude Code reads `CLAUDE.md` as the collaboration entry point.
- Shared stable facts live in `.omx/project-memory.json`.
- Current task notes live in `.omx/notepad.md`.
- General project initialization should use `$setup-ai-coding`; legacy `$setup-cc` is only a compatibility alias.

## Structure

```text
README.md / AGENTS.md / CLAUDE.md
docs/       standards, rule index, RD workflow, verification, integration, review, git, knowledge, runtime boundary
rules/      Java, SQL, transaction, security/logging, delivery, review-level rules
workflow/   agent-workflow.md
templates/  task, review, business-rule, delivery, ADR, project-profile, runtime snippets, knowledge-entry templates
artifacts/  optional RD process record guidance for target projects
knowledge/  reusable company rules, bug roots, SQL/transaction cases, project examples
examples/   target-project snippets, delivery report, static-review fixtures
scripts/    context, integrity, initialization, hook install, static review, knowledge extraction helpers
hooks/      lightweight target-project git hooks
.omx/       project-memory.json and current notepad
```

## Technology

This is currently a documentation/template component, not a Java runtime project. There is no Maven/Gradle build yet.

Python usage follows the workspace rule: use the machine global Python only. Do not create project-local `.venv/`, Conda, pyenv, Codex, Claude, or WorkBuddy Python environments.

## Working Rules

1. Keep the component lightweight; do not copy unrelated command systems, lifecycle hooks, model routing tables, global skill catalogs, or long orchestration protocols into this project.
2. Prefer small, reviewable Markdown and template changes.
3. Do not add runtime dependencies unless the component actually needs executable tooling.
4. Do not write plaintext secrets, internal credentials, or full sensitive logs.
5. For project onboarding behavior, keep Codex and Claude Code entry points aligned.
6. For Java rules, treat `docs/rule-index.md` as the first lightweight routing file and load only matched `rules/`, `workflow/`, or `templates/` files.
7. Treat skill discovery and `$skill` invocation as global runtime behavior; this component owns only project-side Java rules, verification, review, and delivery templates.
8. Keep RD integration phase gates optional until explicitly requested; the default hook scope is staged-file P0 scanning only.

## Verification

For documentation/template changes:

```bash
python3 scripts/context_budget_check.py
python3 scripts/template_integrity_check.py
```

Also run targeted checks when relevant:

```bash
rg -n "v1\\.0|reference-baseline|TODO|FIXME" README.md AGENTS.md CLAUDE.md TOOL.md USAGE.md docs rules workflow templates scripts
```

For target-project initialization script changes, also run a temporary-directory dry integration:

```bash
tmpdir=$(mktemp -d)
python3 scripts/init_target_project.py "$tmpdir" --project-type legacy
python3 scripts/template_integrity_check.py
```

For static review script changes, run:

```bash
python3 scripts/static_review_check.py examples/static-review-good
python3 scripts/static_review_check.py examples/static-review-bad
```

For knowledge extraction changes, run:

```bash
python3 scripts/extract_knowledge_candidate.py examples/delivery-report.example.md --title transaction-rollback-example
```

## Memory

Record stable, non-sensitive project facts in `.omx/project-memory.json`. Keep `.omx/notepad.md` short and current-task focused. Do not preserve long logs in startup context.

Use `docs/git-policy.md` to decide whether a development record belongs in Git. In this component repo, commit reusable template source and sanitized examples; ignore runtime state, logs, `.omx/notepad.md`, `.omx/knowledge-candidates/`, and `.Codex/`.

For target projects, `scripts/init_target_project.py` writes bounded marker blocks into root `AGENTS.md` and `CLAUDE.md`, pointing both runtimes to `.ai-coding-java/docs/rule-index.md`.

Run the budget check before claiming initialization or template restructuring is complete:

```bash
python3 scripts/context_budget_check.py
```
