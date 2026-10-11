-- Calendar refresh tokens are stored encrypted by the application.
-- Apply this migration to the configured MySQL database before deploying.

SET @has_google_refresh_token = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
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
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
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

CREATE TABLE IF NOT EXISTS google_calendar_events (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    meeting_id INT NOT NULL,
    google_event_id VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_google_event_user_meeting (user_id, meeting_id),
    UNIQUE KEY uq_google_event_user_event (user_id, google_event_id),
    CONSTRAINT fk_google_calendar_event_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_google_calendar_event_meeting
        FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;