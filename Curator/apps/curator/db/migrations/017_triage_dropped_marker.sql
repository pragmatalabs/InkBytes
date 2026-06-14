-- Curator migration 017 — terminal marker for triage-dropped articles
-- (ADR-0030 follow-up: "Known limitation").
--
-- The pre-enrich triage gate drops junk (horoscopes/lottery/deals/dead pages)
-- by acking the message and returning WITHOUT writing enrichment. Those rows
-- keep enriched_at = NULL forever, so:
--   1. the /status "articles pending enrichment" counter drifts upward
--      (it's total - enriched), miscounting dropped junk as a backlog;
--   2. --reenrich-missing (topic IS NULL) would re-enrich them and resurrect
--      the junk it just paid a model to reject.
--
-- triage_dropped_at gives dropped articles a terminal marker so both the
-- counter and the reenrich query can exclude them.

ALTER TABLE articles ADD COLUMN IF NOT EXISTS triage_dropped_at  TIMESTAMPTZ;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS triage_drop_reason TEXT;

-- Partial index: the "is this article a triage drop?" lookups all filter on
-- NOT NULL, so only index the dropped rows (small, ~a day's worth).
CREATE INDEX IF NOT EXISTS idx_articles_triage_dropped
    ON articles(triage_dropped_at) WHERE triage_dropped_at IS NOT NULL;
