# ai-coding-java

个人可复用的企业级 Java AI Coding 新开发工程组件。

目标是用轻量入口标准化项目初始化、规则路由、验证矩阵和 Review 口径，让企业级 Java 开发更准确、更快捷、更安全。

## 入口

1. Codex 项目入口：[AGENTS.md](AGENTS.md)
2. Claude Code 项目入口：[CLAUDE.md](CLAUDE.md)
3. 总纲：[docs/ai-coding-java-standard-v1.md](docs/ai-coding-java-standard-v1.md)
4. 轻量规则索引：[docs/rule-index.md](docs/rule-index.md)
5. 工作流路由：[docs/workflow-routing.md](docs/workflow-routing.md)
6. 验证矩阵：[docs/verification-matrix.md](docs/verification-matrix.md)
7. 测试验证流程：[docs/testing-workflow.md](docs/testing-workflow.md)
8. Project Harness：[docs/project-harness.md](docs/project-harness.md)
9. 项目初始化模板：[docs/project-onboarding-template.md](docs/project-onboarding-template.md)
10. Review 输出模板：[docs/review-output-template.md](docs/review-output-template.md)
11. 项目接入指南：[docs/project-integration-guide.md](docs/project-integration-guide.md)
12. 自动 Review 指南：[docs/auto-review-guide.md](docs/auto-review-guide.md)
13. Git 策略：[docs/git-policy.md](docs/git-policy.md)
14. 知识沉淀指南：[docs/knowledge-guide.md](docs/knowledge-guide.md)
15. 运行时技能边界：[docs/runtime-skill-boundary.md](docs/runtime-skill-boundary.md)
16. Git Hooks 指南：[docs/git-hooks-guide.md](docs/git-hooks-guide.md)
17. 远程托管指南：[docs/remote-hosting-guide.md](docs/remote-hosting-guide.md)
18. 研发一体化轻量流程：[docs/rd-integrated-workflow.md](docs/rd-integrated-workflow.md)
19. SDD 参考分析：[docs/sdd-reference-analysis.md](docs/sdd-reference-analysis.md)
20. 研发过程产物目录：[artifacts/](artifacts/)
21. 企业知识库：[knowledge/](knowledge/)
22. 规则文件：[rules/](rules/)
23. 工作流：[workflow/agent-workflow.md](workflow/agent-workflow.md)
24. 交付模板：[templates/](templates/)
25. 接入说明：[USAGE.md](USAGE.md)
26. 组件边界：[TOOL.md](TOOL.md)

## 原则

1. 项目规则优先：最近的 `AGENTS.md` 是执行入口。
2. 技术栈初始化确认：从建议项选择或自定义输入，不强制迁移项目栈。
3. 按需加载：小任务优先读取 `rule-index.md` 和命中的专项文件。
4. 轻量辅助：初始化后自动安装 Git `pre-commit` 和 `pre-push` 预检。
5. 证据交付：能验证的必须验证，不能验证的写入 `Not-tested`。
6. 研发一体化按需使用：复杂需求可生成轻量过程产物，小任务继续走规则索引。
7. 表达正向：README 和能力状态只写已落地、边界清晰、后续增强，外部经验必须转化为适合当前组件的能力和边界。
8. 完整实现：按真实目标完成设计、实现和测试，不避重就轻、不用临时脚本兜底替代应有能力。

## Skill

通用初始化入口使用 `$setup-ai-coding`。历史 `$setup-cc` 保留为兼容别名，不再作为新规范名称。

常规开发中的技能发现和 `$skill` 调用由全局 Codex、Claude Code 或 OMX 运行时处理；本组件只提供项目内 Java 规则、验证矩阵、Review 口径和交付模板。

## 校验

```bash
python3 scripts/context_budget_check.py
python3 scripts/template_integrity_check.py
python3 scripts/structure_check.py
python3 scripts/docs_tone_check.py
python3 scripts/evidence_check.py examples/delivery-report.example.md
python3 scripts/static_review_check.py examples/static-review-good
```

## 如何使用

### 1. 维护

修改 `docs/`、`rules/`、`workflow/`、`templates/`、`scripts/` 后，至少运行：

```bash
python3 scripts/context_budget_check.py
python3 scripts/template_integrity_check.py
python3 scripts/structure_check.py
python3 scripts/docs_tone_check.py
```

### 2. 初始化到目标 Java 项目

```bash
python3 /path/to/ai-coding-java/scripts/init_target_project.py /path/to/target-project \
  --project-type legacy \
  --stack "Java 8 + Spring Boot 2.x + Maven + MyBatis + MySQL + Redis" \
  --verification-level standard \
  --template-policy local-auxiliary \
  --data-boundary "school + school_year"
```

初始化后先运行 doctor：

```bash
python3 /path/to/target-project/.ai-coding-java/scripts/check_target_project.py /path/to/target-project
```

### 3. 目标项目日常开发

目标项目根 `AGENTS.md` 和 `CLAUDE.md` 会指向：

