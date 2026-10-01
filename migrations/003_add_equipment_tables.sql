-- 1. Bảng danh mục thiết bị trong kho
CREATE TABLE IF NOT EXISTS equipments (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(150) NOT NULL,
    code        VARCHAR(50) DEFAULT NULL,
    category    VARCHAR(50) DEFAULT NULL,
    total_qty   INT NOT NULL DEFAULT 1,
    description TEXT DEFAULT NULL,
    is_active   TINYINT(1) NOT NULL DEFAULT 1,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_equipments_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Bảng đăng ký mượn thiết bị theo cuộc họp
CREATE TABLE IF NOT EXISTS meeting_equipments (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    meeting_id   INT UNSIGNED NOT NULL,
    equipment_id INT UNSIGNED NOT NULL,
    quantity     INT NOT NULL DEFAULT 1,
    note         VARCHAR(255) DEFAULT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_meeting_equipment (meeting_id, equipment_id),
    KEY idx_meeting_equipments_meeting (meeting_id),
    KEY idx_meeting_equipments_equipment (equipment_id),
    CONSTRAINT fk_me_meeting FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_me_equipment FOREIGN KEY (equipment_id) REFERENCES equipments (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Bảng thiết bị cố định đi kèm phòng
CREATE TABLE IF NOT EXISTS room_equipments (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    room_id      INT UNSIGNED NOT NULL,
    equipment_id INT UNSIGNED NOT NULL,
    quantity     INT NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_room_equipment (room_id, equipment_id),
    CONSTRAINT fk_re_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_re_equipment FOREIGN KEY (equipment_id) REFERENCES equipments (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;