-- One-time backfill: mark legacy triage-dropped articles (ADR-0030 / migration 017).
-- Run ONCE on prod after deploying migration 017:
--   docker exec -i inkbytes-postgres psql -U inkbytes -d inkbytes < backfill_triage_dropped.sql
--
-- Rationale: the only thing that leaves an article unenriched AFTER it reaches
-- Curator is the pre-enrich triage drop (stale messages are acked at ingest
-- without a row; dedup SKIPs are already enriched). So any row that is
-- unenriched, has no topic, and has sat longer than the pipeline lag (~30 min;
-- we use 1 h for safety) is a triage drop that predates the terminal marker.
-- This clears the inflated "pending enrichment" counter immediately instead of
-- waiting ~2 days for the legacy rows to age out.

UPDATE articles
   SET triage_dropped_at = COALESCE(triage_dropped_at, scraped_at),
       triage_drop_reason = COALESCE(triage_drop_reason, 'backfill: legacy pre-marker triage drop')
 WHERE enriched_at IS NULL
   AND topic IS NULL
   AND triage_dropped_at IS NULL
   AND scraped_at < NOW() - INTERVAL '1 hour';

SELECT count(*) AS now_marked_dropped FROM articles WHERE triage_dropped_at IS NOT NULL;
SELECT count(*) AS true_pending FROM articles WHERE enriched_at IS NULL AND triage_dropped_at IS NULL;
