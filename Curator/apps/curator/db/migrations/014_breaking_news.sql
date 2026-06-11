-- Curator migration 014 — breaking-news fast lane (ADR-0024 / Messor ADR-0017)
--
-- events.breaking_at:    when the cluster-velocity detector flagged the event
--                        (≥2 pulse outlets within 60 min). NULL = never flagged.
-- events.breaking_until: auto-demotion deadline (breaking_at + 2h).
-- outlets.pulse:         outlet is on the 5-minute RSS pulse lane (Messor).

ALTER TABLE events  ADD COLUMN IF NOT EXISTS breaking_at    TIMESTAMPTZ;
ALTER TABLE events  ADD COLUMN IF NOT EXISTS breaking_until TIMESTAMPTZ;
ALTER TABLE outlets ADD COLUMN IF NOT EXISTS pulse BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_events_breaking
    ON events(breaking_until) WHERE breaking_until IS NOT NULL;
