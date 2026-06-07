-- Migration 008: per-article media fields (Phase 1 passive extraction)
--
-- lead_image: og:image / top_image URL extracted by Messor from article HTML
--             (zero extra HTTP requests — newspaper3k provides this for free)
-- video_url:  first YouTube embed URL found in <iframe> tags (also Messor)
--
-- Both are nullable; most articles will have lead_image, fewer will have
-- video_url. The /events API rolls up lead_image per event (first non-null).
-- Phase 2 (IllustrateSkill) will enrich events that have no image by
-- searching YouTube + Bing Images.
--
-- The pages.media_rail column (Phase 2) is NOT added here — it belongs in
-- a separate migration when IllustrateSkill is wired in.

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS lead_image  TEXT,
    ADD COLUMN IF NOT EXISTS video_url   TEXT;
