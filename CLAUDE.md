# ai-coding-java Claude Code Entry

## Project

`ai-coding-java` is a personal reusable component for enterprise Java AI Coding workflows. It helps new or existing Java projects initialize AI-readable rules for technology stack confirmation, scoped rule loading, verification evidence, code review output, and lightweight pre-commit protection.

This component is designed to be recognized by both Claude Code and Codex:

- Claude Code: start from this `CLAUDE.md`.
- Codex: start from `AGENTS.md`.
- Shared project memory: `.omx/project-memory.json`.
- Current task notes: `.omx/notepad.md`.

## Collaboration Model

Claude Code may handle requirement clarification, planning, decomposition, and review. Codex may handle direct implementation and verification. When Claude Code needs Codex to execute work, call Codex with the project root as `--cd`.

Example handoff shape:

```bash
codex exec --cd /path/to/ai-coding-java "<task>"
```

If Codex invocation fails from Claude Code, first check the local environment and proxy path before changing project files.

## Source Of Truth

1. Read `AGENTS.md` for project execution constraints.
2. Use `README.md` as the human-facing component index.
3. Use `docs/rule-index.md` for lightweight rule routing.
4. Use `docs/project-onboarding-template.md` when initializing a target Java project.
5. Use `docs/verification-matrix.md` before claiming behavior is verified.
6. Use `docs/review-output-template.md` for review results.
7. Use `rules/`, `workflow/`, and `templates/` as the concrete template package.

For future project initialization, use `$setup-ai-coding`. Treat `$setup-cc` as a legacy alias only.

## Development Rules

1. Keep this component small and composable.
2. Do not import unrelated command, gate, dashboard, or lifecycle hook stacks into this component by default.
3. `AGENTS.md` and `CLAUDE.md` should stay compact and aligned.
4. Do not add generated logs or runtime state to versioned source.
5. Do not write secrets.

## Verification

Run:

```bash
python3 scripts/context_budget_check.py
```

For content refactors, also search for stale wording:

```bash
rg -n "v1\\.0|reference-baseline|当前项目按本地|强制 hooks" README.md AGENTS.md CLAUDE.md TOOL.md USAGE.md docs rules workflow templates scripts
```

Report any `Not-tested` items explicitly.
