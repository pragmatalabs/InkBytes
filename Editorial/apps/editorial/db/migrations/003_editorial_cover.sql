-- 003 — editorial covers (stylized AI hero images, ADR-0012).
--
-- Each Outlook column gets a stylized, brand-consistent cover generated ONCE per
-- (theme, edition_date) by gpt-image-1-mini and stored in DigitalOcean Spaces
-- (public-read). Covers are language-neutral, so BOTH the es and en rows of a
-- theme/day share one image. A NULL cover_url = "not generated yet" (the
-- `--cover-missing` backfill target). cover_prompt is kept for provenance/audit
-- (these are conceptual illustrations for OPINION columns — never event photos).

ALTER TABLE editorials
    ADD COLUMN IF NOT EXISTS cover_url          TEXT,   -- public WebP URL (NULL = not yet)
    ADD COLUMN IF NOT EXISTS cover_prompt       TEXT,   -- the image prompt used (audit)
    ADD COLUMN IF NOT EXISTS cover_generated_at TIMESTAMPTZ;

-- Cheap lookups for the monthly cost cap (count distinct theme/day this month)
-- and the backfill (rows still missing a cover).
CREATE INDEX IF NOT EXISTS idx_editorials_cover_generated_at
    ON editorials (cover_generated_at);
