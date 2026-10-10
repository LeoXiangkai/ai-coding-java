---
name: flow
description: 阶段导航：根据 work-id 和已有产物判断当前研发阶段并给出唯一下一步入口。触发：下一步做什么、现在到哪一步了、/flow、新任务开始不知从哪起步。不用于执行下游工作或写入任何文件。
---

# 阶段导航

本 skill 只读、只判断、只给导航，不写文件，不执行下游工作。

## 定位任务

1. 定位 `work-id`：优先使用用户指定值；否则取 `.ai-coding-java/artifacts/` 下最近修改的目录，也识别 `.claude/tasks/<id>/` 下的 `add-module` 产物。
2. 读取已有产物和工作区状态；按下表判断阶段。没有任何产物时直接引导到 `req-intake`。

## 阶段表

| 阶段 | 产物文件 | 完成判据 | 下一步 skill/命令 |
|---|---|---|---|
| 需求 | `requirement-brief.md` 或 PRD | 目标、范围、非目标、验收和待确认项清楚 | `req-intake`；业务知识库影响分析用 `req-analysis`；完整多 Story 用 `prd` |
| 设计 | `design-brief.md`（按 `docs/design-first-policy.md` 该有才有） | 影响、边界、接口/数据方案与风险可追溯 | `add-module` 或 `auto-sdd` |
| 计划与测试 | `implementation-plan.md`、`test-plan.md`、`test-case-brief.md` | 任务、测试层级和验收证据可执行 | `auto-sdd` |
| 实现 | 代码 diff；查看 `git status`、`git log` 与 worktree | 需求点有对应代码变更且范围可解释 | `local-verify` |
| 验证评审 | 验证证据、review 结论、`delivery-report` | 测试结果和未测试项明确，评审结论已记录 | `code-review`；随后 `git-commit` |
| 发布 | `release-impact.md` | 发布影响、回滚和环境验收证据齐全 | `automate-test-handoff`（若已安装） |
| 沉淀 | `handoff.md` 或知识候选 | 可复用结论、边界和后续入口已记录 | 按需结束或回到 `flow` |

## 目标或阶段判不出时

判不出阶段，或用户说不清目标与下一步时，先用 `grilling` 问清目标与当前进度，再按上表给唯一建议；`grilling` 未安装则直接问答。

## 固定输出

```text
阶段条：需求 ⏳ | 设计 ⬜ | 计划与测试 ⬜ | 实现 ⬜ | 验证评审 ⬜ | 发布 ⬜ | 沉淀 ⬜
当前阶段：<阶段>
缺失产物：<文件或“无”>
建议下一步：<唯一一个入口>
可跳过阶段：<阶段及理由，或“无”>
```

状态符号：`✅已完成`、`⏳进行中`、`⬜未开始`、`➖按规模可跳过`。文档、配置或 ≤5 行零风险小任务可提示跳过前置阶段；不得强拉完整流程。skill 不存在或未安装时，说明缺失并给出同一阶段的人工只读判断方式，不引用清单外的 skill。
