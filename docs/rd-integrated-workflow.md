# RD Integrated Workflow v1.1

本文件定义轻量研发一体化链路。目标是把需求、领域类型模型、设计、架构评审、实施计划、测试、Review、发布和知识沉淀串起来，减少 AI 直接编码后的返工。

本流程使用轻量模板和按需路由。复杂需求可生成过程产物，小任务继续走规则索引。编码前设计完整性见 `docs/design-first-policy.md`。

公开 SDD / Agent Skill 组件的参考价值和取舍见 `docs/sdd-reference-analysis.md`。本流程只吸收能提升准确性和可验证性的轻量机制，不把外部完整工具链变成默认门禁。

## 适用场景

1. 新功能。
2. 复杂 bugfix。
3. 重构或架构调整。
4. 涉及接口、表结构、批量任务、外部系统、权限、缓存或发布风险的变更。

小范围文案、简单配置、无行为变化的整理可跳过本流程，直接按 `docs/rule-index.md` 命中专项规则。

## 轻量阶段

```text
Requirement -> Domain/Type -> Design -> Architecture Review -> Plan/Test -> Implement -> Verify/Review -> Release -> Knowledge
```

| 阶段 | 目标 | 推荐产物 | 位置 |
|---|---|---|---|
| Requirement | 澄清做什么、为什么做、验收标准是什么 | 需求简报 | `.ai-coding-java/artifacts/<work-id>/requirement-brief.md` |
| Domain/Type | 探索领域对象、状态、操作、约束和边界 | 类型系统/领域模型说明 | `.ai-coding-java/artifacts/<work-id>/domain-type-model.md` |
| Design | 确认新项目宏观/微观设计，或二开项目模块和影响设计 | 设计简报 | `.ai-coding-java/artifacts/<work-id>/design-brief.md` |
| Architecture Review | 确认分层、数据模型、事务、风险和外部借鉴取舍 | 架构评审说明 | `.ai-coding-java/artifacts/<work-id>/architecture-review.md` |
| Plan/Test | 拆任务并前置测试/验收用例 | 落地计划、测试计划、测试用例简表、复杂需求 checklist | `.ai-coding-java/artifacts/<work-id>/implementation-plan.md`、`test-plan.md`、`test-case-brief.md` |
| Implement | 按既有分层和规则实现 | 代码 diff | 业务代码目录 |
| Verify/Review | 证明行为正确并暴露风险 | 验证证据、Review 结论 | 交付报告或 `.ai-coding-java/artifacts/<work-id>/` |
| Release | 说明发布影响、回滚和验收证据 | 发布影响说明 | `.ai-coding-java/artifacts/<work-id>/release-impact.md` |
| Knowledge | 抽取可复用经验 | 知识候选、跨会话交接 | `.omx/knowledge-candidates/` 或 `.ai-coding-java/artifacts/<work-id>/handoff.md` |

## 阶段要求

### Re-baseline

当用户把项目定位从一个方向切换到另一个方向时，例如从“通用业务流 Demo”改为“库存管理完整落地版”，不能沿用旧需求产物直接证明完成。Agent 必须先重建目标基线：

1. 新建或重写当前目标对应的 Work ID。
2. 重新定义范围、非目标、核心流程和验收标准。
3. 标记旧产物只能作为历史上下文，不能作为新目标完成证据。
4. 先补测试计划，再实现核心差异，避免在旧系统上做零散补丁。
5. 交付报告必须明确本次目标重定向后的验证证据。

### Requirement

必须明确：

1. 背景和目标。
2. 非目标。
3. 业务角色和关键流程。
4. Given/When/Then 验收标准。
5. 数据隔离边界。
6. 依赖系统、权限、配置和兼容性约束。

### Domain/Type

复杂业务或完整系统开发前，必须先探索类型系统，避免直接从页面或表单开始编码。至少明确：

1. 核心实体、值对象、枚举状态和状态机。
2. 核心操作命令和查询视图。
3. 领域不变量，例如库存不能为负、调拨总量守恒、流水只能追加。
4. 数据归属边界、审计字段和幂等键。
5. 哪些类型是当前版本必须实现，哪些是后续扩展，例如批次、库位、序列号。

