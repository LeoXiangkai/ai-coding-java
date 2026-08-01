# ai-coding-java Tooling Contract

`ai-coding-java` is a personal reusable AI Coding component for enterprise Java projects.

## What It Provides

1. Project onboarding questions for Java technology stack, commands, data boundaries, and verification level.
2. P0/P1/P2 Java delivery rules.
3. Scoped workflow routing so agents load only relevant rules.
4. Verification matrix and `Not-tested` reporting format.
5. Review and delivery report templates.
6. Lightweight auto-installed Git hooks for deterministic P0 checks and pre-push validation reminders.
7. Codex and Claude Code compatible project entry guidance.
8. GitHub and Gitee remote-hosting guidance.

## Default Scope

1. Target-project initialization.
2. AI-readable Java rules and templates.
3. Lightweight Git `pre-commit` and `pre-push` protection.
4. Manual or AI-driven verification through the verification matrix.
5. Root `AGENTS.md` / `CLAUDE.md` marker blocks for runtime discovery.
6. Source-host neutral Git usage.

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

Target-project initialization also installs:

```bash
python3 .ai-coding-java/scripts/install_git_hooks.py .
```

The installed hooks scan staged files before commit and check personal branch / verification settings before push.

Target-project generated support files should live under `.ai-coding-java/` by default. Root changes are limited to bounded marker blocks in `AGENTS.md` and `CLAUDE.md`.

Recognition note: Codex uses root `AGENTS.md`; Claude Code uses root `CLAUDE.md`. `scripts/init_target_project.py` writes bounded marker blocks that point both runtimes to `.ai-coding-java/docs/rule-index.md`.
