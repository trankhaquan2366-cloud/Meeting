-- Additive migration for meeting equipment. Safe to re-run and does not delete data.
USE meeting_db;

CREATE TABLE IF NOT EXISTS equipments (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    description TEXT DEFAULT NULL,
    is_active   TINYINT(1) NOT NULL DEFAULT 1,
    status      VARCHAR(30) NOT NULL DEFAULT 'available',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_equipments_status (status),
    KEY idx_equipments_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS meeting_equipments (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    meeting_id   INT UNSIGNED NOT NULL,
    equipment_id INT UNSIGNED NOT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_meeting_equipment (meeting_id, equipment_id),
    KEY idx_meeting_equipments_equipment_id (equipment_id),
    CONSTRAINT fk_meeting_equipments_meeting
        FOREIGN KEY (meeting_id) REFERENCES meetings (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_meeting_equipments_equipment
        FOREIGN KEY (equipment_id) REFERENCES equipments (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Add missing columns when an older equipments table already exists.
SET @has_equipments_is_active = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipments' AND COLUMN_NAME = 'is_active'
);
SET @add_equipments_is_active = IF(
    @has_equipments_is_active = 0,
    'ALTER TABLE equipments ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1',
    'SELECT 1'
);
PREPARE stmt FROM @add_equipments_is_active;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_equipments_status = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'equipments' AND COLUMN_NAME = 'status'
);
SET @add_equipments_status = IF(
    @has_equipments_status = 0,
    'ALTER TABLE equipments ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT ''available''',
    'SELECT 1'
);
PREPARE stmt FROM @add_equipments_status;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
