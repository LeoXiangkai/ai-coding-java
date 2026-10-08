# verify-probe

在开工前跑一次，确认编译、单测、服务启动、接口、数据库、前端和 e2e 各层是否具备验证
条件；在声称“已验证”前再跑一次。配置放在 `aicj/verify-profiles/`，每个实际 profile
只填写自己的路径、端点和命令。

profile 可为每层提供 `probe_cmd`。命令退出码 0 表示 RUNNABLE，1 表示 BLOCKED，2 表示
PARTIAL，其他失败表示 UNKNOWN。命令由用户提供，探测会限制超时并捕获输出。可用
`--json` 查看机器可读结果，`--brief` 只看非 RUNNABLE 层；`--from-cwd` 按 profile 根目录
匹配当前目录，`--repo backend|frontend|all` 选择范围。

字段：`backend.root`、`frontend.root`、`e2e.root` 是匹配和命令工作目录；各层的
`probe_cmd` 是待执行命令，`timeout` 可覆盖单层超时；接口层的 `url` 只是给 profile
保留的说明字段，通用探测仍由 `probe_cmd` 决定。`example.json.sample` 只是模板，不会被
当作实际 profile 加载。

BLOCKED 或 PARTIAL 只说明验证条件不足，不能据此声称验证已完成。UNKNOWN 也要先补齐
profile 或探测命令再下结论。没有 profile 时命令以退出码 2 给出提示。
