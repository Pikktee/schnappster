-- Veraltete user_settings-Spalten (nicht mehr im Modell); NOT NULL ohne INSERT-Wert bricht API.
-- Optional manuell in Supabase ausfuehren; die App entfernt dieselben Spalten bei init_db (PG).

ALTER TABLE user_settings DROP COLUMN IF EXISTS notify_email;
ALTER TABLE user_settings DROP COLUMN IF EXISTS notify_mode;
