# Git Hooks Guide v1.1

ai-coding-java 初始化到 Git 项目时会自动安装一个轻量 `pre-commit` hook。

目标：在提交前拦截确定性 P0 风险，同时避免把 hooks 做成复杂流程、度量系统或平台绑定。

## 自动安装

初始化脚本默认执行：

```bash
python3 .ai-coding-java/scripts/install_git_hooks.py .
```

如果目标目录不是 Git 仓库，安装器会跳过，不影响 `.ai-coding-java/` 规则注入。

## Hook 行为

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

## 当前检查

1. 疑似明文密钥或凭据。
2. MyBatis `${}` 动态拼接。
3. `update/delete` 缺少 `where`。
4. `@Transactional` 缺少 `rollbackFor`。

## 兼容已有 Hook

如果目标仓库已经有 `.git/hooks/pre-commit`：

1. 安装器会把原文件移动到 `.git/hooks/pre-commit.before-ai-coding-java.<timestamp>`。
2. 新 wrapper 先执行 ai-coding-java hook。
3. ai-coding-java 放行后再执行旧 hook。

这样既能自动安装，也不会丢失项目已有 hook。

## 手动重装

```bash
python3 .ai-coding-java/scripts/install_git_hooks.py . --force
```

## 边界

本阶段不安装：

1. `pre-push` 编译/测试 hook。
2. `commit-msg` 交付证据检查。
3. Claude Code `PreToolUse` 编辑拦截。
4. 文档审批门禁。
5. 统计、度量、通知或外部平台上报。

这些属于后续可选增强，不进入第一阶段默认安装。
