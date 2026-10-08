---
name: playwright-ui-auto
description: >
  Playwright + pytest UI 自动化测试规范与模式库。用于编写、修复、审查基于 Playwright Python + pytest 的 Web UI 自动化测试，
  包括 Element-UI、Element Plus、iView 和 SVG 画布交互。触发词包括 UI 自动化、Playwright、e2e 测试和端到端测试；
  纯 API 测试、单元测试和非 Playwright 框架不触发。
---

# Playwright + pytest UI 自动化测试编写规范

## 输入要求

- **用例（主体）**：需要自动化的测试用例。**本次代码围绕这些用例展开**
- **业务知识（辅助理解用例意图）**：`project_knowledge/domain/` + `scenarios/`，L1 + L2 即可（不必进 L3）
- **技术规范（代码约定）**：本 skill 的 `references/` 下各规范 + `project_knowledge/tech_spec/playwright-patterns.md`（若项目有定制）
- **环境配置**：代码生成阶段**不读**；脚本里用占位变量，运行时由 `env_config/{env}.md` 注入

## 核心工作流

```
1. 阅读操作文档/需求 → 明确页面流转路径
2. 输出导航脚本 → 先确保能自动进入各目标页面
3. 阅读 pages.py / conftest.py → 了解已有 helper 和 fixture
4. 分析用例依赖 → 识别执行顺序和前置条件
5. 按「页面→模块→功能」层级编写测试 → 遵循「强制规则 R1-R21」
6. 自检 → 对照「Anti-Pattern 清单」逐条检查
7. 补充注释 + 同步更新文档
```

## 强制规则

### R1: 弹窗先行
任何页面交互前，调用弹窗清理：
```python
dismiss_el_dialog(page)   # Element-UI 弹层
dismiss_all_popups(page)  # 全量清理（含 ivu-modal / el-message / 网络异常）
```
Element-UI overlay 会拦截 pointer events，不清理会导致后续所有 click 失败。

### R2: 多策略选择器（禁止单一选择器硬编码）
至少 2 级降级：
```python
# L1: 语义化
btn = page.get_by_role("button", name="开始录制")
# L2: 文本变体
for text in ["开始录制", "录制", "Start"]:
    el = page.get_by_text(text, exact=True).first
    if el.is_visible(timeout=2000): break
# L3: JS DOM 兜底
info = page.evaluate("""() => { ... }""")
```
详见 [references/selector-strategies.md](references/selector-strategies.md)。

### R3: 条件等待优先（禁止裸 wait_for_timeout）
```python
# ✗ WRONG
page.wait_for_timeout(3000)

# ✓ RIGHT
page.wait_for_selector(".track-clip", timeout=5000)
expect(page.locator(".indicator")).to_be_visible(timeout=5000)

# 仅在无可检测终态时用固定等待，必须注释原因
page.wait_for_timeout(500)  # 动画过渡无可检测终态
```

### R4: 精确断言（禁止"页面没崩"式断言）

**核心原则：** 自动化目标是验证功能是否正常，不是让断言通过。每个 assert 必须能在功能异常时失败。

**6 类禁止的断言反模式：**

#### 4a: 恒真断言 — 永远为真的条件
```python
# ✗ WRONG — 坐标/计数/尺寸永不为负，assert 永远通过
assert elem_count >= 0           # 恒真
assert clip["x"] >= 0            # 恒真
assert height_after > 0          # 几乎恒真

# ✓ RIGHT — 与业务预期对比
assert elem_count > 0, "应至少存在1个元素"
assert clip["x"] >= track_area["x"], "片段应在轨道区域内"
assert height_after >= height_before, "向上拖拽后高度应增大"
```

#### 4b: 仅存在性断言 — 只检查非空，不验证内容
```python
# ✗ WRONG — 任何非空字符串都通过
assert page_text
assert page_content

# ✓ RIGHT — 验证包含业务关键词
assert any(kw in page_text for kw in ["暂停", "结束录制", "00:"]), \
    f"录制页应包含录制相关元素，实际: {page_text[:100]}"
```

#### 4c: 无效 OR — 其中一个分支恒真导致整体恒真
```python
# ✗ WRONG — 字符串 "editor" 是 truthy，OR 右侧恒真
assert recording_started or "editor" in page.url

# ✓ RIGHT — 拆为独立条件分支
if recording_started:
    assert "recording" in page.url
else:
    # 明确的降级验证
    assert page.locator(".record-btn").is_visible()
```

