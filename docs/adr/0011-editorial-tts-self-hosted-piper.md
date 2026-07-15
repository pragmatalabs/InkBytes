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
neural TTS — inside the **Editorial batch container**, on the DigitalOcean droplet
where the daily job already runs. Zero per-character cost; no external voice vendor;
no new long-running service; no cross-box network hop.

Flow (all best-effort — a TTS/upload failure never blocks the text batch):

1. After a column is written (`write_editorial`), `Application._synthesize_audio`
   strips the markdown/`[n]` citations to speakable prose (`services/tts.to_speakable`),
   runs **Piper → WAV → ffmpeg → mono 64 kbps MP3** (`services/tts.Tts`), uploads
   **public-read** to DigitalOcean Spaces (`services/storage.SpacesStorage`,
   key `audio/outlook/{date}/{theme}-{lang}.mp3`), and persists the public URL on
   the editorial row.
2. Migration `002_editorial_audio.sql` adds `audio_url`, `audio_voice`,
   `audio_generated_at` to `editorials`. A NULL `audio_url` = "not synthesized yet".
3. **Generated once:** synthesis runs only when a row has no audio. `main.py
   --synthesize-missing` backfills existing rows (idempotent) — the migration path
   for the columns already in prod.
4. Curator `GET /outlook` returns `audio_url` (guarded by an `information_schema`
   column check so a Curator deploy landing before migration 002 can't 500).
5. The Reader outlook page renders a minimal `OutlookAudio` player (`preload="none"`,
   accent play/pause + scrubbable progress) under the headline. The `src` is already
   language-correct because the page fetches per-language.

**One voice per language** ("the InkBytes narrator"), baked into the image and
configurable via `EDITORIAL_TTS_VOICE_EN/_ES`: default **`en_US-ryan-medium`** (warm
US male) + **`es_MX-ald-medium`** (LATAM Spanish, chosen over Castilian for the
LATAM-weighted audience) — a matched male narrator across both languages (Piper uses
a distinct model per language, not a single cross-lingual clone). **Medium** quality,
not `-high`: see the throughput note below.

## Alternatives considered

| Option | Rejected because |
|---|---|
| ElevenLabs (multilingual_v2 / Flash) | ~$450–900/mo for the full scope — "too expensive" for a pre-revenue product. Best fidelity + true one-voice-both-languages, but the cost is unjustifiable at this stage. |
| Cheap cloud TTS (Polly/Google standard) | ~$36/mo — viable, but still a per-character bill that scales with column count, and adds a vendor. Self-hosting is $0 and has no ceiling. |
| XTTS v2 (self-hosted, single cloned voice both langs) | Closest to "one brand voice," but GPU-hungry / minutes-per-clip on the CPU droplet, ~4 GB RAM — 60 clips/night would run for hours and contend with the batch. Piper is faster-than-real-time on CPU. |
| Piper as an HTTP service on the Ollama/Hostinger box | Matches the box literally, but adds a long-running service + firewall wiring + a network failure mode for a job that's only a few CPU-minutes. In-batch on the droplet is simpler and more robust. |

## Consequences

- **$0 marginal cost** for audio, forever — same posture as bge-m3 (ADR-0003).
- The editorial image gains ffmpeg + `piper-tts` + `boto3` and bakes ~175 MB of
  voice models. Build time and image size grow modestly; runtime is a few transient
  CPU-minutes once a day, after gemma4/DeepSeek finishes the text.
- Audio is **best-effort**: disabled cleanly if `EDITORIAL_TTS_ENABLED=false`, if the
  binaries/voice models are absent, or if `DO_SPACES_*` creds are blank — none of
  which block the text batch.
- **macOS caveat (dev):** the `piper-tts` macOS wheel ships a broken espeak-ng-data
  path, so synthesis can't run natively on the Mac. It works on linux/amd64 (prod)
  and linux/arm64 — validated by building the real image and running the full chain
  (synthesize → Spaces → DB → Curator → Reader player) against the dev stack.
- **Deploy runbook (not yet run):** (1) apply `002_editorial_audio.sql` to prod
  (`editorials` gains the audio columns — additive, safe); (2) add `DO_SPACES_*` +
  `EDITORIAL_TTS_*` to `infra/.env`; (3) rebuild the editorial image (bakes the
  voices) + Curator + Reader; (4) backfill existing editorials with
  `run-editorial.sh --synthesize-missing`. The daily cron then covers new columns.
- Voice choice is config, not code — auditioning/swapping voices is an env change
  (to a voice also baked into the image).

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

Net: the daily cron (~36 columns) drops from ~40 min to ~10–15 min within a ≤2-core
slice, memory is flat (one resident model), and the one-time backfill runs safely in the
background newest-first (today's editions get audio first). Further speedups if ever
needed: `-low` voices, a higher `EDITORIAL_CPUS` off-hours window, or moving synthesis to
the 16 GB box (rejected option above).

### Compliance note (workspace policy)

This is AI-generated code destined for an internal system: it must be reviewed by a
human developer before production (review documented, reviewer owns it), run through
the approved application-security tooling, and follow OWASP secure-coding practice.
No secrets are committed — the Spaces credentials live only in `infra/.env`. Piper
is self-hosted OSS (MIT/GPL voices), which sidesteps the third-party-AI-vendor
approval question that ElevenLabs would have raised.
