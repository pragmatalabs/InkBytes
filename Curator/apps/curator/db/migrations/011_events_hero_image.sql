-- Migration 011 — events.hero_image (ADR-0016)
--
-- IllustrateSkill writes the best YouTube thumbnail here after synthesis.
-- The /events API uses COALESCE(article_lead_image, e.hero_image) so the
-- outlet's og:image is preferred when present; the thumbnail is the fallback
-- when lead_image is NULL (hotlink-blocked, author photo, or outlet has none).

ALTER TABLE events ADD COLUMN IF NOT EXISTS hero_image TEXT;
