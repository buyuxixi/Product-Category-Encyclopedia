# Business-Usable Product Category Encyclopedia Design

## Design Summary

将现有原型改造成业务人员可以直接使用的内部工作台：用户先登录，再从真实 Amazon 数据目录导入或查看品类，能够搜索并阅读百科、查看证据、编辑草稿、提交审核、发布本地导出或飞书文档。

本轮默认假设：

- 真实数据源目录为 `/Users/luka/Downloads/res`，部署时通过 `IMPORT_DATA_PATH` / `IMPORT_ROOTS` 配置，不把数据复制进 Git。
- 生产首选飞书 OAuth 登录；在没有 App ID/Secret 前，提供受控的本地账号模式用于开发和验收。
- Web 应用仍以 MySQL 为主库，现有 Vue 3 + FastAPI 技术栈保留。
- 本轮不接入外部大模型；草稿继续使用可追溯的本地确定性生成器，但必须显式选择来源并保存生成输入。

## Existing Context

- 当前后端已有 Category、ListingSnapshot、SourceMaterial、Section、Version、Publication 和 AuditEvent 基础模型。
- 当前前端有百科、导入、审核三个页面，但角色由前端下拉框和客户端请求头决定。
- 数据目录包含大量大小写/命名别名目录，例如 `FAR_INFRARED` 与 `Far-infrared`，以及多个非热疗品类；当前导入器只支持 4 个热疗目录。
- 当前 `sample-data` 为空，不能作为首次使用数据。

## Proposed Changes

| Area | Change | Files/modules |
| --- | --- | --- |
| Authentication | 增加基于 HttpOnly session cookie 的登录、当前用户、退出；生产支持飞书 OAuth 回调；权限由服务端会话解析 | `backend/app/auth/`, `backend/app/api.py`, `backend/app/models.py`, `frontend/src/LoginView.vue` |
| Authorization | 明确 admin/data/researcher/reviewer 权限；所有写接口和敏感读取统一依赖当前会话；移除前端角色伪造 | `backend/app/security.py`, `backend/app/api.py` |
| Data import | 支持配置目录扫描、CSV/JSON、目录预览、别名归并、去重、失败明细和可重复导入 | `backend/app/services/import_service.py`, import schemas/API, `ImportView.vue` |
| Category discovery | 从数据目录发现可导入品类，保留稳定 code；热疗作为已确认样板，其他目录可作为待整理品类 | `backend/app/seed.py`, category/import services |
| Search | 搜索品类、别名、正文、来源、Listing 标题/品牌/痛点；结果可定位到品类或章节 | backend search service/API, frontend search panel |
| Evidence | 证据返回来源标题、站点、ASIN、采集时间、URL 和定位；章节可选择/移除证据；来源材料可查看 | models/API/`EncyclopediaView.vue` |
| Draft workflow | 选择来源和模块生成草稿；保存 provider、输入 source IDs、输出和待确认项；保护人工锁定内容 | `draft_service.py`, models/migration, frontend drawer |
| Review workflow | 待审核/已发布内容锁定；版本详情、差异、证据检查、退回意见和发布记录可见 | `workflow_service.py`, version APIs, `ReviewView.vue` |
| Publishing | 本地 Markdown 下载/复制可用；Feishu publisher 在配置凭据后创建文档并返回链接 | `integrations/feishu.py`, publication APIs/UI |
| Usability | 首次使用引导、明确空状态、中文状态、正文目录、来源面板、移动端可读布局 | `App.vue`, views, `styles.css` |

## Contracts And Data

### Authentication

- `GET /api/v1/auth/config`：返回是否需要登录、可用登录方式和展示名称，不返回密钥。
- `POST /api/v1/auth/local/login`：仅在 `AUTH_MODE=local` 时可用；接收账号密码，成功后设置 HttpOnly、Secure（生产）session cookie。
- `GET /api/v1/auth/feishu/start`：仅在 `AUTH_MODE=feishu` 且配置完整时跳转官方 OAuth 授权地址。
- `GET /api/v1/auth/feishu/callback`：校验 state，使用一次性 code 换取用户信息，建立本地 session。
- `GET /api/v1/auth/me`：返回当前用户 id、姓名、角色和登录来源。
- `POST /api/v1/auth/logout`：撤销本地 session。

Session 只保存随机不可预测 token 的哈希、用户 id、创建时间、过期时间和撤销时间；不把 Feishu access token 返回前端。用户以 Feishu open_id 作为外部稳定标识，角色由本地用户表或受控配置决定。

### Import

