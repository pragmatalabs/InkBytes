#!/usr/bin/env python
"""One-time backfill: un-publish existing ad-style / commerce pages (Curator ADR-0020).

The promo gate only runs at synthesis, so pages published before it shipped keep
their ad-style covers in the feed. This re-applies the same rule to every
published page and un-publishes the ones that are commerce roundups:

  • headline is ad-style (is_promotional), OR
  • a strict majority of the event's article titles are commercial.

Un-publish = set `pages.published_at = NULL` (the /events API filters on it).
Reversible: a future re-synthesis can re-publish if the cluster changes. Dry-run
by default; pass --apply to write.

Run inside the Curator container:
  docker exec inkbytes-curator-worker python scripts/backfill_promo_pages.py
  docker exec inkbytes-curator-worker python scripts/backfill_promo_pages.py --apply
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg  # noqa: E402

from core.config import CuratorConfig  # noqa: E402
from services.promo_filter import is_promotional, promo_reason  # noqa: E402


def _page_is_promo(headline: str, titles: list[str]) -> str | None:
    """Mirror of the synthesize gate. Returns a reason label, or None if clean."""
    r = promo_reason(headline)
    if r:
        return f"headline:{r}"
    clean_titles = [t for t in titles if t]
    if clean_titles:
        promo = sum(1 for t in clean_titles if is_promotional(t))
        if promo * 2 > len(clean_titles):
            return f"cluster:{promo}/{len(clean_titles)}"
    return None


async def _run(config_path: str, apply: bool) -> int:
    cfg = CuratorConfig.load(config_path)
    conn = await asyncpg.connect(cfg.database.url)
    try:
        rows = await conn.fetch(
            """
            SELECT p.id, p.headline, COALESCE(array_agg(a.title) FILTER (WHERE a.title IS NOT NULL), '{}') AS titles
              FROM pages p
              JOIN events e ON e.id = p.event_id
              LEFT JOIN articles a ON a.event_id = e.id
             WHERE p.published_at IS NOT NULL
             GROUP BY p.id, p.headline
            """
        )
        flagged: list[tuple[str, str, str]] = []  # (id, reason, headline)
        for r in rows:
            reason = _page_is_promo(r["headline"], list(r["titles"]))
            if reason:
                flagged.append((r["id"], reason, r["headline"]))

        print(f"[backfill] {len(rows)} published pages · {len(flagged)} promotional "
              f"(mode={'APPLY' if apply else 'dry-run'})")
        for _id, reason, headline in flagged:
            print(f"  [{reason:16}] {headline[:88]}")

        if not flagged:
            print("[backfill] nothing to do.")
            return 0
        if not apply:
            print(f"\n[backfill] dry-run — would un-publish {len(flagged)} page(s). "
                  f"Re-run with --apply to write.")
            return 0

        ids = [f for f, _, _ in flagged]
        result = await conn.execute(
            "UPDATE pages SET published_at = NULL WHERE id = ANY($1::text[])", ids
        )
        print(f"\n[backfill] APPLIED — {result} ({len(ids)} pages un-published)")
        return 0
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Un-publish ad-style/commerce pages (ADR-0020)")
    ap.add_argument("--config", default="env.yaml")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = ap.parse_args()
    return asyncio.run(_run(args.config, args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