#### 4d: 死代码 — 计算了值但从未断言
```python
# ✗ WRONG — 算了 moved 但只 print，不 assert
moved = (pos_after["x"] != pos_before["x"])
if not moved:
    print("WARNING: 元素未移动")  # 永远不会失败

# ✓ RIGHT — 直接断言
assert pos_after["x"] != pos_before["x"], \
    f"拖拽后元素应移动，实际位置未变: {pos_before}"
```

#### 4e: 操作无断言 — 执行了操作但没有任何验证
```python
# ✗ WRONG — 执行了点击但没验证效果
page.get_by_text("保存").click()
page.wait_for_timeout(1000)
# （没有任何 assert）

# ✓ RIGHT — 操作后验证状态变化
page.get_by_text("保存").click()
expect(page.locator(".save-success")).to_be_visible(timeout=5000)
```

#### 4f: 拖拽类断言 — 用 before/after 对比 + 调试日志
拖拽操作受环境影响可能不产生变化，需平衡严格性与稳定性：
```python
# ✓ 拖拽断言模板
before = get_element_bounds(page)
do_drag(page, x1, y1, x2, y2, steps=5)
after = get_element_bounds(page)

# 添加调试日志帮助排查
print(f"  [变化] width: {before['width']} -> {after['width']}")

# 断言：至少验证方向正确（不用精确像素值）
assert after["width"] >= before["width"], \
    f"向右拖拽后宽度应不减小: {before['width']} -> {after['width']}"
```

**断言编写检查表：**
1. 这个 assert 能否在功能异常时**失败**？（若不能 → 恒真断言）
2. 是否验证了**业务语义**而非仅存在性？
3. 操作前后是否有 **before/after 对比**？
4. 计算的中间值是否都被 **assert 覆盖**？

### R5: force=True 仅用于弹层遮挡
已知有 overlay 残留时才加 `force=True`，否则掩盖定位错误。

### R6: SVG 画布交互走 evaluate
SVG 编辑器元素不响应标准定位器：
```python
bounds = get_svg_canvas(page)
count = count_svg_elements(page)
el = get_last_element_bounds(page)
page.mouse.click(el["x"]+el["width"]/2, el["y"]+el["height"]/2)
```

### R7: 拖拽用 3 步 mouse 协议
```python
page.mouse.move(x1, y1)
page.mouse.down()
page.mouse.move(x2, y2, steps=5)  # steps 保证平滑
page.mouse.up()
page.wait_for_timeout(300)  # 拖拽动画
```
Playwright 原生 `.drag_to()` 在复杂 UI 上不可靠。

### R8: xfail vs skip vs 询问用户（禁止静默跳过）
| 情况 | 处理方式 |
|------|---------|
| 选择器/时序可修 | **不标记**，直接修复 |
| 需物理设备（平板） | `xfail(reason="需平板设备验证", strict=False)` + 实现模拟逻辑 |
| 需视觉/音频人工验证 | `xfail(reason="需人工视觉确认xxx", strict=False)` + 实现操作流、放松断言 |
| 需特定测试数据 | `xfail(reason="依赖xxx测试数据", strict=False)` + 注明数据依赖 |
| 功能未上线 | `skip(reason="功能xxx未上线，预计xxx")` |
| **无法判断能否执行** | **必须询问用户**，禁止自行 skip/xfail |

**强制规则：**
- `reason` 必须写明具体原因，禁止空 reason 或泛泛描述
- 优先用 `strict=False`（预期失败但不阻断），`strict=True` 仅用于"必须失败否则说明有 bug"
- **遇到不确定能否自动化的用例，必须与用户确认后再决定标记方式，禁止直接跳过**

### R9: 测试隔离与状态恢复
```python
ensure_recording(page)     # 确保前置状态
# ... 测试操作 ...
click_tool(page, "选择")   # 恢复工具
ensure_recording(page)     # 恢复录制
```
Session-scoped fixture 下一个测试的脏状态会污染后续所有测试。

### R10: 截图标记关键节点
```python
take_screenshot(page, "before_action", counter)
# 操作
take_screenshot(page, "after_action", counter)
```

