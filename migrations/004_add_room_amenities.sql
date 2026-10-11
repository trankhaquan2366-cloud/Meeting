ALTER TABLE rooms
    ADD COLUMN amenities TEXT DEFAULT NULL AFTER description;