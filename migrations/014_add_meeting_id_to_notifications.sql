USE meeting_db;

ALTER TABLE notifications
    ADD COLUMN meeting_id INT NULL AFTER user_id,
    ADD INDEX ix_notifications_meeting_id (meeting_id),
    ADD CONSTRAINT fk_notifications_meeting
        FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE SET NULL;
