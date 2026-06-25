-- 019 — events.centroid (Curator ADR-0031, clustering precision).
--
-- Centroid-linkage replaces single-linkage: an article attaches to the nearest
-- event *centroid* (not its nearest individual member), which stops a cluster
-- from chaining across a whole dense topic region (the World-Cup mega-buckets).
-- centroid = mean of the event's member embeddings (pgvector avg()); cosine
-- distance (<=>) is magnitude-invariant so the raw mean works as the direction.
--
-- Populated only under precision_mode (the clustering rewrite); a one-time
-- backfill (scripts/backfill_event_centroids.py) seeds existing events before
-- the flag is flipped. NULL centroid → the precision candidate query skips the
-- event (it falls back to seeding), which is why the backfill must precede flip.
--
-- Guard (database_service ALTER_GUARDS): skipped when the column already exists.

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS centroid vector(1024);
