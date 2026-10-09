USE meeting_db;

SET @has_recurring_series_id = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'recurring_series_id'
);
SET @add_recurring_series_id = IF(
    @has_recurring_series_id = 0,
    'ALTER TABLE meetings ADD COLUMN recurring_series_id VARCHAR(36) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_recurring_series_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_recurrence_original_start = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'recurrence_original_start'
);
SET @add_recurrence_original_start = IF(
    @has_recurrence_original_start = 0,
    'ALTER TABLE meetings ADD COLUMN recurrence_original_start DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_recurrence_original_start;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_recurrence_is_detached = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'recurrence_is_detached'
);
SET @add_recurrence_is_detached = IF(
    @has_recurrence_is_detached = 0,
    'ALTER TABLE meetings ADD COLUMN recurrence_is_detached BOOLEAN NOT NULL DEFAULT FALSE',
    'SELECT 1'
);
PREPARE stmt FROM @add_recurrence_is_detached;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_recurring_series_index = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND INDEX_NAME = 'ix_meetings_recurring_series_id'
);
SET @add_recurring_series_index = IF(
    @has_recurring_series_index = 0,
    'CREATE INDEX ix_meetings_recurring_series_id ON meetings (recurring_series_id)',
    'SELECT 1'
);
PREPARE stmt FROM @add_recurring_series_index;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
