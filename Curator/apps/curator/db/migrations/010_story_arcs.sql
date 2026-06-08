-- Migration 010: story_arcs — concluded event lifecycle (ADR-0013)
--
-- When an event has been quiet for ≥ conclude_after_days, the ConcludeStories
-- job marks it 'concluded' and writes a story_arcs row.  The row is an ordered
-- pointer list (arc_article_ids) into articles.embedding — zero duplication;
-- replay with:
--   SELECT id, scraped_at, title, embedding
--     FROM articles
--    WHERE id = ANY($1::TEXT[])
--    ORDER BY scraped_at;
--
-- Future Sprint 2: add centroid_start/centroid_end vector(1024) columns for ANN
-- similarity search across concluded story arcs (ADR-0013 §Future work).

-- Extend the status constraint to allow 'concluded'.
ALTER TABLE events DROP CONSTRAINT IF EXISTS events_status_check;
ALTER TABLE events ADD CONSTRAINT events_status_check
    CHECK (status IN ('draft', 'published', 'dropped', 'concluded'));

CREATE TABLE IF NOT EXISTS story_arcs (
    event_id        TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    topic           TEXT,
    language        TEXT NOT NULL,
    first_seen_at   TIMESTAMPTZ NOT NULL,   -- mirrors events.first_seen_at
    concluded_at    TIMESTAMPTZ NOT NULL,   -- events.last_updated_at at archive time
    article_count   INT NOT NULL,
    source_count    INT NOT NULL,
    arc_article_ids TEXT[] NOT NULL,        -- article.id ordered by scraped_at ASC
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_story_arcs_topic     ON story_arcs (topic);
CREATE INDEX IF NOT EXISTS idx_story_arcs_concluded ON story_arcs (concluded_at DESC);
CREATE INDEX IF NOT EXISTS idx_story_arcs_language  ON story_arcs (language);
