---
name: python-verify
description: Python 项目的探测、ruff/类型检查、相关 pytest、启动日志和真实接口自测入口。
---

# Python 本地自测

按证据顺序执行；使用项目既有解释器/环境，本组件不创建或激活新的环境：

1. **探测**：运行 `scripts/detect_python.py <project_dir>`，记录依赖管理器、Python 要求、框架、ORM、迁移、工具、入口和生成命令。
2. **静态检查**：运行 `scripts/static_review.py <changed paths>`；先处理 P0，再处理 P1。按探测结果运行 `ruff check`，若项目启用了格式检查，再运行 `ruff format --check`。
3. **类型检查**：仅当项目配置了 mypy 或 pyright 时运行对应命令；未配置不人为添加工具。
4. **相关单测**：运行探测出的 pytest 命令和受影响测试；不得用 `-k` 或跳过选项制造通过，不能把未执行当作通过。
5. **启动与日志**：FastAPI 按探测入口运行 `uvicorn <module>:app`，Flask 运行 `flask --app <module> run`；以探测结果为准，无法确定入口则记录 `MISSING`。观察启动日志并处理 ERROR、Exception 和异常堆栈。
6. **接口改动**：用真实开发/测试数据 curl 至少一次，记录状态码、关键响应字段和数据来源；没有真实数据时明确写未验证。
7. **汇报**：分别列出探测、ruff、格式、类型、pytest、启动日志、接口和未覆盖项的命令、退出码与证据。

命令前缀按包管理器：uv 使用 `uv run`，poetry 使用 `poetry run`，pip 使用直接 `python -m`。若已安装，可引用组件外的 code-review 或其他 skill；未安装时降级为本清单和人工复核，不把引用能力当作验证证据。
