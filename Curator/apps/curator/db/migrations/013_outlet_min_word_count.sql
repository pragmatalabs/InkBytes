-- Migration 013: per-outlet minimum word count threshold (P4, 2026-06-09)
--
-- NULL means "use the global config default" (currently 40 words via
-- config.scraper.min_word_count).  Set to a lower value for outlets that
-- routinely publish short breaking-news pieces (BBC briefs, Reuters wire
-- stubs, LATAM dailies).
ALTER TABLE outlets ADD COLUMN IF NOT EXISTS min_word_count INT;
