-- Store encrypted Google Calendar refresh tokens for opted-in users.
-- Run against the application's configured database.

SET @has_google_refresh_token = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'google_refresh_token'
);
SET @add_google_refresh_token = IF(
    @has_google_refresh_token = 0,
    'ALTER TABLE users ADD COLUMN google_refresh_token TEXT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_google_refresh_token;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_google_calendar_connected_at = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'google_calendar_connected_at'
);
SET @add_google_calendar_connected_at = IF(
    @has_google_calendar_connected_at = 0,
    'ALTER TABLE users ADD COLUMN google_calendar_connected_at DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_google_calendar_connected_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;