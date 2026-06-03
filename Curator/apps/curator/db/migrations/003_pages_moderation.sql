-- Curator — migration 003: pages moderation support (Phase 2.3)
--
-- Backoffice moderation (publish/unpublish/drop) issues RabbitMQ commands that
-- Curator consumes and applies to public.pages / public.events. The original
-- 001 schema declared `pages.published_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`,
-- which made "unpublish" (clear the publish timestamp) impossible without a
-- sentinel value. We relax the column to NULLable so:
--   • published page  → published_at IS NOT NULL (the publish time)
--   • unpublished page → published_at IS NULL
--   • dropped page     → published_at IS NULL  +  events.status = 'dropped'
--
-- events.status already carries the moderation state of record
-- (CHECK status IN ('draft','published','dropped') from 001) — we reuse it
-- rather than adding a parallel column on pages. No hard delete: a dropped page
-- row is retained (unpublished) so it can be re-published or re-synthesized.
--
-- Idempotent: ALTER ... DROP NOT NULL is a no-op if already dropped.

ALTER TABLE pages ALTER COLUMN published_at DROP NOT NULL;
