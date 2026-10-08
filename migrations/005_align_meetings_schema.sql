-- ============================================================
-- Migration 005: Align meetings table với model thực tế
-- Safe: chỉ modify room_id nullable + update default meeting_type
-- Không DROP cột nào, không mất dữ liệu
-- ============================================================
USE meeting_db;

-- 1. Chuẩn hóa meeting_type: đổi default về lowercase 'offline'
--    Các row cũ đang có giá trị 'OFFLINE' — cập nhật về lowercase để nhất quán
UPDATE meetings SET meeting_type = 'offline' WHERE meeting_type = 'OFFLINE';
UPDATE meetings SET meeting_type = 'online'  WHERE meeting_type = 'ONLINE';

ALTER TABLE meetings
    MODIFY COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT 'offline';

-- 2. Nullable room_id: drop FK cũ, alter column, re-add FK với SET NULL
ALTER TABLE meetings DROP FOREIGN KEY meetings_ibfk_1;
ALTER TABLE meetings MODIFY COLUMN room_id INT NULL;
ALTER TABLE meetings
    ADD CONSTRAINT fk_meetings_room
    FOREIGN KEY (room_id) REFERENCES rooms(id)
    ON DELETE SET NULL ON UPDATE CASCADE;

-- Verify: DESCRIBE meetings;
