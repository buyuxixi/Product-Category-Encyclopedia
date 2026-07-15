# CHANGELOG

## 2026-07-14（药物管理分组标题精简）

### 优化
- 一级分组展示名由「药物管理（药盒，分药器）」改为「药物管理」；子项「药盒」「分药器」不变

### 代码变更
- `backend/app/seed.py`
- 本地 DB `categories`（MEDICATION_MANAGEMENT.name）

## 2026-07-14（药物管理导航分组）

### 新增 / 优化
- 侧栏增加一级「药物管理（药盒，分药器）」：仅下拉分组，不可点进百科
- 子项展示为「药盒」「分药器」，可进入对应百科页
- 品类 `status=group`；总览分组卡只展开；Agent 下拉分组不可选

### 代码变更
- `backend/app/seed.py`
- `backend/app/api.py`
- `frontend/src/App.vue`
- `frontend/src/views/DashboardView.vue`
- `frontend/src/views/AgentView.vue`
- `frontend/src/styles.css`
- `docs/design/medication-nav-group.md`

## 2026-07-14（药盒 1.2 产品类型表排版）

### Bug 修复 / 优化
- 五列表「分格数」「典型材质」被挤成断行（如 `7-28` / `格`）；短单元格 `nowrap`，表头不换行
- 宽表外包横向滚动；首列改为限宽可换行，避免长类型名挤爆中间列
- 同步药盒 1.2 表结构（含药罐/储药瓶行）

### 代码变更
- `frontend/src/styles.css`
- `frontend/src/views/EncyclopediaView.vue`
- `data/pill_organizer.md`

## 2026-07-14（全品类表格全量检查）

### Bug 修复
- 扫描 9 品类共 150 张表：TENS `technology` 两处材料表缺「参考产品」列，已补齐
- 其余品类表格列数 / 加粗标记均通过

### 代码变更
- `data/tens_therapy.md`
- 本地 DB `encyclopedia_sections`（TENS_THERAPY / technology）
- `docs/test/encyclopedia-tables-full-audit.md`

## 2026-07-14（百科表格首列竖排换行修复）

### Bug 修复
- Markdown 表格「阶段」等短标签列被长文挤压后逐字竖排；首列改为 `nowrap` / `keep-all`

### 代码变更
- `frontend/src/styles.css`

## 2026-07-14（远红外 3.2 表格 Markdown 格式修复）

### Bug 修复
- 远红外「用户需求与品类痛点」3.2 表格中加粗标记损坏（如 `*专业评测站**`），界面显示原始 `**` 星号
- 已用 `data/far_infrared.md` 正确内容回写本地库 `needs` 章节，并清理列表项多余空格

### 代码变更
- `data/far_infrared.md`
- 本地 DB `encyclopedia_sections`（FAR_INFRARED / needs）

## 2026-07-14（登录页左侧数据与描述更新）

### 优化
- 热点链接展示由 `659+` 更新为 `700+`（对齐库内约 724 条）
- 左侧描述去掉过时的 Google Trends，改为 Amazon、小红书、YouTube、Reddit 等渠道

### 代码变更
- `frontend/src/views/LoginView.vue`

## 2026-07-14（小红书热度归一化到 0–100）

### Bug 修复 / 优化
- 小红书 `hotness_score` 改为分段封顶：`min(赞/100,40)+min(藏/80,30)+min(评/10,20)`，与 Amazon/Reddit 等同量级可比
- `is_hot` 阈值改为 ≥50；选帖排序仍用原始 engagement
- 本地库 60 条已回刷（max 90）；Seed SQL 同步

### 代码变更
- `backend/scripts/import_cleaned_xhs.py`
- `backend/scripts/backfill_xhs_hotness.py`
- `backend/sql/2026-07-13_xhs_all_data.sql`
- `backend/tests/test_xhs_crawler_compatibility.py`
- `docs/design/xhs-hotness-engagement.md`
- `docs/test/xhs-hotness-backfill.md`

