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
7. 项目初始化模板：[docs/project-onboarding-template.md](docs/project-onboarding-template.md)
8. Review 输出模板：[docs/review-output-template.md](docs/review-output-template.md)
9. 项目接入指南：[docs/project-integration-guide.md](docs/project-integration-guide.md)
10. 自动 Review 指南：[docs/auto-review-guide.md](docs/auto-review-guide.md)
11. Git 策略：[docs/git-policy.md](docs/git-policy.md)
12. 知识沉淀指南：[docs/knowledge-guide.md](docs/knowledge-guide.md)
13. 运行时技能边界：[docs/runtime-skill-boundary.md](docs/runtime-skill-boundary.md)
14. Git Hooks 指南：[docs/git-hooks-guide.md](docs/git-hooks-guide.md)
15. 远程托管指南：[docs/remote-hosting-guide.md](docs/remote-hosting-guide.md)
16. 研发一体化轻量流程：[docs/rd-integrated-workflow.md](docs/rd-integrated-workflow.md)
17. SDD 参考分析：[docs/sdd-reference-analysis.md](docs/sdd-reference-analysis.md)
18. 研发过程产物目录：[artifacts/](artifacts/)
19. 企业知识库：[knowledge/](knowledge/)
20. 规则文件：[rules/](rules/)
21. 工作流：[workflow/agent-workflow.md](workflow/agent-workflow.md)
22. 交付模板：[templates/](templates/)
23. 接入说明：[USAGE.md](USAGE.md)
24. 组件边界：[TOOL.md](TOOL.md)

## 原则

1. 项目规则优先：最近的 `AGENTS.md` 是执行入口。
2. 技术栈初始化确认：从建议项选择或自定义输入，不强制迁移项目栈。
3. 按需加载：小任务优先读取 `rule-index.md` 和命中的专项文件。
4. 轻量辅助：初始化后自动安装 Git `pre-commit` 和 `pre-push` 预检。
5. 证据交付：能验证的必须验证，不能验证的写入 `Not-tested`。
6. 研发一体化按需使用：复杂需求可生成轻量过程产物，小任务继续走规则索引。

## Skill

通用初始化入口使用 `$setup-ai-coding`。历史 `$setup-cc` 保留为兼容别名，不再作为新规范名称。

常规开发中的技能发现和 `$skill` 调用由全局 Codex、Claude Code 或 OMX 运行时处理；本组件只提供项目内 Java 规则、验证矩阵、Review 口径和交付模板。

## 校验

```bash
python3 scripts/context_budget_check.py
python3 scripts/template_integrity_check.py
python3 scripts/static_review_check.py examples/static-review-good
```

目标项目试注入：

```bash
python3 scripts/init_target_project.py /path/to/target-project --project-type legacy
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

Phase 7 已完成 SDD / Agent Skill 借鉴分析和 forge 加固：

```text
docs/sdd-reference-analysis.md              记录可借鉴机制、收益、流程影响和取舍
templates/requirements-checklist-template.md 复杂需求前置澄清 checklist
templates/handoff-template.md               跨会话、跨 Agent、提测前交接模板
```

Phase 7 只把 checklist、handoff 和一致性分析作为复杂需求可选增强，不改变小任务的默认轻量流程。

远程托管兼容 GitHub 和 Gitee。推荐 `origin` 指向 GitHub，`gitee` 指向 Gitee，双端保持同一个 `main` 分支。

目标工程识别规则：

```text
Codex: 根 AGENTS.md 必须指向 .ai-coding-java/docs/rule-index.md
Claude Code: 根 CLAUDE.md 必须指向 .ai-coding-java/docs/rule-index.md，或明确委托读取 AGENTS.md
```

`scripts/init_target_project.py` 会写入上述根入口 marker，初始化后默认可被 Codex 和 Claude Code 识别。
