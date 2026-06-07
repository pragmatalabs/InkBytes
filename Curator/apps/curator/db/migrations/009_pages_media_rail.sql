-- Migration 009: pages.media_rail — structured media results from IllustrateSkill
--
-- Each row is a JSON object with the shape:
--   { url, thumb_url, type ("image"|"video"), title,
--     source_domain, published_at (ISO-8601|null), width, height, score }
--
-- Populated by skills/illustrate.py (Phase 2 Scrapling agent) after synthesis.
-- Defaults to an empty array so the Reader can safely iterate without null-checks.

ALTER TABLE pages
    ADD COLUMN IF NOT EXISTS media_rail JSONB NOT NULL DEFAULT '[]'::jsonb;
