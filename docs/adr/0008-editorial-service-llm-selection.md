# ADR-0008 — Editorial service: daily per-theme editorial persona, provider-pluggable LLM

> *Status: **Phase 1 + "Today's Outlook" LIVE in production** (deployed 2026-07-03) · Owner: Julian · Date: 2026-06-11*
>
> **DEPLOYED 2026-07-03 (`inkbytes.org/outlook`):** curator-api (`/outlook` + `/outlook/available`) + reader (`/outlook`, `/outlook/[topic]`, header nav) rebuilt & recreated (worker untouched); editorial image built on the droplet; **first batch = 30 columns** (all 15 themes × ES+EN) generated on DeepSeek; **daily cron installed** — `59 11 * * *` droplet-local (America/New_York) = 11:59 AM AST = **15:59 UTC**, the morning-briefing cut, which also sits OUTSIDE the DeepSeek peak window (ADR-0038). Cron wrapper = committed `infra/run-editorial.sh` (reads `infra/.env`, provider stays a flag). EN generation validated on prod (clean English, no Spanish bleed). Reader shows the persona **display name** ("El Circuito"), not the kebab key.
>
> **"Today's [Topic] Outlook" (2026-06-28):** the editorial surfaced as a reader product. Bilingual (ES+EN, config default), **morning-briefing cut at 11:59 AM** (daily edition covering the prior ~24h; `editorials` unique-per-day = the saved archive). Curator API `/outlook?theme=&lang=&date=` (edition + cited-events **timeline** + `available_dates` archive) + `/outlook/available` (index), guarded so they return empty until the service runs. Reader `/outlook/[topic]` page (persona header + editorial markdown + timeline + **Copy / Export .md / Print-PDF** via `outlook-actions.tsx` + ES/EN toggle + date picker) + `/outlook` index + a header nav link. Editorial `Dockerfile` added (one-shot batch, run by a daily cron at the cut). NEXT: Phase 2 SLM distillation (the `editorials` table's `input_context` + `prompt` are the training set); flip provider → local gemma4 after the 16 GB droplet upgrade (no code change, env-only).
>
> **Phase 1 (scaffold):** new standalone service `Editorial/apps/editorial/` (Curator conventions, pydantic v2): config (provider-pluggable LLM — ollama|deepseek|anthropic), `services/db.py` (reads published pages/events, writes `editorials`, applies migration `001_editorials.sql`), `services/llm.py` (plain-text completion), `personas.py` (15 named per-theme voices — La Mesa/El Balance/…), `prompts/editorial.md`, orchestrator (gather → min-events gate → render persona → generate → store), CLI (`--generate [--theme] [--lang] [--date] [--dry-run]`). The `editorials` table carries `input_context` + `prompt` → it doubles as the **Phase-2 distilled-SLM training set** (the cost-at-scale, local editorial model). Plumbing validated on dev. **Next:** validate generation quality on prod data; Reader "Editorial" surface; daily cron + Dockerfile/compose; then Phase 2 distillation. Open questions below answered: single-language (es) to start; per-theme named personas; min_events gate = 3.

## Context

InkBytes wants a **vertical curator persona**: a named editorial voice per theme
("La Mesa" for politics, etc.) that publishes one **daily editorial** per
vertical — a 450–600 word column with its own voice that synthesizes the day's
published events into a narrative, cites events as `[n]` links, and gives the
paid reader something no aggregator has.

Decisions fixed up front by Julian:

- **This is NOT a Curator skill.** Editorial is its own service, outside the
  enrich→cluster→synthesize pipeline. Curator produces event pages; Editorial
  consumes *published pages* and produces opinionated daily columns.
- **Prefer local models** (Ollama) where quality and infrastructure allow.

### Theme taxonomy

`articles.theme` is the clean vertical taxonomy — 8 values:
`politics · world · business · culture · health · technology · sports · environment`.
(`events.topic` is **empty for all rows** — do not build on it. An event's theme
is the majority `articles.theme` of its cluster members.)

### Workload

8 themes × 1 editorial/day (×2 if bilingual EN+ES) ≈ **10–16 generations,
~15k output tokens per day**, fully latency-tolerant (nightly batch at a quiet
hour). This is a tiny workload — the constraint is *quality and where the model
can physically run*, not throughput.

## Model bake-off (2026-06-11)

Method: real prod data (top-10 politics events from the last 24h, headline +
synthesis excerpt), one persona prompt in Spanish (the hard case — LATAM is the
vertical), three local models via Ollama on the dev Mac (M5 Pro, 48 GB).
Spanish was chosen deliberately: any model that survives Spanish editorial
prose will do English easily; the reverse is not true.

| Model | Q4 size | Speed (Mac) | Verdict |
|---|---|---|---|
| **gemma4 (12B-class)** | 9.6 GB | 67 tok/s | **Near-publishable.** Correct `[n]` citations, real narrative thread (not event-by-event summary), sober voice, memorable close. Needs only a light copy-edit. |
| qwen3:4b | 2.6 GB | 82 tok/s | Fail. Thinking tokens leaked into output (`think:false` not honored by template); gender errors ("**el** presidente Claudia Sheinbaum"), anglicisms ("un bill", "los ballots"), invented a bill name. |
| llama3.2:3b | 2.0 GB | 108 tok/s | Fail. Fluent but mistranslates ("blank check" → "blanqueador"), ignores the citation instruction. |

**Finding: ~12B is the quality floor for publishable Spanish editorial prose.**
4B-class models produce text you cannot put in front of a paying reader.

### Infrastructure constraint

| Host | Spec | Can run 12B? |
|---|---|---|
| Prod droplet (`67.205.136.61`) | 4 vCPU · 7.8 GB RAM (~2.4 GB free) · disk 89% · CPU-only Ollama (serves bge-m3) | **No.** 12B Q4 needs ~10 GB resident. Even 4B is marginal and risks the OOM killer hitting Postgres. |
| Dev Mac (M5 Pro, 48 GB) | Ollama, GPU-accelerated | Yes — up to ~30B Q4. |
| Droplet upgraded 8→16 GB (~+$48/mo) | CPU-only | Yes — ~3–6 tok/s → 8 editorials ≈ 25–40 min nightly batch. Acceptable for cron. |

### Cost comparison

DeepSeek API (already in the stack for Curator synthesis) prices the entire
daily editorial batch at **< $0.05/day**. Running local-on-droplet today buys
no savings — it costs a $48/mo RAM upgrade to avoid pennies of API spend. The
real arguments for local are independence and data control, which is why the
provider stays a config flag rather than a hard choice.

## Decision

1. **Editorial is a separate service** (own folder, own ADR sequence), following
   Curator conventions: Python + pydantic v2, persona prompts as `.md` files
   (one per theme), reads published pages from Postgres, writes an `editorials`
   table, daily cron at a quiet hour. Reader renders a per-theme "Editorial"
   section.
2. **LLM provider is pluggable** — same pattern as embeddings (Curator
   ADR-0003): `EDITORIAL_LLM_PROVIDER` ∈ `ollama | deepseek | anthropic`, with
   base-url/model config per provider.
3. **Sequencing:**
   - **Dev (now):** `ollama` + **gemma4** on the Mac — passed the bake-off,
     free, fast iteration on personas against the real corpus.
   - **Prod (launch):** `deepseek` — the droplet cannot host the quality floor;
     do not degrade the product to force local.
   - **Prod (after 16 GB upgrade):** flip the flag to `ollama` + gemma4. The
     upgrade also relieves the droplet's 89% disk / 2.4 GB headroom squeeze.

### Sketch: `editorials` table

```sql
CREATE TABLE editorials (
    id           TEXT PRIMARY KEY,
    theme        TEXT NOT NULL,            -- articles.theme value
    language     TEXT NOT NULL,            -- 'es' | 'en'
    edition_date DATE NOT NULL,
    headline     TEXT NOT NULL,
    body_md      TEXT NOT NULL,            -- [n] citations resolved to event links
    event_ids    TEXT[] NOT NULL,          -- events cited, in [n] order
    persona      TEXT NOT NULL,            -- prompt file name, e.g. 'la-mesa'
    model        TEXT NOT NULL,            -- provenance: provider/model used
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (theme, language, edition_date)
);
```

## Alternatives considered

| Option | Rejected because |
|---|---|
| Editorial as a 4th Curator skill | Julian's explicit call: out of Curator. Also different cadence (daily batch vs continuous consume), different failure domain, different LLM needs. |
| 4B-class local model on the current droplet | Fails the quality bar in Spanish (bake-off above); marginal RAM fit risks the whole stack. |
| Hard-commit to API (no local path) | Loses the local option the provider flag preserves for free; dev iteration on personas is better local. |
| Generate on the dev Mac, push artifacts to prod | Prod must be self-contained; a daily product feature cannot depend on a laptop being awake. |

## Open questions (answer at implementation time)

- Bilingual strategy: one editorial per theme in the feed's dominant language,
  or always ES+EN (16 generations/day)?
- Persona definitions: one shared voice vs. a distinct named persona per theme.
- Minimum input gate: skip a theme's editorial when fewer than N events
  published that day (avoid padding thin days).
- Reader surface: dedicated tab vs. pinned card atop each theme filter.
