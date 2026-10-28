USE meeting_db;

SET @has_notification_meeting_id = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND COLUMN_NAME = 'meeting_id'
);
SET @add_notification_meeting_id = IF(
    @has_notification_meeting_id = 0,
    'ALTER TABLE notifications ADD COLUMN meeting_id INT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_notification_meeting_id;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_notification_category = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND COLUMN_NAME = 'category'
);
SET @add_notification_category = IF(
    @has_notification_category = 0,
    'ALTER TABLE notifications ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT ''system''',
    'SELECT 1'
);
PREPARE stmt FROM @add_notification_category;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_notification_group_key = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND COLUMN_NAME = 'group_key'
);
SET @add_notification_group_key = IF(
    @has_notification_group_key = 0,
    'ALTER TABLE notifications ADD COLUMN group_key VARCHAR(80) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_notification_group_key;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_notification_meeting_id_index = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND INDEX_NAME = 'ix_notifications_meeting_id'
);
SET @add_notification_meeting_id_index = IF(
    @has_notification_meeting_id_index = 0,
    'CREATE INDEX ix_notifications_meeting_id ON notifications (meeting_id)',
    'SELECT 1'
);
PREPARE stmt FROM @add_notification_meeting_id_index;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_notification_group_key_index = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND INDEX_NAME = 'idx_notifications_group_key'
);
SET @add_notification_group_key_index = IF(
    @has_notification_group_key_index = 0,
    'CREATE INDEX idx_notifications_group_key ON notifications (group_key)',
    'SELECT 1'
);
PREPARE stmt FROM @add_notification_group_key_index;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_notification_meeting_fk = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND CONSTRAINT_NAME = 'fk_notifications_meeting_id'
);
SET @add_notification_meeting_fk = IF(
    @has_notification_meeting_fk = 0,
    'ALTER TABLE notifications ADD CONSTRAINT fk_notifications_meeting_id FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE SET NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_notification_meeting_fk;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE notifications
SET category = 'reminder'
WHERE title LIKE '%[Nhắc nhở]%' OR title LIKE '%Nhắc nhở%';

UPDATE notifications
SET category = 'response'
WHERE title LIKE '%đồng ý%' OR title LIKE '%từ chối%' OR title LIKE '%xác nhận%';

UPDATE notifications
SET category = 'change'
WHERE title LIKE '%Lời mời%' OR title LIKE '%bị hủy%' OR title LIKE '%thay đổi%';
