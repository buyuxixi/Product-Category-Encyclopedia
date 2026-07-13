# 产品品类百科 MVP

内部 Web 系统，用于沉淀结构化品类知识，展示爬虫采集的热点与趋势数据，并支持基于来源材料的百科内容维护和选品 Agent 分析。

## 技术栈

- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic
- Database: MySQL 8.0
- Frontend: Vue 3, TypeScript, Vite, Element Plus
- Runtime: Docker Compose

当前数据链路以爬虫采集为主：热点链接写入 `hot_links`，趋势信号写入 `trend_signals`，研究材料写入 `source_materials` 并可绑定到百科章节。MySQL 是唯一数据主库；飞书只用于可选的登录鉴权，不再承接旧的版本发布流程。

## 本地启动

1. 创建环境文件：

   ```bash
   cp .env.example .env
   ```

2. 在 `.env` 中配置登录账号。示例：

   ```env
   AUTH_MODE=local
   AUTH_USERS_JSON=[{"username":"admin","password":"请替换为强密码","role":"admin","display_name":"管理员"}]
   ```

   不要把真实密码、Cookie、`.session` 或浏览器状态文件提交到 Git。业务部署时建议改为 `AUTH_MODE=feishu`，并配置 Feishu OAuth。

3. 启动应用：

   ```bash
   docker compose up --build
   ```

4. 打开：

   - Web: <http://localhost:4173>
   - API: <http://localhost:8010/docs>
   - MySQL: `127.0.0.1:3308`

默认开发身份由页面右上角选择。生产环境必须接入飞书 SSO，不能继续信任开发请求头。

## 业务使用主流程

1. 爬虫按计划或受控手动触发，向 `hot_links` 和 `trend_signals` 写入带来源 URL 的数据。
2. 登录后进入品类百科，查看市场热点、趋势信号和已登记的来源材料。
3. 研究人员可补充来源材料、编辑百科章节并绑定证据；人工编辑内容会被锁定，避免被自动生成覆盖。
4. 选品 Agent 读取数据库中的真实链接和趋势数据，生成产品机会分析与多轮对话记录。
5. 需要对外使用时，可导出单个章节或完整品类 Markdown。

旧的文件导入、版本审核、发布到飞书流程已从当前应用移除；对应的历史 Alembic 迁移文件仅保留作数据库演进记录。

## 后端测试

```bash
cd backend
.venv/bin/pytest
```

本地开发可直接启动后端：

```bash
cd backend
DATABASE_URL='mysql+pymysql://encyclopedia:encyclopedia_dev@127.0.0.1:3308/category_encyclopedia?charset=utf8mb4' \
.venv/bin/uvicorn app.main:app --reload --port 8000
```

## 前端校验

```bash
cd frontend
pnpm build
```

启动前端开发服务：

```bash
VITE_DEV_PROXY_TARGET='http://127.0.0.1:8000' pnpm dev
```

如本机 8000 端口已被占用，可让后端改用其他端口，并同步修改 `VITE_DEV_PROXY_TARGET`。

## 鉴权与安全边界

- 默认使用服务端 session cookie 鉴权，前端不能自行选择角色。
- `AUTH_MODE=feishu` 时通过 Feishu OAuth 登录；角色由服务端配置映射。
- 爬虫开关 `CRAWLER_ENABLED` 默认是 `false`；启用前应在独立目录配置脚本和容器可访问的 API 地址，并确认代理与限速策略。
- Agent 默认只读取数据库已有数据；未配置 `LLM_API_KEY` 时不会发起外部模型请求。
- 来源 URL、采集时间和 Agent 分析记录保留在业务库中，便于追溯。

## 常用本地命令

```bash
cd backend && .venv/bin/pytest
cd frontend && pnpm typecheck && pnpm build
```

本地直接启动后端时，需要把 `DATABASE_URL`、`AUTH_MODE` 和 `AUTH_USERS_JSON` 配置到当前 shell。爬虫相关配置见 `.env.example`，默认不会执行采集。
