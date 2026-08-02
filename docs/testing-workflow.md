# 产研测一体化测试验证 Workflow v1.1

本文件定义目标 Java 项目开发过程中的产研测一体化测试验证 workflow。它不是测试平台，也不是临时兜底脚本；它规定需求澄清、研发实现、测试验证和交付证据如何串起来。

目标：开发前知道要验证什么，开发中按层补测试，交付前能证明需求已被覆盖，避免实现完成后反复返工。

TDD 分级策略见 `docs/tdd-policy.md`。本文件规定测试链路，`tdd-policy.md` 规定 L0-L3 的启用条件和证据要求。

## 适用范围

1. 新功能。
2. bugfix 和回归修复。
3. Controller / VO / Service / Mapper / SQL 变更。
4. 涉及权限、数据隔离、状态流转、幂等、缓存、定时任务或外部系统的变更。
5. 发布前需要验收证据的复杂需求。

小文案、无行为变化的文档整理可只做轻量验证，并在交付报告中说明。

## 核心链路

```text
Requirement acceptance -> Test plan -> Code and tests -> Integration/API/SQL verification -> Delivery evidence
```

产研测一体化在本组件中的最小闭环：

1. 产品视角先把目标、非目标、验收标准和数据边界说清楚。
2. 研发视角把验收标准映射到代码层、事务层、接口层和数据层影响。
3. 测试视角在编码前确认测试计划，编码中同步补自动化或替代验证，交付前核对证据。
4. Agent 交付时必须能从需求、领域类型模型、设计、架构评审、实施计划、测试计划、验证命令追溯到同一 Work ID。

小任务可以不生成完整过程产物，但不能省略“验收标准对应什么验证”的判断。

## 测试分层

| 层级 | 目标 | 常见方式 | 触发 |
|---|---|---|---|
| 需求测试 | 验收标准可验证，非目标和边界清楚 | Given/When/Then、验收清单 | 新需求、复杂 bugfix |
| 单元测试 | 业务规则和纯逻辑可回归 | JUnit、focused test | Service、规则、工具类 |
| 集成测试 | Spring Bean、事务、Mapper、配置能协同 | SpringBootTest、真实或受控测试数据 | 多表写、Mapper、配置 |
| SQL 验证 | SQL 语义、数据隔离、性能风险明确 | dev/test 数据、explain、接口验证 | Mapper XML、复杂查询、DDL |
| API 验证 | 接口契约和实际响应正确 | 本地启动 + curl / Postman / OpenAPI | Controller、VO、鉴权 |
| 回归测试 | 修复点不会复发，关键链路不破坏 | focused regression、历史用例 | bugfix、重构 |
| 人工验收 | 自动化覆盖不到的业务流程有记录 | UAT checklist、截图或验收记录 | 复杂业务、外部系统 |

## 开发前

开始实现前，Agent 必须先通过 `docs/design-first-policy.md` 的设计门，再判断测试形态：

1. 需求是否有可验证的 Given/When/Then 或等价验收清单。
2. 每条验收标准应落到需求测试、单元测试、集成测试、API、SQL、回归或人工验收中的哪一类。
3. 是否需要新增或更新单元测试。
4. 是否需要集成测试或真实 dev/test 数据验证。
5. 是否需要本地启动和 curl。
6. 是否涉及权限、数据隔离、状态流转、幂等或并发。
7. 哪些验证无法自动化，必须写入 `Not-tested` 或人工验收。
8. 当前任务的 TDD 等级是 L0、L1、L2 还是 L3。

复杂需求建议先生成：

```text
.ai-coding-java/artifacts/<work-id>/test-plan.md
.ai-coding-java/artifacts/<work-id>/test-case-brief.md
```

## 开发中

测试应跟实现同步推进：

1. 纯逻辑和 Service 规则优先补 focused unit test。
2. bugfix 优先补能复现问题的回归测试，再修复。
3. 多表写同时检查事务、rollbackFor、Spring Bean 调用路径。
4. Mapper XML / SQL 变更必须准备 SQL 语义验证方式。
5. Controller / VO 变更必须准备接口契约验证方式。
6. 测试数据要覆盖正常、边界、异常、权限或数据隔离路径。
7. 不能只写 mock 调用次数断言；测试必须断言业务结果、状态变化或输出契约。

按 TDD 等级执行：

1. L0：可跳过测试先行，但交付报告仍需说明验证方式。
2. L1：先写测试计划或轻量验证清单，再实现。
3. L2：实现前优先补 focused test、集成测试或回归测试；不能补时记录替代验证。
4. L3：必须先记录 RED 失败证据，再实现 GREEN，最后保持测试全绿。

如果项目暂时没有测试框架，不能用“没有测试框架”跳过风险说明；应在交付报告中写明替代验证和剩余风险。

## 阶段门

| 阶段 | 必须确认 | 不满足时 |
|---|---|---|
| 编码前 | 设计门、验收标准、影响面、TDD 等级、测试计划或轻量验证清单明确 | 先补需求澄清、设计简报、TDD 分级或测试计划 |
| 提交前 | 编译、focused test、关键 API/SQL 验证已执行或写明缺口 | 继续补测试或记录 Not-tested |
| 交付前 | 交付报告可追溯需求、代码、测试、验证命令和剩余风险 | 不声明完成 |

## 交付前

交付前按 `docs/verification-matrix.md` 执行验证，并把结果写入 delivery report：

1. Build command。
2. Test command 或 focused test command。
3. Start command。
4. API verification method。
5. SQL / DDL / dev-test 数据验证。
6. Not-tested 项、原因、替代验证和剩余风险。

可运行：

```bash
python3 .ai-coding-java/scripts/evidence_check.py .ai-coding-java/reports/delivery-report.md
```

该脚本只检查证据格式，不替代真实测试。

## 完成标准

一次开发完成测试验证，应满足：

1. 每条核心验收标准至少对应一个测试或验证证据。
2. 核心 Service 业务规则有 focused test 或明确不能补的原因。
3. Controller / VO / Mapper SQL 变更有编译、启动或接口/SQL 验证证据。
4. 数据隔离、权限、异常、边界和回归场景没有被遗漏。
5. `Not-tested` 只记录真实无法执行项，不包装成已验证。
6. 交付报告能从需求、领域类型模型、设计、架构评审、实施计划、测试、验证命令和结果追溯到同一目标。

## 反模式

1. 只写实现，不补需求测试或代码测试。
2. 用临时脚本输出代替应有的单元测试、集成测试或接口验证。
3. 只断言 mock 被调用，不断言业务结果。
4. 因为测试难写就降级成交付说明。
5. 多次返工后仍不补回归测试。
6. 把“没跑”写成“已验证”。
7. 高风险业务变更应为 L2/L3，却降级成 L1 或 L0 且没有说明。
