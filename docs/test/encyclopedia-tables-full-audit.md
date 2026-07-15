# 百科全品类表格全量检查

**日期**: 2026-07-14  
**范围**: 本地库全部 `encyclopedia_sections` 中的 Markdown 表格  
**品类数**: 9  
**表格总数**: 150

## 检查项

| 检查项 | 说明 |
|---|---|
| 分隔行 | 存在 `|---|` 且位置正确 |
| 列数一致 | 表头 / 分隔行 / 数据行列数相同 |
| 加粗标记 | 无奇数个 `**`、无 `*text**` 损坏模式 |
| 首列竖排 | 已由 CSS `td:first-child { white-space: nowrap }` 全局处理 |

## 结果概要

| 品类 | 表格数 | 结果 |
|---|---:|---|
| FAR_INFRARED 远红外热疗 | 25 | ✅ |
| HEAT_THERAPY 热疗 | 9 | ✅ |
| MEDICATION_MANAGEMENT 药物管理（停用） | 23 | ✅ |
| NIGHT_LIGHT 夜间照明-夜灯 | 9 | ✅ |
| PILL_ORGANIZER 药物管理-药盒 | 17 | ✅ |
| PILL_SPLITTER 药物管理-切药器 | 17 | ✅ |
| SEAT_CUSHION 坐垫健康-办公坐垫 | 10 | ✅ |
| SHOULDER_NECK_HEAT_THERAPY 肩颈热敷 | 12 | ✅ |
| TENS_THERAPY 电疗 TENS | 28 | ✅（修复后） |

**最终**: 问题表 0 / 加粗问题 0 → ALL PASS

## 本次发现并修复

### TENS_THERAPY / technology

1. `#### TENS 设备主体材料`：表头 4 列，部分数据行缺「参考产品」列 → 已补齐  
2. `#### 电极片材料`：同上 → 已补齐  

同步文件：`data/tens_therapy.md` + 本地库 `encyclopedia_sections`（TENS_THERAPY / technology）

## 验收

- [x] 全库表格列数一致  
- [x] 全库无损坏加粗  
- [x] TENS 两处材料表已 4 列对齐  
