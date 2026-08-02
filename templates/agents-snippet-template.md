# AGENTS.md ai-coding-java Snippet Template

```markdown
## ai-coding-java

Use `.ai-coding-java/docs/rule-index.md` as the first ai-coding-java routing file.

Project profile: `.ai-coding-java/project-profile.md`

Global runtime skills remain owned by Codex, Claude Code, or OMX. ai-coding-java provides project-side Java rules, verification, review, and delivery templates.

For behavior changes, use `.ai-coding-java/docs/testing-workflow.md` to map acceptance criteria to unit, integration, API, SQL, regression, or manual verification.

Loading order:

1. This `AGENTS.md`
2. User task
3. Project memory/current task notes
4. `.ai-coding-java/docs/rule-index.md`
5. Only matched `.ai-coding-java/rules/`, `workflow/`, `templates/`, `knowledge/`, or `artifacts/` files
6. Relevant code, tests, config, and history

Project business rules, data isolation, environment commands, and API contracts in this `AGENTS.md` override generic ai-coding-java suggestions.

Target-safe helper scripts are under `.ai-coding-java/scripts/`.

Optional RD process records belong under `.ai-coding-java/artifacts/<work-id>/` when the task needs traceability.
```
