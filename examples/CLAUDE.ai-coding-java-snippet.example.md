## ai-coding-java

Use `.ai-coding-java/docs/rule-index.md` as the first ai-coding-java routing file for Java development rules.

Project profile: `.ai-coding-java/project-profile.md`

Global runtime skills remain owned by Codex, Claude Code, or OMX. ai-coding-java provides project-side Java rules, verification, review, and delivery templates.

Confirmed setup:

- Project type: legacy
- Technology stack: Java 8 + Spring Boot 2.x + Maven + MyBatis + MySQL + Redis
- Verification level: standard
- Template policy: local-auxiliary
- Data boundary: school + school_year

Claude Code loading guidance:

1. Read this `CLAUDE.md`.
2. Read the nearest `AGENTS.md` for Codex-compatible project execution rules when present.
3. Read `.ai-coding-java/docs/rule-index.md`.
4. Load only matched `.ai-coding-java/rules/`, `workflow/`, `templates/`, or `knowledge/` files.
5. Use `.ai-coding-java/docs/verification-matrix.md` before claiming completion.

Project business rules, data isolation, environment commands, and API contracts in this `CLAUDE.md` or `AGENTS.md` override generic ai-coding-java suggestions.

Target-safe helper scripts are under `.ai-coding-java/scripts/`.
