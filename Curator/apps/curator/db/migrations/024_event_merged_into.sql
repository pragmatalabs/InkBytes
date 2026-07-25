-- 024 — near-duplicate event merge (ADR-0040).
--
-- The ingest entity-specificity gate (ADR-0031) over-splits some stories: their
-- article embeddings are within the merge distance, but the shared entities are
-- too common (e.g. Spain/Madrid) to satisfy the gate, so each seeds its own event
-- — and nothing merges them afterward. The merge pass consolidates published
-- events whose CENTROIDS are near-identical into one survivor; the losers get
-- status='dropped' + `merged_into` = the survivor's id so their /event/{id} URLs
-- can 302-redirect instead of 404 (event id == page id, 1:1).

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS merged_into TEXT,        -- survivor event id (NULL = not merged)
    ADD COLUMN IF NOT EXISTS merged_at   TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_events_merged_into
    ON events (merged_into) WHERE merged_into IS NOT NULL;
