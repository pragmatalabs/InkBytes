-- 025_entities_name_lower_index.sql
-- Functional index on LOWER(entities.name) — powers GET /entities/{name}, the
-- in-place event-page entity detail (Curator ADR-0042).
--
-- The entity graph keys on LOWER(name). Without this index every
-- `LOWER(ent.name) = $1` lookup seq-scans the ~3M-row / 663 MB entities table,
-- so the entity-detail query ran 2.9 s (a 14-event entity) to 37 s (Trump).
-- With the index the planner starts from the entity and normal/mid entities
-- answer in <500 ms; the handful of mega-entities are cut off by the query
-- timeout and fall back to the light sheet.
--
-- On prod this index was created CONCURRENTLY out-of-band (no table lock), so
-- the guard in database_service skips this file there. On fresh/dev DBs the
-- table is small, so this plain CREATE INDEX is effectively instant.
CREATE INDEX IF NOT EXISTS idx_entities_name_lower ON entities (LOWER(name));

-- The planner only picks the functional index once expression stats exist for
-- it; without this ANALYZE it keeps the old seq-scan plan.
ANALYZE entities;
