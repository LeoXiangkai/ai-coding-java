# ai-coding-java Verification Matrix v1.1

验证目标：证明本次变更可运行、行为正确、风险已暴露。不能执行的验证必须写入 `Not-tested`。

## 最小验证矩阵

| 变更 | 必做验证 | 失败或不可执行时 |
|---|---|---|
| Java 纯逻辑 | 编译 + focused test | 说明失败日志或缺失测试框架 |
| Service 业务规则 | focused test，必要时集成测试 | 补回归测试或说明不能补的原因 |
| 多表写 | 编译 + 测试 + 事务路径检查 | 标注 P0，不允许假装已验证 |
| Controller / VO | 编译 + 本地启动 + curl | 无法启动时做编译/测试，并报告未 curl |
| Mapper XML / SQL | 编译 + 真实数据/接口验证，必要时 explain | 无数据时做静态检查并报告缺失数据 |
| DDL / 数据脚本 | dev/test 执行 + post-state 查询 | 目标不明确时不得执行破坏性操作 |
| 配置变更 | 启动或读取实际配置路径 | 说明环境差异和回滚方式 |
| 缓存 / 异步 / 定时 | 幂等、一致性、重复执行验证 | 报告剩余一致性风险 |

## 验证等级

```text
轻量：compile 或局部测试，适合文档、小配置、小 bugfix。
标准：compile + focused test + 必要接口/SQL 验证。
严格：标准验证 + 本地启动 + curl + 真实 dev/test 数据或环境验证。
```

项目初始化时必须选择默认等级；任务可以因风险临时升级。

## Not-tested 格式

```text
Not-tested:
- 未执行：
- 原因：
- 已替代验证：
- 剩余风险：
```

## Controller / VO / Mapper 特例

涉及 Controller、VO、Mapper SQL 的业务变更，标准验证是：

```text
compile
focused test
local start
curl endpoint with dev/test data
```

无法满足时，不阻塞文档记录，但必须明确缺失证据，不能写“验证通过”。

