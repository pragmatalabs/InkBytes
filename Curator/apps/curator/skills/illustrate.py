"""Skill 4 — ILLUSTRATE (Phase 2 Scrapling agent).

Searches YouTube (DynamicFetcher — JS-rendered) and Bing Images
(StealthyFetcher — bot-detection bypass) for media that illustrates an
event's headline.  Each candidate is scored on three axes:

    source credibility  (0–0.40)  — domain trust tier
    image resolution    (0–0.35)  — pixel area relative to 1920×1080
    recency             (0–0.25)  — exponential decay, half-life = 48 h

The top MAX_RESULTS items are written to pages.media_rail as JSONB.

Failure modes are isolated: if one fetcher hangs or raises, the other
still contributes results.  An empty rail (both fail / nothing found) is
written as [] and is not an error — the Reader simply shows no rail.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import urllib.parse
from datetime import datetime, timezone
from typing import TypedDict

from services.database_service import DatabaseService

logger = logging.getLogger(__name__)


# ── Media item shape ──────────────────────────────────────────────────────────

class MediaItem(TypedDict):
    url: str            # canonical / full-res URL (click-through or direct)
    thumb_url: str      # thumbnail shown in the rail
    type: str           # "image" | "video"
    title: str
    source_domain: str
    published_at: str | None   # ISO-8601 UTC, or null
    width: int
    height: int
    score: float


# ── Scoring constants ─────────────────────────────────────────────────────────

# Domain → credibility score (0–0.40).  Anything unlisted gets 0.10.
_CRED: dict[str, float] = {
    "youtube.com":      0.40,
    "youtu.be":         0.40,
    "reuters.com":      0.38,
    "apnews.com":       0.38,
    "bbc.com":          0.36,
    "bbc.co.uk":        0.36,
    "nytimes.com":      0.34,
    "theguardian.com":  0.34,
    "washingtonpost.com": 0.34,
    "bloomberg.com":    0.33,
    "ft.com":           0.33,
    "cnn.com":          0.30,
    "nbcnews.com":      0.28,
    "foxnews.com":      0.25,
    "twitter.com":      0.15,
    "x.com":            0.15,
    "facebook.com":     0.12,
    "instagram.com":    0.12,
    "reddit.com":       0.12,
}

_CRED_DEFAULT   = 0.10
_MAX_PIXELS     = 1920 * 1080   # normalization reference (Full HD)
_RECENCY_HALF_H = 48.0          # score halves every 48 hours


def _credibility(domain: str) -> float:
    domain = domain.lower().removeprefix("www.")
    return _CRED.get(domain, _CRED_DEFAULT)


def _resolution_score(width: int, height: int) -> float:
    """0–0.35 based on pixel area, capped at 1920×1080."""
    if width <= 0 or height <= 0:
        return 0.0
    return min(0.35, (width * height) / _MAX_PIXELS * 0.35)


def _recency_score(published_at: str | None) -> float:
    """0–0.25 with exponential decay (half-life = _RECENCY_HALF_H)."""
    if not published_at:
        return 0.0
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return 0.25 * math.exp(-age_h / _RECENCY_HALF_H * math.log(2))
    except Exception:
        return 0.0


def _score(item: MediaItem) -> float:
    return (
        _credibility(item["source_domain"])
        + _resolution_score(item["width"], item["height"])
        + _recency_score(item.get("published_at"))
    )


# ── Search query helpers ──────────────────────────────────────────────────────

_STOP = frozenset(
    "a an the and but or for nor so yet both either neither "
    "in on at to of by as is was are were be been being "
    "it its this that these those with from".split()
)


def _search_query(headline: str, max_words: int = 7) -> str:
    """Extract the most meaningful words from a headline for a web search."""
    words = re.sub(r"[^\w\s-]", " ", headline).split()
    meaningful = [w for w in words if w.lower() not in _STOP and len(w) > 2]
    return " ".join(meaningful[:max_words]) or headline[:100]


def _yt_thumb(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


# ── Fetcher wrappers ──────────────────────────────────────────────────────────

async def _fetch_bing_images(query: str) -> list[MediaItem]:
    """Scrape Bing Images using StealthyFetcher (Camoufox anti-bot).

    Bing Images embeds per-result JSON in the `m` attribute of each
    `a.iusc` link:  {"murl": full_url, "turl": thumb_url, "t": title,
                      "imgw": width, "imgh": height, "purl": page_url}
    """
    try:
        from scrapling.fetchers import StealthyFetcher  # type: ignore[import]
    except ImportError:
        logger.warning("ILLUSTRATE: scrapling not installed — Bing skipped")
        return []

    url = (
        "https://www.bing.com/images/search?"
        + urllib.parse.urlencode({"q": query, "form": "HDRSC2", "first": "1"})
    )
    try:
        page = await StealthyFetcher.async_fetch(url, headless=True)
    except Exception as exc:
        logger.warning("ILLUSTRATE: Bing fetch failed — %s", exc)
        return []

    items: list[MediaItem] = []
    try:
        anchors = list(page.css("a.iusc"))
        for a in anchors[:20]:
            raw = (a.attrib or {}).get("m", "")
            if not raw:
                continue
            try:
                m = json.loads(raw)
            except json.JSONDecodeError:
                continue

            img_url   = m.get("murl", "")
            thumb_url = m.get("turl", img_url)
            # Clean Bing title: strip trailing " - YouTube" / " | Reuters" suffixes
            title = re.sub(r"\s*[-|]\s*(YouTube|Getty.*|Reuters.*|AP.*|BBC.*)$", "",
                           m.get("t", ""), flags=re.IGNORECASE)
            # Bing m-attr omits dimensions; we do get them from the img inside the anchor
            img_el = a.find("img")
            width  = int((img_el.attrib or {}).get("width",  0) if img_el else 0)
            height = int((img_el.attrib or {}).get("height", 0) if img_el else 0)
            page_url  = m.get("purl", img_url)

            if not img_url:
                continue

            try:
                domain = urllib.parse.urlparse(page_url).netloc or ""
            except Exception:
                domain = ""

            item: MediaItem = {
                "url":          img_url,
                "thumb_url":    thumb_url,
                "type":         "image",
                "title":        title[:200],
                "source_domain": domain.lower().removeprefix("www."),
                "published_at": None,
                "width":        width,
                "height":       height,
                "score":        0.0,
            }
            item["score"] = _score(item)
            items.append(item)
    except Exception as exc:
        logger.warning("ILLUSTRATE: Bing parse error — %s", exc)

    logger.debug("ILLUSTRATE: Bing returned %d raw items", len(items))
    return items


async def _fetch_youtube_videos(query: str) -> list[MediaItem]:
    """Scrape YouTube search using DynamicFetcher (Playwright JS execution).

    After JavaScript execution the DOM contains `ytd-video-renderer`
    elements.  We extract video IDs from watch-link hrefs and derive the
    thumbnail URL from the well-known ytimg CDN pattern.
    """
    try:
        from scrapling.fetchers import DynamicFetcher  # type: ignore[import]
    except ImportError:
        logger.warning("ILLUSTRATE: scrapling not installed — YouTube skipped")
        return []

    url = (
        "https://www.youtube.com/results?"
        + urllib.parse.urlencode({"search_query": query})
    )
    try:
        page = await DynamicFetcher.async_fetch(url, headless=True)
    except Exception as exc:
        logger.warning("ILLUSTRATE: YouTube fetch failed — %s", exc)
        return []

    items: list[MediaItem] = []
    seen_ids: set[str] = set()

    try:
        # YouTube title links have id="video-title" or class containing
        # "ytd-video-renderer"; the thumbnail anchor (id="thumbnail") has
        # empty text.  Prefer id="video-title", fall back to any watch link
        # with non-empty text content.
        title_links = list(page.css("a#video-title"))
        if not title_links:
            title_links = [
                a for a in page.css("a[href*='/watch?v=']")
                if (a.text or "").strip()
            ]

        for a in title_links[:15]:
            href = (a.attrib or {}).get("href", "")
            m = re.search(r"/watch\?v=([A-Za-z0-9_-]{11})", href)
            if not m:
                continue
            vid_id = m.group(1)
            if vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)

            title = (
                (a.text or "").strip()
                or (a.attrib or {}).get("title", "")
                or (a.attrib or {}).get("aria-label", "").removeprefix("Watch ")
            )[:200]

            item: MediaItem = {
                "url":           f"https://www.youtube.com/watch?v={vid_id}",
                "thumb_url":     _yt_thumb(vid_id),
                "type":          "video",
                "title":         title,
                "source_domain": "youtube.com",
                "published_at":  None,   # YouTube search doesn't expose exact date
                "width":         480,
                "height":        360,
                "score":         0.0,
            }
            item["score"] = _score(item)
            items.append(item)

            if len(items) >= 10:
                break

    except Exception as exc:
        logger.warning("ILLUSTRATE: YouTube parse error — %s", exc)

    logger.debug("ILLUSTRATE: YouTube returned %d raw items", len(items))
    return items


# ── Skill ─────────────────────────────────────────────────────────────────────

class IllustrateSkill:
    """Skill 4 — fetch + score + persist media rail for a published page."""

    name = "illustrate"
    MAX_RESULTS   = 6      # items to keep in pages.media_rail
    FETCH_TIMEOUT = 30.0   # seconds per fetcher (scrapling can be slow)

    def __init__(self, db: DatabaseService) -> None:
        self.db = db

    async def run(self, event_id: str, headline: str) -> list[MediaItem]:
        """Fetch images and videos, rank by score, write to pages.media_rail.

        Both fetchers run concurrently.  Either can fail without affecting
        the other.  An empty result is valid and is persisted as [].
        """
        query = _search_query(headline)
        logger.info("ILLUSTRATE %s | query=%r", event_id, query)

        bing_task = asyncio.create_task(
            asyncio.wait_for(_fetch_bing_images(query), self.FETCH_TIMEOUT)
        )
        yt_task = asyncio.create_task(
            asyncio.wait_for(_fetch_youtube_videos(query), self.FETCH_TIMEOUT)
        )

        raw_results = await asyncio.gather(bing_task, yt_task, return_exceptions=True)

        candidates: list[MediaItem] = []
        for result in raw_results:
            if isinstance(result, list):
                candidates.extend(result)
            elif isinstance(result, Exception):
                logger.warning("ILLUSTRATE fetcher error: %s", result)

        # Deduplicate by URL, sort by score descending, take top N
        seen: set[str] = set()
        rail: list[MediaItem] = []
        for item in sorted(candidates, key=lambda x: x["score"], reverse=True):
            if item["url"] not in seen:
                seen.add(item["url"])
                rail.append(item)
            if len(rail) >= self.MAX_RESULTS:
                break

        await self.db.write_media_rail(event_id, rail)  # type: ignore[arg-type]
        logger.info(
            "ILLUSTRATE %s → %d items (bing=%s, yt=%s)",
            event_id, len(rail),
            len(raw_results[0]) if isinstance(raw_results[0], list) else "err",
            len(raw_results[1]) if isinstance(raw_results[1], list) else "err",
        )
        return rail
