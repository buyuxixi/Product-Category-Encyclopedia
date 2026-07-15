# 选品 Agent：发现页隐藏输入框 + 历史顶置/删除

## 背景

选品 Agent 界面存在两处体验问题：
1. 「发现」tab 底部仍显示聊天输入框，与发现列表无关
2. 左侧扫描历史无法顶置或删除，失败记录堆积难清理

## 方案设计

### 前端
- 输入框仅在 `mainTab === 'chat'` 或扫描失败态显示
- 历史项 hover 显示顶置 / 删除；删除二次确认；操作 `stopPropagation` 避免误开会话

### 后端
- `agent_scans.is_pinned` BOOLEAN，列表按 `is_pinned DESC, id DESC`
- `PATCH /agent/scans/{id}`：更新顶置
- `DELETE /agent/scans/{id}`：硬删除（ORM cascade 清理 discoveries / messages）

## 核心接口

```http
PATCH /api/v1/agent/scans/{id}
{"is_pinned": true}

DELETE /api/v1/agent/scans/{id}
```

## 迁移

- Alembic：`b8c9d0e1f2a3_add_agent_scan_is_pinned.py`

```bash
cd backend && alembic upgrade head
# 或在 docker：
docker compose exec backend alembic upgrade head
```

## 使用说明

1. 打开选品 Agent → 切到「发现」：底部输入框应消失
2. 悬停历史项 → 点顶置图标：该项置顶；再点取消
3. 点删除 → 确认后从列表移除；若删当前项则切到下一项或空态
