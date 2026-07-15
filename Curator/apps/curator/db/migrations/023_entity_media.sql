-- 023 — per-entity media cache (ADR-0034 companion): a Wikidata/Commons photo +
-- one-line description for graph entities (people now; extensible). Keyed by the
-- lowercased entity name, matching the /graph node id (LOWER(entities.name)).
-- `blocked` caches a negative result (resolved, no license-clean human photo) so
-- the backfill doesn't re-query Wikidata for the same miss every run.
CREATE TABLE IF NOT EXISTS entity_media (
    name_norm    TEXT PRIMARY KEY,           -- LOWER(entity name) = /graph node id
    label        TEXT,
    type         TEXT,                        -- PERSON / ORG / LOC / …
    wikidata_qid TEXT,
    image_url    TEXT,
    thumb_url    TEXT,
    license      TEXT,
    license_url  TEXT,
    attribution  TEXT,                        -- required for CC BY / BY-SA
    source_url   TEXT,                         -- Commons file page
    description  TEXT,                         -- Wikidata one-liner (es|en)
    blocked      BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
