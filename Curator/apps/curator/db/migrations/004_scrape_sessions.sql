-- Curator migration 004 — scrape sessions (B12.1, ADR-0006)
--
-- Durable, run-level record of each Messor harvest session, reproducing the
-- run-level view Messor's `GET /api/scrapesessions` returns (one row per run
-- across all outlets, with per-outlet counts in `outlets`).
--
-- ADR-0006 (refined): Messor stays Postgres-free. It EMITS a
-- `scrape.session.completed` event on its `messor` topic exchange; Curator
-- (the DB owner) consumes it and UPSERTs this table. Messor keeps owning the
-- dedup/result computation; Curator only persists.
--
-- Owner: Curator (this migration is the source of DDL truth — ADR-0003).
-- The Backoffice reads this table cross-schema, read-only (B12.2/B12.3).

CREATE TABLE IF NOT EXISTS scrape_sessions (
    session_id          TEXT PRIMARY KEY,                 -- stable run id, e.g. "session-<unix_ts>"
    started_at          TIMESTAMPTZ,                      -- run start
    ended_at            TIMESTAMPTZ,                      -- run end
    total_articles      INT NOT NULL DEFAULT 0,
    successful_articles INT NOT NULL DEFAULT 0,
    failed_articles     INT NOT NULL DEFAULT 0,
    duplicates_total    INT NOT NULL DEFAULT 0,
    success_rate        NUMERIC(5,4) NOT NULL DEFAULT 0,  -- 0.0000 .. 1.0000
    duration_seconds    NUMERIC,                          -- run wall-clock seconds (nullable)
    outlets             JSONB NOT NULL DEFAULT '[]'::jsonb, -- [{name, slug, articles, successful, failed, duplicates}]
    total_outlets       INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scrape_sessions_started_at ON scrape_sessions(started_at DESC);

-- set_updated_at() is defined in 001_initial_schema.sql.
DROP TRIGGER IF EXISTS trg_scrape_sessions_updated_at ON scrape_sessions;
CREATE TRIGGER trg_scrape_sessions_updated_at
    BEFORE UPDATE ON scrape_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
