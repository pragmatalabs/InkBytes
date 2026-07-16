"""InkBytes TTS microservice (ADR-0011) — Piper or Kokoro synthesis over HTTP.

Runs on the 16 GB box (Hostinger), where there's RAM headroom for the models — so
the small shared droplet never synthesizes (it thrashed into swap when it did). The
Editorial batch POSTs already-speakable plain text here and gets back an MP3, which
it uploads to Spaces.

  POST /synthesize  {text, lang, voice?}  + header X-TTS-Token: <secret>  -> audio/mpeg
                    (response header X-TTS-Voice = the engine/voice actually used)
  GET  /healthz

Engine via TTS_ENGINE (default "piper"):
  - piper   — fast CPU neural TTS, one fixed voice per language (models baked in).
  - kokoro  — higher-quality PyTorch TTS; picks a RANDOM voice per request from a
              per-language POOL (mix of male + female) unless `voice` is given.

Models loaded once (reused). Synthesis serialized (one at a time) — the caller is
sequential and one synth already fills several cores.
"""
from __future__ import annotations

import logging
import os
import random
import shutil
import subprocess
import tempfile
import threading
import wave

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tts-server")

ENGINE = os.getenv("TTS_ENGINE", "piper").lower()
BITRATE = os.getenv("TTS_BITRATE", "64k")

# Kokoro is PyTorch on CPU and defaults to a single thread in-container — let it use
# the cores we grant (TORCH_NUM_THREADS, matched to --cpus in run.sh). OMP/MKL are
# also set in the env for the intra-op pools.
if ENGINE == "kokoro":
    _threads = int(os.getenv("TORCH_NUM_THREADS", "0"))
    if _threads > 0:
        try:
            import torch
            torch.set_num_threads(_threads)
        except Exception:  # noqa: BLE001
            pass
SECRET = os.getenv("TTS_SECRET", "")
MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", "20000"))

# ── Piper config ──────────────────────────────────────────────────────────────
PIPER_VOICES = {
    "en": os.getenv("TTS_VOICE_EN", "en_US-ryan-high"),
    "es": os.getenv("TTS_VOICE_ES", "es_MX-claude-high"),
}
PIPER_MODELS_DIR = os.getenv("TTS_MODELS_DIR", "/models")

# ── Kokoro config ─────────────────────────────────────────────────────────────
# Per-language voice POOL (mix of female af_/ef_ + male am_/em_); a random one is
# chosen per column so the narrator varies. Override via KOKORO_VOICES_EN/_ES (csv).
KOKORO_POOLS = {
    "en": [v for v in os.getenv(
        "KOKORO_VOICES_EN", "af_heart,af_bella,am_michael,am_fenrir").split(",") if v],
    "es": [v for v in os.getenv(
        "KOKORO_VOICES_ES", "ef_dora,em_alex").split(",") if v],
}
_KOKORO_LANG = {"en": "a", "es": "e"}   # our lang → Kokoro lang_code

_ffmpeg = shutil.which("ffmpeg")
_load_lock = threading.Lock()      # guards model/pipeline caches
_synth_lock = threading.Lock()     # serializes synthesis
_piper_voices: dict[str, object] = {}
_kokoro_pipes: dict[str, object] = {}
_PiperVoice = None


def _to_mp3(wav_path: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as out:
        subprocess.run(
            [_ffmpeg, "-y", "-loglevel", "error", "-i", wav_path,
             "-ac", "1", "-b:a", BITRATE, out.name],
            check=True, capture_output=True, timeout=180)
        with open(out.name, "rb") as fh:
            return fh.read()


# ── Piper ───────────────────────────────────────────────────────────────────
def _piper_voice(voice: str):
    global _PiperVoice
    if _PiperVoice is None:
        from piper import PiperVoice
        _PiperVoice = PiperVoice
    with _load_lock:
        v = _piper_voices.get(voice)
        if v is None:
            path = os.path.join(PIPER_MODELS_DIR, f"{voice}.onnx")
            if not os.path.exists(path):
                raise HTTPException(500, f"voice model missing: {voice}")
            v = _PiperVoice.load(path)
            _piper_voices[voice] = v
            log.info("loaded Piper voice %s", voice)
        return v


def _piper_synth(text: str, voice: str) -> bytes:
    v = _piper_voice(voice)
    with _synth_lock, tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "o.wav")
        with wave.open(wav, "wb") as wf:
            v.synthesize_wav(text, wf)
        return _to_mp3(wav)


# ── Kokoro ──────────────────────────────────────────────────────────────────
def _kokoro_pipe(lang: str):
    lc = _KOKORO_LANG.get(lang)
    if not lc:
        raise HTTPException(400, f"no kokoro lang for {lang!r}")
    from kokoro import KPipeline
    with _load_lock:
        p = _kokoro_pipes.get(lc)
        if p is None:
            p = KPipeline(lang_code=lc)
            _kokoro_pipes[lc] = p
            log.info("loaded Kokoro pipeline lang_code=%s", lc)
        return p


def _kokoro_synth(text: str, lang: str, voice: str) -> bytes:
    import numpy as np
    import soundfile as sf
    p = _kokoro_pipe(lang)
    with _synth_lock, tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "o.wav")
        chunks = [a for _, _, a in p(text, voice=voice)]
        if not chunks:
            raise HTTPException(500, "kokoro produced no audio")
        sf.write(wav, np.concatenate(chunks), 24000)
        return _to_mp3(wav)


app = FastAPI(title="InkBytes TTS", docs_url=None, redoc_url=None)


class SynthReq(BaseModel):
    text: str
    lang: str = "es"
    voice: str | None = None   # override; else engine default / random pool pick


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "engine": ENGINE, "ffmpeg": bool(_ffmpeg),
            "piper_voices": PIPER_VOICES, "kokoro_pools": KOKORO_POOLS}


@app.post("/synthesize")
def synthesize(req: SynthReq, x_tts_token: str = Header(default="")) -> Response:
    if not SECRET or x_tts_token != SECRET:
        raise HTTPException(401, "unauthorized")
    if not _ffmpeg:
        raise HTTPException(500, "ffmpeg unavailable")
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "empty text")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    if ENGINE == "kokoro":
        pool = KOKORO_POOLS.get(req.lang) or []
        voice = req.voice or (random.choice(pool) if pool else None)
        if not voice:
            raise HTTPException(400, f"no kokoro voice for lang {req.lang!r}")
        mp3 = _kokoro_synth(text, req.lang, voice)
    else:
        voice = req.voice or PIPER_VOICES.get(req.lang)
        if not voice:
            raise HTTPException(400, f"no piper voice for lang {req.lang!r}")
        mp3 = _piper_synth(text, voice)

    used = f"{ENGINE}/{voice}"
    log.info("synthesized %s [%s]: %d chars -> %d KB", req.lang, used, len(text), len(mp3) // 1024)
    return Response(content=mp3, media_type="audio/mpeg", headers={"X-TTS-Voice": used})
