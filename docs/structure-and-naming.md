# Structure And Naming v1.1

本文件定义 `ai-coding-java` 组件自身的文件分层和命名规则。目标是让组件长期保持可扫描、可维护、可注入。

## 分层

| 目录 | 职责 | 命名风格 |
|---|---|---|
| `docs/` | 标准、指南、边界、流程、策略 | kebab-case `.md` |
| `rules/` | Java、SQL、事务、安全、交付、Review 规则 | kebab-case `.md` |
| `workflow/` | Agent 执行流 | kebab-case `.md` |
| `templates/` | 可复制到目标项目的过程产物模板 | kebab-case，后缀 `-template.md` |
| `scripts/` | 本组件和目标项目安全脚本 | snake_case `.py` |
| `hooks/` | Git hook 源文件 | Git hook 标准名 |
| `artifacts/` | 目标项目过程产物目录说明 | `README.md` 为入口 |
| `knowledge/` | 可复用规则、案例和经验 | 分类目录 + kebab-case `.md` |
| `examples/` | 脱敏示例和测试夹具 | 与示例目标一致 |

## 命名规则

1. Markdown 文档默认使用小写 kebab-case，例如 `project-harness.md`。
2. 模板文件必须以 `-template.md` 结尾，例如 `handoff-template.md`。
3. Python 脚本使用 snake_case，例如 `check_target_project.py`。
4. Git hooks 使用 Git 标准名，例如 `pre-commit`、`pre-push`。
5. 根入口文件保留常规大写命名：`README.md`、`AGENTS.md`、`CLAUDE.md`、`TOOL.md`、`USAGE.md`。
6. 示例文件可以保留运行时识别需要的大写片段，例如 `AGENTS.ai-coding-java-snippet.example.md`。

## 文件放置原则

1. 可复用规范放 `docs/`、`rules/`、`workflow/`。
2. 可复制产物骨架放 `templates/`。
3. 可执行检查放 `scripts/`，且必须无第三方依赖。
4. 目标项目生成物默认落 `.ai-coding-java/`，不落业务根目录。
5. 运行日志、当前任务笔记、未脱敏知识候选不入库。

## 检查

组件内运行：

```bash
python3 scripts/structure_check.py
```

目标：

1. 检查关键目录是否存在。
2. 检查文件名是否符合对应目录风格。
3. 检查模板后缀和脚本后缀。
4. 检查不应入库的运行目录是否未出现在 Git 跟踪文件中。

命名检查只覆盖可稳定判断的规则。历史上有明确语义的少量文件名可以保留，但新增文件应按本文件执行。
