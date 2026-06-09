#!/usr/bin/env python3
"""Local verification for Messor ADR-0014 — per-run staging files.

Drives the REAL NewsScraper.process_outlet_articles twice (two simulated
cycles) for one outlet, with network + staging dir stubbed, and asserts:

  1. Each cycle writes its OWN staging file (distinct <run_ts> prefix) — the
     per-day file no longer accumulates across cycles.
  2. Cycle 2 stages ONLY genuinely-new articles (URL dedup via
     load_known_article_urls catches the overlap from cycle 1).
  3. Re-publishing a run's file emits exactly that run's NEW articles — never
     the cumulative history (this is the 105k-flood fix).

Run from apps/scraper with the venv:
    venv/bin/python scripts/test_per_run_staging.py
"""
import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.scraper as scraper
from core.staging_store import load_known_article_urls
from inkbytes.models.articles import Article


def make_np_article(url):
    class _NP:
        pass
    a = _NP()
    a.url = url
    return a


def fake_scrape_outlet_article(np_article, brand):
    """Stand in for the network fetch: build an Article straight from the URL.

    Emits a fresh publish_date so the ADR-0015 freshness gate keeps the article
    (this test exercises per-run staging, not freshness)."""
    import datetime as _dt
    url = np_article.url
    fresh = (_dt.datetime.utcnow() - _dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    return Article(
        id=url,                 # id == url keeps the test deterministic
        article_url=url,
        title=f"title for {url}",
        text="lorem ipsum " * 20,
        language="en",
        publish_date=fresh,
    )


def publish_count_from_file(path):
    """Mirror _publish_articles_from_staging_file's read: count articles in file."""
    import json
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "_default" in data:
        return len(data["_default"])
    if isinstance(data, list):
        return len(data)
    return 0


def run():
    # Isolate staging writes: chdir into a temp dir so the config's relative
    # "data/scrapes/" path resolves under it (config is already loaded from the
    # real env.yaml at import time — we don't touch it).
    tmp = tempfile.mkdtemp(prefix="messor-staging-test-")
    os.chdir(tmp)
    scrapes_dir = scraper.config.storage.staging.local.scraping()  # e.g. "data/scrapes/"
    os.makedirs(scrapes_dir, exist_ok=True)
    print(f"[test] cwd: {tmp}  staging dir: {scrapes_dir}")

    # ── stub network ──────────────────────────────────────────────────────
    scraper.scrape_outlet_article = fake_scrape_outlet_article

    outlet = "testoutlet"

    # ── Cycle 1: 5 fresh URLs ─────────────────────────────────────────────
    urls_c1 = [f"http://x.test/{i}" for i in range(5)]
    s1 = scraper.NewsScraper(outlet=None, paper=None, session=scraper.ScrapingSession())
    known1 = load_known_article_urls(scrapes_dir, outlet)            # empty first run
    s1.process_outlet_articles(outlet, [make_np_article(u) for u in urls_c1], known1)
    file_c1 = os.path.join(scrapes_dir, s1.session.results_staging_file_name)

    assert os.path.exists(file_c1), "cycle 1 staging file missing"
    assert publish_count_from_file(file_c1) == 5, "cycle 1 should stage 5 new"
    print(f"[test] cycle 1 → {s1.session.results_staging_file_name}: 5 staged, 5 would publish ✓")

    # Force a different run_ts (per-run filename is int(time.time())).
    time.sleep(1.1)

    # ── Cycle 2: 3 of the same URLs + 2 brand-new ─────────────────────────
    urls_c2 = urls_c1[:3] + ["http://x.test/new-a", "http://x.test/new-b"]
    s2 = scraper.NewsScraper(outlet=None, paper=None, session=scraper.ScrapingSession())
    known2 = load_known_article_urls(scrapes_dir, outlet)            # scans cycle-1 file
    known2_seen_before = len(known2)                                 # capture before in-place mutation
    s2.process_outlet_articles(outlet, [make_np_article(u) for u in urls_c2], known2)
    file_c2 = os.path.join(scrapes_dir, s2.session.results_staging_file_name)

    # ── Assertions ────────────────────────────────────────────────────────
    assert file_c1 != file_c2, "BUG: cycles share a staging file (per-day accumulation)"
    assert os.path.exists(file_c2), "cycle 2 staging file missing"

    c2_published = publish_count_from_file(file_c2)
    assert c2_published == 2, (
        f"BUG: cycle 2 would publish {c2_published} articles, expected 2 "
        f"(only the genuinely-new ones). The old per-day file would have re-published all 7."
    )
    # cycle 1 file untouched by cycle 2 (no accumulation)
    assert publish_count_from_file(file_c1) == 5, "cycle 1 file was mutated by cycle 2"

    print(f"[test] cycle 2 → {s2.session.results_staging_file_name}: 2 staged, 2 would publish ✓")
    assert known2_seen_before == 5, "cycle 2 should have loaded cycle 1's 5 URLs for dedup"
    print(f"[test] cycle 2 loaded {known2_seen_before} known URLs from cycle 1 for dedup ✓")
    print()
    print("[test] PASS — per-run files, no cross-cycle accumulation, publish == only-new")
    print(f"[test] (old behaviour would have re-published 5 + 7 = 12 events for 7 unique articles)")

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    run()
