"""ADR-0034 Tier 2 — license-clean generic cover images (Openverse).

Picks a deterministic, commercially-licensed, generic image for an event keyed to
its top LOC/ORG entity (a place → its landmark) or, failing that, its theme (crime
→ courthouse, business → trading floor). Strictly a *generic representation* of the
story, never the source outlet's photo and never implying it depicts the real event.

Guardrails (InkBytes is paid):
  - `license_type=commercial` (excludes all NonCommercial/NC).
  - Default `license=cc0,pdm` → public-domain-equivalent, **no attribution
    obligation** (simplest for automated covers; by/by-sa with attribution is a
    later enhancement).
  - Store license + source URL per image for provenance (Openverse does not verify
    license accuracy).
Falls back to None → the Reader shows the owned procedural cover (Tier 1).
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OPENVERSE = "https://api.openverse.org/v1/images/"
_UA = "InkBytes/1.0 (https://inkbytes.org; news aggregator; covers)"
_CANDIDATES = 8        # top-N to pick from (deterministic by event seed)
_TIMEOUT = 20.0

# theme → a generic, non-event-specific concept query (clearly illustrative)
_THEME_QUERY: dict[str, str] = {
    "politics":      "parliament government building",
    "business":      "stock exchange trading floor",
    "technology":    "data center servers",
    "sports":        "stadium",
    "health":        "hospital",
    "environment":   "landscape nature",
    "culture":       "museum gallery",
    "world":         "world map globe",
    "science":       "laboratory research",
    "entertainment": "concert stage",
    "crime":         "courthouse",
    "education":     "university campus",
    "lifestyle":     "city street",
    "religion":      "cathedral temple",
    "disaster":      "emergency response",
}


def build_query(theme: str | None, top_entity: str | None) -> str | None:
    """Prefer the event's top LOC/ORG entity (a place → its landmark/skyline);
    else the theme's generic concept. None when we have neither."""
    if top_entity and len(top_entity) >= 3:
        return top_entity
    if theme:
        return _THEME_QUERY.get(theme.lower())
    return None


def _pick(results: list[dict], seed: str) -> dict | None:
    """Deterministic pick from the candidate pool so the same story keeps the same
    image across re-fetches (seed = event id)."""
    pool = results[:_CANDIDATES]
    if not pool:
        return None
    h = int(hashlib.sha1(seed.encode()).hexdigest(), 16)
    return pool[h % len(pool)]


async def fetch_cover(query: str, seed: str,
                      client: httpx.AsyncClient | None = None) -> dict[str, Any] | None:
    """Query Openverse for a commercial CC0/PDM image; return a provenance dict
    {url, thumb, license, source_url, provider, query} or None."""
    params = {
        "q": query,
        "license_type": "commercial",
        "license": "cc0,pdm",
        "size": "large",
        "mature": "false",
        "page_size": str(_CANDIDATES),
    }
    own = client is None
    client = client or httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _UA})
    try:
        r = await client.get(_OPENVERSE, params=params, headers={"User-Agent": _UA})
        if r.status_code != 200:
            logger.warning("cover: Openverse %s for %r", r.status_code, query)
            return None
        results = (r.json() or {}).get("results") or []
        chosen = _pick(results, seed)
        if not chosen or not chosen.get("url"):
            return None
        return {
            "url":        chosen["url"],
            "thumb":      chosen.get("thumbnail") or chosen["url"],
            "license":    chosen.get("license"),
            "source_url": chosen.get("foreign_landing_url"),
            "provider":   "openverse",
            "query":      query,
        }
    except Exception as exc:  # fail-open → Reader falls back to the procedural cover
        logger.warning("cover: Openverse fetch failed for %r: %s", query, exc)
        return None
    finally:
        if own:
            await client.aclose()
