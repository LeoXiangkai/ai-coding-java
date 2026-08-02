# Project Harness v1.1

本文件定义 `ai-coding-java` 的 project harness 层。Harness 不是项目名称，也不是运行时技能；它是把 Java AI Coding 规则安全接入目标项目的初始化、注入、识别、保护和检查层。

## 目标

1. 新项目能快速获得统一的 AI Coding 入口、规则、模板和轻量预检。
2. 存量项目能接入 `.ai-coding-java/`，不破坏原有业务代码和项目规则。
3. Codex 和 Claude Code 初始化后能识别同一套项目规则。
4. 复杂需求有过程产物位置，小任务继续保持轻量路由。
5. 后续升级前能先做只读检查，避免盲目覆盖。

## 职责边界

Harness 负责：

1. 初始化 `.ai-coding-java/` 目录。
2. 向目标根 `AGENTS.md` 和 `CLAUDE.md` 写入 bounded marker block。
3. 生成 `project-profile.md`，记录技术栈、验证等级、数据边界和模板策略。
4. 安装目标项目本地 Git hooks。
5. 提供目标项目只读检查脚本和 doctor 报告。
6. 提供模板刷新 dry-run、交付证据检查和轻量项目画像。
7. 保持 Codex / Claude Code 入口一致。

协作边界：

1. 全局 `$skill` 发现、模型选择和运行时编排由 Codex、Claude Code 或 OMX 负责。
2. 业务项目自己的架构、权限、数据边界和发布规则由目标项目负责。
3. 业务代码修改由具体开发任务按项目规则执行，Harness 只注入辅助规则、模板和检查脚本。
4. 研发过程产物按需生成，小任务继续走轻量规则路由。
5. 采集上报、评分平台和外部治理平台对接由目标项目或外部平台负责。
6. 生产部署、数据库变更执行和远程平台发布由目标项目发布机制负责。

## 能力矩阵

| 能力 | 状态 | 当前入口 | 说明 |
|---|---|---|---|
| 新项目初始化 | 已落地 | `scripts/init_target_project.py --project-type new` | 注入 `.ai-coding-java/` 和根入口 marker |
| 存量项目注入 | 已落地 | `scripts/init_target_project.py --project-type legacy` | 默认保留已有文件，除 marker block 外不改业务代码 |
| 技术栈确认 | 已落地 | `--stack`、`project-profile.md` | 由初始化参数或人工补全确认 |
| 规则识别 | 已落地 | `AGENTS.md` / `CLAUDE.md` marker | 指向 `.ai-coding-java/docs/rule-index.md` |
| 按需路由 | 已落地 | `docs/rule-index.md` | 小任务只加载命中文件 |
| 轻量保护 | 已落地 | `hooks/pre-commit`、`hooks/pre-push` | 默认 warn，P0 commit 风险可阻断 |
| 复杂需求留痕 | 已落地 | `artifacts/`、`templates/` | 按需使用，不默认门禁 |
| 编码前设计门 | 已落地 | `docs/design-first-policy.md`、`templates/design-brief-template.md` | 新项目要求宏观/微观设计，二开要求模块和影响设计，不完整先补设计 |
| 产研测测试验证 workflow | 已落地 | `docs/testing-workflow.md`、`docs/tdd-policy.md`、`templates/test-plan-template.md` | 编码前映射验收标准、TDD 等级和验证层级，编码中同步测试，交付前核验证据 |
| 目标项目检查 | 已落地 | `scripts/check_target_project.py` | 只读检查注入完整性和关键缺口 |
| Doctor 报告 | 已落地 | `check_target_project.py --report markdown/json` | 输出可评审的目标接入检查记录 |
| 产物一致性检查 | 已落地 | `scripts/artifact_consistency_check.py` | 只读检查复杂需求过程产物是否互相追溯 |
| 交付证据检查 | 已落地 | `scripts/evidence_check.py` | 检查 delivery report 是否包含验证命令、结果和 Not-tested |
| 组件结构检查 | 已落地 | `scripts/structure_check.py` | 检查本组件文件分层和命名风格 |
| 安全刷新 | 已落地 | `scripts/refresh_target_project.py --list-extra` | 默认 dry-run，比对缺失、差异和目标侧额外文件，`--apply` 才复制 |
| 轻量项目画像 | 已落地 | `scripts/generate_project_map.py` | 只读扫描 Controller、Service、Mapper、配置和定时任务信号 |
| 结构化画像 | 后续增强 | `project-profile.md` | 当前是稳定文本和 Markdown 画像，后续再考虑 JSON |
| 外部治理对接 | 边界清晰 | 目标项目 / 外部平台 | 平台接入由目标项目按需完成，组件保留本地轻量检查 |

