# Messor — Operations Runbook

> *Status: v1 · 24/7 service · Last updated: 2026-06-01*

Messor is the harvester agent. It must stay up. This runbook covers the boring
work of keeping it healthy.

## 1. Service summary

| Field | Value |
|---|---|
| Service | `messor-scraper` |
| Runtime | Python 3.10+ inside Docker, `restart: always` |
| Mode | Scheduled (`python main.py --schedule`) |
| Default cycle | 60 minutes (`scraping.schedule_interval_minutes`) |
| Surface | FastAPI on `:8050` (internal) |
| Logs | console + file + RabbitMQ exchange `messor.logs` |
| Storage | `data/` (local staging) + DO Spaces (`inkbytes/messor/...`) |
| Events out | RabbitMQ queue `articles-scraped` |
| Tier | T1 — outage stops the product pipeline |

## 2. Health endpoints (target)

| Endpoint | Purpose | Expected |
|---|---|---|
| `GET /healthz` | Liveness | `200 {"ok": true}` |
| `GET /readyz` | Readiness (DB + RabbitMQ + Spaces reachable) | `200` or `503` with reason |
| `GET /status` | Last cycle summary | JSON with `last_run_at`, `outlets`, `articles`, `errors` |

If these don't yet exist, add them as part of M1 (production hardening).

## 3. Normal day

```text
00:00 ── cycle starts
00:00 ── acquire lock
00:00 ── outlets fetched from platform (or fallback to local)
00:00 ── threadpool fans out per outlet
00:0X ── each outlet scrape:
              fetch → parse → dedup → stage → upload to Spaces
              → POST to platform → publish RabbitMQ event
00:1X ── analytics summary written
00:1X ── lock released
00:60 ── cycle starts again
```

Expected per-cycle output (steady state):

- 1 session JSON per outlet under `data/scrapes/`
- 1 object per session under `s3://inkbytes/messor/staging/`
- 1 RabbitMQ message per article on `articles-scraped`
- Log entries on `messor.logs` exchange

## 4. Routine checks

| Cadence | Check | Where |
|---|---|---|
| Hourly (automated) | Cycle completed within last 75 min | `/status` + log shipper |
| Daily | Per-outlet success rate ≥ 90% | Analytics dashboard |
| Daily | DO Spaces usage growth normal (< 10× baseline) | DO dashboard |
| Weekly | Duplicate rate trend per outlet | Analytics dashboard |
| Weekly | RabbitMQ queue depth on `articles-scraped` not growing | RabbitMQ management |
| Monthly | Outlet inventory audit (dead outlets removed) | Platform admin |
| Quarterly | Secret rotation | Doppler / DO env vars |

## 5. Common operations

### Restart the container

```bash
docker compose -f infra/docker/docker-compose.yaml restart scraper
```

### Run a one-shot cycle

```bash
docker compose exec scraper python main.py --scrape
```

### Drain & stop cleanly

```bash
docker compose exec scraper python main.py   # interactive
# enter:  EXIT
```

### Tail logs

```bash
docker compose logs -f scraper
```

### Inspect last session JSON

```bash
docker compose exec scraper cat scraping_session.json
```

### Clean stale staging files

```bash
docker compose exec scraper python main.py   # then:  CLEAN
```

## 6. Alerts to wire up

| Alert | Condition | Severity |
|---|---|---|
| Cycle missed | No cycle in 90 min | P1 |
| RabbitMQ disconnected | MessageService logs reconnect attempts > 3 | P2 |
| DO Spaces upload failures | > 5% in a cycle | P2 |
| Platform API 5xx rate | > 10% in a cycle | P2 |
| Disk usage > 80% on staging volume | OS metric | P2 |
| Per-outlet success < 50% | Two consecutive cycles | P3 (outlet alert) |
| Duplicate rate > 80% | Suggests outlet feed isn't updating | P3 |

Recommended pipeline: Better Stack / Datadog → Slack `#inkbytes-ops`.

## 7. Incident playbook

### 7.1 "No articles scraped this cycle"

1. Check `/status` — is `errors > 0`?
2. Check container is running and lock isn't stuck — `docker compose ps`.
3. Check egress: `curl -I https://www.bbc.com` from inside the container.
4. Check outlets list isn't empty — `OutletService` may have fallen back to a
   stale local file.
5. If RabbitMQ is the culprit, articles will still be staged locally — events
   resume once broker is back.

### 7.2 "RabbitMQ keeps disconnecting"

1. Confirm broker reachable: `nc -vz kloudsix.io 5672`.
2. Check credentials in env vars.
3. Verify heartbeat config (600s today).
4. Failover: switch `RABBITMQ_URL` to a backup broker (CloudAMQP) and restart.

### 7.3 "DO Spaces uploads failing"

1. Check key validity in DO console.
2. Verify endpoint region matches the bucket region.
3. Test from container:
   `aws --endpoint-url https://nyc3.digitaloceanspaces.com s3 ls s3://inkbytes/`.
4. Sessions remain in local staging; rerun ingest once Spaces is back.

### 7.4 "Container restart loop"

1. `docker compose logs scraper --tail 200` — look for the first traceback.
2. 9 out of 10 times it's a missing env var or a malformed `env.yaml`.
3. Re-deploy with last known good image (`docker compose pull && up`).

### 7.5 "Cycle takes longer than the interval"

Detect via `/status.last_run_duration`. If duration > interval, either:

- reduce outlets per cycle (split into outlet groups), or
- raise `max_threads`, or
- raise `schedule_interval_minutes` until horizontal scale-out (M3).

## 8. Backups

- DO Spaces is the authoritative artifact store; enable bucket versioning and
  a 90-day lifecycle.
- The platform Postgres database (where article metadata lives) is the
  system-of-record — back it up via DO managed backups (daily).
- Messor's local `data/` is **ephemeral** — never the source of truth.

## 9. Capacity guidance

| Dimension | Today's default | Comfortable ceiling per host |
|---|---|---|
| Outlets per cycle | unbounded (limited by ThreadPool) | ~200 |
| Threads | `max_threads: 10` | CPU × 2 |
| Cycle interval | 60 min | down to 15 min with healthy egress |
| Articles per cycle | varies by outlet | ~10k |

Above those, plan M3 horizontal scale-out (outlet sharding + workers).

## 10. Owner & on-call

- Service owner: Julián de la Rosa
- On-call: TBD (define in `OPERATIONS.md` at repo root once team scales)
- Escalation: product owner first, infra second.
