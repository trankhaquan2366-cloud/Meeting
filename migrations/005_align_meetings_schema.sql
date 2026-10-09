-- ============================================================
-- Migration 005: Align meetings table với model thực tế
-- Safe to re-run: add missing columns and align room_id without dropping data.
-- ============================================================
USE meeting_db;

-- Add meeting_type when this migration is applied to an older schema.
SET @has_meeting_type = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'meeting_type'
);
SET @add_meeting_type = IF(
    @has_meeting_type = 0,
    'ALTER TABLE meetings ADD COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT ''offline'' AFTER description',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_type;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_online_link = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'online_link'
);
SET @add_online_link = IF(
    @has_online_link = 0,
    'ALTER TABLE meetings ADD COLUMN online_link VARCHAR(500) NULL AFTER meeting_type',
    'SELECT 1'
);
PREPARE stmt FROM @add_online_link;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Normalize existing values and the default.
UPDATE meetings SET meeting_type = 'offline' WHERE meeting_type = 'OFFLINE';
UPDATE meetings SET meeting_type = 'online'  WHERE meeting_type = 'ONLINE';

ALTER TABLE meetings
    MODIFY COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT 'offline';

-- Replace the existing room foreign key if needed; preserve it on re-runs.
SET @room_fk_name = (
    SELECT CONSTRAINT_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'room_id'
      AND REFERENCED_TABLE_NAME = 'rooms'
    LIMIT 1
);
SET @drop_room_fk = IF(
    @room_fk_name IS NULL OR @room_fk_name = 'fk_meetings_room',
    'SELECT 1',
    CONCAT('ALTER TABLE meetings DROP FOREIGN KEY `', REPLACE(@room_fk_name, '`', '``'), '`')
);
PREPARE stmt FROM @drop_room_fk;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE meetings MODIFY COLUMN room_id INT NULL;

SET @has_room_fk = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'room_id'
      AND REFERENCED_TABLE_NAME = 'rooms'
      AND CONSTRAINT_NAME = 'fk_meetings_room'
);
SET @add_room_fk = IF(
    @has_room_fk = 0,
    'ALTER TABLE meetings ADD CONSTRAINT fk_meetings_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL ON UPDATE CASCADE',
    'SELECT 1'
);
PREPARE stmt FROM @add_room_fk;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verify: DESCRIBE meetings;
