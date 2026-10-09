-- Add meeting mode/link fields and allow room deletion without deleting meetings.
-- Safe to re-run against databases where some or all changes already exist.

USE meeting_db;

-- Add meeting_type when it is not already present.
SET @has_meeting_type = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'meeting_type'
);

SET @add_meeting_type = IF(
    @has_meeting_type = 0,
    'ALTER TABLE meetings ADD COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT ''offline''',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_type;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add meeting_link when it is not already present.
SET @has_meeting_link = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'meeting_link'
);

SET @add_meeting_link = IF(
    @has_meeting_link = 0,
    'ALTER TABLE meetings ADD COLUMN meeting_link VARCHAR(255) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_link;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Replace the current room foreign key, regardless of its constraint name.
SET @room_fk = (
    SELECT CONSTRAINT_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'room_id'
      AND REFERENCED_TABLE_NAME = 'rooms'
    LIMIT 1
);

SET @drop_room_fk = IF(
    @room_fk IS NULL,
    'SELECT 1',
    CONCAT('ALTER TABLE meetings DROP FOREIGN KEY `', @room_fk, '`')
);
PREPARE stmt FROM @drop_room_fk;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE meetings MODIFY COLUMN room_id INT UNSIGNED NULL;
ALTER TABLE meetings
    ADD CONSTRAINT fk_meetings_room
    FOREIGN KEY (room_id) REFERENCES rooms (id)
    ON DELETE SET NULL ON UPDATE CASCADE;