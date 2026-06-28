-- 021 — events.cover_image (Curator ADR-0034 Tier 2, license-clean generic cover).
--
-- A commercially-licensed generic image (Openverse CC0/PDM; Wikimedia entity path
-- later) keyed to the event's top LOC/ORG entity or theme. Provenance JSONB:
--   { "url": ..., "thumb": ..., "license": "cc0", "source_url": ..., "provider": "openverse", "query": ... }
-- NULL → the Reader falls back to the owned procedural cover (Tier 1). Populated
-- by scripts/backfill_covers.py + the per-event fetch; never the source og:image.
--
-- Guard (database_service ALTER_GUARDS): skipped once the column exists.

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS cover_image JSONB;
