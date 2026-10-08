# Worktree 操作细则（从 `rules/worktree-management.md` 下沉）

**加载时机**：新建 worktree、写 REGISTRY、起服务占端口、走完整改动流程、周期清理、异常修复时。
常驻正文只留「何时需要 worktree」判定表、三步法与硬约束；以下是全部操作细则，**约束力未降级**。

## 为什么存在

- 并行任务隔离,避免改动相互污染
- 在隔离副本里编码,主工作区集中做集成 / 审查 / 推送
- 避免主工作区被试验性改动打乱

## 分支与推送策略

> **命名**以 `refs/git-policy.md` 为唯一权威（`feature/` 等斜杠前缀,见 §目录与命名);**推送/合并**用下面的本地基线模型
> ——只借 gitflow 的命名,不套它的"每分支 push + PR"流程。

- 本地创建的所有分支(`feature/` 等)**默认只在本地,绝不 push origin**。
- 项目约定一个**基线分支**(如 `develop`),所有 worktree 分支改动**默认合入基线**(本地 merge)。
- **只有基线分支对接远程**,统一由基线(如 develop)push 到 origin。
- 例外:需临时分享 / 走远端流水线时,才单独 push 某个分支,用完及时删远程分支。

## 目录与命名

> **分支命名唯一权威 = `refs/git-policy.md`**(`feature/{功能名}` / `refactor/{目标}` / `release/{版本}` /
> `hotfix/{问题标识}`,斜杠前缀)。本文件只管 worktree 的生命周期/登记,**不再自定义分支前缀**;旧的
> `feat_`/`fix_`/`spike_`/`chore_`/`docs_` 下划线约定已废弃,一律改用 gitflow 斜杠命名。

- 统一放在仓库根的 `.worktrees/` 下
- 目录名 = 分支名(斜杠会成子目录,可用等价短名如 `feature_aux_input` 作目录名、分支仍 `feature/aux_input`)
- 按 gitflow 分支类型选前缀(生命周期由下表 + REGISTRY 判定,不再靠前缀编码):
- **新模块/功能/开发期修复/文档/杂项/试验** → `feature/<名>`,如 `feature/aux_input`
- 普通任务的 `<名>` 只使用任务名，不拼接负责人姓名、日期、Agent 名称或自动生成编号；例如 `feature/task25-data-extraction`。
  - **重构** → `refactor/<目标>`,如 `refactor/engine_split`
  - **发布** → `release/<版本>`;**线上热修** → `hotfix/<问题标识>`(切/合规则见 `refs/git-policy.md`)
- 一个需要 worktree 的任务只使用一个匹配其范围的 worktree，不跨任务混用；是否复用既有 worktree 见 §“何时需要”与 REGISTRY 语义匹配
- `.worktrees/` 内的临时文件(如 `.DS_Store`)需通过 `.gitignore` 忽略

## 基线选择（最新本地提交分支优先）

新建 worktree 时默认使用**本地分支中提交时间最新的分支**作为基线，避免机械列候选和无效询问，同时不能凭习惯固定拉 `master` / `main` / `develop`。

1. 用户在 prompt 中已明确指定基线（如“基于 master”）→ 直接使用用户指定分支。
2. 否则执行：
   ```bash
   git for-each-ref --count=2 --sort=-committerdate \
     --format='%(refname:short)|%(objectname)|%(committerdate:iso8601)' refs/heads
   ```
   第一行对应分支即默认基线。
3. 仅在以下异常情况使用 `AskUserQuestion`：
   - 最新提交时间并列，无法唯一判定；
   - 最新分支是明显与当前任务无关的 `hotfix/` / `release/` / 专项分支；
   - 分支不存在、损坏或无法解析提交；
   - 用户要求查看或比较候选基线。
4. 读取基线提交：`CHOSEN_BASE_TIP=$(git rev-parse <chosen-base>)`，再执行 `git worktree add .worktrees/<name> -b <branch> <chosen-base>`。
5. 创建成功后记录不可变分叉元数据：`git-safe -C .worktrees/<name> config "branch.<branch>.baseline" "<chosen-base>"` 与 `git-safe -C .worktrees/<name> config "branch.<branch>.fork-oid" "$CHOSEN_BASE_TIP"`（`git-safe` 需在 PATH 中；未安装时用普通 `git` 代替），并把基线写入 `.worktrees/REGISTRY.md`。

