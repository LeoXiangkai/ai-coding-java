# 教训闭环

用户纠错会自动追加到 `corrections.jsonl`。主会话复核原文后，用 `aicj-lesson add` 转成窄范围卡片；工具调用前，召回钩子按工具、精确命令正则或路径模式和作用域注入卡片。

卡片应保持窄：正则或路径要能准确区分触发条件。已过时的卡用 `aicj-lesson set <id> --status retired` 退役。目标是同类纠错不得出现第二次。

运行时数据位于 Claude 目录的 `aicj/lessons/`，不随适配分发，也不在卸载时删除；会话去重状态位于 `aicj/state/`，卸载时可安全清除。
