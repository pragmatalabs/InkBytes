# Epic 08 — Reader & Monetization

> *Move from "single shared password" + "no billing" to real auth, real subscriptions, real legal cover. This is what unlocks growth past invited users.*

Sprint: 4 · Total: 17 pts

---

## IB-49 · Magic-link email auth (Resend + Lucia or Auth.js)

**As** a reader, **I want** to log in with just my email (no password), **so that** signup friction is near-zero.

### Acceptance criteria

```gherkin
Given a visitor enters their email on the Reader login page
When they click "Send magic link"
Then Resend sends an email within 5s
And clicking the link sets a session cookie (HttpOnly, Secure, SameSite=Lax)
And the session lasts 30 days with sliding expiry
And /me returns the user's email when authenticated
```

### Notes

- Lucia or Auth.js (next-auth v5). Recommend Lucia — simpler, no NextAuth quirks.
- Resend free tier: 100 emails/day. Bump to paid once we have > 20 paying users.
- Replaces the v0 single-shared-password gate.

**Sprint**: 4 · **Points**: 5 · **Priority**: P0

---

## IB-50 · Stripe Checkout + webhook → `users.is_paid`

**As** a reader, **I want** to subscribe with a credit card via Stripe Checkout, **so that** I can pay without leaving the site.

### Acceptance criteria

```gherkin
Given an authenticated reader clicks "Subscribe — $9/month"
When they complete Stripe Checkout
Then a webhook updates users.is_paid = true with stripe_customer_id
And the next page load shows full one-pagers (not the truncated preview)
And cancellation sets is_paid = false at period end (not immediately)
And invoices.paid_at is recorded
```

### Notes

- Stripe Test mode for the whole Sprint-4; flip to Live before launch.
- Use Stripe Customer Portal for cancellations (no custom UI needed).
- Webhook signing secret in env var.

**Sprint**: 4 · **Points**: 5 · **Priority**: P0

---

## IB-51 · Free preview vs paid full read

**As** a non-paying visitor, **I want** to see headlines + first 100 words of each event, **so that** I can sample the product before paying.

### Acceptance criteria

```gherkin
Given a visitor opens /event/[id]
When they are not authenticated or is_paid = false
Then they see the headline + first ~100 words of synthesis_md
And a "Subscribe to read in full" CTA
And the evidence_rail is hidden
And the truncation happens in the Reader (Curator returns full JSON)
```

### Notes

- Server-side truncation in the Reader's Server Component.
- Use word count not character count (avoids mid-sentence cuts).
- SEO: include full text only when authenticated to prevent paywall bypass via cached page.

**Sprint**: 4 · **Points**: 2 · **Priority**: P0

---

## IB-52 · Public API rate limiting per IP and per user

**As** the platform, **I want** rate limits on the Reader-facing API and a stricter cap on /events with unauthenticated IPs, **so that** scrapers can't lift our content.

### Acceptance criteria

```gherkin
Given nginx with limit_req modules (or Cloudflare in front)
When a single IP makes > 60 requests/min to /events
Then it gets 429 with Retry-After header
And authenticated users get a more generous 300 req/min cap
And the limit is configurable in nginx config or DO firewall
```

### Notes

- nginx is cheapest. Cloudflare in front of DO is the no-tuning option.
- Tradeoff: rate limiting impacts legitimate users behind shared NATs.

**Sprint**: 4 · **Points**: 2 · **Priority**: P1

---

## IB-53 · Privacy policy + DSAR endpoint (DR Ley 172-13 prep)

**As** the platform owner, **I want** a public privacy policy and an admin endpoint that exports/deletes a user's data on request, **so that** I'm aligned with Dominican Republic data law before the first paying user.

### Acceptance criteria

```gherkin
Given a published /privacy page describes data we collect (email, reading history)
And designated DPO contact email is published
When a user emails the DPO requesting their data
Then the DPO can run `backoffice:user:export <email>` to produce JSON
And `backoffice:user:delete <email>` to remove the row + cascade-delete sessions
And both operations are audit-logged to a separate table
```

### Notes

- DR Ley 172-13 (data protection) + GDPR-lite (if any EU readers).
- Privacy policy template adapted by a lawyer (~$500 one-time).
- DSAR via CLI in v0; UI in Sprint-5.

**Sprint**: 4 · **Points**: 3 · **Priority**: P1
