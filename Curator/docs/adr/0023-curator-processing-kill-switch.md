# ADR-0023 — "Stop Curator" processing kill-switch

> *Status: accepted (implemented) · Owner: Julian · Date: 2026-06-09*

## Context

Operators need a way to **pause Curator's processing pipeline** from the
Backoffice — e.g. during an incident, a cost spike, a bad-config rollout, or
maintenance — without SSHing to the droplet or stopping containers. The
Backoffice is a web app and must not control Docker (privilege escalation,
fragile), so the stop must be a first-class application signal.

## Decision

Add a persistent boolean `processing_enabled` to `backoffice.curator_settings`
(default `true`) and have Curator honor it via its existing 30s settings-refresh
loop (the same hot-reload path used for models/keys/thresholds — ADR-0004).

When `processing_enabled = false`:

- The worker's article handler raises `ProcessingPausedError` **before** any
  work, and the RabbitMQ consumer **requeues** the message (`nack(requeue=true)`)
  after a short back-off (`_PAUSE_BACKOFF = 5s`, throttling the prefetch=1
  consumer so it idles instead of spinning).
- **No articles are lost** — they accumulate in the durable queue and process
  when resumed.
- The **API surface is unaffected** — the Reader keeps serving published pages.

A **persistent** flag (not an in-memory RabbitMQ command) was chosen so a stop
survives restarts/deploys — an operator's pause can't silently undo itself.

### Surfaces

- **Backoffice** (`Messor/apps/platform`): a "Processing" card on the Curator
  Settings page with a Running/Paused chip and a Stop/Resume button (confirm
  dialog on stop). `POST /settings/processing` → `CuratorSettingController::
  toggleProcessing()` writes the row and audit-logs `settings.processing_toggled`.
  Migration `2026_06_09_000001_add_processing_enabled_to_curator_settings`.
- **Curator**: `AppCfg.processing_enabled` + `_DB_SETTINGS_MAP` entry (live
  poll); `_handle_event` gate; `ProcessingPausedError` + back-off in
  `MessageService.consume`; `processing_enabled` surfaced on `/status` (the live
  value the worker is honoring, reflecting the ~30s lag).

## Consequences

- Stop/resume takes effect within the refresh interval (~30s) — acceptable for
  an operational control; not instantaneous.
- While paused the worker wakes every 5s to requeue one message — negligible CPU,
  no LLM calls, no DB writes.
- The flag pauses **processing only**. The API, Messor harvest, and RabbitMQ keep
  running; the queue grows while paused and drains on resume.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Backoffice execs `docker stop` / SSH | Privilege escalation; the web app should never control the host/containers |
| In-memory pause via a RabbitMQ command | Instant, but lost on restart/deploy — a stop could silently undo itself |
| Stop the whole service (incl. API) | Takes the Reader down; the goal is to pause *processing*, not the read surface |
| `basic_cancel` the consumer while paused | Cleaner "no redelivery" but invasive to the consume loop; throttled-requeue is simpler and equally loss-free |

## Verification (local, 2026-06-09)

- Flipped `processing_enabled=false` → `/status` reflected it in ~15s; published a
  test article → worker logged `Processing paused — article requeued.` every 5s,
  queue held the message (1 unacked, not drained), nothing lost.
- Flipped back to `true` → `/status` flipped in ~25s, worker resumed ENRICH
  immediately.
- Backoffice: `php -l` clean (controller/model/migration/routes); Settings page
  JSX parses cleanly.

## Implementation checklist

- [x] Migration: `curator_settings.processing_enabled boolean default true`
- [x] `CuratorSetting` model: fillable + boolean cast
- [x] `CuratorSettingController::toggleProcessing()` + `settings.processing` route + audit
- [x] Settings page: Running/Paused card + Stop/Resume button + confirm dialog
- [x] Curator `AppCfg.processing_enabled` + `_DB_SETTINGS_MAP`
- [x] `ProcessingPausedError` + requeue/back-off in `MessageService.consume`
- [x] `_handle_event` gate + `/status` exposure
