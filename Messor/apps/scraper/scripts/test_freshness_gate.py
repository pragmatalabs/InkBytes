#!/usr/bin/env python3
"""Local verification for Messor ADR-0015 — 48h harvest freshness gate.

1. Unit-checks ``is_article_fresh`` across fresh / stale / undated / future.
2. Drives the REAL ``NewsScraper.process_outlet_articles`` with a mix of
   publish dates and asserts only ≤48h articles are staged (strict: undated
   and far-future dropped).
3. Checks ``_slice_outlet_articles`` keeps the homepage head only (tail dropped).

Run from apps/scraper with the venv:
    venv/bin/python scripts/test_freshness_gate.py
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.scraper as scraper
from core.scraper import is_article_fresh, _slice_outlet_articles, MAX_ARTICLES_PER_OUTLET
from core.staging_store import load_known_article_urls
from inkbytes.models.articles import Article


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def make_np_article(url, pubdate):
    class _NP:
        pass
    a = _NP()
    a.url = url
    a._pubdate = pubdate
    return a


def fake_scrape_outlet_article(np_article, brand):
    return Article(
        id=np_article.url,
        article_url=np_article.url,
        title=f"title {np_article.url}",
        text="lorem ipsum " * 20,
        language="en",
        publish_date=np_article._pubdate,
    )


def publish_ids_from_file(path):
    import json
    data = json.load(open(path, encoding="utf-8"))
    recs = list(data.get("_default", {}).values()) if isinstance(data, dict) else data
    return {r.get("id") for r in recs}


def unit_checks():
    now = datetime.utcnow()
    cases = [
        ("fresh 1h",      _fmt(now - timedelta(hours=1)),   True),
        ("fresh 47h",     _fmt(now - timedelta(hours=47)),  True),
        ("stale 49h",     _fmt(now - timedelta(hours=49)),  False),
        ("stale April",   "2026-04-01 12:00:00",            False),
        ("undated None",  "None",                           False),
        ("undated empty", "",                               False),
        ("tz-aware fresh", (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S+00:00"), True),
        ("bogus future",  _fmt(now + timedelta(days=5)),    False),
    ]
    for label, raw, expected in cases:
        rec = Article(id=label, publish_date=raw)
        got = is_article_fresh(rec, 48)
        assert got == expected, f"is_article_fresh({label!r}={raw!r}) → {got}, expected {expected}"
        print(f"[test] is_article_fresh {label:<14} → {got} ✓")


def slice_check():
    arts = [make_np_article(f"u{i}", "x") for i in range(MAX_ARTICLES_PER_OUTLET + 250)]
    sliced = _slice_outlet_articles(arts)
    assert len(sliced) == MAX_ARTICLES_PER_OUTLET, f"head cap not applied: {len(sliced)}"
    assert sliced[0].url == "u0" and sliced[-1].url == f"u{MAX_ARTICLES_PER_OUTLET-1}", \
        "tail leaked into slice (should be homepage head only)"
    print(f"[test] _slice_outlet_articles: {len(arts)} → {len(sliced)} head-only, tail dropped ✓")


def integration_check():
    tmp = tempfile.mkdtemp(prefix="messor-fresh-test-")
    os.chdir(tmp)
    scrapes_dir = scraper.config.storage.staging.local.scraping()
    os.makedirs(scrapes_dir, exist_ok=True)
    scraper.scrape_outlet_article = fake_scrape_outlet_article

    now = datetime.utcnow()
    feed = [
        ("fresh-a",  _fmt(now - timedelta(hours=2))),
        ("fresh-b",  _fmt(now - timedelta(hours=40))),
        ("stale-3d", _fmt(now - timedelta(days=3))),
        ("april",    "2026-04-01 09:00:00"),
        ("undated",  "None"),
        ("future",   _fmt(now + timedelta(days=5))),
    ]
    nps = [make_np_article(u, pd) for u, pd in feed]
    s = scraper.NewsScraper(outlet=None, paper=None, session=scraper.ScrapingSession())
    known = load_known_article_urls(scrapes_dir, "fresh")
    s.process_outlet_articles("fresh", nps, known)

    staged = publish_ids_from_file(os.path.join(scrapes_dir, s.session.results_staging_file_name))
    expected = {"fresh-a", "fresh-b"}
    assert staged == expected, f"staged={sorted(staged)}, expected={sorted(expected)}"
    print(f"[test] integration: staged {sorted(staged)} (dropped stale-3d, april, undated, future) ✓")

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unit_checks()
    slice_check()
    integration_check()
    print()
    print("[test] PASS — 48h freshness gate (strict on undated), tail-crawl removed")