**Why**：历史失败一端是固定拉 `master`，导致遗漏当前里程碑数百个提交；另一端是每次机械列候选、启动多轮探索再询问，明明最新活跃分支已能唯一表明当前主线却仍浪费时间。以最新本地提交分支为默认，同时只对异常分支保留交互，可兼顾正确率和效率。

## 文件改动与审查流程（Claude Code 直接执行）

1. Claude 先判定任务是否会修改仓库文件：否 → 不创建 worktree，按对应数据库 / 环境 / 平台协议直接执行；是 → 继续下列流程
2. 判断任务类型（新模块 / 修复 / 分析 / 重构）→ 按上表确定命名前缀和生命周期
3. 读 `.worktrees/REGISTRY.md`,按"REGISTRY 三步法"决定**复用**还是**新建**
4. 新建时:按“基线选择”确定默认基线 → `git worktree add .worktrees/<name> -b <branch> <chosen-base>` → 同步登记 REGISTRY；创建成功后记录任务分支的不可变分叉提交 `branch.<task>.fork-oid=<chosen-base-tip>`，同时保留 `branch.<task>.baseline=<baseline-branch>`
5. **在该 worktree 内修改仓库文件**（`cd .worktrees/<name>` 后再编辑、跑构建），严禁默认改主工作区
6. 在该 worktree 内做主会话 diff 自审、编译、单测；独立 reviewer 是否启动由 `code-review` skill（若已安装）按当前仓库+分支实际 diff 判定；未安装时由主会话按 diff 风险自行判定
7. 通过后:合并回基线分支；开发分支已完成验证时，不因普通合并重复跑同一套验证。仅当基线自任务分叉后合入其他任务分支，或合并冲突/手工改写、来源无法可靠判定时，合并后做一次快速定向回归；判定规则见 `rules/git-workflow.md §合并后验证门禁`，执行入口为 `git-commit` skill（若已安装）§6B
8. 收口动作按生命周期分流:
   - **临时型**(fix/spike/refactor):合入基线后**立即** `git worktree remove .worktrees/<name>` + 删分支 + 更新 REGISTRY 状态为 `done`(随即移出表)
   - **长期型**(feat/里程碑):合入基线后**保留** worktree,REGISTRY 状态 `active` → `paused`,后续同范围任务回到这里复用

## 活跃 worktree 登记(强制)

每个项目在 `.worktrees/REGISTRY.md` 维护活跃 worktree 登记。仅当任务需要修改仓库文件、进入 worktree 选择流程时，Claude 才必须先读该文件；纯只读或环境操作无需读取。

最小字段:

| 字段 | 说明 |
|------|------|
| 目录 | `.worktrees/<name>` |
| 分支 | 对应分支名 |
| 类型 | `feature`(长期,保留供复用) / `refactor` / `hotfix` / `release`(gitflow 类型);生命周期(长期/临时)见 §"何时新建"表 |
| 任务 | 一句话说明该 worktree 在做什么 |
| 范围 | 涉及的模块/包/文件域,用于判断新任务是否归并到此 |
| 状态 | active(进行中) / paused(已合入基线但保留,仅长期 `feature` 型有此态) / merging / done(待立即清理) |
| 基线 | 从哪个分支拉出（用户指定或按最新本地提交分支自动判定） |
| 更新时间 | 最后一次有改动或评审的日期 |

操作约束:

- 新建 worktree 时,**同步**在 REGISTRY.md 增加一行(含类型字段)
- 任务收口、合并或废弃时,**立即**更新状态:
  - 临时型(fix/hotfix/spike/refactor/chore/docs):合入基线后**立即** `git worktree remove`,不留 done 态过夜
  - 长期型(feat/里程碑):合入基线后状态 `active` → `paused`,worktree 保留供后续复用
- **选择执行位置三步法**（强制顺序，违反即算违规）:
  1. **读 `.worktrees/REGISTRY.md`**（不读这一步直接算违规）
  2. **按"模块+范围"字段做语义匹配**：
     - 任务主体落在某 worktree 已声明"范围"内 → **复用**
     - 即便任务会新增跨模块支持文件（如 mq Consumer、common 枚举），只要主体仍在原范围，仍算复用
     - 只有任务主体明确跨越所有已有 worktree 时才新建
  3. **复用前**：确认 worktree 工作区 clean；若落后集成分支则 `git merge <integration> --ff-only` 拉齐再开工