### R11: 导航脚本先行
编写测试前，先为每个目标页面输出独立导航脚本，确保能自动进入：
```python
# auto_courseware.py — 进入课件编辑页
# auto_recording.py — 进入录制页
# 导航脚本独立可运行，也可作为 fixture 链的一环
def navigate_to_editor(page):
    """从登录态进入编辑器，含重试和弹窗清理"""
    login(page)
    click_video_recording(page)
    try_claim_task(page)
    dismiss_all_popups(page)
```
导航逻辑必须在测试用例编写前验证通过。

### R12: 按页面→模块→功能组织文件
每个页面至少一个测试文件，文件内按模块分 class，class 内按功能分 method：
```
UI/
├── test_entry.py              # 编辑器入口 (10 cases)
│   ├── TestEditorEntry         # 入口验证
│   └── TestTaskClaim           # 任务领取
├── test_ppt_editor.py         # PPT制作页 (72 cases)
│   ├── TestInsertElements      # 插入元素
│   ├── TestTextOperations      # 文本操作
│   └── TestShapeOperations     # 图形操作
├── test_ppt_recording.py      # PPT录制页 (47 cases)
├── test_edit_preview.py       # 编辑&预览页 (82 cases)
└── test_e2e_flow.py           # 全流程验证 (12 cases)
```
功能测试过多时拆分为 `_phase2.py`，不要单文件超过 50 个测试。

### R13: 用例执行顺序关联
分析用例依赖关系，通过 class 分组 + 方法排序保证执行顺序：
```python
class TestRecordingFlow:
    """录制流程：必须按 001→002→003 顺序执行"""
    def test_rc001_start_recording(self, recording_page): ...
    def test_rc002_pause_recording(self, recording_page): ...
    def test_rc003_end_recording(self, recording_page): ...
```
- 同 class 内的测试按方法定义顺序执行（pytest 默认行为）
- 跨 class 依赖通过 fixture 链传递状态（如 `recording_page` → `preview_page`）
- 需要 `pytest-ordering` 时用 `@pytest.mark.order(n)` 显式声明

### R14: 支持按页面+功能选择性执行
通过 pytest marker + class 结构支持灵活调用：
```bash
# 执行整个页面
pytest UI/test_video_recording.py

# 执行某个功能模块
pytest UI/test_video_recording.py::TestDrawingTools

# 执行单个用例
pytest UI/test_video_recording.py::TestDrawingTools::test_rc005_pen_tool

# 按标记执行
pytest UI/ -m RC    # 所有录制页用例
pytest UI/ -m CE    # 所有课件编辑用例
```
每个 class 和 test 方法必须可独立定位执行。

### R15: 前置条件自动设置
有前置条件的用例，在测试方法开头自动完成前置准备：
```python
def test_ep010_split_clip(self, preview_page):
    """EP-010: 分割片段 — 前置：存在至少一个片段"""
    page = preview_page
    dismiss_all_popups(page)
    # 前置条件：确保轨道上有片段
    clips = find_track_clips(page, "视频")
    if not clips:
        # 自动创建前置数据
        insert_test_clip(page)
        clips = find_track_clips(page, "视频")
    assert len(clips) > 0, "前置条件失败：无可用片段"
    # 正式测试操作
    ...
```
- 前置条件检查放在测试方法内，不依赖外部手动操作
- 前置数据创建失败时 `pytest.skip("前置条件无法满足: ...")`
- 共用前置逻辑提取为 `ensure_*` 系列 helper

### R16: 视口分辨率自动适配
测试框架会自动检测设备屏幕分辨率并设置 viewport，**禁止硬编码 viewport 尺寸**。

**优先级链**：`--viewport` CLI 参数 > `.env` 环境变量 > 自动检测 > 默认 1920x1080

```python
# ✗ WRONG — 硬编码分辨率
ctx = browser.new_context(viewport={"width": 1920, "height": 1080})

# ✓ RIGHT — 使用 config 中的自动检测值
from config import VIEWPORT_WIDTH, VIEWPORT_HEIGHT
ctx = browser.new_context(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
```

- `config.py` 中 `get_screen_resolution()` 自动检测（Windows 用 `ctypes`，非 Windows 用 `tkinter`，兜底 1920x1080）
- `SCREEN_WIDTH/SCREEN_HEIGHT` 为设备物理分辨率，`VIEWPORT_WIDTH/VIEWPORT_HEIGHT` 为实际使用的视口尺寸
- 可通过 `--viewport=1366x768` CLI 参数覆盖，用于多分辨率兼容测试
- 启动时自动打印：`[分辨率] 设备屏幕: 1920x1200, 视口: 1920x1200 (来源: 自动检测)`
- 坐标计算中如需屏幕相关数值，从 `config.VIEWPORT_WIDTH/HEIGHT` 读取，不要硬编码数字

