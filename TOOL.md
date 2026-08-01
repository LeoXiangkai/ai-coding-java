# ai-coding-java Tooling Contract

`ai-coding-java` is not a CI gate or framework runtime. It is a lightweight AI Coding template package for enterprise Java projects.

## What It Provides

1. Project onboarding questions for Java technology stack, commands, data boundaries, and verification level.
2. P0/P1/P2 Java delivery rules.
3. Scoped workflow routing so agents load only relevant rules.
4. Verification matrix and `Not-tested` reporting format.
5. Review and delivery report templates.
6. Codex and Claude Code compatible project entry guidance.

## What It Does Not Do By Default

1. It does not install hooks.
2. It does not block commits.
3. It does not add Java dependencies.
4. It does not run CI.
5. It does not replace project `AGENTS.md` or business rules.

## Recommended Runtime Use

For this component project:

```bash
python3 scripts/context_budget_check.py
python3 scripts/template_integrity_check.py
python3 scripts/static_review_check.py examples/static-review-good
```

For a target Java project:

```text
1. Run or follow $setup-ai-coding in the target project.
2. Run scripts/init_target_project.py from this component or copy the package manually.
3. Confirm project stack and verification level.
4. Add a short pointer from the target AGENTS.md to the injected ai-coding-java rules.
5. Load docs/rule-index.md first, then only the matching rule or knowledge files.
```

For target project static review:

```bash
python3 .ai-coding-java/scripts/static_review_check.py .
```

Target-project generated support files should live under `.ai-coding-java/` by default. Do not write helper scripts into the business project root unless the project explicitly chooses that policy.

Recognition note: Codex and Claude Code do not auto-load arbitrary snippet files under `.ai-coding-java/`. The target root `AGENTS.md` and `CLAUDE.md` must point to `.ai-coding-java/docs/rule-index.md`. `scripts/init_target_project.py` always writes bounded marker blocks for this.
