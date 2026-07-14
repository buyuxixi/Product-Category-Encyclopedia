-- ============================================================================
-- Migration: 为 hot_links / trend_signals 表增加中文标签列
-- Date: 2026-07-13
-- Author: Luka
--
-- 说明：
--   爬虫抓取的 title/description/summary 全部是英文原文。
--   新增 4 个 nullable 列，存储 LLM 生成的中文标签。
--   已有数据不受影响（新列默认 NULL），前端将优先展示中文标签。
--
--   前端展示逻辑：
--     优先显示 title_zh（中文标签），无则 fallback 到 title（英文原文）
--     description_zh 同理
--
-- 执行方式：
--   mysql -u <user> -p category_encyclopedia < add_zh_label_columns.sql
--   或在 MySQL Workbench / Navicat 中直接粘贴执行
-- ============================================================================

-- hot_links 表
ALTER TABLE hot_links
  ADD COLUMN title_zh VARCHAR(200) NULL COMMENT 'LLM生成的中文标题标签',
  ADD COLUMN description_zh TEXT NULL COMMENT 'LLM生成的中文描述';

-- trend_signals 表
ALTER TABLE trend_signals
  ADD COLUMN title_zh VARCHAR(200) NULL COMMENT 'LLM生成的中文标题标签',
  ADD COLUMN summary_zh TEXT NULL COMMENT 'LLM生成的中文摘要';

-- 验证
SELECT
  TABLE_NAME,
  COLUMN_NAME,
  COLUMN_TYPE,
  IS_NULLABLE,
  COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('hot_links', 'trend_signals')
  AND COLUMN_NAME IN ('title_zh', 'description_zh', 'summary_zh');
