# 产品品类百科 MVP

内部 Web 系统，用于沉淀结构化品类知识、导入 Amazon Listing、生成可追溯草稿、人工审核，并将已发布版本单向同步到飞书。

## 技术栈

- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic
- Database: MySQL 8.0
- Frontend: Vue 3, TypeScript, Vite, Element Plus
- Runtime: Docker Compose

MVP 不使用向量数据库。MySQL 是唯一数据主库；飞书只承接发布结果、阅读、评论与分享。

## 本地启动

1. 创建环境文件：

   ```bash
   cp .env.example .env
   ```

2. 在 `.env` 中配置登录账号和数据目录。真实数据目录可以直接使用：

   ```env
   AUTH_MODE=local
   AUTH_USERS_JSON=[{"username":"admin","password":"请替换为强密码","role":"admin","display_name":"管理员"}]
   IMPORT_DATA_PATH=/Users/luka/Downloads/res
   ```

   不要把真实密码、Cookie、`.session` 或浏览器状态文件提交到 Git。业务部署时建议改为 `AUTH_MODE=feishu`，并配置 Feishu OAuth。

3. 启动应用：

   ```bash
   docker compose up --build
   ```

4. 打开：

   - Web: <http://localhost:4173>
   - API: <http://localhost:8000/docs>
   - MySQL: `127.0.0.1:3308`

默认开发身份由页面右上角选择。生产环境必须接入飞书 SSO，不能继续信任开发请求头。

## 业务使用主流程

1. 登录后进入“数据导入”，扫描配置的数据目录，选择需要导入的品类。
2. 系统将同义目录映射为稳定品类编码，并按站点、ASIN、采集时间去重。
3. 在品类详情中生成草稿，选择需要应用的模块。
4. 人工编辑模块后，该模块会锁定，后续生成不能静默覆盖。
5. 提交审核，在“审核发布”中通过版本。
6. 下载/复制本地发布内容；配置 Feishu OAuth 和发布凭据后，可以进一步同步到飞书。

## 后端测试

```bash
cd backend
.venv/bin/pytest
```

本地开发可直接启动后端：

```bash
cd backend
DATABASE_URL='mysql+pymysql://encyclopedia:encyclopedia_dev@127.0.0.1:3308/category_encyclopedia?charset=utf8mb4' \
IMPORT_ROOTS='/path/to/res' \
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
- 只允许从 `IMPORT_ROOTS` 配置的目录导入。
- `.session`、Cookie、浏览器状态和非 Listing JSON 不进入业务库。
- AI 默认使用本地确定性草稿提供者，不发起外部模型请求。
- 发布必须基于人工审核通过的不可变版本。

## 常用本地命令

```bash
cd backend && .venv/bin/pytest
cd frontend && pnpm typecheck && pnpm build
```

本地直接启动后端时，需要把 `DATABASE_URL`、`IMPORT_ROOTS`、`AUTH_MODE` 和 `AUTH_USERS_JSON` 配置到当前 shell；Docker Compose 会自动把宿主机 `IMPORT_DATA_PATH` 挂载到容器 `/imports`。