## 初始化模式

新项目：

```bash
python3 scripts/init_target_project.py /path/to/project \
  --project-type new \
  --stack "Java 8 + Spring Boot 2.x + Maven + MyBatis + MySQL + Redis"
```

存量项目：

```bash
python3 scripts/init_target_project.py /path/to/project \
  --project-type legacy \
  --template-policy local-auxiliary
```

初始化脚本默认：

1. 复制 `docs/`、`rules/`、`workflow/`、`templates/`、`knowledge/`、`artifacts/`、`hooks/`。
2. 复制目标安全脚本到 `.ai-coding-java/scripts/`。
3. 生成 `project-profile.md`。
4. 写入根 `AGENTS.md` 和 `CLAUDE.md` marker。
5. 在 Git 仓库中安装 `pre-commit` 和 `pre-push` wrapper。
6. 目标安全脚本默认放在 `.ai-coding-java/scripts/`。

## 只读检查

初始化后运行：

```bash
python3 .ai-coding-java/scripts/check_target_project.py .
```

检查内容：

1. `.ai-coding-java/` 关键文件是否存在。
2. 根 `AGENTS.md` 和 `CLAUDE.md` 是否包含 marker 并指向 `rule-index.md`。
3. `project-profile.md` 必需字段是否完整，推荐字段是否仍需补充。
4. Git hooks 是否安装。
5. 设计门、TDD 分级、测试计划、复杂需求模板和交付模板是否存在。

检查脚本只读，不修改目标项目。失败项用于提示补全，不代表业务代码不可开发。

需要留存检查结果时：

```bash
python3 .ai-coding-java/scripts/check_target_project.py . --report markdown
python3 .ai-coding-java/scripts/check_target_project.py . --report json
```

报告默认写入 `.ai-coding-java/reports/`。

复杂需求产物检查：

```bash
python3 .ai-coding-java/scripts/artifact_consistency_check.py .ai-coding-java/artifacts/<work-id>
```

该检查确认需求、领域类型模型、设计、架构评审、实施计划、测试计划、测试用例、发布影响和交接文件是否存在关键章节、Work ID 是否一致、测试是否引用需求、类型模型、设计、架构评审和实施计划。它只读报告缺口，不强制小任务生成产物。

交付证据检查：

```bash
python3 .ai-coding-java/scripts/evidence_check.py .ai-coding-java/reports/delivery-report.md
```

该检查确认交付报告包含 Summary、Verification、Not-tested，并且 Verification 中有命令和结果。

目标项目画像：

```bash
python3 .ai-coding-java/scripts/generate_project_map.py .
```

默认写入 `.ai-coding-java/project-map.md`。它只读扫描 Java、Mapper XML 和应用配置文件，用于老项目注入后的快速导航。

## 更新策略

当前推荐策略：

1. 先运行只读检查，明确目标项目缺什么。
2. 小版本模板升级先从新版组件源运行 `refresh_target_project.py --list-extra`，明确缺失、差异和目标侧额外文件。
3. 只在确认差异属于通用模板升级时使用 `refresh_target_project.py --apply`。
4. 重新运行初始化脚本仍保持已有文件跳过；需要整体覆盖时才使用 `--force`。
5. 项目自己的 `AGENTS.md`、`CLAUDE.md`、`project-profile.md` 和业务规则优先于通用建议。

暂不提供复杂 merge/update 子命令。原因是本组件目标是轻量辅助，当前用 dry-run 和显式 apply 控制升级风险。

## 完成标准

一个目标项目完成 harness 接入，应满足：

1. 根 `AGENTS.md` 能把 Codex 路由到 `.ai-coding-java/docs/rule-index.md`。
2. 根 `CLAUDE.md` 能把 Claude Code 路由到同一规则入口，或明确委托读取 `AGENTS.md`。
3. `project-profile.md` 已确认技术栈、验证等级、数据边界和 Hook 模式；推荐字段按项目阶段补齐或说明不适用。
4. Git 仓库已安装 hooks，非 Git 目录明确跳过。
5. 小任务可通过 `rule-index` 快速命中专项规则。
6. 复杂需求可按需使用 `artifacts/<work-id>/` 产物模板，并用 `design-brief.md` 证明新项目宏观/微观设计或二开模块/影响设计完整。
7. 可用 `test-plan.md` 建立验收标准、TDD 等级到测试证据的映射。
8. 存量项目可生成 `project-map.md` 辅助代码定位。
9. 需要交付证据门禁时可运行 `evidence_check.py`。
