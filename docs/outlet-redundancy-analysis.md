# Outlet redundancy analysis — which outlets are safe to cut

> *Status: analysis + recommendation · Owner: Julian · Date: 2026-06-13*
> *Backed by the "Decisive" column on the Backoffice Outlets screen (live metric).*

## Question

Which outlets provide largely the same information, so scraping all of them is
near-duplicative? Cutting redundant outlets saves scrape + enrich + embed budget
without losing unique coverage.

## Method

Two complementary measures over the live event clusters (`articles` grouped by
`event_id`):

1. **Pairwise co-occurrence** — for each outlet pair, **Jaccard** (shared events
   ÷ combined) and **subsumption** (shared ÷ the smaller outlet's events). High =
   the two keep landing in the same stories.
2. **Decisive contribution** (the safe-cut signal, now a live Backoffice column)
   — the share of an outlet's events where it is *load-bearing* for the ≥2-source
   publish bar: the event has ≤2 distinct sources (this outlet is the sole source,
   or one of exactly two). **Low decisive % = almost always a redundant 3rd+
   source → safe cut.** It correctly protects high-unique-value outlets even when
   they co-occur heavily (e.g. clarin: 55% decisive on 169 unique AR stories).

## Findings (prod corpus, 2026-06-13)

Redundancy is **only within the same region + language** — never across EN/ES, so
bilingual coverage of global stories is *not* redundant.

**Co-occurrence clusters:**

| Region | Outlets | Signal |
|---|---|---|
| 🇩🇴 DR (5) | diariolibree, elcaribedr, hoydo, listindiario, eldiado | densest; diariolibree subsumes 54–59% of the others |
| 🇨🇴 CO (4) | eltiempoco, elcolombiano, larepublicaco, portafolioco | larepublicaco+portafolioco (business) share 55% |
| 🇲🇽 MX | excelsiormx ⊃ mileniomx | 60% of mileniomx already in excelsiormx |
| 🇦🇷 AR | clarin + lavozar | 141 shared events |
| 🌐 EN | ground-news ↔ apnews (26%) | ground-news is an aggregator — redundant by design |

**Decisive % (ascending = safe-cut order):**

| Outlet | Decisive % | Verdict |
|---|---|---|
| polifact | **3%** | never load-bearing — clearest cut |
| mileniomx | 19% | + 60% subsumed → strong cut |
| eldiado / portafolioco / hoydo | 27–32% | DR/CO cluster trim candidates |
| clarin / apnews / abces | 50–56% | **keep** — high unique contribution |

## Recommendation

Trim *within* clusters; don't cut across languages:

- **DR**: keep 2 of 5 (e.g. diariolibree + listindiario); drop/deprioritize hoydo, eldiado, elcaribedr.
- **MX**: drop `mileniomx` (subsumed by excelsiormx).
- **CO business**: collapse portafolioco/larepublicaco to one.
- **`polifact`**: drop (never decisive, brings nothing unique).
- **`ground-news`**: reconsider alongside AP/Reuters (it aggregates them).

**Two caveats before cutting:**
1. The product's value is *one page per event, multiple sources* — co-occurrence
   is partly desired corroboration; the win is diminishing-returns budget, not
   quality.
2. Cutting an outlet lowers `source_count`, which feeds both the ≥2-source publish
   bar and the breaking detector's pulse-outlet velocity (ADR-0024). **Never cut a
   pulse outlet.**

## How to act

The Backoffice **Outlets screen → "Decisive" column** shows this metric live
(red <25% = likely safe cut, amber <40%). Sort ascending to surface candidates,
cross-check against the region clusters above, then deactivate via the Outlets
toggle (data change, no redeploy). Re-check after a week — the metric updates as
the corpus grows.
