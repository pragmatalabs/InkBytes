# InkBytes — Dev Workflow

> *Status: v1 · Owner: Julian · Last updated: 2026-06-08*
> *These rules apply to all contributors and agents working in this repo.*

---

## 1. Test locally FIRST, deploy second

**Hard rule (called out explicitly by Julian, 2026-06-08):** no code or config change goes to production without first being verified in local dev. Do not ship directly from edit → commit → push → deploy.

### What "local dev" means for InkBytes

| Service | Command | Port |
|---|---|---|
| Infrastructure (Postgres + RabbitMQ + MinIO) | `bash orchestrator/scripts/up.sh` | 5432 / 5672 / 9000 |
| Curator (API + worker) | `cd Curator/apps/curator && python main.py` | 8000 |
| Messor (harvester) | `cd Messor/apps/scraper && python main.py` | — |
| Reader (Next.js) | `cd Reader/apps/web && npm run dev` | 3000 |
| Full dev (with Ollama embeddings) | `bash orchestrator/scripts/up.sh full` | adds :11434 |

### Required verification by change type

| Change type | What to check |
|---|---|
| Python — Curator / Messor logic | Boot the service locally; confirm it starts without errors; exercise the changed code path (trigger a scrape, synthesis, or API call as appropriate). |
| Reader — UI / component | `npm run dev`, open localhost:3000, visually confirm the change renders correctly end-to-end. |
| Config / env var | Verify the running container picks up the new value via `docker logs` or direct inspection. |
| Schema / DB migration | Run migration locally against dev Postgres before deploying. |
| Infra / docker-compose | `docker compose -f orchestrator/docker-compose.dev.yaml up` and confirm service health. |

### Deploy only after local green

```
# Step-by-step
1. Bring infra up locally:         bash orchestrator/scripts/up.sh
2. Run the changed service locally: <service-specific command above>
3. Verify the change works:         <exercise the changed code path>
4. Commit:                          git commit -m "…"
5. Push:                            git push                       ← only with Julian's "push"
6. Deploy:                          bash infra/deploy.sh [--build] ← only with Julian's "deploy"
```

---

## 2. Commit locally, wait for push/deploy instruction

Per Julian's explicit preference (captured in `memory/git-push-workflow.md`):

- **Always commit locally** — do not leave changes uncommitted.
- **Do NOT push** to `origin/master` unless Julian says "push" or "deploy" in chat.
- **Do NOT trigger a deploy** (`bash infra/deploy.sh`, `make deploy-build-do`, or any SSH-side command) without an explicit instruction.
- End every work session with: _"N commit(s) ahead of origin, ready to push when you say so."_

**Deploy target:** DigitalOcean only — `67.205.136.61` / `inkbytes.org`. Hostinger is retired.

---

## 3. Document before commit

Per the _document-then-commit-push_ memory rule:

1. Write an ADR if the change is non-trivial (new dependency, architectural choice, reversed decision).
2. Update `docs/STATUS.md` if the live state changed.
3. Fix any stale references in `CLAUDE.md` or service-level `CLAUDE.md` files.
4. Then commit all of docs + code together (or doc-first commit, then code commit — never code-only).

---

## Anti-patterns this rule exists to prevent

- Shipping a change that works in production but breaks on the next Docker image build because it assumed a runtime env var that isn't set during `docker build`.
- Shipping ISR pages that call Docker-internal hostnames (`inkbytes-curator-api`) — the build bakes the 503 state permanently. Use `force-dynamic` (ADR-R-0005).
- Deploying Chromium-based changes without smoke-testing the seccomp/Playwright combination locally via the `docker compose` dev stack (ADR-0011).
- Deploying and discovering the breakage from production logs instead of from local `npm run dev`.
