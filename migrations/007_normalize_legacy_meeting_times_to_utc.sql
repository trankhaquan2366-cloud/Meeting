-- One-time conversion of existing Asia/Ho_Chi_Minh wall-clock values to UTC.
-- The schema_migrations row prevents a second execution from shifting times again.
USE meeting_db;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) NOT NULL PRIMARY KEY,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

START TRANSACTION;

INSERT IGNORE INTO schema_migrations (version)
VALUES ('007_normalize_legacy_meeting_times_to_utc');
SET @apply_utc_conversion = ROW_COUNT();

SET @convert_meeting_times = IF(
    @apply_utc_conversion = 1,
    'UPDATE meetings SET start_time = DATE_SUB(start_time, INTERVAL 7 HOUR), end_time = DATE_SUB(end_time, INTERVAL 7 HOUR)',
    'SELECT 1'
);
PREPARE stmt FROM @convert_meeting_times;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

COMMIT;
