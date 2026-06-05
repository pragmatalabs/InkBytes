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

Live reconfiguration (ADR-0004): the provider/model/base_url are admin-managed
via backoffice.curator_settings. The client is built ONCE per (provider, model,
base_url) signature, so a settings change must REBUILD it — `reconfigure()` does
that, with a dimension-probe guard so a model whose vectors don't fit the live
pgvector column width is never switched in (that would break every INSERT).
"""
from __future__ import annotations

import hashlib
import logging

from core.config import EmbedCfg, PLACEHOLDER

logger = logging.getLogger(__name__)


def _build_client(cfg: EmbedCfg):
    """Return (client, stub_mode) for a config. No probing, no side effects."""
    provider = (cfg.provider or "openai").lower()
    if provider == "ollama":
        from openai import AsyncOpenAI
        base_url = cfg.base_url or "http://localhost:11434/v1"
        # Ollama ignores the key, but the SDK requires a non-empty string.
        return AsyncOpenAI(api_key="ollama", base_url=base_url), False
    # provider=openai (hosted vendor) — with offline stub fallback.
    stub = cfg.api_key in (PLACEHOLDER, "LOCAL_DEV_UNSET", "")
    if stub:
        return None, True
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=cfg.api_key), False


def _signature(cfg: EmbedCfg) -> tuple[str, str, str | None]:
    return ((cfg.provider or "openai").lower(), cfg.model, cfg.base_url)


async def _embed_with(client, stub: bool, model: str, dims: int, text: str) -> list[float]:
    if stub:
        return _deterministic_pseudo_embedding(text, dims)
    resp = await client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding


class EmbeddingService:
    def __init__(self, cfg: EmbedCfg) -> None:
        self.cfg = cfg
        self._client, self._stub_mode = _build_client(cfg)
        self._signature = _signature(cfg)
        if (cfg.provider or "openai").lower() == "ollama":
            logger.info(
                "EmbeddingService using local Ollama at %s (model=%s, dims=%d)",
                cfg.base_url, cfg.model, cfg.dimensions,
            )
        elif self._stub_mode:
            logger.warning("EmbeddingService running in STUB mode (no OPENAI_API_KEY)")

    async def embed(self, text: str) -> list[float]:
        return await _embed_with(
            self._client, self._stub_mode, self.cfg.model, self.cfg.dimensions, text
        )

    async def reconfigure(self, cfg: EmbedCfg, expected_dims: int | None = None) -> dict:
        """Rebuild the client if (provider, model, base_url) changed.

        Returns a dict describing the outcome:
          {"changed": False}                          — nothing to do
          {"changed": True, "applied": True,  ...}    — switched; vectors now STALE
          {"changed": True, "applied": False, "reason": "dim_mismatch", ...}
                                                      — refused (would break inserts)

        The dimension-probe guard: before swapping, embed a probe with the
        CANDIDATE client and compare its width to `expected_dims` (the live
        pgvector column width). A mismatch means a vector-width migration +
        re-embed is required first — so we keep the current client untouched and
        report the block instead of silently emitting unstorable vectors.
        """
        new_sig = _signature(cfg)
        if new_sig == self._signature:
            self.cfg = cfg  # keep non-signature fields (e.g. api_key) fresh
            return {"changed": False, "applied": False}

        candidate, cand_stub = _build_client(cfg)
        probed = None
        if not cand_stub:
            try:
                probed = len(await _embed_with(candidate, cand_stub, cfg.model, cfg.dimensions, "dimension probe"))
            except Exception as e:  # noqa: BLE001 — surface as a non-apply, don't crash refresh
                logger.error("Embedding reconfigure probe failed for %s/%s: %s — keeping current embedder.",
                             cfg.provider, cfg.model, e)
                return {"changed": True, "applied": False, "reason": "probe_failed", "error": str(e)}

        if expected_dims is not None and probed is not None and probed != expected_dims:
            logger.error(
                "Embedding model %s/%s emits %d-d vectors but articles.embedding is %d-d. "
                "A vector-width migration + full re-embed is required before switching; "
                "NOT applying live. Keeping %s/%s.",
                cfg.provider, cfg.model, probed, expected_dims, *self._signature[:2],
            )
            return {"changed": True, "applied": False, "reason": "dim_mismatch",
                    "probed_dims": probed, "expected_dims": expected_dims}

        # Commit the swap.
        self._client, self._stub_mode = candidate, cand_stub
        self._signature, self.cfg = new_sig, cfg
        logger.warning(
            "Embedding provider/model switched to %s/%s. Existing vectors are now "
            "STALE (different vector space) — run a corpus re-embed.",
            cfg.provider, cfg.model,
        )
        return {"changed": True, "applied": True, "probed_dims": probed}


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
