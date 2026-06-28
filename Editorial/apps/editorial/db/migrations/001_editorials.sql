-- 001 — editorials (ADR-0008). Daily per-theme editorial columns.
--
-- The Editorial service is SEPARATE from Curator: it consumes published event
-- pages and produces one opinionated ~450-600 word column per theme/day, citing
-- events as [n] links. This table is the product AND the training set for the
-- Phase-2 distilled editorial SLM (cost-at-scale, local) — so each row carries
-- its full generation provenance: input_context (the events fed, numbered) and
-- the rendered prompt → body_md is the supervised target.

CREATE TABLE IF NOT EXISTS editorials (
    id            TEXT PRIMARY KEY,
    theme         TEXT NOT NULL,             -- articles.theme value (15 verticals)
    language      TEXT NOT NULL,             -- 'es' | 'en'
    edition_date  DATE NOT NULL,
    persona       TEXT NOT NULL,             -- persona key, e.g. 'la-mesa'
    headline      TEXT NOT NULL,
    body_md       TEXT NOT NULL,             -- markdown; [n] citations map to event_ids[n-1]
    event_ids     TEXT[] NOT NULL,           -- cited events, in [n] order (we number them)
    model         TEXT NOT NULL,             -- provenance: provider/model used

    -- ── SLM training provenance (Phase 1 = data factory for Phase 2 distill) ──
    input_context JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{event_id, headline, excerpt}]
    prompt        TEXT,                                 -- the rendered system+user prompt

    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (theme, language, edition_date)
);

CREATE INDEX IF NOT EXISTS idx_editorials_theme_date
    ON editorials (theme, edition_date DESC);
