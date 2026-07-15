"""InkBytes TTS microservice (ADR-0011) — Piper synthesis over HTTP.

Runs on the 16 GB box (Hostinger), where there's RAM headroom for onnxruntime —
so the small shared droplet never synthesizes (it thrashed into swap when it did).
The Editorial batch on the droplet POSTs already-speakable plain text here and gets
back an MP3, which it then uploads to Spaces.

  POST /synthesize   {text, lang}  + header X-TTS-Token: <secret>  -> audio/mpeg
  GET  /healthz

Voices are baked into the image and loaded ONCE (reused across requests). Synthesis
is serialized (one at a time) — the caller is sequential and one synth already fills
several cores, so this keeps a shared onnxruntime session safe without gain lost.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading
import wave

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tts-server")

VOICES = {   # language → Piper voice id (models baked into the image; both
             # -high and -medium are baked, so you can A/B via TTS_VOICE_EN/_ES)
    "en": os.getenv("TTS_VOICE_EN", "en_US-ryan-high"),
    "es": os.getenv("TTS_VOICE_ES", "es_MX-claude-high"),
}
MODELS_DIR = os.getenv("TTS_MODELS_DIR", "/models")
BITRATE = os.getenv("TTS_BITRATE", "64k")
SECRET = os.getenv("TTS_SECRET", "")
MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", "20000"))

_ffmpeg = shutil.which("ffmpeg")
_voices: dict[str, object] = {}
_load_lock = threading.Lock()     # guards the voice cache
_synth_lock = threading.Lock()    # serializes synthesis (shared onnxruntime session)
_PiperVoice = None


def _voice(lang: str):
    global _PiperVoice
    if _PiperVoice is None:
        from piper import PiperVoice
        _PiperVoice = PiperVoice
    with _load_lock:
        v = _voices.get(lang)
        if v is None:
            vid = VOICES.get(lang)
            if not vid:
                raise HTTPException(400, f"no voice configured for lang {lang!r}")
            path = os.path.join(MODELS_DIR, f"{vid}.onnx")
            if not os.path.exists(path):
                raise HTTPException(500, f"voice model missing: {vid}")
            v = _PiperVoice.load(path)
            _voices[lang] = v
            log.info("loaded Piper voice %s (%s)", vid, lang)
        return v


def _synth(text: str, lang: str) -> bytes:
    voice = _voice(lang)
    with _synth_lock, tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "o.wav")
        mp3 = os.path.join(tmp, "o.mp3")
        with wave.open(wav, "wb") as wf:
            voice.synthesize_wav(text, wf)
        subprocess.run(
            [_ffmpeg, "-y", "-loglevel", "error", "-i", wav,
             "-ac", "1", "-b:a", BITRATE, mp3],
            check=True, capture_output=True, timeout=180)
        with open(mp3, "rb") as fh:
            return fh.read()


app = FastAPI(title="InkBytes TTS", docs_url=None, redoc_url=None)


class SynthReq(BaseModel):
    text: str
    lang: str = "es"


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "voices": VOICES, "ffmpeg": bool(_ffmpeg)}


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
    mp3 = _synth(text, req.lang)
    log.info("synthesized %s: %d chars -> %d KB", req.lang, len(text), len(mp3) // 1024)
    return Response(content=mp3, media_type="audio/mpeg")
