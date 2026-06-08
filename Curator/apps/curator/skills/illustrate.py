"""Skill 4 — ILLUSTRATE.

Searches YouTube (Playwright headless) for videos that illustrate an event's
headline.  Images are intentionally excluded — the media rail shows only
videos (YouTube links and, in future, direct outlet embeds).

Each candidate is scored on three axes:

    source credibility  (0–0.40)  — domain trust tier
    video resolution    (0–0.35)  — proxy via pixel area (YouTube defaults)
    recency             (0–0.25)  — exponential decay, half-life = 48 h

The top MAX_RESULTS items are written to pages.media_rail as JSONB.

An empty rail (fetch fails / nothing found) is written as [] and is not an
error — the Reader simply shows no rail.

Implementation note — browser launch:
  Scrapling's StealthyFetcher/DynamicFetcher always set channel='chromium'
  when building _browser_options.  On Docker (DO droplet) that channel lookup
  crashes with SIGTRAP even with seccomp:unconfined.  We bypass Scrapling's
  wrapper entirely and use the Playwright async API directly, which omits
  `channel` and launches the bundled Chromium without issues (ADR-0011).
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


# ── Domain blocklist ─────────────────────────────────────────────────────────
# These domains are never useful as news illustrations.  Items whose
# source_domain matches (exact or subdomain) are dropped before scoring.

_BLOCKED_DOMAINS: frozenset[str] = frozenset({
    # Educational / infographic / diagram sites
    "wikipedia.org", "wikimedia.org", "commons.wikimedia.org",
    "slideshare.net", "academia.edu", "researchgate.net", "scribd.com",
    "brainly.com", "brainly.com.br", "brainly.lat",
    "quora.com", "khanacademy.org", "study.com", "thoughtco.com",
    "mundoeducacao.uol.com.br", "brasilescola.uol.com.br",
    "coladaweb.com", "infoescola.com", "todoestudo.com.br",
    "educacao.uol.com.br", "sobiologia.com.br", "biomania.com.br",
    "resumoescolar.com.br", "estudokids.com.br",
    # Stock photo / watermarked
    "shutterstock.com", "gettyimages.com", "gettyimages.es",
    "gettyimages.com.br", "istock.com", "istockphoto.com",
    "dreamstime.com", "alamy.com", "123rf.com", "depositphotos.com",
    "stockfresh.com", "bigstockphoto.com",
    # Social / aggregator noise
    "pinterest.com", "pinterest.co.uk", "pinterest.es", "pinterest.com.br",
    "tumblr.com", "deviantart.com", "flickr.com",
})


def _is_blocked(domain: str) -> bool:
    """Return True if the domain is on the blocklist (exact or subdomain match)."""
    d = domain.lower().removeprefix("www.")
    if d in _BLOCKED_DOMAINS:
        return True
    # Subdomain check: e.g. "cdn.shutterstock.com" → matches "shutterstock.com"
    return any(d.endswith(f".{b}") for b in _BLOCKED_DOMAINS)


def _is_relevant(item: "MediaItem", query_words: frozenset[str]) -> bool:
    """Relevance gate: credible news sources are trusted unconditionally; unknown
    domains must share at least one meaningful keyword with the search query.

    This prevents infographic/diagram images (e.g. chemistry lessons) from
    appearing in news media rails simply because they're large and high-scoring.
    """
    if _credibility(item["source_domain"]) >= 0.25:
        # Reuters, AP, BBC, NYT, Guardian, WaPo, Bloomberg, FT, CNN, NBC …
        return True
    if not item.get("title"):
        return False
    title_words = frozenset(
        w for w in re.sub(r"[^\w]", " ", item["title"].lower()).split()
        if w not in _STOP and len(w) > 2
    )
    return bool(title_words & query_words)


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

# Docker-safe Chromium flags (no channel= override, no setuid helper, no zygote fork)
_CHROMIUM_ARGS: list[str] = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-zygote",
]


async def _fetch_bing_images(query: str) -> list[MediaItem]:
    """Scrape Bing Images using Patchright (direct API, no Scrapling wrapper).

    PARKED (ADR-0014) — the media rail is video-only; this fetcher is no
    longer called from IllustrateSkill.run().  Kept for reference.

    Bing Images embeds per-result JSON in the `m` attribute of each
    `a.iusc` link:  {"murl": full_url, "turl": thumb_url, "t": title,
                      "imgw": width, "imgh": height, "purl": page_url}

    We bypass Scrapling's StealthyFetcher because it always injects
    channel='chromium' into launch options, which crashes on Docker even
    with seccomp:unconfined (SIGTRAP in Chromium channel lookup).
    Direct patchright.launch() with no `channel` works correctly.
    """
    try:
        from patchright.async_api import async_playwright  # type: ignore[import]
    except ImportError:
        logger.warning("ILLUSTRATE: patchright not installed — Bing skipped")
        return []

    url = (
        "https://www.bing.com/images/search?"
        + urllib.parse.urlencode({"q": query, "form": "HDRSC2", "first": "1"})
    )

    items: list[MediaItem] = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=_CHROMIUM_ARGS)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                anchors = await page.query_selector_all("a.iusc")
                for a in anchors[:20]:
                    raw = await a.get_attribute("m")
                    if not raw:
                        continue
                    try:
                        m = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    img_url   = m.get("murl", "")
                    thumb_url = m.get("turl", img_url)
                    # Clean title: strip trailing " - YouTube" / " | Reuters" etc.
                    title = re.sub(
                        r"\s*[-|]\s*(YouTube|Getty.*|Reuters.*|AP.*|BBC.*)$",
                        "", m.get("t", ""), flags=re.IGNORECASE,
                    )
                    # m-attr includes original image dimensions
                    width  = int(m.get("imgw", 0) or 0)
                    height = int(m.get("imgh", 0) or 0)
                    page_url = m.get("purl", img_url)

                    if not img_url:
                        continue

                    try:
                        domain = urllib.parse.urlparse(page_url).netloc or ""
                    except Exception:
                        domain = ""

                    item: MediaItem = {
                        "url":           img_url,
                        "thumb_url":     thumb_url,
                        "type":          "image",
                        "title":         title[:200],
                        "source_domain": domain.lower().removeprefix("www."),
                        "published_at":  None,
                        "width":         width,
                        "height":        height,
                        "score":         0.0,
                    }
                    item["score"] = _score(item)
                    items.append(item)
            finally:
                await browser.close()
    except Exception as exc:
        logger.warning("ILLUSTRATE: Bing fetch failed — %s", exc)

    logger.debug("ILLUSTRATE: Bing returned %d raw items", len(items))
    return items


async def _fetch_youtube_videos(query: str) -> list[MediaItem]:
    """Scrape YouTube search using Playwright (direct API, no Scrapling wrapper).

    After JavaScript execution the DOM contains `ytd-video-renderer`
    elements.  We extract video IDs from watch-link hrefs and derive the
    thumbnail URL from the well-known ytimg CDN pattern.

    Uses plain playwright (not patchright) since YouTube search does not
    require anti-fingerprinting.  Same Docker-safe launch flags apply.
    """
    try:
        from playwright.async_api import async_playwright  # type: ignore[import]
    except ImportError:
        logger.warning("ILLUSTRATE: playwright not installed — YouTube skipped")
        return []

    url = (
        "https://www.youtube.com/results?"
        + urllib.parse.urlencode({"search_query": query})
    )

    items: list[MediaItem] = []
    seen_ids: set[str] = set()
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=_CHROMIUM_ARGS)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Wait for video title links to appear in the JS-rendered DOM
                try:
                    await page.wait_for_selector("a#video-title", timeout=10000)
                except Exception:
                    pass

                title_links = await page.query_selector_all("a#video-title")
                if not title_links:
                    all_links = await page.query_selector_all("a[href*='/watch?v=']")
                    for a in all_links:
                        txt = (await a.inner_text() or "").strip()
                        if txt:
                            title_links.append(a)

                for a in title_links[:15]:
                    href = (await a.get_attribute("href")) or ""
                    m = re.search(r"/watch\?v=([A-Za-z0-9_-]{11})", href)
                    if not m:
                        continue
                    vid_id = m.group(1)
                    if vid_id in seen_ids:
                        continue
                    seen_ids.add(vid_id)

                    title = (
                        (await a.inner_text() or "").strip()
                        or (await a.get_attribute("title")) or ""
                        or ((await a.get_attribute("aria-label")) or "").removeprefix("Watch ")
                    )[:200]
                    if not title:
                        continue

                    item: MediaItem = {
                        "url":           f"https://www.youtube.com/watch?v={vid_id}",
                        "thumb_url":     _yt_thumb(vid_id),
                        "type":          "video",
                        "title":         title,
                        "source_domain": "youtube.com",
                        "published_at":  None,
                        "width":         480,
                        "height":        360,
                        "score":         0.0,
                    }
                    item["score"] = _score(item)
                    items.append(item)

                    if len(items) >= 10:
                        break
            finally:
                await browser.close()
    except Exception as exc:
        logger.warning("ILLUSTRATE: YouTube fetch failed — %s", exc)

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
        """Fetch YouTube videos, rank by score, write to pages.media_rail.

        Images are excluded — the media rail is video-only (ADR-0014).
        An empty result is valid and is persisted as [].
        """
        query = _search_query(headline)
        logger.info("ILLUSTRATE %s | query=%r", event_id, query)

        # Query words used for relevance gating of unknown-domain results
        query_words: frozenset[str] = frozenset(
            w.lower() for w in re.sub(r"[^\w\s]", " ", query).split()
            if w.lower() not in _STOP and len(w) > 2
        )

        # Only YouTube for now; direct outlet video fetchers can be added here.
        try:
            yt_results = await asyncio.wait_for(
                _fetch_youtube_videos(query), self.FETCH_TIMEOUT
            )
        except Exception as exc:
            logger.warning("ILLUSTRATE: YouTube fetch error — %s", exc)
            yt_results = []

        candidates: list[MediaItem] = yt_results

        # ── Filter: blocked domains + relevance gate ───────────────────────
        before = len(candidates)
        candidates = [
            c for c in candidates
            if not _is_blocked(c["source_domain"])
            and _is_relevant(c, query_words)
        ]
        dropped = before - len(candidates)
        if dropped:
            logger.info(
                "ILLUSTRATE %s | dropped %d irrelevant/blocked candidates "
                "(blocked domains or no keyword overlap with query %r)",
                event_id, dropped, query,
            )

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
            "ILLUSTRATE %s → %d video items (yt_raw=%d)",
            event_id, len(rail), len(yt_results),
        )
        return rail
