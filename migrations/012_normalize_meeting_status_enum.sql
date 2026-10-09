USE meeting_db;

UPDATE meetings
SET status = CASE LOWER(status)
    WHEN 'scheduled' THEN 'CONFIRMED'
    WHEN 'confirmed' THEN 'CONFIRMED'
    WHEN 'completed' THEN 'COMPLETED'
    WHEN 'cancelled' THEN 'CANCELLED'
    WHEN 'canceled' THEN 'CANCELLED'
    ELSE status
END
WHERE LOWER(status) IN (
    'scheduled',
    'confirmed',
    'completed',
    'cancelled',
    'canceled'
);

ALTER TABLE meetings
    ALTER COLUMN status SET DEFAULT 'CONFIRMED';
