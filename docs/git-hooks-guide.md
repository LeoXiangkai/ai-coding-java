# Git Hooks Guide v1.1

ai-coding-java 初始化到 Git 项目时会自动安装轻量 Git hooks。

目标：在 commit 前拦截确定性 P0 风险，在 push 前检查个人开发分支和验证命令配置。

## 自动安装

初始化脚本默认执行：

```bash
python3 .ai-coding-java/scripts/install_git_hooks.py .
```

如果目标目录不是 Git 仓库，安装器会跳过，不影响 `.ai-coding-java/` 规则注入。

## pre-commit

`pre-commit` 只扫描 staged files：

```text
git diff --cached --name-only --diff-filter=ACMR
```

执行：

```bash
python3 .ai-coding-java/scripts/static_review_check.py --include-docs <staged files>
```

结果：

1. P0 findings: 阻断 commit。
2. P1 findings: 输出告警，允许 commit。
3. 无 findings: 放行。

当前检查：

1. 疑似明文密钥或凭据。
2. MyBatis `${}` 动态拼接。
3. `update/delete` 缺少 `where`。
4. `@Transactional` 缺少 `rollbackFor`。

## pre-push

`pre-push` 做两个预检：

1. 个人开发分支命名。
2. build/test 命令配置和 strict 模式执行。

个人开发分支约定：

```text
feature/<name>
bugfix/<name>
hotfix/<name>
refactor/<name>
chore/<name>
test/<name>
release/<version>
```

`main`、`master`、`develop`、`dev` 视为集成分支。默认 `warn` 模式只提醒，`strict` 模式阻断。

Hook mode 配置在 `.ai-coding-java/project-profile.md`：

```text
Hook mode: warn
```

也可以临时使用环境变量：

```bash
AI_CODING_HOOK_MODE=strict git push
```

`warn` 模式：

1. 检查分支命名并提醒。
2. 输出已配置的 Build/Test command。
3. 不执行 compile/test。

`strict` 模式：

1. 分支不符合约定则阻断。
2. 必须配置 Build command。
3. 执行 Build command。
4. Test command 已配置时继续执行。
5. 命令失败则阻断 push。

## 兼容已有 Hook

如果目标仓库已经有同名 Git hook：

1. 安装器会把原文件移动到 `.git/hooks/<hook>.before-ai-coding-java.<timestamp>`。
2. 新 wrapper 先执行 ai-coding-java hook。
3. ai-coding-java 放行后再执行旧 hook。

这样既能自动安装，也不会丢失项目已有 hook。

## 手动重装

```bash
python3 .ai-coding-java/scripts/install_git_hooks.py . --force
```

## 后续增强方向

1. `commit-msg` 交付证据检查。
2. Agent 编辑时安全检查。
3. 研发过程产物一致性检查。