### R17: 充分注释 + 文档同步
```python
class TestDrawingTools:
    """画笔工具测试 — 覆盖 RC-005~RC-012

    前置条件：已进入录制页面，录制状态为「录制中」
    涉及功能：画笔、橡皮擦、选择工具、颜色切换
    """
    def test_rc005_pen_tool(self, recording_page):
        """RC-005: 画笔工具绘制

        操作步骤：
        1. 点击画笔工具
        2. 在画布上绘制一笔
        3. 验证 SVG 元素数量增加
        """
```
- 每个 class 注释：覆盖用例范围、前置条件、涉及功能
- 每个 test 注释：用例 ID + 标题、操作步骤摘要
- 修改测试后同步更新项目入口文档中的覆盖范围表

### R18.1: 改完之后重跑多大范围（复测范围）

改了用例、page object 或 fixture 之后，**只重跑那一条不够**：

| 改了什么 | 至少要重跑 |
|---|---|
| 单条用例 | 该用例 + **同一个 test class**（共享 fixture 与 teardown，见 R25） |
| page object / selector helper | 所有引用该 page object 的用例 |
| fixture / conftest | 所有使用该 fixture 的用例 |

**新增或修改过的用例，按 `refs/test-suite-hygiene.md §四` 连续跑 3 次全绿**才算稳定，才可进默认套件——一次绿可能只是这次没撞上时序。

共享状态是这条规则存在的原因：R9 的测试隔离和 R25 的 teardown 意味着**改一条用例的清理逻辑会影响同类的其他用例**，只跑自己那条看不出来。

### R18: 失败处理与重试策略
```python
# flaky 测试：网络/动画导致偶发失败，使用 pytest-rerunfailures
@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_upload_file(self, editor_page):
    """偶发失败：上传依赖网络，允许重试2次"""
    ...

# 失败自动截图：在 conftest.py 中通过 hook 实现
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        page = item.funcargs.get("editor_page") or item.funcargs.get("recording_page")
        if page:
            take_screenshot(page, f"FAIL_{item.name}", _counter)
```
- `reruns` 仅用于已确认的偶发失败（网络、动画时序），禁止用于掩盖真实 bug
- 失败截图自动保存，文件名含 `FAIL_` 前缀 + 测试方法名

### R19: 数据驱动测试（parametrize）
```python
# ✓ 同一操作多组输入
@pytest.mark.parametrize("shape", ["矩形", "圆形", "三角形", "箭头"])
def test_insert_shape(self, editor_page, shape):
    """插入不同形状并验证"""
    page = editor_page
    insert_shape(page, shape)
    assert count_svg_elements(page) > 0

# ✓ 多参数组合
@pytest.mark.parametrize("color,expected_rgb", [
    ("红色", "rgb(255, 0, 0)"),
    ("蓝色", "rgb(0, 0, 255)"),
])
def test_change_color(self, editor_page, color, expected_rgb):
    ...

# ✗ WRONG — 不要用 parametrize 替代独立用例
# 每个参数组合有不同前置条件或验证逻辑时，写独立测试方法
```
- 适用场景：同一操作 + 不同输入数据 + 相同验证逻辑
- 不适用：不同操作流程、不同前置条件、需要不同断言

### R20: 动态断言 — 文字验证与 OCR 识别
页面元素无标准 DOM 文本时（如 Canvas/SVG 渲染文字、图片内文字），使用以下方法：

**方法 1: 动态添加文字后验证 DOM**
```python
# 插入文本框 → 输入文字 → 通过 DOM 验证内容
insert_text_box(page, "测试文字")
text_content = page.evaluate("""() => {
    const texts = document.querySelectorAll('text, [class*="text"], foreignObject');
    return [...texts].map(t => t.textContent).join('|');
}""")
assert "测试文字" in text_content
```

**方法 2: 截图 + OCR 识别（无 DOM 文本时）**
```python
from PIL import Image
import pytesseract  # 需安装 tesseract-ocr

def assert_text_by_ocr(page, expected_text, region=None, lang="chi_sim+eng"):
    """截图后 OCR 识别验证文字内容"""
    screenshot_path = take_screenshot(page, "ocr_check", _counter)
    img = Image.open(screenshot_path)
    if region:  # (left, top, right, bottom) 裁剪区域
        img = img.crop(region)
    result = pytesseract.image_to_string(img, lang=lang)
    assert expected_text in result, f"OCR未识别到'{expected_text}'，实际: {result[:100]}"

# 使用示例
assert_text_by_ocr(page, "录制完成", region=(400, 200, 800, 300))
```

