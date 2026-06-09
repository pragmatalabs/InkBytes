# ADR-0021 — Lead-image must come from a cluster CORE member

> *Status: accepted / implemented · Owner: Julián · Last updated: 2026-06-09*
>
> Stops a marginal/mis-clustered article from supplying an off-topic hero photo.

## Context

The event **"Michael Tilson Thomas, Renowned Conductor, Dies at 81"** (3 NPR
articles about the late conductor) rendered a hero photo of **Stevie Nicks /
Fleetwood Mac**. The image came from a Guardian article *"Stevie Nicks donates
$3m to medical school…"* that had clustered into the event.

```
dist    outlet       title                                                      has_image
0.000   npr          Remembering symphony conductor Michael Tilson Thomas        no
0.285   npr          Michael Tilson Thomas, renowned conductor … dies at 81      no
0.427   npr          Stream NPR Classical's Playlist On Spotify                  no
0.470   theguardian  Stevie Nicks donates $3m to medical school …               YES  ← hero
```

Two facts combined:

1. The cluster attach threshold is **0.50** cosine distance
   ([ADR-0017](./0017-cluster-threshold-bge-m3-calibration.md)). The Stevie Nicks
   article attached at **0.47** — a legitimately-attached but *marginal* member.
2. The `/events` `lead_image` rollup picked the **freshest** article with an image
   (`ORDER BY scraped_at DESC`). The on-topic NPR articles had no og:image, so the
   only image-bearing article — the marginal Stevie Nicks one, also the freshest —
   won the hero.

Result: an off-topic hero. This is the recurring "wrong cover photo" class, and is
distinct from the hotlink/blank-cover problem
([ADR-0019](./0019-lead-image-hotlink-guard.md)).

## Decision

Gate the `lead_image` rollup (both `/events` and `/events/{id}` in
[`core/api_server.py`](../../apps/curator/core/api_server.py)) to **core cluster
members**: only consider an image whose article is within
`cluster_distance <= 0.45` — comfortably inside the 0.50 attach threshold — then
keep the existing freshest-wins order among those.

```sql
WHERE a.event_id = e.id
  AND a.lead_image IS NOT NULL AND a.lead_image <> ''
  AND a.cluster_distance <= 0.45          -- core members only
ORDER BY a.scraped_at DESC
LIMIT 1
```

An event whose only image sits on a marginal member now renders **text-only**
rather than a wrong photo. It's a query-time rollup, so no data migration is
needed — every event reflects the new rule on the next request.

## Impact (measured on the live corpus)

Of 281 published events (278 had a hero):

- **270** keep a hero · **8** go text-only (their only image was a >0.45 outlier) ·
  **39** switch to a more-core image (their freshest image was an outlier).

The 8 that go text-only are mostly broad multi-topic aggregations ("X, Y, Z face
crises") or genuinely off-topic (Stevie Nicks on the MTT obituary; Dave Mason on a
Kathy Sledge event).

## Trade-off (honest)

Distance alone cannot separate an *off-topic outlier* from an *on-topic article on
a loose cluster*: Stevie Nicks (0.47, off-topic) and "Karina Gao" (0.48, the
event's own subject) sit at nearly the same distance. Any ceiling that drops the
former also drops the latter. We accept that a handful of loose-cluster events lose
an otherwise-correct hero and go text-only, because **a missing image is better
than a wrong one** — the product preference is explicit.

The ceiling (0.45) is a constant near the 0.50 attach threshold; raising it toward
0.47 would re-admit the Stevie Nicks case, lowering it trims more heroes. A future,
more precise fix would score image-article relevance against the event's dominant
entities/headline rather than rely on cluster distance.

## Alternatives considered

- **Most-central image (`ORDER BY cluster_distance ASC`).** More principled, but
  changed **189/278** heroes (every multi-image event) for little additional
  off-topic protection beyond the ceiling. Rejected as high-churn.
- **Entity/headline relevance match.** Most precise (compare the image article's
  entities to the event's), but requires the rollup to join entities and score
  overlap. Deferred; revisit if the distance ceiling proves too blunt.
