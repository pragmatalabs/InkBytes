-- Curator migration 016 — scrape session lane (pulse vs cycle)
--
-- The breaking-news pulse lane (Messor ADR-0017) emits ~120 sessions/hour
-- (10 outlets × 5-min ticks), each a small RSS fetch that's mostly duplicates
-- — which floods the Backoffice Scrape Results view and makes intake look low
-- even though daily new-article totals are at an all-time high. `lane` lets the
-- Backoffice tag + filter pulse ticks apart from the full 2-hour cycles.
--
-- Default 'cycle' so existing rows + any session emitted without the field
-- read as a normal cycle run.

ALTER TABLE scrape_sessions ADD COLUMN IF NOT EXISTS lane TEXT NOT NULL DEFAULT 'cycle';

CREATE INDEX IF NOT EXISTS idx_scrape_sessions_lane ON scrape_sessions(lane);
