"""Lead-image validation — hotlink probe + author-photo URL guard.

Two gates run at article ingest to keep hero images relevant:

1. **Hotlink probe** (``is_displayable``, ADR-0019) — async, sends the exact
   ``Sec-Fetch-*`` browser fingerprint that trips CDN hotlink guards (notably
   LA Times' brightspot). Keeps the URL if the probe times out (fail-open).

2. **Author-photo URL guard** (``is_author_photo``, ADR-0016) — sync, no HTTP.
   Detects byline headshots via URL path patterns common across WordPress/CMS
   outlets (``/author/``, ``/avatar/``, ``/profile/``, Spanish equivalents,
   etc.).  Heraldo and similar outlets set ``og:image`` to the journalist's
   headshot rather than a story photo; this gate NULLs it so the
   ``events.hero_image`` YouTube-thumbnail fallback kicks in instead.
"""
from __future__ import annotations

import logging
import re
from collections import OrderedDict

import httpx

logger = logging.getLogger(__name__)

# The exact header fingerprint a browser sends for a cross-origin <img> load.
# Sec-Fetch-Dest:image + Sec-Fetch-Site:cross-site together are what trip the
# hotlink guards; neither alone does (verified against brightspot, ADR-0019).
_BROWSER_IMG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "cross-site",
    "Referer": "https://inkbytes.org/",
}

# A real lead image is kilobytes+. Anything smaller is a tracking/placeholder
# pixel (brightspot's placeholder-1x1.png is 69 bytes).
_MIN_IMAGE_BYTES = 512
_CACHE_MAX = 5000

# ── Author-photo URL patterns (ADR-0016) ─────────────────────────────────────
# Path segments and parameter names that reliably indicate a journalist byline
# headshot rather than a story photo.  Covers English and Spanish CMS patterns.
_AUTHOR_URL_RE = re.compile(
    r"("
    r"/authors?/"
    r"|/autores?/"           # Spanish
    r"|/journalists?/"
    r"|/reporters?/"
    r"|/contributors?/"
    r"|/columnists?/"
    r"|/staff/"
    r"|/people/"
    r"|/team/"
    r"|/profiles?/"
    r"|/avatars?/"
    r"|/headshots?/"
    r"|/bylines?/"
    r"|[_\-]author[_\-]"
    r"|author[_\-]photo"
    r"|author[_\-]image"
    r"|profile[_\-]image"
    r"|profile[_\-]photo"
    r")",
    re.IGNORECASE,
)


class MediaValidator:
    """Probes whether a ``lead_image`` URL renders for a cross-origin ``<img>``.

    Owns one ``httpx.AsyncClient`` (built lazily on first use). Results are
    cached in-process per URL for the worker's lifetime, so a given URL is
    probed over the network at most once — re-scrapes of the same article and
    multiple articles sharing a CDN-templated image hit the cache.
    """

    def __init__(self, *, enabled: bool = True, timeout_s: float = 4.0) -> None:
        self.enabled = enabled
        self.timeout_s = timeout_s
        self._client: httpx.AsyncClient | None = None
        self._cache: "OrderedDict[str, bool]" = OrderedDict()

    def _client_or_build(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_s,
                follow_redirects=True,
                max_redirects=4,
                headers=_BROWSER_IMG_HEADERS,
            )
        return self._client

    def _remember(self, url: str, ok: bool) -> bool:
        self._cache[url] = ok
        self._cache.move_to_end(url)
        if len(self._cache) > _CACHE_MAX:
            self._cache.popitem(last=False)
        return ok

    async def is_displayable(self, url: str) -> bool:
        """Return True if a browser would render ``url`` as a cross-origin image.

        Fail-open: on timeout / network error we return True (keep the URL) — a
        transient outlet hiccup shouldn't permanently drop a good image. The
        deterministic hotlink case (a 200 placeholder pixel) is what we catch.
        """
        if not self.enabled or not url:
            return True
        # Only http(s) URLs are probeable. `data:`/`blob:` URIs are inline images
        # the browser renders directly (keep them); a relative path or unknown
        # scheme isn't ours to judge — keep rather than drop. httpx also raises on
        # a non-http scheme, so this guard doubles as a crash guard.
        if not url.lower().startswith(("http://", "https://")):
            return True
        if url in self._cache:
            self._cache.move_to_end(url)
            return self._cache[url]
        try:
            # stream() so we read headers + the final (post-redirect) URL without
            # downloading the image body. A real GET is required: brightspot's
            # hotlink redirect only fires on an image GET, not a HEAD.
            async with self._client_or_build().stream("GET", url) as resp:
                status = resp.status_code
                ctype = resp.headers.get("content-type", "").lower()
                final_url = str(resp.url).lower()
                clen = resp.headers.get("content-length")
        except Exception as e:  # noqa: BLE001 — fail open on any probe error
            logger.debug("lead_image probe failed, keeping %s: %s", url, e)
            return self._remember(url, True)

        if status != 200:
            return self._remember(url, False)
        # An error / landing page served as 200 — HTML, JSON or plain text rather
        # than an image. We do NOT block on a *missing* content-type: some CDNs
        # serve real images with no Content-Type header (e.g. eltiempo) and the
        # browser sniffs them fine — blocking those would be a false positive.
        if ctype.startswith(("text/", "application/")):
            return self._remember(url, False)
        # Followed a hotlink redirect to a placeholder/tracking pixel.
        if "placeholder" in final_url:
            return self._remember(url, False)
        # A 1×1 tracking/placeholder pixel — real lead images are kilobytes+.
        if clen is not None and clen.isdigit() and int(clen) < _MIN_IMAGE_BYTES:
            return self._remember(url, False)
        return self._remember(url, True)

    @staticmethod
    def is_author_photo(url: str) -> bool:
        """Return True if the URL path looks like a journalist byline headshot.

        Sync and free — pure regex, no HTTP.  Intended to be called after
        ``is_displayable`` (which is async/network) so that cheap pattern
        matching runs even when probe validation is disabled.

        Covers common English and Spanish CMS path patterns:
        /author/, /avatar/, /profile/, /headshot/, /staff/, /people/,
        /autores/, /journalists/, /reporters/, /contributors/ …
        Also catches query-param and filename patterns like
        ``author_photo.jpg`` or ``profile-image.png``.
        """
        return bool(_AUTHOR_URL_RE.search(url))

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
