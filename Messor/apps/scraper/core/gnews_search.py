"""Google News RSS search + URL decoding for the on-demand breaking-news gate.

Messor normally harvests a fixed outlet catalogue. This module adds *query*
discovery: given a title/topic, query Google News' public RSS search, then
resolve each result to its real source URL so the existing scraper can fetch it.

Why the decode step?
  Google News RSS items link to ``news.google.com/rss/articles/CBMi…`` (newer
  ``AU_yqL…``) URLs — opaque protobuf blobs that DON'T 302-redirect to the
  source. The real URL is recovered by replaying Google's internal
  ``batchexecute`` RPC with a per-article signature+timestamp scraped from the
  article shell page. Verified working 2026-06-12 (4/4 on a live query).

Fragility note: ``batchexecute`` is an undocumented Google endpoint and can
change without notice. Every failure path here degrades gracefully (the entry
is skipped, never raised), and a pasted source URL bypasses this module
entirely — so a Google-side change can reduce search recall but never breaks
the on-demand gate as a whole.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass

import feedparser
import requests

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_BATCHEXECUTE = "https://news.google.com/_/DotsSplashUi/data/batchexecute"


@dataclass
class GNewsHit:
    url: str          # decoded real source URL
    title: str        # article title from the RSS entry
    source: str       # outlet name from the RSS entry (e.g. "CNBC")
    published: str | None = None  # RFC822 pubDate string if present


def _decode_article_url(session: requests.Session, gnews_url: str, timeout: int) -> str | None:
    """Resolve a news.google.com/rss/articles/<blob> URL to the real source URL.

    Replays Google's batchexecute RPC. Returns None on any failure (caller skips).
    """
    try:
        blob = gnews_url.split("/articles/")[1].split("?")[0]
    except IndexError:
        return None
    try:
        shell = session.get(gnews_url, headers={"User-Agent": _UA}, timeout=timeout)
        shell.raise_for_status()
        sg = re.search(r'data-n-a-sg="([^"]+)"', shell.text)
        ts = re.search(r'data-n-a-ts="([^"]+)"', shell.text)
        if not (sg and ts):
            return None
        inner = json.dumps([
            "garturlreq",
            [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
              None, None, None, None, None, 0, 1],
             "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
            blob, int(ts.group(1)), sg.group(1),
        ])
        payload = [[["Fbv4je", inner, None, "generic"]]]
        resp = session.post(
            _BATCHEXECUTE,
            headers={
                "User-Agent": _UA,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            data={"f.req": json.dumps(payload)},
            timeout=timeout,
        )
        resp.raise_for_status()
        for line in resp.text.split("\n"):
            if "http" not in line:
                continue
            m = re.search(r'(https?://[^\\"]+)', line)
            if m and "google.com" not in m.group(1):
                return m.group(1)
    except Exception as exc:  # noqa: BLE001 — never raise into the caller
        logger.debug("gnews decode failed for %s: %s", gnews_url[:60], exc)
    return None


def search(query: str, lang: str = "en", limit: int = 10, timeout: int = 20) -> list[GNewsHit]:
    """Search Google News for `query` and return decoded source-URL hits.

    `lang` maps to Google's hl/gl/ceid (en→US, es→ES). Entries that fail to
    decode are skipped — the returned list may be shorter than `limit`.
    """
    hl, gl, ceid = {
        "es": ("es-419", "MX", "MX:es-419"),
        "en": ("en-US", "US", "US:en"),
    }.get(lang, ("en-US", "US", "US:en"))
    feed_url = (
        f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}"
        f"&hl={hl}&gl={gl}&ceid={ceid}"
    )
    logger.info("GNews search: %r (lang=%s)", query, lang)
    parsed = feedparser.parse(feed_url, request_headers={"User-Agent": _UA})
    if not parsed.entries:
        logger.warning("GNews search returned 0 entries for %r", query)
        return []

    hits: list[GNewsHit] = []
    decoded = skipped = 0
    with requests.Session() as session:
        for entry in parsed.entries:
            if len(hits) >= limit:
                break
            link = entry.get("link", "")
            if "news.google.com" not in link:
                # Already a direct URL (rare) — use as-is.
                real = link or None
            else:
                real = _decode_article_url(session, link, timeout)
            if not real:
                skipped += 1
                continue
            decoded += 1
            source = ""
            src = entry.get("source")
            if isinstance(src, dict):
                source = src.get("title", "") or ""
            hits.append(GNewsHit(
                url=real,
                title=entry.get("title", "") or "",
                source=source,
                published=entry.get("published"),
            ))
    logger.info(
        "GNews search %r → %d hits (decoded=%d, skipped=%d, raw=%d)",
        query, len(hits), decoded, skipped, len(parsed.entries),
    )
    return hits