**方法 3: Playwright 截图对比（视觉回归）**
```python
# 对比关键区域截图，容忍度 0.1
expect(page.locator(".preview-area")).to_have_screenshot(
    "expected_preview.png", max_diff_pixel_ratio=0.1
)
```

- 优先用方法 1（DOM 验证），其次方法 2（OCR），最后方法 3（截图对比）
- OCR 依赖 `pytesseract` + 系统安装 `tesseract-ocr`，中文需 `chi_sim` 语言包
- 截图对比需维护基线图，适合稳定 UI 的回归测试

### R21: 目录结构规范
```
UI/
├── config.py                  # 环境配置
├── pages.py                   # Page Object 层（公共 helper）
├── page_entries.py            # Standalone 模式页面入口
├── preconditions.py           # 前置条件 helper（ensure_* 系列）
├── conftest.py                # Fixture 链 + pytest hook
├── .env                       # 环境变量（不提交）
├── .env.example               # 环境变量模板
│
├── test_entry.py              # 编辑器入口用例
├── test_ppt_editor.py         # PPT制作页用例
├── test_ppt_recording.py      # PPT录制页用例
├── test_edit_preview.py       # 编辑&预览页用例
├── test_e2e_flow.py           # 全流程验证用例
├── test_full_chain.py         # 全链路冒烟（standalone，非 pytest）
│
├── legacy/                    # 归档旧版测试（不被 pytest 自动收集）
│   ├── test_courseware_editor.py
│   ├── test_video_recording.py
│   ├── test_video_editing.py
│   └── test_video_editing_phase2.py
│
├── scripts/                   # 入口脚本 & 工具脚本
│   ├── auto_courseware.py     # 导航到课件编辑页
│   ├── auto_recording.py     # 导航到录制页
│   └── auto_editing.py       # 导航到编辑页
│
├── tools/                     # 报告生成、数据读取、验证工具
│   └── report_generator.py
│
├── data/                      # 测试数据（JSON/Excel）
│
├── reports/                   # HTML 测试报告输出
│
├── jietu/                     # 截图输出（按时间戳子目录隔离）
│   └── 20260313_143000/
│
└── debug/                     # 浏览器探测调试脚本
```

**存放规则：**
- 新增测试文件：根目录，命名 `test_{页面名}.py`
- 新增公共 helper：`pages.py`
- 新增前置条件函数：`preconditions.py`
- 新增导航/入口脚本：`scripts/`
- 新增测试数据文件：`data/`
- 临时/调试脚本：`debug/` 或 ``debug/``（不放项目根目录）
- 归档旧测试：移入 `legacy/`
- 功能测试过多时拆分：`test_{页面名}_phase2.py`，单文件不超过 50 个测试

### R22: 缺陷发现与缺陷文档输出
测试执行后，自动分析失败用例并输出结构化缺陷文档：

**缺陷文档格式（Markdown）：**
```markdown
# 缺陷报告 — {测试模块名}

> 执行日期：{YYYY-MM-DD HH:MM}
> 执行环境：{URL} | {浏览器} | {分辨率}
> 总用例数：{N} | 通过：{P} | 失败：{F} | 跳过：{S}

## 缺陷列表

### BUG-001: {缺陷标题}
- **用例ID**：{test_id}
- **严重程度**：P0/P1/P2/P3
- **复现步骤**：
  1. {步骤1}
  2. {步骤2}
- **预期结果**：{expected}
- **实际结果**：{actual}
- **失败截图**：{screenshot_path}
- **错误日志**：
  ```
  {assertion error / traceback 摘要}
  ```
```

**严重程度定义：**
| 等级 | 定义 | 示例 |
|------|------|------|
| P0 | 功能完全不可用/崩溃 | 页面白屏、JS报错阻断流程 |
| P1 | 核心功能异常 | 录制无法开始、保存失败 |
| P2 | 非核心功能异常 | 颜色切换无效、动画缺失 |
| P3 | 体验/UI 问题 | 文案错误、对齐偏差 |

