# Editorial — Service Briefing

> *Daily per-theme editorial columns. Separate service (ADR-0008), NOT a Curator skill.*
> *Status: Phase 1 scaffold · Last updated: 2026-06-28*

## What this is

Editorial consumes Curator's **published event pages** and produces one **~450–600
word opinionated column per theme/day** in a named persona voice (`La Mesa` for
politics, `El Balance` for business, …), citing events inline as `[n]`. It's the
"vertical curator persona" — something no aggregator has — and the **data factory**
for the Phase-2 distilled editorial SLM (every row stores its input + prompt).

It is deliberately separate from Curator (different cadence — nightly batch vs
continuous; different LLM needs; opinion vs neutral synthesis). See
[`docs/adr/0008-editorial-service-llm-selection.md`](../docs/adr/0008-editorial-service-llm-selection.md).

## Layout
```
Editorial/apps/editorial/
  main.py                 ← CLI: --generate [--theme X] [--lang es] [--date Y] [--dry-run]
                             | --synthesize-missing [--audio-limit N]  (backfill TTS)
  core/config.py          ← YAML + env overlay (provider-pluggable LLM; TTS; Spaces)
  core/application.py     ← orchestrator: gather → gate → render persona → LLM → store → speak
  services/db.py          ← asyncpg; reads pages/events, writes editorials, applies migration
  services/llm.py         ← ollama|deepseek → OpenAI-compatible; anthropic → native
  services/tts.py         ← ADR-0011: Piper (CPU) → ffmpeg → MP3; markdown→speakable
  services/storage.py     ← ADR-0011: boto3 → DO Spaces (public-read), returns public URL
  personas.py             ← theme → (key, reader display name, mission)
  prompts/editorial.md    ← persona prompt template (interim single-voice)
  prompts/personas-spec.md ← ADR-0010 method-persona ROSTERS (150; 10/column;
                             method NOT identity — journalist names are internal
                             routing refs, never shown to readers or imitated)
  db/migrations/001_editorials.sql · 002_editorial_audio.sql (audio_url etc.)
  env.example.yaml · requirements.txt · Dockerfile (bakes ffmpeg + Piper voices)
```

## Audio — self-hosted TTS (ADR-0011)

Each column is voiced **once** in EN + ES by **Piper** (CPU neural TTS, $0/char —
the local-first call, like bge-m3), stored public-read in DO Spaces, URL on
`editorials.audio_url`; the Reader `/outlook` page plays it. Best-effort: a TTS or
upload failure never blocks the text batch. Voices baked into the image:
`en_US-ryan-medium` + `es_MX-ald-medium` (override via `EDITORIAL_TTS_VOICE_EN/_ES`).
`tts.py` loads each voice **once** (Piper Python API) — NOT the CLI per clip, which
reloaded the model every call and thrashed the shared droplet (load ~55, ADR-0011
"Throughput"). Synthesis is decoupled into `_synthesize_batch` after the text loop,
CPU-capped by `run-editorial.sh` (`--cpus`, default 2.0); `tts.concurrency` default 1
(onnxruntime fills the cap per synth). Daily run ~10–15 min, never starves the box.
`--synthesize-missing` backfills old rows. ⚠️ Piper's macOS wheel can't synthesize —
test via the Linux image (works amd64 + arm64).
⚠️ The `piper-tts` **macOS** wheel can't synthesize (broken espeak-data path) —
build/run the Linux image (works on amd64 + arm64) to test locally.

## Run
```bash
cd Editorial/apps/editorial
DATABASE_URL=postgresql://... python main.py --config env.yaml --generate --dry-run
# real run (writes editorials): drop --dry-run
```

## Model (ADR-0008 bake-off)
**~12B is the quality floor** for publishable Spanish editorial prose (gemma4 passed;
4B-class fail). Dev: `ollama`+gemma4 (Mac). Prod: `ollama`+gemma4 on the Hostinger box
(16 GB) or `deepseek` fallback — set `EDITORIAL_LLM_PROVIDER`/`_BASE_URL`/`_MODEL`.

## Phase 1 status / next steps
- [x] Scaffold: config, db, llm, personas, prompt, orchestrator, CLI, migration
- [ ] Validate generation quality on real prod data (dry-run on the droplet vs gemma4/DeepSeek)
- [ ] Reader surface: per-theme "Editorial" card/section + an API endpoint
- [ ] Daily cron (quiet hour) + Dockerfile + compose entry
- [ ] **ADR-0010: wire method-persona selection** — load `personas-spec.md` rosters,
      select by reporting-problem, Global Editorial Policy preamble, store method label
- [ ] Phase 2 (SLM): bulk-distill the `editorials` rows → LoRA a 2–3B → GGUF on Hostinger
```
