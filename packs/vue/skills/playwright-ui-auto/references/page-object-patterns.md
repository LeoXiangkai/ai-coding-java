# Page Object 与 Fixture 模式

## 目录
1. [三层架构](#三层架构)
2. [Fixture 链设计](#fixture-链设计)
3. [弹窗处理架构](#弹窗处理架构)
4. [Helper 函数分层](#helper-函数分层)
5. [状态管理](#状态管理)
6. [常见陷阱](#常见陷阱)

---

## 三层架构

```
config.py          → 环境配置（URL、凭据、超时、开关）
pages.py           → Page Object 层（所有页面交互封装）
conftest.py        → Fixture 层（测试生命周期管理）
test_*.py          → 测试层（业务用例）
```

### config.py 职责
```python
# 从 .env 加载，支持多环境
TARGET_URL = os.getenv("TARGET_URL")
USER_ID = os.getenv("USER_ID")
AUTH_VALUE = os.getenv("AUTH_VALUE")
VIEWPORT = {"width": 1920, "height": 1080}
SLOW_MO = int(os.getenv("SLOW_MO", "500"))
USE_FAKE_MEDIA = os.getenv("USE_FAKE_MEDIA", "true").lower() == "true"
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")
```

### pages.py 职责
- 所有与页面元素的交互封装为函数
- 函数名为 **动作**：`login()`, `insert_text_box()`, `dismiss_el_dialog()`
- 参数为 `page` 对象 + 业务参数
- 内部处理弹窗、等待、多选择器降级
- 不含任何 assert（断言属于测试层）

### conftest.py 职责
- fixture 链管理浏览器生命周期
- session-scoped 减少登录/导航开销
- 自动截图（失败时）
- pytest hook（报告生成）

---

## Fixture 链设计

### Session-Scoped 链（当前架构）
```python
@pytest.fixture(scope="session")
def pw():
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser(pw):
    args = ["--start-maximized"]
    if config.USE_FAKE_MEDIA:
        args += ["--use-fake-device-for-media-stream",
                 "--use-fake-ui-for-media-stream"]
    browser = pw.chromium.launch(headless=False, slow_mo=config.SLOW_MO, args=args)
    yield browser
    browser.close()

@pytest.fixture(scope="session")
def context(browser):
    ctx = browser.new_context(
        viewport=config.VIEWPORT,
        permissions=["microphone"]
    )
    yield ctx
    ctx.close()

@pytest.fixture(scope="session")
def logged_in_page(context):
    page = context.new_page()
    login(page)
    yield page

@pytest.fixture(scope="session")
def editor_page(logged_in_page):
    # 导航到编辑器（含重试）
    page = navigate_to_editor(logged_in_page)
    yield page

@pytest.fixture(scope="session")
def recording_page(editor_page):
    page = navigate_to_recording(editor_page)
    yield page

@pytest.fixture(scope="session")
def preview_page(recording_page):
    page = complete_recording_and_go_preview(recording_page)
    yield page
```

### Session-Scoped 的注意事项
- 一个 fixture 失败 → 所有下游测试 skip
- 测试间共享状态 → 必须在每个测试末尾恢复状态（R9）
- 测试执行顺序有依赖 → 用 `pytest-ordering` 或文件名排序
- 新标签页处理 → 用 `context.expect_page()` + `context.pages[-1]` 兜底

### 多标签页处理模式
```python
try:
    new_page = context.expect_page(timeout=10000)
    new_page = new_page.value
except TimeoutError:
    # 兜底：检查 context 中最后一个 page
    if len(context.pages) > 1:
        new_page = context.pages[-1]
    else:
        pytest.skip("新标签页未打开")
```

---

## 弹窗处理架构

### 四层弹窗清理（从轻到重）

```python
# Layer 1: ivu-modal（最常见）
def dismiss_modal(page):
    for text in ["确定", "知道了"]:
        btn = page.locator(f".ivu-modal-wrap:visible").get_by_text(text)
        if btn.is_visible(timeout=500):
            btn.click(force=True)

# Layer 2: Element-UI dialog
def dismiss_el_dialog(page):
    # 关闭按钮
    for sel in [".el-dialog__close", ".el-overlay-dialog:visible .close"]:
        btn = page.locator(sel)
        if btn.is_visible(timeout=500):
            btn.click(force=True)
    # 确认按钮
    for text in ["确定", "确认", "知道了"]:
        btn = page.locator(".el-overlay-dialog:visible").get_by_text(text)
        if btn.is_visible(timeout=500):
            btn.click(force=True)

# Layer 3: 通用弹窗
def dismiss_popups(page):
    for text in ["确定", "确认", "知道了", "关闭", "取消"]:
        for el in page.get_by_text(text, exact=True).all():
            if el.is_visible():
                el.click(force=True)

# Layer 4: 全量清理（含错误提示）
def dismiss_all_popups(page):
    dismiss_modal(page)
    dismiss_el_dialog(page)
    dismiss_popups(page)
    # 关闭 el-message / el-notification
    for sel in [".el-message__closeBtn", ".el-notification__closeBtn"]:
        for btn in page.locator(sel).all():
            if btn.is_visible():
                btn.click(force=True)
```

### 弹窗内按钮点击
```python
def click_in_el_dialog(page, text):
    """在 dialog 内点击，避免穿透到背后元素"""
    dialog = page.locator(".el-overlay-dialog:visible")
    btn = dialog.get_by_text(text, exact=True)
    btn.click(force=True)
```

---

## Helper 函数分层

### 判断标准

```
通用度高 + 多文件使用 → pages.py (public)
    ↓ 否
单文件使用 + 非 trivial → test 文件顶部 (_前缀)
    ↓ 否
单次使用 + trivial → inline 在测试方法内
```

### pages.py 函数命名规范
```python
# 动作类：动词开头
login(page)
insert_text_box(page, text)
click_tool(page, tool_name)
drag_clip_edge(page, bounds, side, offset)

# 查询类：get/find/is/has 开头
get_svg_canvas(page)
find_track_clips(page, keyword)
is_tool_active(page, tool_name)
has_element(page, selectors)

# 辅助类：dismiss/ensure/expand
dismiss_all_popups(page)
ensure_recording(page)
expand_track_by_name(page, name)
```

### 从 test 文件迁移到 pages.py
```python
# 1. 移到 pages.py，去掉下划线前缀
# pages.py
def click_tool(page, tool_text): ...

# 2. test 文件保留兼容别名
# test_video_recording.py
from pages import click_tool
_click_tool = click_tool  # 向后兼容，避免全文替换
```

---

## 状态管理

### 录制状态机
```
初始 → [开始录制] → 录制中 → [暂停] → 暂停中 → [继续] → 录制中
                                                      ↓
                                              [结束录制] → 完成
```

### 状态保障函数
```python
def ensure_recording(page):
    """确保当前处于录制中状态"""
    # 检查是否有"开始录制"按钮（说明还没开始）
    # 检查是否有"继续录制"按钮（说明已暂停）
    # 相应点击

def reset_recording(page):
    """重置到初始状态（重新录制）"""
    # 点击"重新录制"→ 确认 → 回到初始
```

### 测试模式
```python
def test_pause_resume(self, recording_page):
    page = recording_page
    ensure_recording(page)      # 前置保障

    # 暂停
    page.get_by_text("暂停").click()
    expect(page.get_by_text("继续录制")).to_be_visible()

    # 恢复
    page.get_by_text("继续录制").click()
    expect(page.get_by_text("暂停")).to_be_visible()

    ensure_recording(page)      # 后置恢复
```

---

## 常见陷阱

### 1. Session-Scoped 污染
**问题**：Test A 修改了页面状态，Test B 依赖初始状态
**方案**：每个测试末尾调用状态恢复函数

### 2. Element-UI Overlay 拦截点击
**问题**：`click()` 被不可见的 overlay 拦截
**方案**：先 `dismiss_el_dialog(page)`，必要时 `force=True`

### 3. SVG 元素不可 click
**问题**：`page.locator("rect").click()` 无效
**方案**：用 `evaluate()` 获取坐标，用 `page.mouse.click(x, y)`

### 4. 新标签页丢失
**问题**：`context.expect_page()` 超时
**方案**：兜底检查 `context.pages[-1]`

### 5. 录制自动开始
**问题**：fake media 模式下录制自动触发
**方案**：检查"开始录制"和"录制中"两种状态

### 6. 截图文件名冲突
**问题**：多模块用同一计数器
**方案**：每个模块设置不同起始偏移或使用 test ID 做前缀
