USE meeting_db;

CREATE TABLE IF NOT EXISTS email_deliveries (
    id INT NOT NULL AUTO_INCREMENT,
    meeting_id INT NOT NULL,
    user_id INT NOT NULL,
    reminder_type VARCHAR(20) NOT NULL,
    recipient VARCHAR(320) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    attempts INT NOT NULL DEFAULT 0,
    next_attempt_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_error TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_email_deliveries_reminder (
        meeting_id,
        user_id,
        reminder_type
    ),
    KEY ix_email_deliveries_meeting_id (meeting_id),
    KEY ix_email_deliveries_user_id (user_id),
    KEY ix_email_deliveries_due (status, next_attempt_at),
    CONSTRAINT fk_email_deliveries_meeting
        FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE,
    CONSTRAINT fk_email_deliveries_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;
