-- Curator — initial schema (v0)
-- Run against the Postgres instance that backs InkBytes.
-- Requires the `vector` extension (provided by pgvector/pgvector:pg16 image).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ───────────────────────────────────────────── events ──────────────
-- An "event" is a cluster of articles about the same newsworthy thing.
CREATE TABLE IF NOT EXISTS events (
    id              TEXT PRIMARY KEY,                  -- ULID
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_seen_at   TIMESTAMPTZ NOT NULL,
    last_updated_at TIMESTAMPTZ NOT NULL,
    source_count    INT NOT NULL DEFAULT 1,
    article_count   INT NOT NULL DEFAULT 1,
    language        TEXT NOT NULL,
    topic           TEXT,
    status          TEXT NOT NULL DEFAULT 'draft'
                       CHECK (status IN ('draft','published','dropped'))
);

CREATE INDEX IF NOT EXISTS idx_events_last_updated ON events(last_updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_status        ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_topic         ON events(topic);

-- ────────────────────────────────────────────── articles ───────────
-- One row per Messor-harvested article. Curator enriches in place.
CREATE TABLE IF NOT EXISTS articles (
    -- Messor-provided fields (from inkbytes.article.v1 contract)
    id                 TEXT PRIMARY KEY,            -- Messor's canonical id
    outlet_id          TEXT NOT NULL,
    outlet_name        TEXT NOT NULL,
    url                TEXT NOT NULL,
    canonical_url      TEXT,
    title              TEXT NOT NULL,
    body_text          TEXT NOT NULL,
    language           TEXT NOT NULL,
    published_at       TIMESTAMPTZ,
    scraped_at         TIMESTAMPTZ NOT NULL,
    word_count         INT NOT NULL,
    spaces_key         TEXT,          -- NULL when article flows inline; populated after S3 archive
    raw_meta           JSONB,

    -- Skill 1 (ENRICH) fields
    enriched_at        TIMESTAMPTZ,
    topic              TEXT,
    sentiment          TEXT,
    factuality         REAL CHECK (factuality BETWEEN 0 AND 1),
    summary_50w        TEXT,
    keywords_canonical TEXT[],
    embedding          vector(1536),

    -- Skill 2 (CLUSTER) fields
    event_id           TEXT REFERENCES events(id) ON DELETE SET NULL,
    cluster_distance   REAL,

    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_scraped_at ON articles(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_event      ON articles(event_id);
CREATE INDEX IF NOT EXISTS idx_articles_outlet     ON articles(outlet_id);
CREATE INDEX IF NOT EXISTS idx_articles_topic      ON articles(topic);
CREATE INDEX IF NOT EXISTS idx_articles_lang       ON articles(language);
-- Approximate-NN cosine index (IVFFlat).
-- Tune `lists` (~rows/1000) once we have real volume; 100 is fine for v0.
CREATE INDEX IF NOT EXISTS idx_articles_embedding
    ON articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ────────────────────────────────────────────── entities ───────────
-- Extracted per article. We dedupe at the cluster level via SQL, not by
-- maintaining a canonical entities table — simpler for v0.
CREATE TABLE IF NOT EXISTS entities (
    id          BIGSERIAL PRIMARY KEY,
    article_id  TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,                       -- PERSON|ORG|LOC|EVENT|OTHER
    salience    REAL DEFAULT 0.5 CHECK (salience BETWEEN 0 AND 1),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_article ON entities(article_id);
CREATE INDEX IF NOT EXISTS idx_entities_name    ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_type    ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_name_trgm
    ON entities USING gin (name gin_trgm_ops);

-- ────────────────────────────────────────────── pages ──────────────
-- The reader-facing one-pager. One row per published event.
CREATE TABLE IF NOT EXISTS pages (
    id              TEXT PRIMARY KEY,                 -- same as event_id
    event_id        TEXT NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
    headline        TEXT NOT NULL,
    synthesis_md    TEXT NOT NULL,                    -- markdown, 200-250 words
    evidence_rail   JSONB NOT NULL,                   -- [{source, url, quote}]
    entities        JSONB NOT NULL,                   -- [{name, type}]
    freshness_at    TIMESTAMPTZ NOT NULL,
    published_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cost_cents      INT,                              -- ~LLM cost for this page
    schema_version  TEXT NOT NULL DEFAULT 'inkbytes.page.v1'
);

CREATE INDEX IF NOT EXISTS idx_pages_published_at ON pages(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_pages_freshness    ON pages(freshness_at DESC);

-- ────────────────────────────────────────────── trigger ────────────
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_articles_updated_at ON articles;
CREATE TRIGGER trg_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
