# Curator ADR-0035 — Evolving event titles + a story-title timeline (history of mutations)

> *Status: **P0+P1 implemented** (2026-06-28, committed, not deployed) · Owner: Julian De La Rosa · Date: 2026-06-25*
>
> **Implemented:** P0 capture — migration `020_page_title_history.sql` (`pages.title_history` JSONB) + `SynthesizeSkill._persist` upsert appends the PREVIOUS headline (with publish time + source count) on re-synthesis *only when it changed* (validated on dev: changed re-synth captured, same-headline re-synth did not duplicate). P1 Reader — `/events/{id}` decodes `title_history`; the event page renders a collapsible "Story timeline · N earlier headlines" (hidden until history accrues). P2 (carry into `story_arcs` on conclude) pending. Titles already evolve via re-synthesis; this preserves + surfaces the trail.

## Context

An event is not static — as it materially develops (ADR-0033 material updates), its
synthesized **headline should evolve to reflect the latest state** so the page reads
*current*, not frozen at the first-published title. Example: a story published as
"Mexico opens its World Cup campaign" should, after the round-of-16 result, read
"Mexico reaches the round of 16" — same event, evolved headline.

But the **history of those title mutations must be preserved** — both in the
**vault** (a concluded event keeps the full arc of how it was told) and in a
per-event **timeline** the reader can see (how the story, and its framing, evolved
over time). Today the headline is simply overwritten on re-synthesis; the prior
titles are lost.

This composes with ADR-0033 (the material clock decides *when* to evolve),
ADR-0013 (the vault/story_arcs that the history is preserved into), and ADR-0031
(tighter events make an evolving title meaningful rather than a grab-bag).

## Decision

### 1. Titles evolve on material re-synthesis
Re-synthesis already re-fires when an event gains sources past its synth watermark
(ADR-0015, `events.last_synth_source_count`). Keep that as the throttle — the
headline evolves when the story **materially grows** (a new source/development),
not on every tangential article (which, per ADR-0033, doesn't even bump the
material clock). So title evolution is automatically tied to *real* developments.

### 2. Capture every title mutation
On re-synthesis, if the new headline **differs** from the current one, append the
**previous** headline to a per-event history *before* overwriting:

```
pages.title_history  JSONB DEFAULT '[]'
  -- ordered oldest→newest: [{ "headline": "...", "at": "<ISO>", "sources": <n> }, ...]
```

The live `pages.headline` is always the latest; `title_history` is the trail of
what it used to say (with the timestamp + source count at each version). A new
migration; the write happens in `SynthesizeSkill` (it already upserts the page).

### 3. The vault preserves the timeline
When an event concludes (ADR-0013 → `story_arcs`), carry its `title_history` into
the arc so the archived story retains the full narrative arc, not just its final
headline. A concluded event in the vault therefore shows *how it was told over time*.

### 4. Reader: a "Story timeline"
On the event page (and in the vault view), render a compact **timeline** from
`title_history` + the current headline + `occurred_at`/`last_material_update_at`:
"Developing since {occurred} · {N} title updates", expandable to the list of past
headlines with their dates. This makes the evolution legible and signals an
actively-developing story without faking the date.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Never change the headline (freeze at first publish) | Stale — an actively-developing story reads as old; the whole point of "look current". |
| Overwrite the headline, keep no history (today) | Loses the narrative arc; the vault/timeline can't show how the story evolved. |
| Re-synthesize the headline on *every* article attach | Cost + churn; tangential articles shouldn't change the title. The material-update/watermark throttle ties evolution to real developments. |
| Separate `event_title_history` table | A JSONB column on `pages` is simpler, travels with the page, and is enough for an append-only ordered list; revisit if we need to query across histories. |

## Consequences

- Event pages stay **current** (headline tracks the latest development) without
  faking recency — pairs with ADR-0033's honest `occurred_at` date.
- The **vault becomes a narrative archive** — each concluded story keeps the arc
  of how it was told, not just the last headline.
- New **timeline** surface in the Reader; a small JSONB column + one write in
  synthesize; no new LLM calls (re-synthesis already happens on material growth).
- Slight page-row growth (the history list); bounded (one entry per material
  re-synth, which is throttled by the source watermark).

## Rollout

1. **P0 — capture:** migration `pages.title_history`; `SynthesizeSkill` appends the
   prior headline when it changes. Backfill seeds `[]`. (Curator-only, invisible.)
2. **P1 — Reader timeline:** "Story timeline" on the event page from `title_history`.
3. **P2 — vault:** carry `title_history` into `story_arcs` on conclude; surface it
   in the vault view.
