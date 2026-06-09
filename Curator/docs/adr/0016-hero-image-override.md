# ADR-0016 — Hero image: author-photo blocker + YouTube thumbnail fallback

> *Status: accepted · Owner: Julian · Date: 2026-06-09*

## Context

Event hero images are sourced from the outlet's `og:image` via `articles.lead_image`.
Two failure modes were observed in production:

1. **Author photo** — Heraldo (and other Latin American outlets using WordPress) set
   `og:image` to the journalist's byline headshot rather than a story photo.
   Event `/01KTMRBKA2YC44Z3XJ1PXDPPFT` showed a journalist profile picture as the hero.

2. **Semantically-wrong stock image** — an outlet chose a generic stock photo matching
   a keyword in the headline (e.g. shopping cart for a "buyer" story). The image
   passes the hotlink probe (ADR-0019) and the cluster-distance gate (ADR-0021) but
   is editorially unrelated to the story.

Existing validation:
- **ADR-0019 (hotlink probe):** catches CDN-blocked images; does not check content relevance.
- **ADR-0021 (cluster gate):** requires `cluster_distance ≤ 0.45`; catches marginal members
  with off-topic photos, but the Heraldo headshot comes from a core member.

## Decision

Two-part fix, both in Curator with no Reader changes:

### Part 1 — Author-photo URL guard (sync, free)

`MediaValidator.is_author_photo(url)` — a static regex method that checks the URL
path for patterns common to CMS byline photo storage:

```
/author[s]?/   /autores?/   /journalist[s]?/   /reporter[s]?/
/contributor[s]?/   /columnist[s]?/   /staff/   /people/   /team/
/profile[s]?/   /avatar[s]?/   /headshot[s]?/   /byline[s]?/
author_photo   author_image   profile_image   profile_photo
[_-]author[_-]
```

Called in `_handle_event()` after the existing hotlink check. If it matches, the
article's `lead_image` is set to NULL before storage — the same behaviour as the
hotlink gate. Sync and zero-cost: no HTTP, no cache needed.

### Part 2 — YouTube thumbnail as fallback

`IllustrateSkill` already runs a headline-based YouTube search after synthesis.
Those video thumbnails are inherently story-relevant (the search engine found them
for this specific headline). After writing `media_rail`, the skill now also writes
the best thumbnail URL to `events.hero_image` (new `TEXT` column, migration 011).

The API's `lead_image` derivation in both `/events` and `/events/{event_id}` is
updated to:

```sql
COALESCE(
    (SELECT a.lead_image FROM articles a
     WHERE a.event_id = e.id AND a.lead_image IS NOT NULL ...
     ORDER BY a.scraped_at DESC LIMIT 1),
    e.hero_image
) AS lead_image
```

Priority: **outlet og:image first** (authoritative, hi-res journalism photo when
valid) → **YouTube thumbnail fallback** when outlet image is NULL.

## Failure mode coverage

| Failure mode | Fixed? | Mechanism |
|---|---|---|
| Author / byline headshot (Heraldo) | ✅ | `is_author_photo()` NULLs it; YouTube thumb fills in |
| Hotlink-blocked CDN image (LA Times) | ✅ (pre-existing ADR-0019) | hotlink probe NULLs it; YouTube thumb fills in |
| Outlet has no og:image at all | ✅ | already NULL; YouTube thumb fills in |
| Semantically-wrong stock image (renders fine) | ⚠️ deferred | Would need vision-model check; not addressed here |

## Deferred

Semantically-wrong stock images (case 2) cannot be detected via URL patterns alone —
they pass both the hotlink probe and the author-photo guard. The correct fix would be
a vision-model relevance check (`claude-3-haiku` with the image URL + headline).
Deferred due to API cost (~$0.002/image). Acceptable for v0 given low frequency.

## Consequences

- **Positive:** journalist headshots replaced by story-relevant YouTube thumbnails
  for affected outlets (Heraldo, any outlet that sets `og:image` to byline photo).
- **Positive:** events with no outlet image now show a relevant YouTube thumbnail
  instead of a blank hero.
- **Positive:** zero latency overhead — `is_author_photo()` is sync regex; `write_hero_image()`
  runs in the existing post-synthesis `IllustrateSkill` background task.
- **Neutral:** good outlet images (Reuters, AP, BBC, CNN) are unaffected — they pass
  author-photo check and continue to show as hero (COALESCE prefers them).
- **Neutral:** existing pages in DB keep their current `lead_image` until the next
  re-synthesis or re-harvest triggers the new guards.
- **Requires:** DB migration 011 (`events.hero_image TEXT`) run before deploy.
