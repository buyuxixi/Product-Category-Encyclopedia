# 选品笔记示例数据

## 背景

选品笔记存于浏览器 `localStorage`（`encyclopedia_notes`），新环境常为空，演示时界面只有引导页。

## 方案

首次进入且笔记为空时，种入 8 条示例笔记（覆盖「选品机会 / 竞品分析 / 用户洞察 / 技术趋势 / 其他」），并写入标记 `encyclopedia_notes_seeded_v1=1`。

用户手动删光笔记后**不再**自动回填，避免干扰真实使用。

## 重置示例数据

浏览器控制台执行：

```js
localStorage.removeItem('encyclopedia_notes')
localStorage.removeItem('encyclopedia_notes_seeded_v1')
location.reload()
```