```text
.ai-coding-java/docs/rule-index.md
```

日常任务按以下方式使用：

```text
小任务：读 rule-index -> 命中专项规则 -> 修改代码 -> 按 verification-matrix 验证 -> delivery report
复杂需求：补 requirement/design/test-plan/test-case/release/handoff 轻量产物 -> 按产研测测试验证 workflow 实现和验证 -> Review
```

### 4. 可选辅助检查

```bash
# 留存目标接入 doctor 报告
python3 .ai-coding-java/scripts/check_target_project.py . --report markdown

# 生成存量项目代码地图
python3 .ai-coding-java/scripts/generate_project_map.py .

# 升级已有目标模板前 dry-run
python3 /path/to/ai-coding-java/scripts/refresh_target_project.py . --list-extra

# 检查复杂需求过程产物
python3 .ai-coding-java/scripts/artifact_consistency_check.py .ai-coding-java/artifacts/<work-id>

# 检查交付报告证据
python3 .ai-coding-java/scripts/evidence_check.py .ai-coding-java/reports/delivery-report.md
```

详细接入说明见 [docs/project-integration-guide.md](docs/project-integration-guide.md)。

## Harness 能力状态

```text
已落地：新项目初始化、存量项目注入、技术栈确认、规则识别、按需路由、轻量 Git 保护、复杂需求留痕、目标项目只读检查
已落地：产研测测试验证 workflow、Doctor 报告、组件结构命名检查、复杂需求产物一致性只读检查、交付证据检查、模板刷新 dry-run、轻量项目画像
边界清晰：业务代码实现、全局 skill 编排、采集上报、评分平台、外部发布平台由项目或运行时负责
后续增强：结构化 JSON 画像、细粒度 merge/update
```

## 当前落地状态

Phase 1 已提供最小可用模板包：

```text
docs/       总纲、规则索引、验证矩阵、项目初始化、Review 输出
rules/      Java 分层、SQL、事务、安全日志、交付、Review 分级
workflow/   Agent 执行路由
templates/  任务、Review、业务规则、交付报告、ADR 模板
```

Phase 2 已提供项目接入脚本、项目画像模板、AGENTS snippet 和示例文件。

Phase 3 已提供轻量确定性 Review 脚本和自动 Review 指南。

Phase 4 已提供企业知识库目录、知识条目模板和交付报告到知识候选的提取脚本。

Phase 5 已提供研发一体化轻量流程、过程产物目录和需求/设计/测试/发布影响模板。

Phase 6 已提供自动安装的轻量 Git hooks：`pre-commit` 做 P0 确定性扫描，`pre-push` 做个人开发分支和验证命令预检。

Phase 7 已完成 SDD / Agent Skill 机制分析和 forge 加固：

```text
docs/sdd-reference-analysis.md              记录可转化机制、收益、流程影响和取舍
templates/requirements-checklist-template.md 复杂需求前置澄清 checklist
templates/handoff-template.md               跨会话、跨 Agent、提测前交接模板
```

Phase 7 只把 checklist、handoff 和一致性分析作为复杂需求可选增强，不改变小任务的默认轻量流程。

Phase 8 已补齐 Project Harness 层：

```text
docs/project-harness.md          定义初始化、注入、适配、路由、保护、检查的职责边界
docs/documentation-tone-and-reuse.md 约束首页能力表达和外部经验转化方式
docs/testing-workflow.md         定义产研测一体化测试验证、需求测试、单元测试、集成/API/SQL 验证和交付前证据链路
templates/test-plan-template.md  复杂需求测试计划模板，映射验收标准和各层测试证据
scripts/check_target_project.py  只读检查目标项目注入完整性、入口 marker、profile 和 hooks
scripts/docs_tone_check.py       检查 README 和文档中的反向能力表达
scripts/evidence_check.py        检查交付报告是否包含验证证据和 Not-tested 说明
scripts/generate_project_map.py  只读生成目标 Java 项目代码地图
scripts/refresh_target_project.py dry-run 比对目标模板缺失、差异和额外文件
scripts/structure_check.py       检查组件自身文件分层和命名风格
scripts/artifact_consistency_check.py 检查复杂需求过程产物一致性
```

Phase 8 仍保持轻量策略：当前提供 check/doctor、dry-run refresh、evidence check 和 project map，不提供复杂 merge/update 子命令；升级前先检查，避免误覆盖目标项目自定义内容。

远程托管兼容 GitHub 和 Gitee。推荐 `origin` 指向 GitHub，`gitee` 指向 Gitee，双端保持同一个 `main` 分支。

目标工程识别规则：

```text
Codex: 根 AGENTS.md 必须指向 .ai-coding-java/docs/rule-index.md
Claude Code: 根 CLAUDE.md 必须指向 .ai-coding-java/docs/rule-index.md，或明确委托读取 AGENTS.md
```

`scripts/init_target_project.py` 会写入上述根入口 marker，初始化后默认可被 Codex 和 Claude Code 识别。
