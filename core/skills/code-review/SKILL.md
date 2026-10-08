---
name: code-review
description: Use when reviewing a local worktree, current branch change-set, explicit repository path, or pull request before merge or task completion.
---

# Scoped Code Review

Review identity is **repository root + current branch**. One invocation owns one repository and one branch-relative change-set; a cross-repository feature is reviewed once per repository branch, never as one filesystem-wide scan.

## 1. Freeze the boundary before reading code

Run:

```bash
python3 ~/.claude/skills/code-review/scripts/scope.py \
  --target "<explicit target path or .>" \
  --effort "<low|medium|high|xhigh|max>"
```

The JSON is the review contract:

- `repo_root` is the only readable repository root for this review.
- `base_oid` comes from `branch.<branch>.fork-oid`; the named baseline or upstream merge-base is only a fallback.
- `files` is the complete whitelist: committed branch changes, tracked working-tree changes, staged changes, and untracked files relative to `base_oid`.
- Use only repository-relative paths from this whitelist. Never read sibling repositories, parent workspace paths, another worktree, or files discovered outside `repo_root`.
- Empty `files` means there is no change-set to review.

If the target is a PR, first resolve its checkout/worktree, then run the same scope command there. Do not let PR metadata broaden the filesystem boundary.

## 2. Complexity gate

`scope.py` derives the gate from actual diff size and risk signals:

| `review_gate` | Action |
|---|---|
| `skip` | No independent reviewer. The main session still performs its normal diff self-review and tests. |
| `single` | Launch exactly one scoped reviewer. |
| `dual-candidate` | Launch two reviewers only when the two prompts cover independent critical risk dimensions; otherwise launch one. |

High-risk signals include API/serialized contracts, database migrations or DML, authorization/security/PII, concurrency/transactions, and cross-process boundaries.

The requested effort controls depth inside the same whitelist. **effort does not increase reviewer count**. Even `high`, `xhigh`, or `max` permits **at most two reviewer agents**.

## 3. Multi-window ownership

Use `coordination_key` as the change-set identity.

1. Call `ListAgents` once（若当前环境提供该工具；没有则视为无其他窗口持有，本窗口即 owner）.
2. If another live session clearly owns the **same repository root + branch**, send one message containing the coordination key and ask it to remain the sole review owner; this window skips duplicate review.
3. Different branches are different change-sets and need no coordination message.
4. Do not poll. If ownership is not already clear, this invocation remains owner.

## 4. Reviewer dispatch contract

Use `Agent` directly, never a workflow. Launch a **fresh scoped reviewer agent** (omit `subagent_type`, use the environment's default mid-tier model) so it receives only the explicit review prompt instead of inheriting the main conversation. This keeps a small branch review small even when the parent session is long. Use read-only intent and include this exact contract in every prompt:

```text
Review only repo_root=<repo_root>, branch=<branch>, base_oid=<base_oid>.
The only allowed source files are this exact whitelist: <files>.
Do not inspect sibling repositories, parent directories, other worktrees, or files outside the whitelist.
Do not broaden scope based on imports; report missing context to the parent instead.
You must not call Agent, Skill, or /code-review, and must not spawn or delegate to any child agent.
Return only concrete findings with file, line, failure scenario, and severity; return “no findings” when none survive.
```

One reviewer covers correctness, side effects, error paths, integration, reuse, and simplification together. A second reviewer is allowed only for an independently separable critical dimension identified by `risk_details` (for example security versus a data migration). Never dispatch one reviewer per language, file, module, or generic review dimension.

## 5. Verify findings and finish

- The parent independently verifies every candidate against a concrete input/state → wrong output/crash scenario.
- Discard style preferences, speculative risks, and claims outside the whitelist.
- If the diff changes how business data is written, computed or configured, confirm the consumer-side list from `rules/context-engineering.md §3.4` exists (若已安装；未安装时主会话自行沿数据流列出消费方); if not, produce it before finishing. Consumers the diff does not touch are outside the reviewer whitelist, so this check stays with the parent.
- Batch confirmed findings, fix once, and run targeted regression.
- Incremental re-review is limited to fixed files and their already-whitelisted direct context. Do not launch another full review unless the contract, scope, or core design materially changed.
- Report whether independent review was skipped, single, or dual, plus the repository, branch, base OID, file count, changed lines, and verified findings.
- At finish time (regardless of `review_gate`, including `skip`), record the outcome by running `python3 ~/.claude/skills/code-review/scripts/scope.py --target <repo_root> --outcome --reviewers <0|1|2> --findings <n> --confirmed <n>`; this appends one line to the review log (`<claude>/aicj/review-logs/code-review-gates.jsonl`) and prints `recorded`. Only the final outcome counts must be supplied; the script resolves repository root, branch, and base OID the same way as the gate command.

## 6. Push gate

`push-review-gate.py`（随组件安装于 `<claude>/hooks/aicj/`，若已启用）在每次 `git push` 前把待推送区间与 `code-review-gates.jsonl` 中的 `reviewed_blobs` 比对。每个变更文件都被一条 blob 与 commit 侧一致（且 `common_dir` 与仓库一致）的 outcome 覆盖时放行；否则按 `AICJ_HOOK_MODE` 行动：`block` 拒绝（退出 2），默认 `warn` 在 stderr 给出同内容提示后放行。拒绝/提示都会指明仓库与分支，要求先跑本 skill 并记录 outcome 后重试；outcome 必须覆盖最终内容——修复 finding 后要重新记录。确认要跳过时在提示框执行 `! git push` 手动推。未安装该钩子时按本节语义人工自检后推送。

## Hard stops

- A reviewer tries to inspect a sibling repository or another worktree: stop that reviewer and discard out-of-bound output.
- More agents would improve confidence: deepen the existing review; do not exceed the cap.
- Multiple windows touch related features on different branches: each reviews only its own branch.
- A small/medium low-impact diff feels worth “just one quick reviewer”: obey `skip`; direct verification remains mandatory, independent fan-out does not.