**输出规则：**
- 测试执行完成后自动生成缺陷文档，保存到 `reports/defects_{日期}.md`
- 每个失败用例对应一条缺陷记录，包含截图和错误日志
- 区分「真实缺陷」和「脚本问题」：选择器失效/环境问题标记为「待排查」，不计入缺陷
- 缺陷文档生成后提示用户review，确认后可导出为提交格式

### R23: 异常检测与自动恢复
每条用例执行时自动注入异常检测，由 `exception_handler.py` + conftest `_exception_guard` fixture 实现：

**预检（用例执行前）**：
- 检查并清理遮挡弹窗（el-dialog / ivu-modal / el-message）
- 检查页面状态（白屏、网络错误、登录态失效）
- 异常时自动恢复（刷新页面/重新登录）

**阻塞检测（用例执行中）**：
- 用例执行超过 20s 未完成时，后台线程自动触发异常检测
- 检测到弹窗遮挡 → 自动关闭
- 检测到页面异常 → 自动恢复（刷新/重新登录）
- 恢复操作会在控制台打印 `[异常恢复]` 日志

**使用方式**：
```python
# 无需手动调用，conftest.py 中 autouse=True 自动注入
# 也可在测试中手动调用预检
from exception_handler import pre_check
pre_check(page)
```

**配置**：
- 阻塞超时：`config.MAX_STEP_TIMEOUT`（默认 20000ms）
- 文件位置：`UI/exception_handler.py`

### R24: 新增用例必须标记 new-test
所有新增的测试用例必须加上 `new-test` 标签，只有经过人工执行并确认通过后，才能去掉该标签。
```python
# ✓ 新增用例
@pytest.mark.new_test
def test_crys_3100_new_feature(self, editor_page):
    """CRYS-3100: 新功能验证"""
    ...

# 人工确认通过后，去掉标签
def test_crys_3100_new_feature(self, editor_page):
    ...
```

**执行方式**：
```bash
# 只执行新增用例
pytest UI/ -m new_test

# 排除新增用例（只跑已确认的）
pytest UI/ -m "not new_test"
```

**强制规则**：新增用例必须自动加上 `@pytest.mark.new_test`，禁止省略。

### R25: 用例执行后环境清理（teardown）
用例截图完成后，必须清理本次执行对页面产生的副作用，确保下一条用例进入时页面处于干净状态。

**必须清理的场景：**
| 副作用 | 清理动作 |
|--------|---------|
| 打开了弹窗（公式/颜色/插入等） | 关闭弹窗（ESC 或点关闭按钮） |
| 打开了下拉菜单/popover | 点击空白区域关闭 |
| 暂停了录制 | 点击「继续录制」恢复 |
| 切换了工具（画笔/橡皮擦等） | 切回「选择」工具 |
| 选中了元素（显示缩放手柄） | 点击空白区域取消选中 |
| 进入了文本编辑状态（双击） | 按 ESC 退出编辑 |
| 修改了缩放比例 | 恢复默认缩放 |
| 展开了面板/侧边栏 | 收起面板 |

**代码模式：**
```python
def test_crys_2900_formula_popup(self, editor_page):
    """CRYS-2900: 验证公式弹窗"""
    page = editor_page
    dismiss_all_popups(page)

    # 操作：打开公式弹窗
    page.get_by_text("公式").click()
    expect(page.locator(".formula-dialog:visible")).to_be_visible()
    take_screenshot(page, "formula_popup", _counter)

    # ── teardown: 清理本次操作的影响 ──
    # 关闭公式弹窗
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    # 点击空白区域确保退出所有状态
    click_empty_area(page)

def test_rc_pause_resume(self, recording_page):
    """RC-XXX: 验证暂停录制"""
    page = recording_page
    ensure_recording(page)

    # 操作：暂停录制
    page.get_by_text("暂停").click()
    expect(page.get_by_text("继续录制")).to_be_visible()
    take_screenshot(page, "paused", _counter)

    # ── teardown: 恢复录制状态 ──
    page.get_by_text("继续录制").click()
    ensure_recording(page)
```

**通用 teardown 模板（放在用例末尾）：**
```python
# 最小化 teardown：适用于大多数用例
page.keyboard.press("Escape")       # 关闭弹窗/退出编辑
page.wait_for_timeout(300)
click_empty_area(page)              # 取消选中/关闭菜单
dismiss_all_popups(page)            # 兜底清理残余弹窗
```

