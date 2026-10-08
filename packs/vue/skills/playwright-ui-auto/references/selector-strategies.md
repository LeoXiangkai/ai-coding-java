# 选择器策略详解

## 目录
1. [三级降级模式](#三级降级模式)
2. [中文 UI 文本匹配](#中文-ui-文本匹配)
3. [Element-UI 组件定位](#element-ui-组件定位)
4. [SVG 画布元素定位](#svg-画布元素定位)
5. [图标按钮（无文本）定位](#图标按钮定位)
6. [JS Evaluate 模板库](#js-evaluate-模板库)

---

## 三级降级模式

每个元素查找必须实现至少 2 级降级：

```python
def find_button(page, primary_text, fallback_texts, css_hints=None):
    """通用按钮查找：语义 → 文本变体 → JS DOM"""
    # Level 1: 语义化（最稳定）
    try:
        btn = page.get_by_role("button", name=primary_text)
        if btn.is_visible(timeout=3000):
            return btn
    except Exception:
        pass

    # Level 2: 文本变体（应对多语言/文案变更）
    for text in fallback_texts:
        try:
            el = page.get_by_text(text, exact=True).first
            if el.is_visible(timeout=2000):
                return el
        except Exception:
            continue

    # Level 3: JS DOM 兜底（应对动态渲染）
    selectors = css_hints or []
    info = page.evaluate("""(selectors) => {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.offsetParent !== null) {
                const r = el.getBoundingClientRect();
                return {x: r.x, y: r.y, width: r.width, height: r.height};
            }
        }
        // 最终兜底：遍历所有可见按钮
        const btns = document.querySelectorAll('button, [role="button"]');
        for (const b of btns) {
            if (b.offsetParent && b.textContent.includes(primary_text)) {
                const r = b.getBoundingClientRect();
                return {x: r.x, y: r.y, width: r.width, height: r.height};
            }
        }
        return null;
    }""", selectors)

    if info:
        return info  # 返回坐标，用 page.mouse.click() 点击
    return None
```

### 何时使用哪一级

| 场景 | 推荐级别 |
|------|---------|
| 有明确 role + name 的标准按钮 | Level 1 |
| 中文 UI、文案可能变化 | Level 1 + Level 2 |
| 图标按钮、动态渲染组件 | Level 2 + Level 3 |
| SVG 内部元素 | 直接 Level 3 (evaluate) |

---

## 中文 UI 文本匹配

### 常见变体表

| 功能 | 可能文案 |
|------|---------|
| 录制 | "开始录制", "录制", "录制中", "Start Recording" |
| 暂停 | "暂停", "暂停录制", "Pause" |
| 结束 | "结束录制", "完成录制", "End", "Stop" |
| 保存 | "保存", "自动保存中", "Save" |
| 撤销 | "撤销", "回退", "Undo" |
| 重做 | "重做", "恢复", "Redo" |
| 复制 | "复制", "复制ID", "Copy" |
| 确认 | "确定", "确认", "知道了", "OK" |
| 取消 | "取消", "Cancel" |
| 关闭 | "关闭", "×", "Close" |

### 匹配原则
```python
# exact=True 避免"录制"匹配到"录制中"
page.get_by_text("开始录制", exact=True)

# 部分匹配用 filter
page.locator("button").filter(has_text="录制")
```

---

## Element-UI 组件定位

### 弹窗/对话框
```python
# el-dialog
page.locator(".el-overlay-dialog:visible")
page.locator(".el-dialog__body:visible")

# el-message (顶部提示)
page.locator(".el-message:visible")

# el-notification
page.locator(".el-notification:visible")

# el-popover
page.locator(".el-popper:visible")
```

### 弹窗内按钮
```python
# 必须限定作用域到 dialog 内，避免点到背后按钮
dialog = page.locator(".el-overlay-dialog:visible")
dialog.get_by_text("确定").click(force=True)
```

### ivu-modal
```python
page.locator(".ivu-modal-wrap:visible .ivu-btn")
```

---

## SVG 画布元素定位

SVG 编辑器元素无法用标准 Playwright 定位器交互。

### 获取画布坐标系
```python
bounds = page.evaluate("""() => {
    const svgs = [...document.querySelectorAll('svg')];
    const big = svgs
        .map(s => { const r = s.getBoundingClientRect(); return {el: s, area: r.width * r.height, ...r}; })
        .filter(s => s.width > 200)
        .sort((a, b) => b.area - a.area);
    return big.length ? {x: big[0].x, y: big[0].y, width: big[0].width, height: big[0].height} : null;
}""")
```

### 统计用户元素（排除 defs/metadata）
```python
count = page.evaluate("""() => {
    const svg = /* 获取主 SVG */;
    const skip = new Set(['defs', 'metadata', 'title', 'desc']);
    return [...svg.children].filter(c => !skip.has(c.tagName.toLowerCase())).length;
}""")
```

### 点击最后添加的元素
```python
el = page.evaluate("""(idx) => {
    const svg = /* 获取主 SVG */;
    const children = [...svg.children].filter(c => !skip.has(c.tagName));
    const target = children[idx >= 0 ? idx : children.length + idx];
    if (!target) return null;
    const r = target.getBoundingClientRect();
    return {x: r.x, y: r.y, width: r.width, height: r.height};
}""", -1)
page.mouse.click(el["x"] + el["width"]/2, el["y"] + el["height"]/2)
```

---

## 图标按钮定位

无文本的图标按钮（撤销/重做/画笔工具等）：

```python
# 策略 1: title / aria-label
page.locator('[title="撤销"], [aria-label="撤销"], [title="Undo"]')

# 策略 2: class 名包含关键词
page.locator('[class*="undo"], [class*="revoke"]')

# 策略 3: SVG 图标的父容器属性
page.evaluate("""(keyword) => {
    const all = document.querySelectorAll('button, [role="button"], [class*="tool"]');
    for (const el of all) {
        const txt = (el.title || '') + (el.className || '') + (el.getAttribute('aria-label') || '');
        if (txt.toLowerCase().includes(keyword)) {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && el.offsetParent) return {x: r.x, y: r.y, width: r.width, height: r.height};
        }
    }
    return null;
}""", "undo")

# 策略 4: 配对按钮检测（撤销/重做通常相邻）
page.evaluate("""() => {
    const btns = document.querySelectorAll('button svg, [role="button"] svg');
    // 找到相邻的一对 SVG 图标按钮，通常是撤销+重做
    const pairs = [];
    // ...
}""")
```

---

## JS Evaluate 模板库

### 模板: 查找可见元素
```javascript
(keyword) => {
    const all = document.querySelectorAll('*');
    for (const el of all) {
        const text = el.textContent || el.title || el.getAttribute('aria-label') || '';
        if (text.includes(keyword) && el.offsetParent !== null) {
            const r = el.getBoundingClientRect();
            if (r.width > 5 && r.height > 5) {
                return {x: r.x, y: r.y, width: r.width, height: r.height, tag: el.tagName};
            }
        }
    }
    return null;
}
```

### 模板: 查找颜色色块
```javascript
() => {
    const els = document.querySelectorAll('[class*="color"], [class*="swatch"], [class*="palette"]');
    const result = [];
    for (const el of els) {
        const r = el.getBoundingClientRect();
        if (r.width >= 10 && r.width <= 50 && r.height >= 10 && el.offsetParent) {
            const bg = getComputedStyle(el).backgroundColor;
            result.push({x: r.x, y: r.y, width: r.width, height: r.height, color: bg});
        }
    }
    return result;
}
```

### 模板: 检查工具激活状态
```javascript
(toolText) => {
    const all = document.querySelectorAll('[class*="tool"], [class*="btn"], button');
    for (const el of all) {
        if (el.textContent.includes(toolText) || (el.title || '').includes(toolText)) {
            let node = el;
            while (node) {
                if (node.className && typeof node.className === 'string' &&
                    (node.className.includes('active') || node.className.includes('selected'))) {
                    return true;
                }
                node = node.parentElement;
            }
            return false;
        }
    }
    return null;  // 未找到工具
}
```

### 模板: 轨道片段查找
```javascript
(trackKeyword) => {
    const rows = document.querySelectorAll('[class*="track"], [class*="row"], [class*="lane"]');
    const clips = [];
    for (const row of rows) {
        const text = row.textContent || row.className || '';
        if (text.includes(trackKeyword)) {
            const items = row.querySelectorAll('[class*="clip"], [class*="segment"], [class*="block"]');
            for (const item of items) {
                const r = item.getBoundingClientRect();
                if (r.width > 5 && r.height > 3 && item.offsetParent) {
                    clips.push({x: r.x, y: r.y, width: r.width, height: r.height});
                }
            }
        }
    }
    return clips;
}
```