### Design

必须明确：

1. 本次是新项目、完整模块、二开改造、小修还是纯文档。
2. 新项目必须有宏观模块设计和核心模块微观设计。
3. 二开项目必须有既有模块、复用点、修改点、不改范围和影响设计。
4. 受影响模块、接口、表、任务、缓存、文件和外部系统。
5. 事务、幂等、并发和失败处理。
6. SQL 性能、兼容性、数据迁移和回滚风险。
7. 设计是否足够进入实现；不足时先补设计，不进入编码。

### Architecture Review

设计进入实现前必须经过一次轻量架构评审，至少回答：

1. 类型系统是否覆盖验收标准。
2. 表结构、接口、页面和测试是否能从类型系统追溯。
3. 事务边界、并发保护和失败回滚是否清楚。
4. 是否借鉴了外部成熟项目，借鉴内容是否转化为本项目自己的设计表达。
5. 是否存在为了快速实现而绕开核心流程的风险。

### Plan/Test

任务要能独立验证。测试 workflow 见 `docs/testing-workflow.md`，TDD 分级见 `docs/tdd-policy.md`。测试用例优先从验收标准派生，至少覆盖：

1. 正常路径。
2. 边界条件。
3. 异常和失败路径。
4. 权限或数据隔离。
5. 回归场景。

复杂需求可使用 `templates/requirements-checklist-template.md`，用来确认验收标准、非目标、数据边界、权限、兼容性和发布影响是否清楚。Checklist 是前置澄清工具，不是小任务的默认阻塞门禁。

复杂需求或高风险变更建议先使用 `templates/test-plan-template.md`，把需求验收、单元测试、集成测试、API/curl、SQL/数据验证、回归测试和人工验收串成一条证据链。测试计划不是形式文档；它用于防止开发后再临时补验证。

### Implement

执行仍以 `workflow/agent-workflow.md` 和命中的 `rules/` 为准。不得为了补产物而扩大代码 diff。

### Verify/Review

验证依据 `docs/verification-matrix.md`。Review 使用 P0/P1/P2 分级。不能执行的验证必须写入 `Not-tested`。

复杂需求或发布前建议做一次只读一致性分析：需求、领域类型模型、设计、架构评审、实施计划、测试、发布影响和交付报告应能互相追溯。发现 P0 风险时必须处理；P1/P2 记录风险、建议和未验证项。

可使用以下脚本检查过程产物一致性：

```bash
python3 .ai-coding-java/scripts/artifact_consistency_check.py .ai-coding-java/artifacts/<work-id>
```

该脚本只读检查，不修改产物；小任务不需要运行。

### Release

发布前至少说明：

1. 变更摘要。
2. 数据库、配置、缓存、定时任务、外部系统影响。
3. 部署和验证命令。
4. 回滚方式。
5. 人工验收或接口验证证据。

### Knowledge

只有稳定、可复用、已脱敏的经验进入 `knowledge/`。过程草稿先生成到 `.omx/knowledge-candidates/`，经人工审查后再入库。

跨会话、跨 Agent、多模块或提测前交接可使用 `templates/handoff-template.md`。交接只记录当前目标、已完成项、证据、未验证项、风险和下一步，不保存长篇过程日志。

## 文件策略

目标项目初始化后，研发一体化过程产物默认放在：

```text
.ai-coding-java/artifacts/<work-id>/
```

建议 `<work-id>` 使用需求号、缺陷号、任务号或短功能名，例如：

```text
.ai-coding-java/artifacts/feature-class-roster/
.ai-coding-java/artifacts/bug-sync-timeout/
```

是否把 artifacts 入业务仓库，由目标项目策略决定：

1. 本地辅助模式：过程产物可不入库。
2. 团队协作模式：已脱敏、可追溯的产物可按任务入库。
3. 禁止提交运行日志、原始客户数据、真实凭据、未脱敏生产输出。

## 与全局技能的关系

全局 Codex、Claude Code 或 OMX 可以按自身规则调用规划、TDD、Review、提测、提交等技能。本文件只规定项目内产物和 Java 规则，不规定全局技能清单。
