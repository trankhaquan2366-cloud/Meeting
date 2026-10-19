SET @has_room_status = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'rooms'
      AND COLUMN_NAME = 'room_status'
);
SET @add_room_status = IF(
    @has_room_status = 0,
    'ALTER TABLE rooms ADD COLUMN room_status VARCHAR(20) NOT NULL DEFAULT ''active''',
    'SELECT 1'
);
PREPARE stmt FROM @add_room_status;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @normalize_room_status = IF(
    @has_room_status = 0,
    'UPDATE rooms SET room_status = ''maintenance'' WHERE is_active = 0',
    'SELECT 1'
);
PREPARE stmt FROM @normalize_room_status;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_room_image = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'rooms'
      AND COLUMN_NAME = 'room_image'
);
SET @add_room_image = IF(
    @has_room_image = 0,
    'ALTER TABLE rooms ADD COLUMN room_image VARCHAR(2048) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_room_image;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_layout_type = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'rooms'
      AND COLUMN_NAME = 'layout_type'
);
SET @add_layout_type = IF(
    @has_layout_type = 0,
    'ALTER TABLE rooms ADD COLUMN layout_type VARCHAR(30) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_layout_type;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
