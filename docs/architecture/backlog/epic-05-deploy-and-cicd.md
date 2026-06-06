# Epic 05 — Deploy & CI/CD

> *Replace the manual ssh-and-pray deploy with reproducible pipelines. Every merge to master should be one button-press away from production.*

Risk-links: enabler for everything · Sprints: 2 · Total: 11 pts

---

## IB-35 · `.do/app.yaml` for DO App Platform autodeploy

**As** the platform owner, **I want** every push to `master` to autodeploy to DO App Platform, **so that** I don't ssh into servers to ship code.

### Acceptance criteria

```gherkin
Given the repo has .do/app.yaml at root
When I push a commit to master
Then DO App Platform builds each declared service from its Dockerfile
And replaces running instances in a rolling restart
And /healthz returns 200 within 90s of replacement
And the deploy shows in DO dashboard with build logs
```

### Notes

- One service block per: `messor-worker`, `messor-api`, `curator-worker`, `curator-api`, `backoffice`, `reader`, `queue-worker`.
- All env vars marked SECRET in the spec.
- Cost vs single Droplet + docker-compose: +$12/mo for managed builds. Worth it for one-click rollback.

**Sprint**: 2 · **Points**: 5 · **Was**: INK-8 · **Priority**: P0

---

## IB-36 · CI pipeline (lint + test + image build)

**As** the team, **I want** every PR to run ruff + pytest + docker build on every Python service, **so that** master never breaks silently.

### Acceptance criteria

```gherkin
Given a PR is opened on the repo
When CI runs
Then ruff lint passes on Curator + Messor
And pytest passes for both services (min 60% coverage)
And docker build succeeds for every Dockerfile
And images are pushed to GHCR on master merges, tagged with the short SHA
```

### Notes

- GitHub Actions: `.github/workflows/ci.yml`.
- Matrix: Python 3.11 + 3.12.
- Cache pip + Docker layers for speed.
- Add a `coverage-comment` PR comment with delta.

**Sprint**: 2 · **Points**: 3 · **Was**: INK-9 · **Priority**: P0

---

## IB-37 · One-command rollback runbook

**As** ops, **I want** a single documented command to roll back any service to its previous image, **so that** I can recover from a bad deploy in under 2 minutes.

### Acceptance criteria

```gherkin
Given a service is on master-{sha2} and master-{sha1} was the previous good
When I run `bash infra/rollback.sh <service> <sha>` (or DO CLI equivalent)
Then DO redeploys that service with the older image
And /healthz returns 200 within 90s
And the rollback action is logged in #ops Slack
```

### Notes

- For DO App Platform: `doctl apps create-deployment --image inkbytes/<service>:<sha>`.
- Document the command in `docs/architecture/views/deployment-view.md` §Rollback.
- Test once per sprint as a fire-drill.

**Sprint**: 2 · **Points**: 1 · **Risk**: R-005 mitigation · **Priority**: P1

---

## IB-38 · Staging environment with mirror config

**As** the team, **I want** a staging deploy that mirrors production except using a `staging-` prefixed Spaces bucket and a separate RabbitMQ vhost, **so that** D6/D7 soak tests happen against real services without contaminating prod.

### Acceptance criteria

```gherkin
Given .do/app-staging.yaml exists alongside .do/app.yaml
When merges to a `staging` branch (or `develop`) happen
Then a staging app spec deploys to a separate URL (staging.inkbytes.app)
And it points at staging Postgres + staging Spaces prefix + staging RMQ vhost
And no production data is touched
```

### Notes

- Separate DO Postgres ($15/mo).
- Reuse existing Spaces bucket with `messor-staging/` prefix.
- Single shared password for staging Reader.

**Sprint**: 3 · **Points**: 2 · **Priority**: P1

---

## IB-39 · 7-day staging soak as ship-gate

**As** the platform owner, **I want** every release candidate to run 7 consecutive days on staging without intervention before going to prod, **so that** v0 ship is evidence-based rather than vibes-based.

### Acceptance criteria

```gherkin
Given a release candidate is deployed to staging
When 7 days elapse
Then there are zero unplanned restarts
And articles_total > 5000 across 168 cycles
And errors_total / articles_total < 5%
And ≥5 outlets each returned ≥10 articles
And at least 50 events have synthesized pages
```

### Notes

- Sprint-1's INK-10 promised this; this story holds it open across sprints.
- Auto-promote script gated on metrics from `/status` endpoint.

**Sprint**: 3 · **Points**: 2 · **Was**: INK-10 · **Priority**: P1
