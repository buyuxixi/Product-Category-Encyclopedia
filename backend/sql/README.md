# 增量 SQL

按以下顺序执行：

```bash
mysql -u <user> -p category_encyclopedia \
  < backend/sql/2026-07-13_add_zh_label_columns.sql

mysql -u <user> -p category_encyclopedia \
  < backend/sql/2026-07-13_xhs_incremental_data.sql
```

## 文件说明

- `2026-07-13_add_zh_label_columns.sql`
  - 为 `hot_links`、`trend_signals` 增加中文标签列。
  - 已存在的列会跳过，可重复执行。
- `2026-07-13_xhs_incremental_data.sql`
  - 增量写入本轮精选小红书链接和评论趋势信号。
  - 热点链接按 URL 去重，趋势信号按品类、平台和标题去重。
  - 将 TENS cleaned 清单中的已知旧链接收敛至确认保留的 10 条。
  - 不依赖自增 ID，通过品类 `code` 查找外键。

两个脚本已在临时数据库连续执行两次验证，第二次不会产生重复数据。
