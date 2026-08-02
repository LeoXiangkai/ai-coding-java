# ai-coding-java

个人可复用的企业级 Java AI Coding 工程组件。

目标：把项目初始化、规则路由、编码前设计、测试验证、Review 和轻量 Git 保护收敛到一套可被 Codex 与 Claude Code 识别的项目规则，减少返工和误改。

## 快速入口

1. 组件维护入口：`AGENTS.md`、`CLAUDE.md`
2. 目标项目规则入口：`docs/rule-index.md`
3. 执行主流程：`workflow/agent-workflow.md`
4. 编码前设计门：`docs/design-first-policy.md`
5. 测试与 TDD：`docs/testing-workflow.md`、`docs/tdd-policy.md`
6. 最低验证：`docs/verification-matrix.md`
7. 复杂需求链路：`docs/rd-integrated-workflow.md`
8. 接入与能力边界：`docs/project-integration-guide.md`、`docs/project-harness.md`

## 使用方式

初始化到目标 Java 项目：

```bash
python3 /path/to/ai-coding-java/scripts/init_target_project.py /path/to/target-project \
  --project-type legacy \
  --stack "Java 8 + Spring Boot 2.x + Maven + MyBatis + MySQL + Redis" \
  --verification-level standard \
  --template-policy local-auxiliary \
  --data-boundary "school + school_year"
```

初始化后检查：

```bash
python3 /path/to/target-project/.ai-coding-java/scripts/check_target_project.py /path/to/target-project
```

目标项目日常开发：

```text
小任务：AGENTS/CLAUDE -> rule-index -> 命中规则 -> 实现 -> verification-matrix -> delivery report
复杂需求：Requirement -> Domain/Type -> Design -> Architecture Review -> Plan/Test -> Implement -> Verify/Review -> Release
```

## OPC 模式

OPC 指个人主导的快速交付模式。默认策略是轻量、可验证、不中断节奏：

1. 小任务不生成完整研发产物，但必须说明影响和验证。
2. 新项目、完整模块、二开改造和影响不清的行为变更必须先过设计门。
3. 高风险业务点按 TDD L2/L3 执行；普通任务用测试计划或验证清单即可。
4. Git hooks 默认 warn，P0 确定性问题在 commit 前拦截。
5. 无法验证的内容写入 `Not-tested`，不包装成已验证。

## 核心能力

已落地：

1. 新项目初始化、存量项目注入、技术栈确认和 Codex/Claude 入口 marker。
2. 轻量规则索引、Java/Spring/MyBatis/SQL/事务/安全/交付规则。
3. 编码前设计门：新项目宏观/微观设计，二开模块/影响设计。
4. 产研测测试验证 workflow、TDD 分级、验证矩阵和交付证据模板。
5. 自动安装轻量 Git hooks、目标项目 doctor、模板刷新 dry-run、项目画像、复杂需求产物一致性检查。

边界清晰：

1. 全局 skill 编排、模型选择、提测部署、外部平台发布由 Codex、Claude Code、OMX 或目标项目负责。
2. 业务规则、接口契约、数据隔离和环境命令以目标项目最近的 `AGENTS.md` / `CLAUDE.md` / `project-profile.md` 为准。
3. 复杂需求产物按需生成，不作为小任务默认门禁。

后续增强：

1. 结构化项目画像。
2. 更细粒度的目标模板合并与更新。
3. 更强的复杂需求产物一致性检查。

## 组件维护校验

```bash
python3 scripts/context_budget_check.py
python3 scripts/template_integrity_check.py
python3 scripts/structure_check.py
python3 scripts/docs_tone_check.py
python3 scripts/evidence_check.py examples/delivery-report.example.md
python3 scripts/static_review_check.py examples/static-review-good
```

更多说明：

1. 接入指南：`docs/project-integration-guide.md`
2. Harness 边界：`docs/project-harness.md`
3. Git hooks：`docs/git-hooks-guide.md`
4. 远程托管：`docs/remote-hosting-guide.md`
