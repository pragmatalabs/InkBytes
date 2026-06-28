-- 020 — pages.title_history (Curator ADR-0035, evolving titles).
--
-- As an event materially develops, re-synthesis evolves its headline so the page
-- reads current ("Mexico opens its World Cup campaign" → "Mexico reaches the
-- round of 16"). The PRIOR headlines must be preserved — for the vault and a
-- per-event story timeline. On re-synthesis, SynthesizeSkill appends the previous
-- headline to this list BEFORE overwriting (only when it actually changed).
--
-- Ordered oldest→newest: [{"headline": "...", "at": "<ISO>", "sources": <n>}, ...]
-- The live pages.headline is always the latest; title_history is the trail.
--
-- Guard (database_service ALTER_GUARDS): skipped once the column exists.

ALTER TABLE pages
    ADD COLUMN IF NOT EXISTS title_history JSONB NOT NULL DEFAULT '[]'::jsonb;
