# Multica Worktree Agent Template

```markdown
## Multica worktree guard

Task:

Project:

Worktree:

Branch:

Base branch:

Task branch contract:

Source of truth:
- .ai-coding-java/docs/git-policy.md (project profile; init_target_project.py copies docs/)
- ~/.claude/refs/git-policy.md (global layer; use when no project profile is present)
- project AGENTS.md / CLAUDE.md

Required checks before any edit:
1. Read project AGENTS.md / CLAUDE.md.
2. Read .ai-coding-java/docs/git-policy.md when injected; otherwise read ~/.claude/refs/git-policy.md. Ensure the execution environment can access the selected source.
3. Verify current branch, base branch, and worktree path explicitly.
4. Confirm the branch name matches the task-name-only contract.
5. Confirm the base branch is declared by the project contract or the task.

Hard stop conditions:
- branch prefix or base branch is missing
- worktree path is missing or inconsistent
- current branch is an integration branch
- branch name includes agent name, date, owner name, or generated task number that is not part of the task name
- the task depends on ~/.claude/rules or ~/.codex/AGENTS.md instead of project-side rules

Forbidden assumptions:
- Do not infer base_branch from global config.
- Do not infer worktree ownership from chat context.
- Do not start implementation before the guard passes.

Expected output:
- branch/worktree evidence
- changed files
- verification evidence
- remaining risk
```
