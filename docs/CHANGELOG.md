# CHANGELOG

## 2026-07-13（社区讨论展示小红书 social_post）

### Bug 修复
- 小红书 `link_type=social_post` 热点入库后界面不显示：并入「社区讨论」Tab 与 Reddit 一起展示
- 平台标签补齐「小红书」；总览热门讨论同步纳入小红书
- 修复 `AgentView.vue` 流式光标 CSS 未闭合字符串，导致前端无法构建
- Agent 对话失败时不再只显示笼统「请求失败」，改为带 HTTP 状态 / 响应摘要；已热更新 Docker 前端静态包（含 `chat/stream`）
- 修复 Nginx 尾斜杠导致列表接口 301 到错误端口，并用新 URL 绕过 Chrome 已缓存的永久重定向

### 代码变更
- `frontend/src/views/EncyclopediaView.vue`
- `frontend/src/views/DashboardView.vue`
- `frontend/src/views/TrendView.vue`
- `frontend/src/views/AgentView.vue`
- `frontend/src/api.ts`
- `frontend/Dockerfile`
- `docs/debug/xhs-social-post-not-shown.md`
- `docs/debug/agent-chat-request-failed.md`

## 2026-07-13（Agent 对话流式输出 + Markdown 表格）

### 新增功能
- 选品 Agent 对话改为 SSE 流式输出，前端逐字渲染
- 对话 Markdown 支持表格 / 标题 / 列表 / 代码块等，修复表格显示为原始 `|` 的问题

### 优化
- 对话 LLM 调用关闭 JSON mode，避免自由文本被网关约束
- Nginx 对 `/api/v1/agent/scans/` 关闭 proxy buffering，保障 SSE

### 代码变更
- `backend/app/services/agent_service.py`
- `backend/app/api.py`
- `frontend/src/views/AgentView.vue`
- `frontend/src/api.ts`
- `frontend/src/lib/markdown.ts`
- `frontend/nginx.conf`
- `docs/design/agent-chat-streaming-markdown.md`

## 2026-07-13（修复 Reddit OAuth 爬取回退）

### 修复
- 单品类与定时 Reddit 爬取复用 OAuth 优先、RSS 回退的共享逻辑。
- 修复 RSS 空响应时将 HTTP 429 误判为 HTTP 0 的问题，并支持重定向。

### 代码变更
- `backend/crawler/crawl_reddit.py`
- `backend/crawler/crawl_reddit_single.py`
- `backend/requirements.txt`
- `backend/tests/test_reddit_crawler.py`
- `backend/crawler/README.md`
- `docs/debug/reddit-oauth-fallback.md`

## 2026-07-13（总览展示热疗子品类）

### 新增功能
- 总览品类概览在一级品类后展示其子品类卡片（如热疗 → 肩颈热敷、远红外热疗），子卡带父品类标注

### 代码变更
- `frontend/src/views/DashboardView.vue`
- `frontend/src/styles.css`

## 2026-07-13（总览品类卡片墙可扩展布局）

### 优化
- 总览品类区由 5 卡 Bento 改为均匀三列网格，5 个时自然排成 3+2，观感更整齐
- 一级品类超过 12 个时按活跃度截断并提供「查看全部」入口，避免挤占下方动态区

### 代码变更
- `frontend/src/views/DashboardView.vue`
- `frontend/src/styles.css`
- `frontend/src/App.vue`
- `docs/design/dashboard-category-grid-scale.md`
