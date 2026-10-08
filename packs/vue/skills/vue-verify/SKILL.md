---
name: vue-verify
description: Vue 项目的探测、lint、类型检查、单测、构建、开发启动和浏览器联调自测入口。
---

# Vue 本地自测

按证据顺序执行，所有入口先从 `package.json` 探测，不硬编码项目命令：

1. **探测**：运行 `scripts/detect_vue.py <project_dir>`，记录 Vue 主版本、构建工具、TypeScript、UI 库、状态库、测试运行器、包管理器、Playwright 和 scripts。脚本不存在或 package.json 非法时如实记录默认值。
2. **lint**：执行探测得到的 lint 命令；若脚本支持 `--max-warnings 0`，追加该参数。没有 lint 脚本报告 `MISSING`，不自行猜命令。本包不另写 JavaScript 静态检查器，以项目 eslint / vue-tsc 为准。
3. **类型检查**：优先执行 type-check 脚本（常见实现为 `vue-tsc --noEmit`）；没有入口报告 `MISSING`。
4. **单测**：按探测得到的 test 命令执行 Vitest 或 Jest。没有 test:unit / test 脚本报告 `MISSING`。
5. **构建**：执行 build 命令并保留完整输出；没有 build 脚本报告 `MISSING`。
6. **开发启动与浏览器**：执行 dev / serve 命令，等待可访问后用浏览器打开关键页面，检查控制台无错误、网络请求成功和关键业务数据已渲染。浏览器自动化使用本包的 `playwright-ui-auto` skill；若已安装 Playwright，按其 references 执行，未安装则用项目已有浏览器工具或人工打开并记录降级方式。
7. **前后端联调**：字段问题同时检查前端调用方和后端实际返回结构，确认空值、错误码、分页和 blob 错误响应的处理一致；不要只看前端类型或网络状态码。
8. **汇报**：分别列出探测、lint、类型检查、单测、构建、启动、浏览器、接口和未覆盖项的命令、退出码与证据；`MISSING` 必须如实写出。

包管理器按锁文件探测：`pnpm-lock.yaml`→pnpm，`yarn.lock`→yarn，`package-lock.json`→npm，`bun.lockb` 或 `bun.lock`→bun，无锁文件→npm。
