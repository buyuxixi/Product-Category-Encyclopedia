# 选品扫描「请求失败」排查

## 问题描述

在选品 Agent 对「夜间照明-夜灯」点「开始扫描」后，顶部弹出「请求失败」。

## 日志证据

1. Nginx：`POST /api/v1/agent/scan` → **504**（upstream timed out，默认 60s）
2. Backend：`httpx.ReadTimeout` → `AgentError: LLM服务暂时不可用`
3. 再次点击后：`POST /api/v1/agent/scan` → **500**  
   `AttributeError: 'NoneType' object has no attribute 'id'`  
   发生在 `trigger_agent_scan` → `_scan_payload(scan)`，说明 `run_scan()` 返回了 `None`

## 根因

1. **LLM 调用超时**：扫描 prompt 大、`max_tokens=12000`，偶发超过 Nginx 默认 60s / httpx 90s。
2. **代码 bug**：`run_scan()` 成功路径写完 DB 后**缺少 `return scan`**，函数隐式返回 `None`，接口 500，前端只能显示笼统「请求失败」。

## 修复

- `run_scan()` 成功后 `return scan`
- `call_llm` 读超时改为 180s
- Nginx 为 `POST /api/v1/agent/scan` 设置 `proxy_read_timeout 300s`

## 验证

- 部署后 `inspect.getsource(run_scan)` 含 `return scan`
- Nginx 配置含 `location = /api/v1/agent/scan` 且 timeout 300s
