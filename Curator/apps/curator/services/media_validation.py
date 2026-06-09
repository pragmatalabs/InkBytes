"""Lead-image displayability probe — drops hotlink-blocked og:images at ingest.

A source outlet's og:image URL (``articles.lead_image``) is embedded by the
Reader as a *cross-origin* ``<img>``. Some outlet CDNs (notably LA Times'
brightspot) detect that exact request fingerprint —
``Sec-Fetch-Dest: image`` + ``Sec-Fetch-Site: cross-site`` — as hotlinking and
302-redirect to a 1×1 ``placeholder-1x1.png``. That redirect lands on a *valid*
HTTP 200 transparent pixel, so the Reader's ``<img onError>`` fallback never
fires — the hero renders as a blank box with no fallback (Curator ADR-0019).

Server-side fetchers (Messor harvest, link-preview bots, plain ``curl``) don't
send the ``Sec-Fetch-*`` headers, so they see the real image and HTTP 200 — which
is why the dead URL sails through extraction and only fails inside a real
browser. We reproduce the browser fingerprint here, at ingest, and let the
caller NULL out blocked URLs so the ``/events`` ``lead_image`` rollup falls back
to another source's image.
"""
from __future__ import annotations

import logging
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
        if not ctype.startswith("image/"):
            return self._remember(url, False)
        # Followed a hotlink redirect to a placeholder/tracking pixel.
        if "placeholder" in final_url:
            return self._remember(url, False)
        if clen is not None and clen.isdigit() and int(clen) < _MIN_IMAGE_BYTES:
            return self._remember(url, False)
        return self._remember(url, True)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
