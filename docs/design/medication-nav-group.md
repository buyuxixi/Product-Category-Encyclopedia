# 药物管理导航分组

## 背景

药盒、切药器原先并列为一级目录（`药物管理-药盒` / `药物管理-切药器`），缺少与「热疗」类似的一级分组。

## 方案

| 节点 | code | status | 行为 |
|---|---|---|---|
| 药物管理 | `MEDICATION_MANAGEMENT` | `group` | 仅展开/收起，不可进入百科 |
| 药盒 | `PILL_ORGANIZER` | `active` | 可进入百科 |
| 分药器 | `PILL_SPLITTER` | `active` | 可进入百科 |

- API `/categories` 返回 `active` + `group`
- 侧栏：`group` 点击 = `toggleTree`；子项点击 = 进入百科
- 总览：分组父卡点击只展开子卡，不跳转
- Agent 扫描下拉：分组名 `disabled`，仅子品类可选

## 与热疗差异

「热疗」仍为 `active` 一级品类（可进入百科）。药物管理父节点为纯导航分组（`group`）。
