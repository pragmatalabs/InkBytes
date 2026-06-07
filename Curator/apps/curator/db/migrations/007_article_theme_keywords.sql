-- 007 — article enrichment fields: theme, raw keywords, Messor categories
--
-- theme           TEXT   — LLM-derived broad bucket (ENRICH Skill 1)
-- keywords_raw    TEXT[] — raw <meta> keywords from Messor (harvester-side)
-- meta_categories TEXT[] — Messor HTML/URL-extracted category tags
-- article_category TEXT  — Messor's primary category pick
--
-- Guard: skipped when articles.theme already exists (idempotent).

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS theme            TEXT,
    ADD COLUMN IF NOT EXISTS keywords_raw     TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS meta_categories  TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS article_category TEXT;

CREATE INDEX IF NOT EXISTS idx_articles_theme    ON articles(theme);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(article_category);
