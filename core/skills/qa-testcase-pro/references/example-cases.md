# 数据示例

```json
{
  "project": "示例项目",
  "test_cases": [
    {
      "group_l1": "账户",
      "group_l2": "资料维护",
      "group_l3": "必填校验",
      "id": "TC-001",
      "test_item": "保存资料",
      "priority": "P1",
      "requirement_id": "REQ-001",
      "title": "缺少必填项时拒绝保存",
      "preconditions": "已进入资料编辑页",
      "steps": "1. 清空必填项；\n2. 点击保存",
      "expected": "页面显示对应校验提示，数据未保存",
      "test_data": "空字符串",
      "is_reverse": "是",
      "type": "Negative",
      "automation_type": "接口自动化",
      "ai_generated": "是"
    }
  ]
}
```
