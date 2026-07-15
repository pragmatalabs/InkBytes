"""Self-hosted text-to-speech for editorial columns (ADR-0011).

Piper (a fast, CPU-only neural TTS) synthesizes a column to WAV; ffmpeg transcodes
to a small mono MP3. Zero per-character cost — the same local-first decision as
bge-m3 embeddings (Curator ADR-0003), no external voice vendor.

Each voice model is loaded **once** (Piper Python API) and reused across every clip
of that language. The earlier CLI-subprocess-per-clip approach reloaded the ~60 MB
model on every call, which churned CPU + memory hard enough to spike the shared
droplet's load — see ADR-0011 "Throughput". Loading once fixes that at the source.

onnxruntime uses all cores by default; the container is CPU-capped by
run-editorial.sh (--cpus), so a batch can't starve the live stack. `available()`
reports whether ffmpeg + the voice model + the piper import are all present so the
caller can skip cleanly (best-effort — TTS never blocks text generation).

⚠️ The piper-tts macOS wheel can't synthesize (its espeakbridge ignores the runtime
data path). It works on Linux (amd64 + arm64), which is all prod runs.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import wave

from core.config import TtsCfg

logger = logging.getLogger(__name__)

# Markdown → speakable plain text. Order matters: strip links/citations before
# punctuation. We keep sentence punctuation (Piper prosodies on it) and drop the
# rest of the markup that would otherwise be mispronounced.
_CITATION = re.compile(r"`?\[(\d{1,2})\]`?")            # [3] citation markers → gone
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")          # [text](url) → text
_MD_IMG = re.compile(r"!\[[^\]]*\]\([^)]+\)")            # ![alt](url) → gone
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)  # ## Heading → Heading
_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_BULLET = re.compile(r"^\s{0,3}[-*+]\s+", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*{1,3}|_{1,3}|`+)")           # **bold** _em_ `code` markers
_MULTI_NL = re.compile(r"\n{3,}")


def to_speakable(headline: str, body_md: str) -> str:
    """Flatten a headline + markdown body into clean prose for TTS."""
    text = f"{headline.strip()}.\n\n{body_md.strip()}"
    text = _MD_IMG.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _CITATION.sub("", text)
    text = _HEADING.sub("", text)
    text = _BLOCKQUOTE.sub("", text)
    text = _BULLET.sub("", text)
    text = _EMPHASIS.sub("", text)
    text = _MULTI_NL.sub("\n\n", text)
    # tidy artefacts left by removed markers: space-before-punctuation and runs
    text = re.sub(r"[ \t]+([.,;:!?…])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


class Tts:
    def __init__(self, cfg: TtsCfg) -> None:
        self.cfg = cfg
        self._ffmpeg = shutil.which("ffmpeg")
        self._PiperVoice = None            # lazy import (linux-only synthesis)
        self._voices: dict[str, object] = {}   # language → loaded PiperVoice (once)
        self._lock = threading.Lock()      # guards the voice cache across worker threads

    def voice_id(self, language: str) -> str | None:
        return self.cfg.voices.get(language)

    def _model_path(self, language: str) -> str | None:
        vid = self.voice_id(language)
        if not vid:
            return None
        path = os.path.join(self.cfg.models_dir, f"{vid}.onnx")
        return path if os.path.exists(path) else None

    def available(self, language: str) -> bool:
        """Everything present to synthesize this language? (ffmpeg + voice + piper)."""
        if not self.cfg.enabled:
            return False
        if not self._ffmpeg:
            logger.warning("TTS unavailable: ffmpeg not found")
            return False
        if not self._model_path(language):
            logger.warning("TTS voice model missing for %s (%s) in %s",
                           language, self.voice_id(language), self.cfg.models_dir)
            return False
        if self._PiperVoice is None:
            try:
                from piper import PiperVoice
                self._PiperVoice = PiperVoice
            except Exception as e:  # noqa: BLE001 — degrade cleanly (e.g. macOS dev)
                logger.warning("TTS unavailable: piper import failed: %s", e)
                return False
        return True

    def _voice(self, language: str):
        """Loaded PiperVoice for the language — loaded once, then cached/reused."""
        with self._lock:
            v = self._voices.get(language)
            if v is None:
                model = self._model_path(language)
                v = self._PiperVoice.load(model)   # finds the sibling .onnx.json
                self._voices[language] = v
                logger.info("loaded Piper voice %s (%s)", self.voice_id(language), language)
            return v

    def synthesize(self, text: str, language: str) -> bytes:
        """text → MP3 bytes using the cached voice. Assumes available(language).
        Raises on failure (the caller wraps it so a synth failure never aborts a batch)."""
        voice = self._voice(language)
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, "out.wav")
            mp3 = os.path.join(tmp, "out.mp3")
            with wave.open(wav, "wb") as wf:
                voice.synthesize_wav(text, wf)
            subprocess.run(
                [self._ffmpeg, "-y", "-loglevel", "error", "-i", wav,
                 "-ac", "1", "-b:a", self.cfg.bitrate, mp3],
                check=True, capture_output=True, timeout=120)
            with open(mp3, "rb") as fh:
                return fh.read()
