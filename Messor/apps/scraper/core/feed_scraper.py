"""RSS/Atom feed-first URL discovery for Messor.

Replaces newspaper3k's homepage crawl for outlets that have a ``feed_url``
configured.  Returns a list of lightweight article-like objects whose ``.url``
attribute the existing ``process_outlet_articles()`` loop can consume unchanged.

Why feed-first?
  - Newspaper3k builds a full newspaper (homepage + all category pages) which
    hits every outlet URL — some outlets geo-block that broad crawl even when
    they're happy to serve individual article pages.
  - RSS/Atom feeds are explicit editorial selections: 20-50 fresh items, already
    within the freshness window, no section-page noise.
  - feedparser is already in requirements.txt (≥6.0.11).

Design (ADR-0015 follow-up, 2026-06-10):
  1. fetch feed with feedparser (no browser, no JS)
  2. filter entries to freshness window (same 48h as newspaper3k path)
  3. return real newspaper.Article objects (undownloaded) — the downstream
     pipeline (process_outlet_articles → scrape_outlet_article →
     pre_process_article) calls .download()/.parse() on each one, so a
     bare URL stub is NOT enough (2026-06-11 prod incident: every feed
     article failed with AttributeError on a __slots__ stub)
  4. if feed fetch fails → caller falls back to newspaper3k homepage crawl
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser
import newspaper

logger = logging.getLogger(__name__)

# Feedparser user-agent — mirrors the scraper's default UA so CDNs don't block
_UA = (
    "InkBytes-Dev/0.1 Mozilla/5.0 AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _make_article(url: str) -> newspaper.Article:
    """Build an undownloaded newspaper.Article for a feed entry URL.

    Config kwargs must use real ``newspaper.Configuration`` attribute names —
    ``extend_config`` silently drops unknown keys (``agent`` and
    ``MAX_REDIRECTS`` in NewsPaper.build() are dropped this way).
    """
    return newspaper.Article(
        url,
        memoize_articles=False,
        follow_meta_refresh=False,
        http_success_only=False,
        request_timeout=30,
        browser_user_agent=_UA,
    )


def get_articles_from_feed(
    feed_url: str,
    freshness_hours: int = 48,
    max_articles: int = 300,
) -> Optional[list]:
    """Fetch a RSS/Atom feed and return article stubs ready for download.

    Args:
        feed_url:         RSS/Atom URL to fetch.
        freshness_hours:  Drop entries older than this many hours (0 = no filter).
        max_articles:     Cap on returned stubs (matches MAX_ARTICLES_PER_OUTLET).

    Returns:
        List of undownloaded newspaper.Article on success, or None if the feed
        could not be fetched (caller should fall back to newspaper3k homepage
        crawl).
    """
    logger.info("RSS fetch: %s", feed_url)
    try:
        parsed = feedparser.parse(
            feed_url,
            request_headers={"User-Agent": _UA},
        )
    except Exception as exc:
        logger.warning("feedparser error for %s: %s", feed_url, exc)
        return None

    # feedparser never raises — it sets bozo=True on malformed feeds.
    if parsed.bozo and not parsed.entries:
        logger.warning(
            "Feed %s is malformed (bozo=%r) and has no entries — skipping",
            feed_url, parsed.bozo_exception,
        )
        return None

    if not parsed.entries:
        logger.warning("Feed %s returned 0 entries", feed_url)
        return None

    cutoff: Optional[datetime] = None
    if freshness_hours > 0:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=freshness_hours)

    stubs: list[newspaper.Article] = []
    stale = 0
    no_url = 0

    for entry in parsed.entries:
        url: Optional[str] = entry.get("link") or entry.get("id")
        if not url or not url.startswith("http"):
            no_url += 1
            continue

        # Entry pubDate — outlet-authoritative (RSS/Atom), unlike newspaper3k's
        # byline extraction which fails entirely on some outlets (BBC).
        pub: Optional[datetime] = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pub = None  # malformed date — let it through rather than silently drop

        # Freshness gate on the feed date.
        if cutoff is not None and pub is not None and pub < cutoff:
            stale += 1
            continue

        art = _make_article(url)
        if pub is not None:
            # Survives .download()/.parse(); scrape_outlet_article() uses it as
            # the publish_date fallback so the strict ADR-0015 freshness gate
            # doesn't drop feed articles newspaper3k can't date (BBC → 29/29
            # dropped as "undated", 2026-06-11).
            art._feed_published = pub.isoformat()
        stubs.append(art)
        if len(stubs) >= max_articles:
            break

    logger.info(
        "RSS %s → %d stubs (stale-skip=%d, no-url=%d, raw-entries=%d)",
        feed_url, len(stubs), stale, no_url, len(parsed.entries),
    )

    if not stubs:
        logger.warning("Feed %s produced 0 usable stubs after filtering", feed_url)
        return None  # trigger fallback

    return stubs
