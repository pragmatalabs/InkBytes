"""Per-entity Wikidata photo + description (ADR-0034 companion, entity map).

Resolves a PERSON name → a license-clean Wikimedia Commons portrait (Wikidata
P18) + a one-line description, reusing the cover agent's Commons/license flow
(`services/cover_image`). Two guards against the disambiguation trap (the
Proton→carmaker class of bug):

  1. **Human filter** — only accept a candidate whose Wikidata P31 (instance-of)
     includes Q5 (human). A person's name that also matches a company/place is
     rejected, so we never show a logo where a face belongs.
  2. **Context re-rank** — among candidates, prefer the one whose label +
     description overlaps the story context (same idea as the cover agent).

Returns a provenance dict (image + license + attribution + description) or None
(no human hit / no P18 / license rejected). The caller caches a None as
`blocked` so we don't re-query the same miss.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from services.cover_image import _COMMONS, _WIKIDATA, _license_gate, _strip_html

logger = logging.getLogger(__name__)
_HUMAN_QID = "Q5"


async def resolve_person(name: str, client: httpx.AsyncClient,
                         context: str = "") -> dict[str, Any] | None:
    try:
        r = await client.get(_WIKIDATA, params={
            "action": "wbsearchentities", "search": name, "language": "en",
            "format": "json", "limit": "7"})
        hits = (r.json() or {}).get("search") or []
        if not hits:
            return None

        ctx = set(re.findall(r"[a-z0-9]+", context.lower()))

        def _score(h: dict) -> int:
            words = set(re.findall(
                r"[a-z0-9]+",
                (h.get("label", "") + " " + (h.get("description") or "")).lower()))
            return len(words & ctx)

        # Context-first ordering; ties keep Wikidata prominence.
        order = sorted(range(len(hits)), key=lambda i: (-_score(hits[i]), i))

        # Try the best few candidates until one is a HUMAN with a P18 image.
        for i in order[:4]:
            qid = hits[i]["id"]
            r = await client.get(_WIKIDATA, params={
                "action": "wbgetentities", "ids": qid,
                "props": "claims|descriptions", "languages": "es|en", "format": "json"})
            ent = (((r.json() or {}).get("entities") or {}).get(qid) or {})
            claims = ent.get("claims") or {}

            # human filter — P31 must include Q5
            p31 = claims.get("P31") or []
            is_human = any(
                (((c.get("mainsnak") or {}).get("datavalue") or {})
                 .get("value") or {}).get("id") == _HUMAN_QID for c in p31)
            if not is_human:
                continue

            p18 = claims.get("P18")
            if not p18:
                continue
            fname = p18[0]["mainsnak"]["datavalue"]["value"]

            r = await client.get(_COMMONS, params={
                "action": "query", "titles": f"File:{fname}", "prop": "imageinfo",
                "iiprop": "url|extmetadata", "iiurlwidth": "400", "format": "json"})
            pages = ((r.json() or {}).get("query") or {}).get("pages") or {}
            info = ((next(iter(pages.values()), {}) or {}).get("imageinfo") or [{}])[0]
            gate = _license_gate(info.get("extmetadata") or {})
            if not gate:
                continue
            license_name, attr_required = gate
            url = info.get("thumburl") or info.get("url")
            if not url:
                continue

            descs = ent.get("descriptions") or {}
            description = ((descs.get("es") or {}).get("value")
                           or (descs.get("en") or {}).get("value"))
            return {
                "wikidata_qid": qid,
                "image_url":   info.get("url") or url,
                "thumb_url":   url,
                "license":     license_name,
                "license_url": ((info.get("extmetadata") or {}).get("LicenseUrl") or {}).get("value"),
                "attribution": _strip_html(((info.get("extmetadata") or {}).get("Artist") or {}).get("value"))
                               if attr_required else None,
                "source_url":  info.get("descriptionurl"),
                "description": description,
            }
        return None
    except Exception as exc:  # noqa: BLE001 — resolution must fail soft
        logger.warning("entity photo: Wikidata failed for %r: %s", name, exc)
        return None
