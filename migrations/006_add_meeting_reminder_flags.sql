-- Add idempotency flags for the 24-hour and 15-minute meeting reminders.
USE meeting_db;

SET @has_is_reminded_24h = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'is_reminded_24h'
);
SET @add_is_reminded_24h = IF(
    @has_is_reminded_24h = 0,
    'ALTER TABLE meetings ADD COLUMN is_reminded_24h BOOLEAN NOT NULL DEFAULT FALSE',
    'SELECT 1'
);
PREPARE stmt FROM @add_is_reminded_24h;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_is_reminded_15m = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'is_reminded_15m'
);
SET @add_is_reminded_15m = IF(
    @has_is_reminded_15m = 0,
    'ALTER TABLE meetings ADD COLUMN is_reminded_15m BOOLEAN NOT NULL DEFAULT FALSE',
    'SELECT 1'
);
PREPARE stmt FROM @add_is_reminded_15m;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
