#!/usr/bin/env python
"""Test the lead-image hotlink guard (Curator ADR-0019).

Two layers:
  1. Deterministic logic tests — a fake httpx transport returns crafted
     responses (placeholder pixel, real image, 404, non-image, redirect),
     verifying MediaValidator.is_displayable() classifies each correctly and
     caches the result. No network.
  2. Live smoke test (best-effort, network) — probes the real brightspot URL
     that triggered ADR-0019 (expected: NOT displayable → 1×1 placeholder) and
     a known-good image (expected: displayable). Skipped/soft on network error.

Run:
  cd Curator/apps/curator && .venv/bin/python scripts/test_lead_image_validation.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from services.media_validation import MediaValidator  # noqa: E402

# The real URL from the ADR-0019 report: an LA Times brightspot og:image that
# hotlink-redirects to placeholder-1x1.png for a cross-origin <img>.
BLOCKED_URL = (
    "https://ca-times.brightspotcdn.com/dims4/default/122202a/2147483647/strip/"
    "true/crop/5000x2625+0+355/resize/1200x630!/quality/75/?url=https%3A%2F%2F"
    "california-times-brightspot.s3.amazonaws.com%2Fcd%2F74%2F"
    "61557556498d9fb099b5973a5616%2F1557787-la-de-los-boyle-heights-youth-fest-el-10.jpg"
)
# A plain CDN image with no hotlink protection — serves a real 200 image/png to
# the browser fingerprint. (Wikimedia/picsum 400 or redirect on this fingerprint,
# so they make poor controls.)
GOOD_URL = "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=identicon&s=200"

passed = 0
failed = 0


def check(label: str, got, want) -> None:
    global passed, failed
    ok = got == want
    mark = "✓" if ok else "✗ FAIL"
    print(f"[test] {label:<46} got={got!s:<6} want={want!s:<6} {mark}")
    passed += ok
    failed += not ok


def _make_stub_validator(routes: dict[str, httpx.Response]) -> MediaValidator:
    """A MediaValidator whose client uses a MockTransport keyed by request URL."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Match on the final path so redirect targets resolve too.
        for key, resp in routes.items():
            if key in str(request.url):
                return resp
        return httpx.Response(404)

    v = MediaValidator(enabled=True, timeout_s=2.0)
    v._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
        max_redirects=4,
    )
    return v


async def logic_tests() -> None:
    print("\n=== deterministic logic (no network) ===")

    # 1. Hotlink redirect → 1×1 placeholder pixel (the ADR-0019 case).
    v = _make_stub_validator({
        "/image.jpg": httpx.Response(
            302, headers={"location": "https://cdn.example/placeholder-1x1.png"}
        ),
        "/placeholder-1x1.png": httpx.Response(
            200, headers={"content-type": "image/png", "content-length": "69"},
            content=b"x" * 69,
        ),
    })
    check("placeholder redirect → blocked",
          await v.is_displayable("https://cdn.example/image.jpg"), False)

    # 2. Real image, 200, image/jpeg, plenty of bytes → displayable.
    v = _make_stub_validator({
        "/real.jpg": httpx.Response(
            200, headers={"content-type": "image/jpeg", "content-length": "119424"},
            content=b"x" * 1024,
        ),
    })
    check("real image 200 → displayable",
          await v.is_displayable("https://cdn.example/real.jpg"), True)

    # 3. 404 → not displayable.
    v = _make_stub_validator({"/gone.jpg": httpx.Response(404)})
    check("404 → blocked",
          await v.is_displayable("https://cdn.example/gone.jpg"), False)

    # 4. 200 but text/html (CDN error page) → not displayable.
    v = _make_stub_validator({
        "/oops.jpg": httpx.Response(200, headers={"content-type": "text/html"}),
    })
    check("200 non-image content-type → blocked",
          await v.is_displayable("https://cdn.example/oops.jpg"), False)

    # 5. 200 image but tiny (< 512 B tracking pixel) → not displayable.
    v = _make_stub_validator({
        "/pixel.gif": httpx.Response(
            200, headers={"content-type": "image/gif", "content-length": "43"},
            content=b"x" * 43,
        ),
    })
    check("tiny pixel (<512B) → blocked",
          await v.is_displayable("https://cdn.example/pixel.gif"), False)

    # 6. Disabled validator never probes → always displayable.
    vd = MediaValidator(enabled=False)
    check("disabled → always displayable",
          await vd.is_displayable(BLOCKED_URL), True)

    # 7. Empty / None URL → treated as displayable (nothing to drop).
    check("empty url → displayable",
          await v.is_displayable(""), True)

    # 7b. Non-http schemes are kept, never probed (httpx would raise on them).
    #     A data: URI is an inline image the browser renders directly.
    check("data: URI → displayable (no probe)",
          await v.is_displayable("data:image/svg+xml,%3Csvg%3E%3C/svg%3E"), True)
    check("relative path → displayable (no probe)",
          await v.is_displayable("/local/image.png"), True)

    # 8. Cache: second call to a blocked URL returns the cached verdict.
    v = _make_stub_validator({"/gone.jpg": httpx.Response(404)})
    await v.is_displayable("https://cdn.example/gone.jpg")
    cached = "https://cdn.example/gone.jpg" in v._cache
    check("verdict cached after first probe", cached, True)
    await v.aclose()


async def live_smoke() -> None:
    print("\n=== live smoke test (network, best-effort) ===")
    v = MediaValidator(enabled=True, timeout_s=8.0)
    try:
        blocked = await v.is_displayable(BLOCKED_URL)
        good = await v.is_displayable(GOOD_URL)
    except Exception as e:  # noqa: BLE001
        print(f"[test] live smoke skipped (network): {e}")
        await v.aclose()
        return
    check("real brightspot URL → blocked", blocked, False)
    check("known-good image URL → displayable", good, True)
    await v.aclose()


async def main() -> int:
    await logic_tests()
    await live_smoke()
    print()
    if failed:
        print(f"[test] FAIL — {failed} failed, {passed} passed")
        return 1
    print(f"[test] PASS — lead-image hotlink guard ({passed} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
