# ADR-0011 — Editorial audio: self-hosted Piper TTS (not ElevenLabs)

> *Status: v1 · Owner: Julian · Date: 2026-07-15 · Built + verified locally, NOT yet deployed*

## Context

Each daily "Today's [Topic] Outlook" editorial (ADR-0008) should be listenable —
a spoken-word version of the column, in **both English and Spanish**, generated
**once** per edition and cached (never re-synthesized on read). The trigger was a
request to wire up ElevenLabs' text-to-speech API.

ElevenLabs is billed **per character**. The Outlook runs ~30 columns/day (15
themes × 2 languages, ADR-0008). At ~5k characters/column that is ~9M chars/month:

| Provider | Rate | ~Monthly (all 30/day × EN+ES) |
|---|---|---|
| ElevenLabs multilingual_v2 | $0.10 / 1k | ~$900 |
| ElevenLabs Flash v2.5 | $0.05 / 1k | ~$450 |
| Amazon Polly / Google **standard** | ~$4 / 1M | ~$36 |
| OpenAI `tts-1` / Polly neural | ~$0.015 / 1k | ~$135 |
| **Self-hosted Piper (CPU)** | **$0** | **~$0** |

Julian's verdict on the ElevenLabs numbers: "too expensive." This is the same
economics that drove **Curator ADR-0003** (local Ollama `bge-m3` embeddings over
paid OpenAI): a recurring per-unit SaaS bill for a bulk, non-differentiating
primitive, on a product with no paying users yet.

## Decision

