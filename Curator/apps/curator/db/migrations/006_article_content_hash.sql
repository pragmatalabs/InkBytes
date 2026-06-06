-- 006_article_content_hash.sql
--
-- Track content changes on re-scraped articles.
--
-- The articles.id is a UUID v3 from the canonical URL, so a re-scrape of the
-- same URL reuses the same PK.  Without this column, upsert_article_raw uses
-- ON CONFLICT (id) DO NOTHING — silently discarding any updated body_text or
-- title, so events built on that article are synthesized from stale content.
--
-- With content_hash, upsert_article_raw can detect that the body changed and
-- update in-place, resetting enrichment fields (topic/embedding/etc.) so the
-- normal ENRICH→CLUSTER→SYNTHESIZE pipeline picks up the fresh content.
--
-- Existing rows get NULL; they will be populated the next time Messor
-- re-scrapes and publishes each article.  NULL IS DISTINCT FROM any non-NULL
-- hash → the first re-scrape will update and re-enrich, which is correct.
--
-- Guarded in _ensure_schema by ALTER_GUARD:
--   TRUE when the column already exists → skip on subsequent boots.

ALTER TABLE articles ADD COLUMN IF NOT EXISTS content_hash TEXT;

COMMENT ON COLUMN articles.content_hash IS
  'MD5 of (title || body_text) at scrape time. Changed on re-scrape → '
  'triggers in-place update + enrichment reset so stale articles are refreshed.';
