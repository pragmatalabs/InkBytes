-- 002 — editorial audio (self-hosted TTS, ADR-0008 companion).
--
-- Each editorial row (theme × language × day) gets a spoken-word MP3, synthesized
-- ONCE by Piper in the daily batch and stored in DigitalOcean Spaces (public-read).
-- We persist only the public URL + provenance here — never the audio bytes. A NULL
-- audio_url means "not synthesized yet" (the `--synthesize-missing` backfill target).

ALTER TABLE editorials
    ADD COLUMN IF NOT EXISTS audio_url          TEXT,        -- public MP3 URL (NULL = not yet)
    ADD COLUMN IF NOT EXISTS audio_voice        TEXT,        -- provenance, e.g. 'piper/es_MX-ald-medium'
    ADD COLUMN IF NOT EXISTS audio_generated_at TIMESTAMPTZ;