- **新建 worktree 的前置检查**：写出"为什么已有 worktree 不能满足"的一句话理由；写不出来就说明应该复用
- 若 REGISTRY 与实际 `git worktree list` 不一致,以 `git worktree list` 为准并立即修正 REGISTRY

## 运行时隔离(重要)

worktree 只做**文件级隔离**,端口、数据库、Redis、MQ、本地缓存在所有 worktree 间**共享**。约定:

1. **同一时刻只允许一个 worktree 启动应用**(占用本机端口/连共享基础设施)
2. 启动前须在 `.worktrees/REGISTRY.md` 将该行"运行中"标记为 `yes`(或端口号),停止后改回 `no`
3. 想切换启动位置:先停旧 worktree 的进程、清"运行中"标记,再去新 worktree 启动
4. 若业务必须同时跑多个,走"不同 profile + 不同端口"方案(成本高,仅在确有需要时单独设计)

## 卫生约束

1. 并行 worktree 不超过 5 个(业界实用上限),超出先收口再开新的
2. 不在 worktree 内再嵌套 worktree
3. 主工作区**禁止任何仓库文件改动**，文件改动任务中仅做 worktree 列表查看、REGISTRY 维护、最终合并收口；不修改仓库文件的只读或环境操作可直接执行
4. 在 worktree 内修改仓库文件前必须先 `cd .worktrees/<task>` 再操作，严禁默认改主工作区
5. worktree 元数据损坏时用 `git worktree prune` 修复,不手工删 `.git/worktrees/*`
6. `.worktrees/` 下须有 `.gitignore`,至少忽略 `.DS_Store`
7. **磁盘卫生**:每个 worktree 独立 `target/`,Maven 多模块单个 worktree 可达 1-2GB。每个里程碑收口或每月一次清理:
   ```bash
   find .worktrees -type d -name target -prune -exec rm -rf {} +
   ```
   `audit.sh` 会输出各 worktree 磁盘占用供参考

## 原生能力配合(Claude Code v2.1.49+)

- subagent 调用可用 `isolation: "worktree"`，Claude Code 自动建临时 worktree；仅用于可能写入文件的短生命周期试验或实现任务，纯只读探索不启用隔离
- CLI 侧 `claude --worktree <name>` 创建隔离副本（落在 `.claude/worktrees/<name>/`），同样只用于会写文件的一次性任务
- 这两种方式绕过 REGISTRY，因此只用于短生命周期文件改动；长期并行任务仍走 `.worktrees/` + REGISTRY

## 周期清理

触发节律:每个里程碑收口 + 每月一次。因为 worktree 分支只在本地,stale 判定不看远程,而是看**是否已合入本地集成分支**。

**按类型分流处理**(临时型其实任务收口时已删,周期清理主要扫漏 + 处理长期型):

```bash
# 1. 同步远端(用于刷新集成分支状态)
git fetch --prune

# 2. 列所有 worktree + 读 REGISTRY 类型字段
git worktree list
cat .worktrees/REGISTRY.md

# 3. 对每个 worktree 分支,判断是否已全部合入集成分支
git rev-list --count <integration>..<branch>
#   = 0  → 已合入
#   > 0  → 仍有未合入改动,留着

# 4. 回收策略按类型分流
#   - 临时型(fix/hotfix/spike/refactor/chore/docs)若仍在表 → 异常,任务收口时应已删,补删
#   - 长期型(feat/里程碑)已合入 + 超过一个里程碑没被复用 → 回收
#   - 长期型(feat/里程碑)已合入 + 仍在当前里程碑内 → 保留 paused 态
git worktree remove .worktrees/<name>
git branch -d <branch>   # 已合并可安全删本地分支

# 5. 清理元数据残留
git worktree prune -v
```

项目级可用 `.worktrees/audit.sh` 一键执行。每次 `worktree remove` 后立即更新 `.worktrees/REGISTRY.md`。

## 异常处理

- 改错位置(代码落到主工作区) → `git stash` 后转移到正确 worktree
- 分支冲突 → 在 worktree 内 rebase 解决,不在主工作区强推
- worktree 残留(目录已删但 git 仍登记) → `git worktree prune`
- 远程分支已删除但本地 worktree 还在 → 确认无未推送改动后 `git worktree remove`

## 引用关系

- 与 `rules/git-workflow.md` 配合:分支命名、提交规范保持一致

