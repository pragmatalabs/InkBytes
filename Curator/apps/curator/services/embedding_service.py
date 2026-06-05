"""Embedding service — local Ollama (bge-m3) by default, OpenAI as fallback.

Two providers, one client: Ollama exposes an OpenAI-compatible /v1/embeddings
endpoint, so both paths use `AsyncOpenAI` and the same `embeddings.create(...)`
call — they differ only in `base_url` and `model`. See Curator ADR-0003.

  provider=ollama  → AsyncOpenAI(base_url=…/v1, api_key="ollama") · bge-m3, 1024d
  provider=openai  → AsyncOpenAI(api_key=OPENAI_API_KEY)          · 3-small, 1536d

If provider=openai and no OPENAI_API_KEY is set, falls back to a deterministic
pseudo-embedding (hash → N floats) so the pipeline is testable offline. Ollama
needs no key, so it is never in stub mode — if Ollama is unreachable it fails
loudly rather than silently degrading clustering.
"""
from __future__ import annotations

import hashlib
import logging

from core.config import EmbedCfg, PLACEHOLDER

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, cfg: EmbedCfg) -> None:
        self.cfg = cfg
        self._client = None
        self._stub_mode = False
        provider = (cfg.provider or "openai").lower()

        if provider == "ollama":
            from openai import AsyncOpenAI
            base_url = cfg.base_url or "http://localhost:11434/v1"
            # Ollama ignores the key, but the SDK requires a non-empty string.
            self._client = AsyncOpenAI(api_key="ollama", base_url=base_url)
            logger.info(
                "EmbeddingService using local Ollama at %s (model=%s, dims=%d)",
                base_url, cfg.model, cfg.dimensions,
            )
            return

        # provider=openai (hosted vendor) — with offline stub fallback.
        self._stub_mode = cfg.api_key in (PLACEHOLDER, "LOCAL_DEV_UNSET", "")
        if self._stub_mode:
            logger.warning("EmbeddingService running in STUB mode (no OPENAI_API_KEY)")
        else:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=cfg.api_key)

    async def embed(self, text: str) -> list[float]:
        if self._stub_mode:
            return _deterministic_pseudo_embedding(text, self.cfg.dimensions)
        resp = await self._client.embeddings.create(  # type: ignore[union-attr]
            model=self.cfg.model, input=text
        )
        return resp.data[0].embedding


def _deterministic_pseudo_embedding(text: str, dims: int) -> list[float]:
    """Hash the text into a `dims`-length float vector in [-1, 1].
    Deterministic; for offline dev only. NOT semantically meaningful."""
    digest = hashlib.sha512(text.encode("utf-8")).digest()
    # Expand the 64-byte digest by re-hashing chunks until we have enough.
    buf = bytearray()
    counter = 0
    while len(buf) < dims * 2:
        buf.extend(hashlib.sha512(digest + counter.to_bytes(4, "big")).digest())
        counter += 1
    out: list[float] = []
    for i in range(dims):
        n = int.from_bytes(buf[i * 2:i * 2 + 2], "big")
        out.append((n / 65535.0) * 2 - 1)  # map 0..65535 → -1..1
    return out
