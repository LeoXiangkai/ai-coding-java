# Git Policy

This policy separates reusable template source from runtime or target-project artifacts.

## Commit To This Component Repository

These files are source for `ai-coding-java` and should be versioned:

```text
README.md
AGENTS.md
CLAUDE.md
TOOL.md
USAGE.md
.gitignore
.claudeignore
docs/
rules/
workflow/
templates/
examples/
scripts/
artifacts/
.omx/project-memory.json
```

Notes:

1. `.omx/project-memory.json` may be committed in this component only because it contains stable, non-sensitive component facts.
2. `examples/` should contain sanitized fixtures only. No real customer data, secrets, credentials, internal hostnames, or production logs.
3. `scripts/` must stay dependency-free unless a dependency is explicitly justified.

## Ignore In This Component Repository

These files are local runtime state or temporary development artifacts and should not be committed:

```text
.omx/logs/
.omx/state/
.omx/metrics.json
.omx/notepad.md
.omx/knowledge-candidates/
.Codex/
*.log
.worktrees/
node_modules/
target/
build/
dist/
.DS_Store
```

Notes:

1. `.omx/notepad.md` is current-task working memory, not stable source.
2. `.Codex/memory/MEMORY.md` is useful locally, but should not be required for the shared template package.
3. Runtime logs and hook state are evidence during a run, not source artifacts.

## Target Java Project Policy

When `scripts/init_target_project.py` injects `.ai-coding-java/` into a business project, the target project must choose one of two policies:

```text
local-auxiliary:
  .ai-coding-java/ is local AI development assistance and should be ignored by the business repo.

committed:
  .ai-coding-java/ is reviewed, sanitized, and committed as a project-specific rule package.
```

For target business projects, never commit:

```text
.ai-coding-java/project-profile.md if it contains environment-sensitive details
.ai-coding-java/AGENTS.ai-coding-java-snippet.md after it has been merged into AGENTS.md
.ai-coding-java/CLAUDE.ai-coding-java-snippet.md after it has been merged into CLAUDE.md
.ai-coding-java/artifacts/ when it contains local drafts, raw evidence, private business details, or unsanitized output
runtime logs
temporary reports
real data exports
curl outputs with personal or business-sensitive data
```

Target project placement rule:

```text
Generated AI Coding support files go under .ai-coding-java/ by default.
The only expected target-root edits are bounded ai-coding-java marker blocks in AGENTS.md and CLAUDE.md.
Do not place helper scripts, reports, or knowledge drafts in the business root.
```

## Development Product Records

Development records are useful, but their destination differs:

| Record | Destination |
|---|---|
| Stable component decision | `.omx/project-memory.json` or docs |
| Current task progress | `.omx/notepad.md`, ignored |
| Unsanitized knowledge candidate | `.omx/knowledge-candidates/`, ignored |
| Reusable rule/template/example | docs, rules, workflow, templates, examples; committed |
| Reusable artifact directory guidance | artifacts/README.md; committed |
| Verification command result | final report or sanitized docs if reusable |
| One-off command output/log | ignored runtime logs |
| Target project generated `.ai-coding-java/` | target policy decides |
