# RD Integrated Workflow v1.1

本文件定义轻量研发一体化链路。目标是把需求、设计、测试、Review、发布和知识沉淀串起来，减少 AI 直接编码后的返工。

本流程使用轻量模板和按需路由。复杂需求可生成过程产物，小任务继续走规则索引。

公开 SDD / Agent Skill 组件的参考价值和取舍见 `docs/sdd-reference-analysis.md`。本流程只吸收能提升准确性和可验证性的轻量机制，不把外部完整工具链变成默认门禁。

## 适用场景

1. 新功能。
2. 复杂 bugfix。
3. 重构或架构调整。
4. 涉及接口、表结构、批量任务、外部系统、权限、缓存或发布风险的变更。

小范围文案、简单配置、无行为变化的整理可跳过本流程，直接按 `docs/rule-index.md` 命中专项规则。

## 轻量阶段

```text
Requirement -> Design -> Task/Test -> Implement -> Verify/Review -> Release -> Knowledge
```

| 阶段 | 目标 | 推荐产物 | 位置 |
|---|---|---|---|
| Requirement | 澄清做什么、为什么做、验收标准是什么 | 需求简报 | `.ai-coding-java/artifacts/<work-id>/requirement-brief.md` |
| Design | 确认影响面、数据边界、接口和技术取舍 | 设计简报 | `.ai-coding-java/artifacts/<work-id>/design-brief.md` |
| Task/Test | 拆任务并前置测试/验收用例 | 测试用例简表、复杂需求 checklist | `.ai-coding-java/artifacts/<work-id>/test-case-brief.md` |
| Implement | 按既有分层和规则实现 | 代码 diff | 业务代码目录 |
| Verify/Review | 证明行为正确并暴露风险 | 验证证据、Review 结论 | 交付报告或 `.ai-coding-java/artifacts/<work-id>/` |
| Release | 说明发布影响、回滚和验收证据 | 发布影响说明 | `.ai-coding-java/artifacts/<work-id>/release-impact.md` |
| Knowledge | 抽取可复用经验 | 知识候选、跨会话交接 | `.omx/knowledge-candidates/` 或 `.ai-coding-java/artifacts/<work-id>/handoff.md` |

## 阶段要求

### Requirement

必须明确：

1. 背景和目标。
2. 非目标。
3. 业务角色和关键流程。
4. Given/When/Then 验收标准。
5. 数据隔离边界。
6. 依赖系统、权限、配置和兼容性约束。

### Design

必须明确：

1. 受影响模块、接口、表、任务、缓存、文件和外部系统。
2. 复用现有能力的判断。
3. 事务、幂等、并发和失败处理。
4. SQL 性能和数据迁移风险。
5. 回滚或降级方式。

### Task/Test

任务要能独立验证。测试用例优先从验收标准派生，至少覆盖：

1. 正常路径。
2. 边界条件。
3. 异常和失败路径。
4. 权限或数据隔离。
5. 回归场景。

复杂需求可使用 `templates/requirements-checklist-template.md`，用来确认验收标准、非目标、数据边界、权限、兼容性和发布影响是否清楚。Checklist 是前置澄清工具，不是小任务的默认阻塞门禁。

### Implement

执行仍以 `workflow/agent-workflow.md` 和命中的 `rules/` 为准。不得为了补产物而扩大代码 diff。

### Verify/Review

验证依据 `docs/verification-matrix.md`。Review 使用 P0/P1/P2 分级。不能执行的验证必须写入 `Not-tested`。

复杂需求或发布前建议做一次只读一致性分析：需求、设计、测试、发布影响和交付报告应能互相追溯。发现 P0 风险时必须处理；P1/P2 记录风险、建议和未验证项。

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
