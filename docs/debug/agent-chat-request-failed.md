# Agent 对话「Failed to fetch」/ 扫描列表为空

## 问题描述

打开选品 Agent 页弹「Failed to fetch」，左侧显示「暂无对话」。

## 根因

热更新的 `nginx.conf` 使用了：

```nginx
location /api/v1/agent/scans/ { ... }
```

对列表接口 `GET /api/v1/agent/scans?limit=...`（无尾斜杠），Nginx 返回 **301**，Location 为 `http://127.0.0.1/api/v1/agent/scans/?limit=...`（**丢掉 4173 端口**）。浏览器 `fetch` 跟到错误地址 → `TypeError: Failed to fetch`。

更改 Nginx 后问题仍会复现，因为 **301 是永久重定向，Chrome 会缓存它**。证据是刷新后其他 API 都返回 200，但浏览器没有向 Nginx 发出 `/agent/scans` 请求。

## 修复

改为不带强制尾斜杠的前缀：

```nginx
location /api/v1/agent/scans {
  proxy_buffering off;
  ...
}
```

同时覆盖列表与 `/chat/stream` SSE。

前端列表请求增加 `_route=v2` 查询参数，使用一个未被 301 缓存污染的新 URL：

```text
/api/v1/agent/scans?limit=100&_route=v2
```

通用 `apiRequest` 也补充网络异常转换，后续不再只显示浏览器原生 `Failed to fetch`。

## 验证

- 新前端资源：`index-C39huxA5.js`
- `GET /api/v1/agent/scans?limit=100&_route=v2` → 未登录 401 JSON（证明请求到达后端，无 301）
- `POST .../chat/stream` → text-delta 正常
