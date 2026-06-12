-- Curator migration 015 — persistent synthesis watermark
--
-- _last_synth_source_count was an in-memory dict, wiped on every worker
-- restart. After a deploy each qualifying event re-synthesized once on its
-- next incoming article — harmless as a trickle, but a restart in front of a
-- multi-thousand-message backlog re-synthesized hundreds of events in a burst
-- (the 2026-06-12 post-deploy synthesis storm: deepseek-reasoner calls
-- occupying most pipeline slots for hours).
--
-- events.last_synth_source_count records the distinct-outlet count at the
-- moment the event's page was last synthesized. The gate "only re-synthesize
-- when a NEW outlet joined" now survives restarts.

ALTER TABLE events ADD COLUMN IF NOT EXISTS last_synth_source_count INT NOT NULL DEFAULT 0;

-- Backfill: events that already have a page were synthesized at SOME point;
-- seed the watermark with their current source_count so the fleet doesn't
-- re-synthesize once per event when this migration first deploys.
UPDATE events e
   SET last_synth_source_count = e.source_count
 WHERE e.last_synth_source_count = 0
   AND EXISTS (SELECT 1 FROM pages p WHERE p.event_id = e.id);
