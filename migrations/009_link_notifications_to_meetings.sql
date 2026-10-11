-- Add an optional meeting reference so invitation notifications can expose
-- RSVP actions without guessing from their human-readable message.
SET @has_meeting_id = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND COLUMN_NAME = 'meeting_id'
);
SET @add_meeting_id = IF(
    @has_meeting_id = 0,
    'ALTER TABLE notifications ADD COLUMN meeting_id INT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_meeting_id_index = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND INDEX_NAME = 'ix_notifications_meeting_id'
);
SET @add_meeting_id_index = IF(
    @has_meeting_id_index = 0,
    'CREATE INDEX ix_notifications_meeting_id ON notifications (meeting_id)',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_id_index;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_meeting_id_foreign_key = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND CONSTRAINT_NAME = 'fk_notifications_meeting_id'
);
SET @add_meeting_id_foreign_key = IF(
    @has_meeting_id_foreign_key = 0,
    'ALTER TABLE notifications ADD CONSTRAINT fk_notifications_meeting_id FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE SET NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_id_foreign_key;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
