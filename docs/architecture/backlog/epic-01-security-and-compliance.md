# Epic 01 — Security & Compliance

> *Close R-009 (leaked secrets) before first paying user. Build the secrets-handling discipline that should have existed from day one.*

Risk-links: **R-009 (Critical)** · Sprints: 2 & 4 · Total: 16 pts

---

## IB-12 · Rotate all legacy production-looking tokens

**As** the platform owner, **I want** every secret that ever sat in `env.yaml` revoked and reissued, **so that** the previously-leaked tokens can't be used against us.

### Acceptance criteria

```gherkin
Given the legacy env.yaml had DO Spaces, Strapi, Platform, OpenAI and RabbitMQ tokens
When I rotate them in each provider's console
Then each old token returns 401/403 on any subsequent request
And the new tokens are stored only in 1Password or DO env vars
And a doc records who rotated what and when
```

### Notes

- Providers: DigitalOcean (Spaces + API), Anthropic, OpenAI, RabbitMQ (CloudAMQP or DO managed).
- Pair with IB-13 (history scrub) — order doesn't matter, but both must complete.
- DO Spaces key needs least-privilege (`s3:Put`, `s3:Get`, `s3:List` on `inkbytes/*`).

**Sprint**: 2 · **Points**: 2 · **Risk**: R-009 · **Priority**: P0

---

## IB-13 · Scrub leaked tokens from git history

**As** the platform owner, **I want** the leaked tokens permanently removed from every reachable commit, **so that** the repo can be cloned by anyone without exposing the old values.

### Acceptance criteria

```gherkin
Given the legacy tokens appear in past commits of env.yaml and env.do.yaml
When I run `git filter-repo --replace-text <patterns.txt>`
Then no past commit returns any of the leaked tokens for `git log -p | rg <token>`
And the rewrite is force-pushed to origin (with team coordination)
And every contributor re-clones or re-bases on the new history
```

### Notes

- Use `git filter-repo` (NOT `bfg` — it's more reliable with multi-line replacements).
- Coordinate force-push window: all collaborators stop pushing, scrub, push, re-clone.
- Add the scrubbed token patterns to the pre-commit secret-scanner so they can't return.

**Sprint**: 2 · **Points**: 3 · **Risk**: R-009 · **Priority**: P0 · **Depends on**: IB-12

---

## IB-14 · Install pre-commit secret scanner (gitleaks)

**As** a contributor, **I want** any attempt to commit a real secret to be blocked locally, **so that** R-009 never repeats itself.

### Acceptance criteria

```gherkin
Given a developer tries to commit a file containing an `sk-ant-` or `sk-` prefixed key
When the pre-commit hook runs
Then the commit is rejected with a clear pointer to the offending line
And the rejected hash never enters the repo
```

### Notes

- Tool: `gitleaks` via `pre-commit`.
- Config in `.pre-commit-config.yaml`; install instructions in `CONTRIBUTING.md`.
- CI mirror: `gitleaks-action` runs on every PR to catch developers who skipped local setup.

**Sprint**: 2 · **Points**: 2 · **Risk**: R-009 · **Priority**: P0

---

## IB-15 · Enable GitHub secret scanning + push protection

**As** the platform owner, **I want** GitHub to refuse pushes containing known secret patterns, **so that** the leak fence is enforced at the SCM level too.

### Acceptance criteria

```gherkin
Given the repo is on GitHub
When push protection is enabled in repo settings
Then a push containing a recognized provider token is rejected with a GH error
And any new partner provider can be added to the patterns list within an hour
```

### Notes

- Free on public repos. For pragmatalabs/InkBytes (currently public per `git remote -v`), turn on under Settings → Code security → Secret scanning + Push protection.
- Pair with IB-14 for defense in depth.

**Sprint**: 2 · **Points**: 1 · **Risk**: R-009 · **Priority**: P0

---

## IB-16 · Move RabbitMQ from user/pass to TLS-cert auth

**As** the platform team, **I want** Messor and Curator to authenticate to RabbitMQ with mTLS rather than `user:pass`, **so that** a leaked AMQPS URL alone is insufficient to publish/consume.

### Acceptance criteria

```gherkin
Given the broker (CloudAMQP or DO managed) supports x509 client cert auth
When Messor and Curator are reconfigured to present client certs
Then connection succeeds only with valid cert + key
And the broker logs reject any user/pass attempt with a clear error
And cert rotation procedure is documented in security.md
```

### Notes

- Requires broker plan upgrade (Little Lemur free tier may not support mTLS).
- Cost impact: ~$19/mo. Compare against risk.
- Defer to Sprint-3 if budget gate blocks v0; we already have AMQPS + auth.

**Sprint**: 3 · **Points**: 5 · **Risk**: R-009 (STRIDE Tampering) · **Priority**: P1

---

## IB-17 · External penetration test before second user cohort

**As** the platform owner, **I want** an independent pentest report before scaling past 50 paying users, **so that** I have evidence-based assurance instead of "I think we're secure."

### Acceptance criteria

```gherkin
Given v0 is live with 20+ paying users
When a third-party security vendor performs OWASP Top 10 + auth/session/cookie review
Then findings are categorized as Critical / High / Medium / Low
And every Critical or High finding has a tracked remediation ticket
And the report is filed under compliance/
```

### Notes

- Budget: ~$3-5k for a focused web app pentest.
- Vendors to evaluate: Cobalt.io, Bishop Fox lite, local providers.
- Timing: late Sprint-4 so v0 has been live long enough to be representative.

**Sprint**: 4 · **Points**: 3 · **Risk**: R-009 (defense depth) · **Priority**: P2