**Self-host TTS with [Piper](https://github.com/rhasspy/piper)** — a fast, CPU-only
neural TTS — as a small **HTTP microservice on the 16 GB box** (Hostinger, alongside
Ollama), NOT on the droplet. Zero per-character cost; no external voice vendor. The
first cut ran Piper *inside the droplet's editorial batch* and it **swap-thrashed the
4 GB-free shared droplet into a site outage** (see the throughput note) — onnxruntime's
~1 GB working set has no room there. Synthesis moved off-box; the droplet only makes a
network call.

- **`Editorial/apps/tts-server`** — FastAPI: `POST /synthesize {text, lang}` (+ an
  `X-TTS-Token` shared secret) → `audio/mpeg`. Voices baked in + loaded once; synthesis
  serialized. Exposed via the box's existing Traefik at a subdomain over HTTPS.
- **The droplet's editorial batch** keeps doing everything else. `services/tts.Tts`
  has a **remote mode** (`EDITORIAL_TTS_URL` set): `to_speakable` runs locally (pure
  regex), then it POSTs the clean text to the service, receives the MP3, and uploads
  **public-read** to DigitalOcean Spaces (`services/storage.SpacesStorage`,
  key `audio/outlook/{date}/{theme}-{lang}.mp3`), persisting the URL on the row. The
  droplet editorial image ships **no** Piper/ffmpeg/voices — it stays slim.

Supporting pieces (all best-effort — a TTS/upload failure never blocks the batch):

- Migration `002_editorial_audio.sql` adds `audio_url`, `audio_voice`,
  `audio_generated_at` to `editorials`. A NULL `audio_url` = "not synthesized yet".
- **Generated once:** synthesis runs only when a row has no audio. `main.py
  --synthesize-missing` backfills existing rows (idempotent) — the migration path
  for the columns already in prod.
- Curator `GET /outlook` returns `audio_url` (guarded by an `information_schema`
  column check so a Curator deploy landing before migration 002 can't 500).
- The Reader outlook page renders a minimal `OutlookAudio` player (`preload="none"`,
  accent play/pause + scrubbable progress) under the headline. The `src` is already
  language-correct because the page fetches per-language.

**One voice per language** ("the InkBytes narrator"), baked into the **service** image
and configurable via `EDITORIAL_TTS_VOICE_EN/_ES` / `TTS_VOICE_EN/_ES`: default
**`en_US-ryan-high`** + **`es_MX-claude-high`** — bumped medium→high once synthesis
moved off the droplet (the box has headroom); both -high and -medium are baked into
the service image for A/B. (Historically **`en_US-ryan-medium`**, warm
US male) + **`es_MX-ald-medium`** (LATAM Spanish, chosen over Castilian for the
LATAM-weighted audience) — a matched male narrator across both languages (Piper uses
a distinct model per language, not a single cross-lingual clone). **Medium** quality,
not `-high`: see the throughput note below.

## Alternatives considered

| Option | Rejected because |
|---|---|
| ElevenLabs (multilingual_v2 / Flash) | ~$450–900/mo for the full scope — "too expensive" for a pre-revenue product. Best fidelity + true one-voice-both-languages, but the cost is unjustifiable at this stage. |
| Cheap cloud TTS (Polly/Google standard) | ~$36/mo — viable, but still a per-character bill that scales with column count, and adds a vendor. Self-hosting is $0 and has no ceiling. |
| XTTS v2 (self-hosted, single cloned voice both langs) | Closest to "one brand voice," but GPU-hungry / minutes-per-clip on CPU, ~4 GB RAM. Piper is faster-than-real-time on CPU. |
| **Piper in the droplet's editorial batch** (first attempt) | **Tried and reverted.** onnxruntime's ~1 GB working set swap-thrashed the 4 GB-free shared droplet into a site outage (load 137, swap maxed). No CPU cap fixes a RAM shortage. This is *why* synthesis moved to the 16 GB box — the "no cross-box hop" simplicity wasn't worth an unusable box. |
| Piper HTTP service on the 16 GB box (**chosen**) | Adds a small long-running service + a Traefik route + a network hop — accepted, because it's the only placement with RAM headroom (10 GB free vs the droplet's swap wall). The droplet stays slim and safe. |

## Consequences

- **$0 marginal cost** for audio, forever — same posture as bge-m3 (ADR-0003).
- The **TTS service image** (16 GB box) bakes ffmpeg + `piper-tts` + ~120 MB of
  medium voices. The **droplet editorial image** stays slim — just `httpx` (call the
  service) + `boto3` (upload) — because the droplet has no RAM for onnxruntime.
- Audio is **best-effort**: disabled cleanly if `EDITORIAL_TTS_ENABLED=false`, if
  `EDITORIAL_TTS_URL` is unset (no local fallback on the droplet — the image ships no
  Piper), or if `DO_SPACES_*` creds are blank — none of which block the text batch.
- **macOS caveat (dev):** the `piper-tts` macOS wheel ships a broken espeak-ng-data
  path, so synthesis can't run natively on the Mac. It works on linux/amd64 + arm64 —
  validated by building both images and running the full remote chain (droplet batch →
  service → Spaces → DB → Curator → Reader player) against the dev stack.
- **Deploy status (2026-07-15):** DONE — migration `002` applied to prod; Curator +
  Reader deployed (serve/play `audio_url`); droplet editorial slimmed; droplet-side TTS
  disabled (`EDITORIAL_TTS_ENABLED=false`) after the outage; **`tts-server` deployed on
  the 16 GB box** (`/root/inkbytes-tts`, behind Traefik for `tts.inkbytes.news`,
  `X-TTS-Token` secret, restart-always, 2 GB cap) — verified internally (healthz + a
  synth + a 401-without-token; WordPress + box unaffected). ~11 of today's columns
  already have audio from the (reverted) droplet runs. BLOCKED ON — a DNS A record
  `tts.inkbytes.news → 82.112.250.139` (user action; Let's Encrypt HTTP-01 needs it to
  resolve). AFTER DNS — set `EDITORIAL_TTS_URL`/`_SECRET` + re-enable TTS in the
  droplet's `infra/.env`, then `run-editorial.sh --synthesize-missing` to backfill.
- Voice choice is config, not code — swapping voices is an env change (to a voice also
  baked into the service image).

### Throughput / capacity (lesson learned at deploy, 2026-07-15)

The first deploy ran `-high` EN voices synthesized **serially, one CPU-uncapped
container per run**. Real columns are long (~600 words → 2–4 min audio), so each
clip took **~60–140 s** of CPU, and two overlapping runs drove the 4-core droplet to
**load ~69** (Piper/onnxruntime grabs every core). The public site stayed up but was
at risk. Fixes, all shipped:

1. **Load the voice model ONCE** (`services/tts.py` now uses the Piper **Python API**,
   not a CLI subprocess per clip). The CLI reloaded the ~60 MB model + re-init'd
   onnxruntime on *every* clip; with concurrency that churned CPU **and memory** hard
   enough to push the box to load ~55 with memory pinned at the cgroup cap (D-state
   thrash). Loading once and reusing the cached voice removes that entirely — the root
   cause. (macOS can't run the API — its espeakbridge ignores the data path — but
   Linux, all prod cares about, is fine.)
2. **Medium voice** (`en_US-ryan-medium`) — ~2× faster synth than `-high`, quality
   still fine for narration.
3. **Hard resource cap in `run-editorial.sh`** — `--cpus` (default **2.0**) + `--memory`
   + `OMP_NUM_THREADS`: a kernel-enforced guardrail so a batch can never starve the live
   stack regardless of onnxruntime threading. One synth's onnxruntime fills the 2-core
   slice, so `tts.concurrency` defaults to **1** (higher risks sharing one session across
   threads for no gain under the cap). Synthesis is decoupled from text generation into a
   `_synthesize_batch` run after the text loop (`generate_theme` no longer voices inline).

The CPU story improved a lot — but the **memory** story didn't. Even load-once +
medium + cap, a backfill pushed the already-tight 7.8 GB droplet (whole stack + other
projects, swap in use) to **swap 3.6 GB / load 137 → site timeouts**. onnxruntime's
~1 GB working set simply has no room on that box. So the resolution was to **move
synthesis off the droplet entirely** to the 16 GB box's Piper microservice (see the
Decision). The `--cpus` cap, load-once, and medium voice all still apply *there* (and
keep the service polite next to Ollama), but the decisive fix was placement, not tuning.

### Compliance note (workspace policy)

This is AI-generated code destined for an internal system: it must be reviewed by a
human developer before production (review documented, reviewer owns it), run through
the approved application-security tooling, and follow OWASP secure-coding practice.
No secrets are committed — the Spaces credentials live only in `infra/.env`. Piper
is self-hosted OSS (MIT/GPL voices), which sidesteps the third-party-AI-vendor
approval question that ElevenLabs would have raised.
