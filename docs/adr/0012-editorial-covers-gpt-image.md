# ADR-0012 — Editorial Outlook covers: stylized AI heroes via gpt-image-1-mini

> *Status: v1 · Owner: Julian · Date: 2026-07-15 · Built + verified locally, NOT yet deployed*

## Context

The "Today's [Topic] Outlook" editorial columns (ADR-0008) render with a
persona-icon masthead but no imagery. We wanted a hero cover per column. The
options weighed (with Julian):

- **Stock via Envato MCP** — its MCP is *search-only* ("download? No, not currently"),
  Elements has no download API, and per-download licensing doesn't automate. Rejected
  as a pipeline source (fine as a manual discovery helper).
- **Existing cover system (ADR-0034: Openverse/Wikimedia/Unsplash)** — real photos,
  great for *event* heroes, but these are opinion columns, not events.
- **AI generation** — owned images, no per-download licensing, and (crucially) safe
  for opinion columns if kept abstract. Cheapest good option: **OpenAI
  `gpt-image-1-mini`** (~$0.005–0.01/image) — and OpenAI is already our vendor.

Cost, at real volume (~14 covers/day — one per theme/day, shared across languages):
~420/mo × ~$0.008 ≈ **$3–4/mo**. The full ElevenLabs-image / premium tiers weren't
worth it here.

## Decision

Generate **one stylized cover per `(theme, edition_date)`** (language-neutral, both
es + en rows share it) with `gpt-image-1-mini`, cached in DigitalOcean Spaces,
rendered as the Outlook hero. Runs **in the droplet's editorial batch** — it's a
remote API call, zero local compute, so none of the Piper/onnxruntime droplet-thrash
(ADR-0011) applies.

- **`Editorial/apps/editorial/services/covers.py`** — `Covers`: prompt from
  `prompts/cover.md` (theme + headline + per-theme accent) → `images.generate(model,
  size=1536x1024, quality=low, output_format=webp)` → ~50 KB WebP bytes.
- **`application.py`** — after text + audio, `_cover_batch` generates one cover per
  unique theme/day (English headline preferred for the prompt), uploads public-read
  to Spaces (`covers/outlook/{date}/{theme}.webp`), persists on all rows. `main.py
  --cover-missing` backfills. Best-effort — a failure never blocks text/audio.
- **Migration `003`** — `cover_url`, `cover_prompt`, `cover_generated_at` on `editorials`.
- **Curator `GET /outlook`** returns `cover_url` (same `information_schema` guard as
  `audio_url` so a deploy before migration 003 can't 500).
- **Reader** — a landscape hero on `/outlook/[topic]` above the masthead (bleeds to
  edges on mobile, rounded on desktop); graceful fallback to the persona masthead
  when there's no cover.

**News-integrity + legal guardrail (in the prompt):** covers are for *opinion*
columns and prompted to be **abstract / conceptual illustration — NO text, NO real
people, NOT photorealistic**, so a cover can never read as a documentary photo of a
real event. The exact prompt is stored per row (`cover_prompt`) for audit. This
*reduces* the image-licensing exposure in the legal-risk memo (owned illustration vs
hotlinked outlet og:images), it doesn't add to it.

**Hard cost cap:** `EDITORIAL_COVERS_MONTHLY_CAP_USD` (default **$10**). Before a
batch, `count_covers_this_month() × unit_cost` gives spend; generation stops at the
cap and logs. `EDITORIAL_COVERS_ENABLED=false` is a hard kill-switch. Belt + suspenders.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Envato Elements (MCP or API) | MCP is search-only; Elements has no download API; per-download licensing can't automate. Manual discovery only. |
| ElevenLabs Image | Aggregator (markup) over the same models incl. GPT Image 1; ~$127+/mo tier for its good models; new vendor. |
| Premium (Imagen/Chirp, Flux pro) | Nicer but 4–10× the cost for a cover slot; `gpt-image-1-mini` is plenty at this size/role. |
| Photoreal AI heroes for hard news | Integrity + legal minefield (fabricated event/person imagery). Restricted to abstract illustration for opinion columns only. |
| Per-language covers | Wasteful — an image needs no translation. One per theme/day, shared. |

## Consequences

- **~$3–4/mo** for all-theme daily covers; hard-capped at $10 regardless.
- Editorial image needs no new deps (openai already present; WebP comes straight from
  the API — no Pillow). `OPENAI_API_KEY` + `EDITORIAL_COVERS_*` forwarded by
  `run-editorial.sh`.
- **Verified locally (2026-07-15):** the real `gpt-image-1-mini` call on the droplet
  produced an on-brand 53 KB WebP (violet, abstract, no text/people — the intended
  house style); the full render path (seeded cover → Curator `cover_url` → Reader
  hero) verified on the dev stack. The in-app `covers.py` generate + cap enforcement
  are compile-checked and mirror the validated API call; a single real batch on the
  droplet at deploy is the last check (like the audio backfill).
- **Follow-up (P1b):** cover **thumbnails on the Outlook index + "more outlooks"
  cards** — needs `cover_url` added to `/outlook/available` + `/outlook/archive` and
  their Reader types. Detail-page hero (the core) shipped first.
- **Deploy runbook (not yet run):** apply migration `003`; set `OPENAI_API_KEY` +
  `EDITORIAL_COVERS_*` in `infra/.env`; rebuild editorial + Curator + Reader; backfill
  with `run-editorial.sh --cover-missing` (cost-capped, newest-first).

### Compliance note

AI-generated code for an internal system: human review + approved security tooling
before production; OpenAI is an existing vendor; `OPENAI_API_KEY` stays in `infra/.env`
only; covers are abstract illustration (no real people/events) with the prompt stored
for audit.