## 2026-07-14（选品笔记示例数据）

### 优化
- 首次进入「选品笔记」且无本地笔记时，自动种入 8 条示例（覆盖 5 种标签与现有品类），便于演示

### 代码变更
- `frontend/src/views/NotesView.vue`

## 2026-07-14（趋势发现卡片补链接）

### Bug 修复
- 话题「趋势/讨论」模式部分发现卡片无 `source_links`：优先匹配公开新闻，否则补 Google/Bing 搜索入口
- 扫描快照补充持久化 `live_news` / `topic_links`，便于事后补链

### 代码变更
- `backend/app/services/agent_service.py`
- `backend/tests/test_topic_public_sources.py`
- `docs/design/topic-scan-trends-discussion.md`

## 2026-07-14（总览品类：子品类可从父卡展开）

### 优化
- 品类概览默认只展示一级品类；有子类的父卡显示「N 个子品类」按钮
- 展开后子卡嵌在父卡下方（缩进 + 浅绿底 +「子品类」标签），层级更清晰

### 代码变更
- `frontend/src/views/DashboardView.vue`
- `frontend/src/styles.css`
- `docs/design/dashboard-category-expand.md`

## 2026-07-14（小红书热度统一为赞+藏+评×2）

### Bug 修复
- 同事导入的小红书 `hotness_score` 原先等于点赞数，与选帖用的 engagement 不一致；统一为 `赞 + 收藏 + 评论×2`，`is_hot` 阈值 2000
- 本地库 60 条小红书记录已回刷；Seed SQL 同步，避免二次导入回退

### 代码变更
- `backend/scripts/import_cleaned_xhs.py`
- `backend/scripts/backfill_xhs_hotness.py`
- `backend/sql/2026-07-13_xhs_all_data.sql`
- `backend/tests/test_xhs_crawler_compatibility.py`
- `docs/design/xhs-hotness-engagement.md`
- `docs/test/xhs-hotness-backfill.md`

## 2026-07-14（话题扫描：趋势/讨论模式）

### 新增功能
- 话题扫描库内无选品数据时，拉取 Bing News + Google Suggest，输出趋势/讨论洞察
- 发现页展示友好提示：暂无选品推荐，现阶段为趋势与讨论参考

### Bug 修复
- 话题模式不再注入其他品类 Amazon 商品，避免「水杯文案挂药盒链接」

### 代码变更
- `backend/app/services/topic_public_sources.py`
- `backend/app/services/agent_service.py`
- `backend/tests/test_topic_public_sources.py`
- `frontend/src/views/AgentView.vue`
- `frontend/src/types.ts`
- `docs/design/topic-scan-trends-discussion.md`

## 2026-07-14（选品 Agent 发现页隐藏输入框 + 历史顶置/删除）

### 新增功能
- 扫描历史支持顶置（持久化 `is_pinned`）与硬删除（二次确认）
- 列表按顶置优先、再按 id 倒序

### Bug 修复
- 「发现」tab 不再显示底部聊天输入框（仅对话 / 失败态显示）

### 代码变更
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/api.py`
- `backend/alembic/versions/b8c9d0e1f2a3_add_agent_scan_is_pinned.py`
- `backend/tests/test_agent_service.py`
- `frontend/src/views/AgentView.vue`
- `frontend/src/types.ts`
- `docs/design/agent-history-pin-delete.md`

## 2026-07-14（修复选品扫描「请求失败」）

### Bug 修复
- `run_scan()` 成功路径补回 `return scan`，避免接口 500（`scan is None`）
- LLM 读超时提到 180s；Nginx `/api/v1/agent/scan` 超时提到 300s，减少误报超时

### 代码变更
- `backend/app/services/agent_service.py`
- `frontend/nginx.conf`
- `docs/debug/agent-scan-request-failed.md`

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
