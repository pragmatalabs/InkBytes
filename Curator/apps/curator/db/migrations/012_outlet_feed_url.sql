-- Migration 012 — add feed_url to outlets
-- RSS/Atom feed URL for outlets that support it.
-- NULL = no feed configured; scraper falls back to newspaper3k homepage crawl.
-- Non-null = scraper uses feed-first discovery (ADR-0015 follow-up).

ALTER TABLE outlets
    ADD COLUMN IF NOT EXISTS feed_url TEXT;
