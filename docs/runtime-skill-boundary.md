# Runtime Skill Boundary v1.1

本文件说明 ai-coding-java 与 Codex、Claude Code、OMX 等全局运行时的职责边界。

## 结论

1. 技能发现、技能触发、`$skill` 调用、模型选择和全局编排由运行时处理。
2. ai-coding-java 不复制全局技能目录、模型路由表或长编排协议。
3. ai-coding-java 只提供项目内 Java 开发规则、上下文加载顺序、验证矩阵、Review 口径和交付模板。
4. 初始化到业务项目后，根 `AGENTS.md` 和 `CLAUDE.md` 必须指向 `.ai-coding-java/docs/rule-index.md`，让 Codex 和 Claude Code 都能进入同一套项目规则。

## 常规新需求怎么走

当用户提出新需求时，推荐链路是：

```text
全局运行时识别任务和可用技能
-> 读取项目根 AGENTS.md / CLAUDE.md
-> 进入 .ai-coding-java/docs/rule-index.md
-> 读取 workflow/agent-workflow.md 和命中的专项规则
-> 修改代码
-> 按 docs/verification-matrix.md 验证
-> 按 templates/delivery-report-template.md 汇报
```

全局运行时可能会按自身规则加载规划、TDD、Review、提测、提交等技能；ai-coding-java 不强制这些技能必须存在，也不把技能实现写入目标项目。

## 技能归属

| 场景 | 负责方 |
|---|---|
| 用户显式输入 `$setup-ai-coding`、`$cp`、`$release-test` 等 | 全局运行时 |
| 根据技能描述判断是否加载某个技能 | 全局运行时 |
| Codex 读取项目根 `AGENTS.md` | Codex 运行时 |
| Claude Code 读取项目根 `CLAUDE.md` | Claude Code 运行时 |
| Java 分层、SQL、事务、安全日志、交付规则 | ai-coding-java |
| 任务类型到规则文件的路由 | ai-coding-java |
| 验证矩阵、Review 分级、交付报告模板 | ai-coding-java |
| 企业知识库条目和项目画像 | ai-coding-java |

## 不做什么

ai-coding-java 不应：

1. 内置完整全局技能清单。
2. 要求所有项目安装相同 hooks 或门禁。
3. 绑定某个模型、供应商或 CLI 版本。
4. 把运行时日志、临时计划、调试输出作为项目规范入库。

## 推荐写法

项目根入口只需要表达项目规则和轻量路由，例如：

```markdown
Use `.ai-coding-java/docs/rule-index.md` as the first ai-coding-java routing file.
Project business rules in this `AGENTS.md` / `CLAUDE.md` override generic ai-coding-java suggestions.
Global runtime skills remain owned by Codex, Claude Code, or OMX.
```

这样可以保证：

1. Codex 和 Claude Code 都能识别项目内规则。
2. 全局技能升级不需要改业务项目模板。
3. 企业 Java 规范稳定留在项目侧，运行时能力稳定留在全局侧。