**强制规则**：
- 每条用例的操作步骤如果改变了页面状态，必须在截图后补充清理代码
- 清理代码以注释 `# ── teardown ──` 标记，便于审查
- 不确定是否需要清理时，至少执行「ESC + 点击空白区域 + dismiss_all_popups」三件套

## 测试结构模板

```python
"""模块文档：覆盖用例范围 XX-001 ~ XX-042"""
import pytest
from playwright.sync_api import expect
from pages import (dismiss_all_popups, get_svg_canvas,
                   count_svg_elements, take_screenshot)
from conftest import ScreenshotCounter

_counter = ScreenshotCounter(start=0)

def _module_helper(page):
    """仅本文件用的 helper 放模块级"""
    pass

@pytest.mark.CE  # 或 RC / EP
class TestFeatureName:
    """二级分组名称"""
    def test_id001_description(self, editor_page):
        """CE-NEW-001: 中文用例标题"""
        page = editor_page
        dismiss_all_popups(page)
        # Step 1 → Step 2 → 精确断言
        expect(page.locator(".result")).to_contain_text("预期值")
        take_screenshot(page, "ce001_done", _counter)
```

## Helper 函数放置规则

| 使用范围 | 放置位置 |
|----------|----------|
| ≥2 个测试文件共用 | `pages.py`（public API，无下划线前缀） |
| 仅 1 个文件内使用 | 该测试文件顶部（`_` 前缀） |
| 从 pages.py 导入后需别名 | `_func = func`（向后兼容） |

## Anti-Pattern 自检清单

编写或审查测试时逐条检查：

- [ ] 裸 `wait_for_timeout` 无注释？→ 违反 R3
- [ ] 单一选择器无降级？→ 违反 R2
- [ ] `assert page.url` 类松散断言？→ 违反 R4
- [ ] `assert x >= 0` 恒真断言（坐标/计数永不为负）？→ 违反 R4a
- [ ] `assert page_text` 仅存在性断言，无关键词验证？→ 违反 R4b
- [ ] `assert X or "fallback"` 无效 OR 恒真？→ 违反 R4c
- [ ] 计算了变量但从未 assert（死代码）？→ 违反 R4d
- [ ] 执行操作后无任何断言？→ 违反 R4e
- [ ] 拖拽操作只断言 `> 0` 而非 before/after 对比？→ 违反 R4f
- [ ] 交互前未调弹窗清理？→ 违反 R1
- [ ] `force=True` 无弹层原因？→ 违反 R5
- [ ] 拖拽无 `steps` 参数？→ 违反 R7
- [ ] 测试结束未恢复状态？→ 违反 R9
- [ ] 通用 helper 写在了 test 文件？→ 应移到 pages.py
- [ ] 硬编码 viewport 尺寸（如 1920x1080）？→ 违反 R17，应使用 config 常量
- [ ] 硬编码绝对路径（测试数据/截图）？→ 改用环境变量或相对路径
- [ ] `page.evaluate` 超过 20 行？→ 提取为 pages.py 函数
- [ ] 未先验证导航脚本就写测试？→ 违反 R11
- [ ] 多个页面测试挤在同一文件？→ 违反 R12
- [ ] 有依赖关系的用例未按顺序排列？→ 违反 R13
- [ ] class/method 命名无法通过 pytest 选择执行？→ 违反 R14
- [ ] 有前置条件的用例未自动设置前置状态？→ 违反 R15
- [ ] class/method 缺少用例 ID 和步骤注释？→ 违反 R17
- [ ] flaky 测试未标记 `@pytest.mark.flaky`？→ 违反 R18
- [ ] 同操作多输入写了重复测试方法而非 parametrize？→ 违反 R19
- [ ] 无 DOM 文本的元素仅靠"不报错"验证？→ 违反 R20，应用 OCR 或 DOM 动态验证
- [ ] 不确定能否自动化就直接 skip？→ 违反 R8，必须询问用户
- [ ] 新文件放错目录（如临时脚本放项目根目录）？→ 违反 R21
- [ ] 测试失败未自动截图？→ 违反 R18
- [ ] xfail/skip 的 reason 为空或含糊？→ 违反 R8

## 参考文件

- **[选择器策略详解](references/selector-strategies.md)** — 多策略降级、JS evaluate 模板、中文 UI 匹配、Element-UI 组件定位
- **[Page Object 与 Fixture 模式](references/page-object-patterns.md)** — fixture 链设计、helper 分层、弹窗处理架构、状态管理
