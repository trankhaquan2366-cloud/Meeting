SET @has_search_keywords = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'equipments'
      AND COLUMN_NAME = 'search_keywords'
);
SET @add_search_keywords = IF(
    @has_search_keywords = 0,
    'ALTER TABLE equipments ADD COLUMN search_keywords TEXT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_search_keywords;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_operational_status = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'equipments'
      AND COLUMN_NAME = 'operational_status'
);
SET @add_operational_status = IF(
    @has_operational_status = 0,
    'ALTER TABLE equipments ADD COLUMN operational_status VARCHAR(20) NOT NULL DEFAULT ''active''',
    'SELECT 1'
);
PREPARE stmt FROM @add_operational_status;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @normalize_operational_status = IF(
    @has_operational_status = 0,
    'UPDATE equipments SET operational_status = ''retired'' WHERE is_active = 0',
    'SELECT 1'
);
PREPARE stmt FROM @normalize_operational_status;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
