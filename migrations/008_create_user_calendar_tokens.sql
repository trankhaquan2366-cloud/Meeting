USE meeting_db;

CREATE TABLE IF NOT EXISTS user_calendar_tokens (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    provider VARCHAR(20) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NULL,
    expires_at DATETIME NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_calendar_tokens_user_provider (user_id, provider),
    KEY ix_user_calendar_tokens_user_id (user_id),
    CONSTRAINT ck_user_calendar_tokens_provider
        CHECK (provider IN ('google', 'outlook')),
    CONSTRAINT fk_user_calendar_tokens_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;
