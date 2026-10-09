# 外部执行体契约

调用形态：

```text
aicj-worker --cd <worktree> --tier high|mid|low [--engine claude|codex] [--dry-run] "<prompt>"
```

`--cd` 必须指向 Git linked worktree，不能指向主工作区。档位只表达任务所需能力；模型由本机环境决定。退出码含义：`0` 表示执行完成（无效超时配置会在 stderr 报错并按不限制继续），`2` 表示参数错误或 worktree 校验失败，`124` 表示达到 `AICJ_EXECUTOR_TIMEOUT` 秒限制，`127` 表示引擎 CLI 不在 PATH，其他非零值表示引擎返回了非零退出码。

任何非零退出都按 `core/rules/executor-handoff.md` 的降级条款改派子代理。外部执行体禁止 commit、push 和派子代理；主会话必须独立核实执行体汇报。

Claude 引擎可通过 `AICJ_EXECUTOR_BASE_URL`、`AICJ_EXECUTOR_TOKEN` 接入本机 Anthropic 兼容 CPA，并可用 `AICJ_EXECUTOR_CONFIG_DIR` 指定隔离的 Claude 配置目录；未指定时使用安装目录下的 `aicj/worker-home`。启动前会请求 `/v1/models`，凭据缺失或后端不可达退出 69，且不会启动引擎。`--dry-run` 不请求网络，只显示 BASE_URL（不显示 token）。

接入自有执行体时，只需提供同一 CLI 形态，或让 `AICJ_EXECUTOR_ENGINE` 选择本适配支持的引擎。环境变量 `AICJ_EXECUTOR_MODEL_HIGH`、`AICJ_EXECUTOR_MODEL_MID`、`AICJ_EXECUTOR_MODEL_LOW` 可按档位传递本机模型标识；不设置时使用引擎默认值。codex 引擎按档位传推理强度（high/medium/low），沙箱默认 `danger-full-access`（与 claude 引擎跳过权限确认对齐，构建需要网络与本机缓存目录），可用 `AICJ_EXECUTOR_CODEX_SANDBOX` 收紧为 `workspace-write`。执行体 stdin 固定为空，避免后台调用时等待输入挂死。

`AICJ_EXECUTOR_TIMEOUT` 是可选正数秒数；留空或未设置表示不限制。Claude 的 prompt 位于 `--` 后，避免被多值 `--disallowedTools Agent` 吞掉。
