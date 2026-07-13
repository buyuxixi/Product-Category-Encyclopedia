# Agent 对话流式 + Markdown 验证

## 测试概要

| 项 | 结果 |
|---|---|
| SSE 端点注册 | ✅ OpenAPI 含 `/chat/stream` |
| 未登录 | ✅ 401 |
| 已登录流式 | ✅ 连续 `text-delta` 事件 |
| Markdown 表格渲染 | ✅ `renderMarkdown` 产出 `<table class="md-table">` |

## 用例 1：SSE 流式

- **请求**: `POST /api/v1/agent/scans/16/chat/stream`（登录后）
- **预期**: 多条 `data: {"event":"text-delta",...}`，最终 `[DONE]`
- **结果**: ✅ 约 3s 内开始吐字，内容含 Markdown 表格管道符

## 用例 2：Markdown 表格

- **输入**: GFM 表格 + 加粗 + 列表
- **预期**: HTML 含 `<table>` / `<strong>` / `<ul>`
- **结果**: ✅ Node 直接调用 `lib/markdown.ts` 通过
