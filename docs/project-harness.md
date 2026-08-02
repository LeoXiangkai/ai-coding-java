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
5. 提供目标项目只读检查脚本。
6. 保持 Codex / Claude Code 入口一致。

Harness 不负责：

1. 全局 `$skill` 发现、模型选择或运行时编排。
2. 替代业务项目自己的架构、权限、数据边界和发布规则。
3. 自动修改业务代码。
4. 强制生成所有研发过程产物。
5. 采集上报、评分平台或外部治理平台绑定。
6. 生产部署、数据库变更执行或远程平台发布。

## 能力矩阵

| 能力 | 状态 | 当前入口 | 说明 |
|---|---|---|---|
| 新项目初始化 | 已支持 | `scripts/init_target_project.py --project-type new` | 注入 `.ai-coding-java/` 和根入口 marker |
| 存量项目注入 | 已支持 | `scripts/init_target_project.py --project-type legacy` | 默认保留已有文件，除 marker block 外不改业务代码 |
| 技术栈确认 | 已支持 | `--stack`、`project-profile.md` | 由初始化参数或人工补全确认 |
| 规则识别 | 已支持 | `AGENTS.md` / `CLAUDE.md` marker | 指向 `.ai-coding-java/docs/rule-index.md` |
| 按需路由 | 已支持 | `docs/rule-index.md` | 小任务只加载命中文件 |
| 轻量保护 | 已支持 | `hooks/pre-commit`、`hooks/pre-push` | 默认 warn，P0 commit 风险可阻断 |
| 复杂需求留痕 | 已支持 | `artifacts/`、`templates/` | 按需使用，不默认门禁 |
| 目标项目检查 | 已支持 | `scripts/check_target_project.py` | 只读检查注入完整性和关键缺口 |
| 产物一致性检查 | 已支持 | `scripts/artifact_consistency_check.py` | 只读检查复杂需求过程产物是否互相追溯 |
| 组件结构检查 | 已支持 | `scripts/structure_check.py` | 检查本组件文件分层和命名风格 |
| 安全刷新 | 部分支持 | `init_target_project.py --force` | 当前仅有跳过/覆盖，不提供细粒度 merge |
| 结构化画像 | 部分支持 | `project-profile.md` | 当前是稳定文本字段，未引入 JSON |
| 采集上报 | 不支持 | 无 | 有意不做，保持个人轻量组件定位 |

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

## 只读检查

初始化后运行：

```bash
python3 .ai-coding-java/scripts/check_target_project.py .
```

检查内容：

1. `.ai-coding-java/` 关键文件是否存在。
2. 根 `AGENTS.md` 和 `CLAUDE.md` 是否包含 marker 并指向 `rule-index.md`。
3. `project-profile.md` 是否仍有未确认的关键字段。
4. Git hooks 是否安装。
5. 复杂需求模板和交付模板是否存在。

检查脚本只读，不修改目标项目。失败项用于提示补全，不代表业务代码不可开发。

复杂需求产物检查：

```bash
python3 .ai-coding-java/scripts/artifact_consistency_check.py .ai-coding-java/artifacts/<work-id>
```

该检查确认需求、设计、测试、发布影响和交接文件是否存在关键章节、Work ID 是否一致、测试是否引用需求和设计。它只读报告缺口，不强制小任务生成产物。

## 更新策略

当前推荐策略：

1. 先运行只读检查，明确目标项目缺什么。
2. 小版本模板升级优先重新运行初始化脚本，让已存在文件保持跳过。
3. 需要覆盖通用模板时才使用 `--force`，并先确认目标项目没有本地改写。
4. 项目自己的 `AGENTS.md`、`CLAUDE.md`、`project-profile.md` 和业务规则优先于通用建议。

暂不提供复杂 merge/update 子命令。原因是本组件目标是轻量辅助，过早做自动合并会引入误覆盖风险。

## 完成标准

一个目标项目完成 harness 接入，应满足：

1. 根 `AGENTS.md` 能把 Codex 路由到 `.ai-coding-java/docs/rule-index.md`。
2. 根 `CLAUDE.md` 能把 Claude Code 路由到同一规则入口，或明确委托读取 `AGENTS.md`。
3. `project-profile.md` 已确认技术栈、验证等级、数据边界、构建/测试/启动命令或缺失原因。
4. Git 仓库已安装 hooks，非 Git 目录明确跳过。
5. 小任务可通过 `rule-index` 快速命中专项规则。
6. 复杂需求可按需使用 `artifacts/<work-id>/` 产物模板。