- `POST /api/v1/imports/preview`：接受 JSON/CSV 文件或已配置目录，返回目录/字段/样本/重复预估，不写业务数据。
- `POST /api/v1/imports/amazon`：使用 preview 结果或配置目录执行导入。
- 每个文件单独事务；同一 `(marketplace, asin, scraped_at)` 幂等；敏感键如 cookie、session、token、password 不写入 raw payload。
- 导入状态至少包含 `queued/running/completed/completed_with_errors/failed`，错误只返回文件名和安全原因。

### Search and evidence

- 搜索结果统一包含 `kind`、`category_code`、`title`、`snippet`、`section_key`、`updated_at` 和可选 `source_id`。
- 章节证据必须关联 `listing_snapshot` 或 `source_material`，API 返回已解析的展示字段而不是只返回裸 ID。
- 页面展示采集日期和“待复核”状态，不能把 2026 年 2 月快照写成实时市场状态。

### Workflow invariants

- `pending_review` 和 `published` 版本不可被当前编辑直接改变；修改必须从版本创建新 draft。
- 生成草稿不得覆盖 `locked_by_human=true` 的章节。
- 提交审核前检查至少一个有内容章节、所有关键章节都有证据或“待验证”标记。
- 发布只接受 `approved` 版本，发布失败可重试且不改变审批结果。

## Workflow And Side Effects

1. 用户登录并看到自己可操作的工作区。
2. 首次使用进入“数据准备”向导，选择已配置数据目录或上传文件，预览映射和重复项。
3. 导入后从品类树或搜索找到品类，阅读正文、Listing、来源和证据。
4. 研究人员选择来源和模块生成草稿；系统显示生成范围、缺失证据和待验证项。
5. 用户编辑章节并锁定；提交审核生成不可变版本。
6. 审核人查看正文、证据和差异后通过或退回。
7. 管理员/审核人导出 Markdown 或显式发布到已配置的飞书文档，记录链接和结果。

外部网络调用只发生在 Feishu OAuth、用户信息和显式发布动作；都需要超时、错误脱敏和可审计记录。

## Security And Failure Handling

- 默认不再使用 `development` 角色头作为可部署模式；开发模式也必须登录或使用明确的本地开发账号。
- CSRF：所有 cookie 写请求检查 same-site/CSRF token；CORS 只允许配置的前端 origin。
- 登录失败使用统一错误，不泄露账号是否存在；session 过期返回 401，前端跳转登录并保留未提交编辑提示。
- Feishu state 一次性、短时有效；App Secret 只在后端环境变量中存在。
- 导入路径必须位于配置根目录；拒绝 `.session`、隐藏文件、符号链接和不符合 Listing schema 的文件。
- 原始数据中的 cookies、authorization、access_token、refresh_token、password、session 等字段全部丢弃或遮蔽。

## Test Plan

### Backend

- 登录成功、错误密码、过期 session、退出后访问、未登录写接口、角色权限矩阵。
- Feishu OAuth state 不匹配、回调错误、用户信息请求失败；无凭据时安全降级。
- JSON/CSV preview、目录别名、重复导入、坏文件、`.session`、超大文件和敏感键清洗。
- 搜索命中类别/正文/Listing/来源及空结果。
- 证据展示、人工锁定、待审核/已发布编辑拦截、版本差异和审核门槛。
- 本地导出成功、Feishu 发布失败和重复发布幂等。

### Frontend

- 登录/退出和 401 处理。
- 首次导入向导、结果统计、失败明细和重复提示。
- 搜索结果定位章节、正文目录和来源证据抽屉。
- 草稿选择/应用、人工锁定、审核退回和发布结果。
- 390px、768px 和桌面宽度下的阅读、导入和审核布局。

## Implementation Steps

1. 修正启动和测试基线，接入真实 `/Users/luka/Downloads/res` 作为本地配置数据根目录。
2. 增加用户、session、登录 API 和服务端权限依赖，前端加入登录页。
3. 重构导入服务：目录发现、JSON/CSV preview、敏感字段清洗和全目录导入。
4. 增加搜索、来源/证据详情、版本差异和状态锁定。
5. 重做前端首屏、导航、正文目录、来源/证据和审核页面，修复移动端。
6. 完成本地 Markdown 下载/复制，并保留 Feishu OAuth/发布配置入口。
7. 添加 API/服务测试、前端构建和浏览器端到端验收。

## Required User Configuration Before Production

- Feishu 自建应用 App ID、App Secret、OAuth redirect URI 和可见范围/成员角色映射。
- 部署域名、HTTPS 和数据库持久化位置。
- 业务 Owner、审核人和管理员名单。
- 是否允许所有公司成员登录，或只允许指定部门/邮箱域。

