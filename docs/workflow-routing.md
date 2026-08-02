# ai-coding-java Workflow Routing v1.1

目标：让 Agent 快速判断本次要读什么、改什么、验什么，避免全量规范拖慢开发。

## 固定顺序

1. 读最近的 `AGENTS.md`。
2. 读用户本次任务说明。
3. 读项目画像、项目记忆或当前任务说明。
4. 用本文件识别任务类型。
5. 只加载命中的专项规则和相关代码。

`$skill` 调用、技能发现、模型选择和全局编排由 Codex、Claude Code 或 OMX 运行时处理；本组件只定义项目内 Java 规则、验证和交付口径。职责边界见 `docs/runtime-skill-boundary.md`。

## 任务类型

| 类型 | 典型输入 | 最小上下文 |
|---|---|---|
| feature | 新增功能、页面、接口、流程 | 需求、相关模块、接口/表/权限、测试验证 workflow、验证矩阵；复杂需求再读 `docs/rd-integrated-workflow.md` |
| bugfix | 修复错误、数据异常、线上问题 | 复现证据、相关代码、回归测试、测试验证 workflow、验证矩阵；复杂问题可补轻量设计和测试产物 |
| refactor | 重构、优化、拆分 | 目标边界、现有测试、兼容性约束、测试验证 workflow；中高风险重构先写设计简报 |
| sql-change | SQL 查询、Mapper XML、索引 | 表结构、数据隔离、真实数据量、验证矩阵 |
| ddl-change | 建表、改字段、数据脚本 | 环境、回滚、dev/test 执行证据 |
| config-change | 配置、开关、部署参数 | 环境差异、默认值、回滚方式 |
| release | 提测、发布、回滚 | 分支、提交、流水线、环境验证、发布影响说明 |
| review | 代码审查、方案审查 | diff、相关规则、验证结果 |

## 轻量执行流程

```text
Intake -> Scope -> Context -> Impact -> Test Plan -> Implement -> Verify -> Review -> Report
```

小改动允许合并步骤，但最终报告必须说明：

1. 修改了什么。
2. 影响了什么。
3. 执行了什么验证。
4. 未验证什么。
5. 是否有 P0/P1/P2 问题。

## 子 Agent 使用

默认单 Agent。只有以下情况才拆分：

1. 多模块只读探索可并行。
2. 实现和 Review 可独立。
3. 验证命令耗时且不依赖继续编辑。

子 Agent 必须限制范围，输出文件路径、证据和结论，不允许泛泛评价。
