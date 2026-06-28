"""ADR-0034 Tier 2 — license-clean generic cover images.

`pick_cover` chooses, for an event, a commercially-licensed *generic representation*
(never the source outlet's photo, never implying it depicts the real event):

  1. **Wikimedia / Wikidata P18** (preferred) — the canonical image for the event's
     top LOC/ORG entity (a place → its landmark/flag; an org → its HQ). Most relevant.
  2. **Openverse keyword** (fallback) — a CC0/PDM image keyed to the entity or theme.
  3. None → the Reader renders the owned procedural cover (Tier 1).

Commercial-use guardrails (InkBytes is paid):
  - Openverse: `license_type=commercial` + `license=cc0,pdm` (no attribution burden).
  - Wikimedia: accept CC0/PD/BY/BY-SA; **reject** NC/ND, `NonFree`, any `Restrictions`
    (trademark/personality/currency). Query commons.wikimedia.org (free-content only).
    Render attribution (Artist + license + url) for BY/BY-SA; CC0/PD need none.
  - Store license + attribution + source URL per image for provenance (neither source
    verifies license accuracy → keep the trail). Wikimedia requires a descriptive UA.
  - Prefer places/things over people (a person's photo adds publicity-rights concerns).
"""
from __future__ import annotations

import hashlib
import html
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OPENVERSE = "https://api.openverse.org/v1/images/"
_WIKIDATA  = "https://www.wikidata.org/w/api.php"
_COMMONS   = "https://commons.wikimedia.org/w/api.php"
_UA = "InkBytes/1.0 (https://inkbytes.org; news aggregator; covers; contact@inkbytes.org)"
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
            "url":         chosen["url"],
            "thumb":       chosen.get("thumbnail") or chosen["url"],
            "license":     chosen.get("license"),
            "license_url": chosen.get("license_url"),
            "attribution": None,   # cc0/pdm → no attribution required
            "source_url":  chosen.get("foreign_landing_url"),
            "provider":    "openverse",
            "query":       query,
        }
    except Exception as exc:  # fail-open → Reader falls back to the procedural cover
        logger.warning("cover: Openverse fetch failed for %r: %s", query, exc)
        return None
    finally:
        if own:
            await client.aclose()


# ── Wikimedia / Wikidata P18 entity-keyed path ────────────────────────────────

def _strip_html(s: str | None) -> str | None:
    """Wikimedia `Artist`/attribution fields are HTML — reduce to plain text."""
    if not s:
        return None
    txt = html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt or None


def _license_gate(ext: dict) -> tuple[str, bool] | None:
    """Return (license_short_name, attribution_required) if commercial-OK, else None.

    Accept CC0/PD (no attribution) and CC BY / BY-SA (attribution required). Reject
    NonCommercial/NoDerivatives, NonFree, and anything with Restrictions
    (trademark/personality/currency)."""
    def val(k: str) -> str:
        return str((ext.get(k) or {}).get("value") or "").strip()

    if val("NonFree") not in ("", "0", "False", "false"):
        return None
    if val("Restrictions"):
        return None
    name = val("LicenseShortName").lower()
    if not name:
        return None
    if "-nc" in name or "-nd" in name or "noncommercial" in name or "noderiv" in name:
        return None
    if "cc0" in name or "public domain" in name or name.startswith("pd"):
        return (val("LicenseShortName"), False)
    if "cc by" in name or "cc-by" in name:
        return (val("LicenseShortName"), True)
    return None  # unknown license → reject (conservative)


async def wikimedia_entity_cover(entity: str,
                                 client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Canonical Wikimedia Commons image for an entity (Wikidata P18), license-gated.
    Returns the provenance dict or None (no Q-id / no P18 / license rejected / error)."""
    try:
        r = await client.get(_WIKIDATA, params={
            "action": "wbsearchentities", "search": entity, "language": "en",
            "format": "json", "limit": "1"})
        hits = (r.json() or {}).get("search") or []
        if not hits:
            return None
        qid = hits[0]["id"]
        r = await client.get(_WIKIDATA, params={
            "action": "wbgetentities", "ids": qid, "props": "claims", "format": "json"})
        claims = (((r.json() or {}).get("entities") or {}).get(qid) or {}).get("claims") or {}
        p18 = claims.get("P18")
        if not p18:
            return None
        fname = p18[0]["mainsnak"]["datavalue"]["value"]
        r = await client.get(_COMMONS, params={
            "action": "query", "titles": f"File:{fname}", "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": "1200", "format": "json"})
        pages = ((r.json() or {}).get("query") or {}).get("pages") or {}
        info = (next(iter(pages.values()), {}) or {}).get("imageinfo") or [{}]
        info = info[0]
        gate = _license_gate(info.get("extmetadata") or {})
        if not gate:
            return None
        license_name, attr_required = gate
        url = info.get("thumburl") or info.get("url")
        if not url:
            return None
        return {
            "url":         url,
            "thumb":       url,
            "license":     license_name,
            "license_url": ((info.get("extmetadata") or {}).get("LicenseUrl") or {}).get("value"),
            "attribution": _strip_html(((info.get("extmetadata") or {}).get("Artist") or {}).get("value"))
                           if attr_required else None,
            "source_url":  info.get("descriptionurl"),
            "provider":    "wikimedia",
            "query":       entity,
        }
    except Exception as exc:
        logger.warning("cover: Wikimedia failed for %r: %s", entity, exc)
        return None


# ── Orchestrator ──────────────────────────────────────────────────────────────

async def pick_cover(theme: str | None, top_loc: str | None, top_org: str | None,
                     seed: str, client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Wikimedia entity-canonical (prefer places, then orgs) → Openverse keyword →
    None (procedural). Deterministic; fail-open at each step."""
    for ent in (top_loc, top_org):
        if ent and len(ent) >= 3:
            cov = await wikimedia_entity_cover(ent, client)
            if cov:
                return cov
    q = build_query(theme, top_loc or top_org)
    if q:
        return await fetch_cover(q, seed, client=client)
    return None
