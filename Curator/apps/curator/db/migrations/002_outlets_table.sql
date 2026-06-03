-- Curator migration 002 — outlets catalogue
-- Stores the canonical outlet config so the API can serve it without
-- reading from the Messor filesystem. Seeded from outlets.json on startup.

CREATE TABLE IF NOT EXISTS outlets (
    id              TEXT PRIMARY KEY,          -- slug, e.g. "bbc"
    name            TEXT NOT NULL,             -- scraper key (matches Messor outlet name)
    display_name    TEXT NOT NULL,
    url             TEXT NOT NULL,
    region          TEXT NOT NULL DEFAULT 'global',  -- global | latam-dr | latam-mx | latam-co | latam-ar
    language        TEXT NOT NULL DEFAULT 'en',
    vertical        TEXT NOT NULL DEFAULT 'general', -- general | business | tech | politics
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    priority        INT NOT NULL DEFAULT 2,          -- 1=high 2=medium 3=low
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outlets_region   ON outlets(region);
CREATE INDEX IF NOT EXISTS idx_outlets_language ON outlets(language);
CREATE INDEX IF NOT EXISTS idx_outlets_active   ON outlets(active);

DROP TRIGGER IF EXISTS trg_outlets_updated_at ON outlets;
CREATE TRIGGER trg_outlets_updated_at
    BEFORE UPDATE ON outlets
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
