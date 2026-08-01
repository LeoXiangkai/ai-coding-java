# ai-coding-java Usage

## Initialize A Target Java Project

1. In the target repository, run or follow `$setup-ai-coding`.
2. Confirm project type:
   - new project
   - legacy project
   - maintenance project
3. Confirm technology stack from suggestions or custom input.
4. Confirm build, test, start, database, cache, and external-system dependencies.
5. Confirm data isolation boundary, such as tenant, organization, school, year, or region.
6. Confirm default verification level: lightweight, standard, or strict.
7. Decide template placement:
   - local auxiliary `.ai-coding-java/` not committed
   - committed project rule package after review

## Scripted Injection

```bash
python3 /path/to/ai-coding-java/scripts/init_target_project.py /path/to/target-project \
  --project-type legacy \
  --stack "Java 8 + Spring Boot 2.x + Maven + MyBatis + MySQL + Redis" \
  --verification-level standard \
  --template-policy local-auxiliary \
  --data-boundary "school + school_year"
```

By default, the script writes `.ai-coding-java/` and adds small marker blocks to target root `AGENTS.md` and `CLAUDE.md`, so Codex and Claude Code can discover the rules.

It also writes snippets for review:

```text
.ai-coding-java/AGENTS.ai-coding-java-snippet.md
.ai-coding-java/CLAUDE.ai-coding-java-snippet.md
```

## Static Review

After injection, run from the target project:

```bash
python3 .ai-coding-java/scripts/static_review_check.py .
```

Use this before AI semantic review. Treat findings as review evidence, not as an installed commit hook unless the target project explicitly chooses that policy.

## Target Project File Placement

Generated AI Coding support files should stay under `.ai-coding-java/` by default.

The only expected target-root changes are bounded ai-coding-java marker blocks in `AGENTS.md` and `CLAUDE.md`.

## Minimal Target `AGENTS.md` Pointer

```markdown
## ai-coding-java

Use `.ai-coding-java/docs/rule-index.md` as the first rule routing file.

Load only matching rules:
- Controller / VO: delivery + review + verification matrix
- Service write flow: transaction + delivery + verification matrix
- Mapper XML / SQL: sql + delivery + verification matrix
- Security or logging: security-logging + review

Project business rules, data isolation, environment commands, and API contracts in this `AGENTS.md` override generic ai-coding-java suggestions.
```

## Minimal Target `CLAUDE.md` Pointer

```markdown
## ai-coding-java

Use `.ai-coding-java/docs/rule-index.md` as the first ai-coding-java routing file for Java development rules.

Read the nearest `AGENTS.md` for Codex-compatible project execution rules when present.
Use `.ai-coding-java/docs/verification-matrix.md` before claiming completion.
```

## Agent Loading Order

```text
1. nearest AGENTS.md
2. user task
3. project memory or current task notes
4. .ai-coding-java/docs/rule-index.md
5. matched rule/workflow/template files only
6. matched reusable knowledge entries only when relevant
7. relevant code, tests, config, and history
```

## Expected Delivery Report

Use `templates/delivery-report-template.md`.

Every report must include:

1. Changed files.
2. Impacted modules, APIs, or tables.
3. Verification evidence.
4. `Not-tested` items.
5. P0/P1/P2 review result.
