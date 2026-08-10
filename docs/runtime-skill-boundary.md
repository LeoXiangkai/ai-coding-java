# Runtime Skill Boundary v1.1

本文件说明 ai-coding-java 与 Codex、Claude Code、OMX 等全局运行时的职责边界。

## 结论

1. 技能发现、技能触发、`$skill` 调用、模型选择和全局编排由运行时处理。
2. ai-coding-java 提供项目内 Java 开发规则、上下文加载顺序、验证矩阵、Review 口径和交付模板。
3. 运行时能力通过 Codex、Claude Code 或 OMX 的全局配置提供。
4. 初始化到业务项目后，根 `AGENTS.md` 和 `CLAUDE.md` 必须指向 `.ai-coding-java/docs/rule-index.md`，让 Codex 和 Claude Code 都能进入同一套项目规则。
5. `$setup-ai-coding` 初始化当前项目工作区，并在 Java 项目中调用 `scripts/init_target_project.py` 接入 `.ai-coding-java/`；非 Java 项目和组件源仓库跳过注入。

## 常规新需求怎么走

当用户提出新需求时，推荐链路是：

```text
全局运行时识别任务和可用技能
-> 读取项目根 AGENTS.md / CLAUDE.md
-> 进入 .ai-coding-java/docs/rule-index.md
-> 对新需求、完整模块或不清晰行为变更先执行 $grilling 需求拷问
-> 读取 workflow/agent-workflow.md 和命中的专项规则
-> 修改代码
-> 按 docs/verification-matrix.md 验证
-> 按 templates/delivery-report-template.md 汇报
```

全局运行时可以按自身规则加载规划、TDD、Review、提测、提交等技能；项目侧继续使用 ai-coding-java 的设计门、规则、TDD 分级和验证矩阵。

Grilling 边界：

1. 新功能、完整模块、跨模块需求、二开行为改造或需求边界不清时，进入设计门和实现前必须先调用全局 `$grilling`，用轮次问题确认目标、非目标、验收标准、影响范围和阻塞歧义。
2. 文案、注释、无行为配置、小范围明确 bugfix、纯分析或 Review 可跳过 `$grilling`，但仍要按项目规则说明范围和验证。
3. `$grilling` 的技能发现、问题轮次和用户确认由全局运行时负责；ai-coding-java 只规定它在 Java 新需求流程中的前置位置。

TDD 边界：

1. ai-coding-java 负责在 `docs/tdd-policy.md` 中定义 L0-L3 分级和触发条件。
2. 全局运行时负责在 L3 或用户显式要求 TDD 时执行具体 RED/GREEN/REFACTOR 技能。
3. 项目交付报告负责记录 TDD 等级、RED/GREEN 证据或无法执行的原因。

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

## setup 与目标注入

`setup-ai-coding` 把工作区初始化和 Java 规则组件接入放在同一轮执行：

1. `python3 scripts/install_setup_ai_coding_skill.py` 把全局 `~/.agents/skills/setup-ai-coding` 和 `~/.claude/skills/setup-ai-coding` 软链到本仓库的 `skills/setup-ai-coding/`，让新机器能识别 `$setup-ai-coding`。
2. `$setup-ai-coding` 初始化当前项目的 `AGENTS.md`、`CLAUDE.local.md`、`.omx/`、ignore 与权限等工作区约定。
3. 如果当前项目是 Java 项目且不是 `ai-coding-java` 组件源，`$setup-ai-coding` 继续调用 `scripts/init_target_project.py /path/to/target-project ... --claude-entry local` 创建 `.ai-coding-java/`，并把 Claude marker 写入 `CLAUDE.local.md`。
4. 目标 `.ai-coding-java/` 不携带 `setup-ai-coding` 副本；需要安装或刷新全局 skill 时，从 `ai-coding-java` 组件仓库运行安装脚本。

## 组件职责

1. 维护 Java 项目开发规则。
2. 维护验证矩阵和交付模板。
3. 维护目标项目初始化入口。
4. 维护轻量 Git commit/push 预检。
5. 维护 project harness 只读检查入口，确认目标项目已正确接入。

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
