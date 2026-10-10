-- Track invitee RSVP state for the dashboard and meeting organizers.
SET @has_response_status = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meeting_participants'
      AND COLUMN_NAME = 'response_status'
);
SET @add_response_status = IF(
    @has_response_status = 0,
    'ALTER TABLE meeting_participants ADD COLUMN response_status VARCHAR(20) NOT NULL DEFAULT ''pending''',
    'SELECT 1'
);
PREPARE stmt FROM @add_response_status;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
