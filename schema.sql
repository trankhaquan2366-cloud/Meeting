-- =====================================================
-- Meeting Management System - Database Schema
-- Users / Rooms / Meetings + sample data (admin, VIP room)
-- =====================================================

CREATE DATABASE IF NOT EXISTS meeting_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE meeting_db;

-- ---------------------- USERS ----------------------
CREATE TABLE IF NOT EXISTS users (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
    username        VARCHAR(50)  NOT NULL,
    email           VARCHAR(150) DEFAULT NULL,
    full_name       VARCHAR(150) DEFAULT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'user',
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------- ROOMS ----------------------
CREATE TABLE IF NOT EXISTS rooms (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    location    VARCHAR(255) DEFAULT NULL,
    capacity    INT          NOT NULL DEFAULT 1,
    description TEXT         DEFAULT NULL,
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_rooms_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------- MEETINGS ----------------------
CREATE TABLE IF NOT EXISTS meetings (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    title        VARCHAR(200) NOT NULL,
    description  TEXT         DEFAULT NULL,
    room_id      INT UNSIGNED NOT NULL,
    organizer_id INT UNSIGNED DEFAULT NULL,
    start_time   DATETIME     NOT NULL,
    end_time     DATETIME     NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'scheduled',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_meetings_room_id (room_id),
    KEY idx_meetings_organizer_id (organizer_id),
    KEY idx_meetings_start_time (start_time),
    CONSTRAINT fk_meetings_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_meetings_organizer FOREIGN KEY (organizer_id) REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- SAMPLE DATA
-- =====================================================

-- Admin user, mat khau: Admin@123
-- Hash: pbkdf2_sha256$100000$meeting-admin-salt$46dacbe62a361500b457bc3c89f392826de1631e92e182a92fa27fd55655c166
INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
VALUES ('admin', 'admin@meeting.local', 'Quản trị viên',
        'pbkdf2_sha256$100000$meeting-admin-salt$46dacbe62a361500b457bc3c89f392826de1631e92e182a92fa27fd55655c166',
        'admin', 1);

-- Phong VIP
INSERT INTO rooms (name, location, capacity, description, is_active)
VALUES ('Phòng VIP', 'Tầng 5 - Tòa A', 12, 'Phòng họp VIP với đầy đủ thiết bị trình chiếu và hội nghị truyền hình.', 1);