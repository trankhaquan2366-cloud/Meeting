USE meeting_db;

SET @has_external_series_event_id = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_calendar_events'
      AND COLUMN_NAME = 'external_series_event_id'
);
SET @add_external_series_event_id = IF(
    @has_external_series_event_id = 0,
    'ALTER TABLE user_calendar_events ADD COLUMN external_series_event_id VARCHAR(512) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_external_series_event_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_external_occurrence_id = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_calendar_events'
      AND COLUMN_NAME = 'external_occurrence_id'
);
SET @add_external_occurrence_id = IF(
    @has_external_occurrence_id = 0,
    'ALTER TABLE user_calendar_events ADD COLUMN external_occurrence_id VARCHAR(512) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_external_occurrence_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE user_calendar_events
SET external_series_event_id = external_event_id
WHERE external_series_event_id IS NULL
  AND meeting_id IN (
      SELECT id
      FROM meetings
      WHERE recurring_series_id IS NOT NULL
  );
