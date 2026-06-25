-- 018 — events.last_material_update_at (Curator ADR-0033, P0 event lifecycle).
--
-- The "material clock": bumped ONLY when a genuinely on-story (core-cluster)
-- article attaches, NOT on every tangential re-mention. Distinct from
-- last_updated_at (which bumps on any touch). It drives the lifecycle:
--   • conclude/vault treats a story as "quiet" only when no MATERIAL update,
--   • the feed ranks + windows on it, so a tangential attach can't re-float a
--     9-day-old event to the top as if it happened today.
-- Backfill = last_updated_at (current-behaviour baseline → no regression on the
-- existing corpus; the material gate applies to future attaches).
--
-- Guard (database_service ALTER_GUARDS): skipped when the column already exists.

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS last_material_update_at TIMESTAMPTZ;

UPDATE events
   SET last_material_update_at = COALESCE(last_updated_at, first_seen_at)
 WHERE last_material_update_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_events_material_update
    ON events(last_material_update_at);
