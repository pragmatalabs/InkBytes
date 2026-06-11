-- Seed the 10 breaking-news pulse outlets (Messor ADR-0017 / Curator ADR-0024).
-- Run after deploying the pulse release (Curator migration 014 adds the column):
--   docker exec -i inkbytes-postgres psql -U inkbytes -d inkbytes \
--     < /opt/inkbytes/infra/scripts/backfill_pulse_outlets.sql
-- All 10 have droplet-verified feed_url (2026-06-11). Approved by Julian 2026-06-11.
BEGIN;
UPDATE outlets SET pulse = TRUE WHERE name IN (
    'bbc', 'aljazeera', 'theguardian', 'npr', 'latimes',
    'cnbc', 'infobae', 'clarin', 'lanacionar', 'eluniversalmx'
);
COMMIT;
SELECT name, pulse, feed_url IS NOT NULL AS has_feed
FROM outlets WHERE pulse ORDER BY name;
