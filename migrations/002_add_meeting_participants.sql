-- Additive migration: meeting_participants . Does not drop any database or data.
USE meeting_db;

CREATE TABLE IF NOT EXISTS meeting_participants (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    meeting_id INT UNSIGNED NOT NULL,
    user_id    INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_meeting_participant (meeting_id, user_id),
    CONSTRAINT fk_meeting_participants_meeting FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_meeting_participants_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;