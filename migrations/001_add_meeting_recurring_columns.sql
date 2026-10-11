-- Additive migration for existing MySQL databases. Run while using meeting_db.
-- Safe to re-run: each column is only added if it does not already exist.

USE meeting_db;

-- Check and add is_recurring
SET @has_is_recurring = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'meetings'
      AND COLUMN_NAME  = 'is_recurring'
);

SET @add_is_recurring = IF(
    @has_is_recurring = 0,
    'ALTER TABLE meetings ADD COLUMN is_recurring TINYINT(1) NOT NULL DEFAULT 0 AFTER description',
    'SELECT 1'
);
PREPARE stmt FROM @add_is_recurring;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add recurring_type
SET @has_recurring_type = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'meetings'
      AND COLUMN_NAME  = 'recurring_type'
);

SET @add_recurring_type = IF(
    @has_recurring_type = 0,
    'ALTER TABLE meetings ADD COLUMN recurring_type VARCHAR(20) NULL AFTER is_recurring',
    'SELECT 1'
);
PREPARE stmt FROM @add_recurring_type;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;