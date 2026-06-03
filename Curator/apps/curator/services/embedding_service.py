"""Embedding service — OpenAI text-embedding-3-small.

Falls back to a deterministic pseudo-embedding (hash → 1536 floats) if
OPENAI_API_KEY is not set, so the clustering skill is testable offline.
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
