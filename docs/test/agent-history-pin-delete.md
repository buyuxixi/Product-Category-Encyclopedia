# 选品 Agent 历史顶置/删除 & 发现页输入框

| 用例 | 步骤 | 预期 | 结果 |
|---|---|---|---|
| 发现页无输入框 | 打开已完成扫描 → 切「发现」 | 底部输入框消失 | 代码：`v-if="mainTab === 'chat' \|\| failed"`；前端已 build 部署 |
| 对话页有输入框 | 切回「对话」 | 输入框出现 | 同上 |
| 列表含 is_pinned | `GET /agent/scans` | 每项有 `is_pinned` | ✅ 实测 False |
| 顶置排序 | PATCH is_pinned=true 后刷新列表 | 该项排最前 | 单元测试 ✅ |
| 硬删除级联 | 删除含 discovery 的 scan | scan + discovery 均无 | 单元测试 ✅ |

## 验证命令

```bash
cd backend && python3 -m pytest tests/test_agent_service.py -q
# 迁移：b8c9d0e1f2a3
```
