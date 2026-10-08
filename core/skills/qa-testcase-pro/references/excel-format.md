# Excel 格式

最多 5 级分组：`group_l1` 系统/顶层模块，`group_l2` 功能模块，`group_l3` 子功能/场景，`group_l4` 测试类别，`group_l5` 细粒度变体。相邻且父级相同的组可合并。

13 个数据字段：`id`、`test_item`、`priority`、`requirement_id`、`title`、`preconditions`、`steps`、`expected`、`test_data`、`is_reverse`、`type`、`automation_type`、`ai_generated`。

优先级：P1 核心必测，P2 重要，P3 一般，P4 次要。每个字段都应填入可供测试人员直接执行或核验的内容，不能用“正常”“无误”等不可判定短语替代结果。
