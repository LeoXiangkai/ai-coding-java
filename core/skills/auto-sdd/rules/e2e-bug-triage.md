# auto-sdd · e2e bug 分类闸（冷层，e2e 出 fail 时加载）

> 主文件只留指针。当 outer loop(STEP4)e2e 报告出 fail 时加载本文件。

不是所有 fail 都回 STEP1。e2e 报告出 fail,**先过熔断守卫**(见同目录 `circuit-breaker.md`),未熔断再**按 `errorClass` 分类路由**,五路修法不同:

| 分类 | 信号 | 路由 | 改什么 |
|------|------|------|--------|
| **真代码缺陷** | 断言对、行为错(落库/状态/返回与需求不符) | **回 STEP1 inner loop** | 业务码(走 `rules/executor-handoff.md` + 根因纪律) |
| **测试用例脆性** | selector 失效 / 断言写死 / 等待时序 | **修 e2e 用例** | e2e 脚本,**不动业务码**(改测试红线见下) |
| **环境 / flake** | CI-only / 偶发 / 时序抖动 | **重试 · 环境处理** | 环境/重跑,非代码 |
| **契约漂移** | schema / response 结构变 | **回设计 §三点六**(`refs/design-doc-principles.md`) | 契约重对齐(可能回 STEP1 设计) |
| **验收条件/用例本身坏** | 某 e2e **0% 通过** / grader 死板误判合法格式 / 需求自相矛盾 | **回查用例与验收条件,非回炉改码** | e2e 用例或验收条件本身;真错则回设计改 spec |

判别纪律:**不许把测试脆性/环境问题当代码 bug 去无限改业务码**(对应 Red Flag)。分类拿不准 → 当"真代码缺陷"对待先查根因,查完发现是脆性再改路由,并在 ledger 记一行。**0% 通过的用例先疑"验收条件/grader 坏了"**(评测经验:0% 常是任务/grader 坏而非 agent 无能),别在一个坏验收条件上无限回炉烧 token——这是 outer loop 最大的烧钱陷阱。

**测试脆性四桶(各绑唯一修法,禁笼统判"脆性"后乱改)**:① **timing race**(断言早于异步)→ `waitForResponse`/auto-retry 断言,**禁延长 timeout**;② **shared-state leak**(前一用例污染后一)→ fixture teardown;③ **locator 歧义/顺序依赖**(modal/toast/重名)→ region-scoped 定位;④ **config/auth mismatch**(错 project/缺 token/未声明 setup)→ 修 wiring。**环境 flake 用"跑 10 次数失败数"客观分流**:0/10=CI-only(查 worker 隔离);**1-3/10=真 flake,retry≤2**;**4+/10=不是 flake 是坏了,当 bug 升级回开发**;10/10=setup 错(没跑对用例)。**retry 永不超 2、永不用重试盖代码/测试问题**(retries are lying)。

🔴 **改测试红线(防 reward hacking,最高门禁)**:同一 agent 既写业务码又改 e2e = 造假攻击面最大(业界已记录"模型改单测骗过评估")。走"测试脆性"路改脚本时**只准动 selector / wait / fixture / 数据准备,绝不准动 expected 断言值 / 状态码 / 落库字段期望**。出现"放宽断言 / 删 step / 改期望值把红改绿"→ **强制升级人工审核闸(主文件 §人工审核闸)**,不让 agent 自己消化(与 `refs/test-suite-hygiene.md §九` 反 smoke 降级同源)。

修完任一路 → **targeted 回归**:只跑**受影响 e2e + smoke**(`design-doc-principles §二点一` 相邻影响),**非全量**重跑;回归绿才算该 bug closed。

**探索 vs 复测(决策③)**:e2e 脚本**探索一次即固化**(三层流转:探索→UI 脚本→API+DB 兜底,见 `refs/design-doc-principles.md §4.7.1`);**后续每轮复测直接复用固化脚本,不重复探索**——复测是纯脚本回归,省熔断迭代预算。e2e 资产沉淀与登记见主文件 STEP4 与 `sdd-pipeline` e2e 回归沉淀。
