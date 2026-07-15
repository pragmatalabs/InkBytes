"""Self-hosted text-to-speech for editorial columns (ADR-0011).

Piper (a fast, CPU-only neural TTS) synthesizes a column to WAV; ffmpeg transcodes
to a small mono MP3. Zero per-character cost — the same local-first decision as
bge-m3 embeddings (Curator ADR-0003), no external voice vendor.

One voice per language, configured in `TtsCfg.voices` and baked into the image
(`models_dir`). The Piper CLI is invoked as a subprocess (stable across the
package's Python-API churn); it reads plain text on stdin and writes a WAV.

`available()` reports whether the binaries + the language's voice model are present
so the caller can skip cleanly (best-effort — TTS never blocks text generation).
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile

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
        self._piper = shutil.which("piper")
        self._ffmpeg = shutil.which("ffmpeg")

    def voice_id(self, language: str) -> str | None:
        return self.cfg.voices.get(language)

    def _model_path(self, language: str) -> str | None:
        vid = self.voice_id(language)
        if not vid:
            return None
        path = os.path.join(self.cfg.models_dir, f"{vid}.onnx")
        return path if os.path.exists(path) else None

    def available(self, language: str) -> bool:
        """Everything present to synthesize this language? (binaries + voice)."""
        if not self.cfg.enabled:
            return False
        if not self._piper or not self._ffmpeg:
            logger.warning("TTS unavailable: piper=%s ffmpeg=%s",
                           bool(self._piper), bool(self._ffmpeg))
            return False
        if not self._model_path(language):
            logger.warning("TTS voice model missing for %s (%s) in %s",
                           language, self.voice_id(language), self.cfg.models_dir)
            return False
        return True

    def synthesize(self, text: str, language: str) -> bytes:
        """text → MP3 bytes. Assumes available(language) is True. Raises on failure
        (the caller wraps it so a synth failure never aborts the batch)."""
        model = self._model_path(language)
        if not model:
            raise RuntimeError(f"no voice model for {language}")
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, "out.wav")
            mp3 = os.path.join(tmp, "out.mp3")
            cfg_json = model + ".json"
            piper_cmd = [self._piper, "--model", model, "--output_file", wav]
            if os.path.exists(cfg_json):
                piper_cmd += ["--config", cfg_json]
            subprocess.run(piper_cmd, input=text.encode("utf-8"),
                           check=True, capture_output=True, timeout=600)
            subprocess.run(
                [self._ffmpeg, "-y", "-loglevel", "error", "-i", wav,
                 "-ac", "1", "-b:a", self.cfg.bitrate, mp3],
                check=True, capture_output=True, timeout=120)
            with open(mp3, "rb") as fh:
                return fh.read()
