USE meeting_db;

CREATE TABLE IF NOT EXISTS user_calendar_events (
    id INT NOT NULL AUTO_INCREMENT,
    meeting_id INT NOT NULL,
    user_id INT NOT NULL,
    provider VARCHAR(20) NOT NULL,
    external_event_id VARCHAR(512) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_calendar_events_meeting_user_provider (
        meeting_id,
        user_id,
        provider
    ),
    KEY ix_user_calendar_events_meeting_id (meeting_id),
    KEY ix_user_calendar_events_user_id (user_id),
    CONSTRAINT ck_user_calendar_events_provider
        CHECK (provider IN ('google', 'outlook')),
    CONSTRAINT fk_user_calendar_events_meeting
        FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_calendar_events_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;
