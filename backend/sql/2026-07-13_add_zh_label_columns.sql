-- 中文标签字段增量更新（MySQL 8）
-- 可重复执行；已有列会自动跳过。

SET @schema_name = DATABASE();

SET @ddl = IF(
  EXISTS(
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema_name AND TABLE_NAME = 'hot_links' AND COLUMN_NAME = 'title_zh'
  ),
  'SELECT 1',
  'ALTER TABLE hot_links ADD COLUMN title_zh VARCHAR(200) NULL COMMENT ''LLM生成的中文标题标签'' AFTER title'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  EXISTS(
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema_name AND TABLE_NAME = 'hot_links' AND COLUMN_NAME = 'description_zh'
  ),
  'SELECT 1',
  'ALTER TABLE hot_links ADD COLUMN description_zh TEXT NULL COMMENT ''LLM生成的中文描述'' AFTER description'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  EXISTS(
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema_name AND TABLE_NAME = 'trend_signals' AND COLUMN_NAME = 'title_zh'
  ),
  'SELECT 1',
  'ALTER TABLE trend_signals ADD COLUMN title_zh VARCHAR(200) NULL COMMENT ''LLM生成的中文标题标签'' AFTER title'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = IF(
  EXISTS(
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema_name AND TABLE_NAME = 'trend_signals' AND COLUMN_NAME = 'summary_zh'
  ),
  'SELECT 1',
  'ALTER TABLE trend_signals ADD COLUMN summary_zh TEXT NULL COMMENT ''LLM生成的中文摘要'' AFTER summary'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT
  TABLE_NAME,
  COLUMN_NAME,
  COLUMN_TYPE,
  IS_NULLABLE,
  COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('hot_links', 'trend_signals')
  AND COLUMN_NAME IN ('title_zh', 'description_zh', 'summary_zh')
ORDER BY TABLE_NAME, ORDINAL_POSITION;
