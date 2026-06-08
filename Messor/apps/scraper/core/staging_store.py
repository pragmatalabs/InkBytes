#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Per-cycle staging store for scraped articles.

Replaces the previous TinyDB-backed `DataHandler` with a plain JSON file
store. v1 only needs:

  - read existing article IDs from a staging file (for dedup)
  - insert a batch of articles (write a JSON array)
  - check whether a given article ID exists across all prior staging
    files for an outlet (for cross-session dedup)

That's three operations. TinyDB's `Query` machinery and atomic-write
guarantees aren't worth the dep. JSON is enough.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2026 InkBytes Technologies
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterable, List, Set

from inkbytes.models.articles import Article

logger = logging.getLogger(__name__)


class StagingStore:
    """A JSON-file-backed store of articles for a single scraping session.

    The on-disk format is a JSON object compatible with the TinyDB layout
    we used previously: ``{"_default": {"<n>": {<article dict>}, ...}}``.
    Keeping the structure means old staging files remain readable.

    Thread-safety: the store is intended to be owned by a single thread
    (the outlet worker). Cross-thread access requires external locking.
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._records: List[dict] = []
        self._known_ids: Set[str] = set()
        self._load()

    # ---- file I/O ------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Tolerate both shapes: TinyDB legacy and plain list.
            if isinstance(data, dict) and "_default" in data:
                self._records = list(data["_default"].values())
            elif isinstance(data, list):
                self._records = data
            for rec in self._records:
                aid = rec.get("id")
                if aid:
                    self._known_ids.add(aid)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not load staging file %s: %s", self.file_path, e)

    def _flush(self) -> None:
        Path(os.path.dirname(self.file_path) or ".").mkdir(parents=True, exist_ok=True)
        # TinyDB-compatible shape: {"_default": {"1": <rec>, "2": <rec>, ...}}
        payload = {"_default": {str(i + 1): rec for i, rec in enumerate(self._records)}}
        tmp_path = self.file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp_path, self.file_path)

    # ---- public API ----------------------------------------------------

    def contains(self, article_id: str) -> bool:
        return article_id in self._known_ids

    def insert(self, article: Article) -> None:
        self._records.append(article.dict())
        if article.id:
            self._known_ids.add(article.id)
        self._flush()

    def insert_multiple(self, articles: Iterable[Article]) -> None:
        for a in articles:
            self._records.append(a.dict())
            if a.id:
                self._known_ids.add(a.id)
        self._flush()

    @property
    def size(self) -> int:
        return len(self._records)


def article_id_exists_in_file(file_path: str, article_id: str) -> bool:
    """Cheap one-shot check for an article ID inside a staging file.

    Streams the JSON; does not load the file into a StagingStore.
    """
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        records = (
            data.get("_default", {}).values() if isinstance(data, dict) else data
        )
        for rec in records:
            if rec.get("id") == article_id:
                return True
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not scan staging file %s: %s", file_path, e)
    return False


_URL_DEDUP_WINDOW_DAYS = 7   # only scan staging files from the last N days (ADR-0012)
_PRUNE_KEEP_DAYS       = 30  # delete staging files older than N days (ADR-0012)


def load_known_article_urls(scrapes_dir: str, outlet_name: str) -> set:
    """Return a set of article URLs from recent staging files for this outlet.

    Called ONCE at the start of each outlet's scrape (ADR-0011 Layer 3).
    Replaces the per-article ``check_article_exists_in_all_scrapes`` file reads
    with a single O(N_files) pass; subsequent dedup is O(1) set lookup.

    Only files from the last ``_URL_DEDUP_WINDOW_DAYS`` days are scanned
    (ADR-0012).  Older files would cause unbounded memory growth and slow
    startup; any article genuinely absent for >7 days would hit Curator's
    content-hash fast-path cheaply if re-published.

    Staging records store the URL in the ``article_url`` field (set by
    ArticleBuilder.buildFromNewspaper3K).  ``url``/``canonical_url`` are checked
    as fallbacks for older file formats.

    File naming convention: ``<unix-day-ts>.<outlet_name>.db.json`` where
    ``<unix-day-ts>`` is the Unix timestamp of midnight UTC for that day
    (``generate_today_timestamp()``).  Files whose prefix cannot be parsed as an
    integer are included unconditionally (graceful handling of legacy names).
    """
    import time as _time

    cutoff_ts = _time.time() - _URL_DEDUP_WINDOW_DAYS * 86400

    known: set = set()
    if not os.path.exists(scrapes_dir):
        return known
    try:
        candidates = [
            f for f in os.listdir(scrapes_dir)
            if outlet_name in f and f.endswith(".db.json")
        ]
    except OSError as e:
        logger.warning("Could not list scrapes dir %s: %s", scrapes_dir, e)
        return known

    # Filter by age: parse the leading integer timestamp from the filename.
    recent: list = []
    for fname in candidates:
        prefix = fname.split(".")[0]
        try:
            file_ts = int(prefix)
            if file_ts >= cutoff_ts:
                recent.append(fname)
        except ValueError:
            recent.append(fname)   # unparseable prefix → include unconditionally

    logger.debug(
        "load_known_article_urls: %d/%d staging files in window for %s",
        len(recent), len(candidates), outlet_name,
    )

    for fname in recent:
        file_path = os.path.join(scrapes_dir, fname)
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            records = (
                data.get("_default", {}).values()
                if isinstance(data, dict)
                else data
            )
            for rec in records:
                url = (
                    rec.get("article_url")
                    or rec.get("canonical_url")
                    or rec.get("url")
                )
                if url:
                    known.add(url)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not read staging file %s: %s", file_path, e)
    return known


def prune_old_staging_files(scrapes_dir: str, keep_days: int = _PRUNE_KEEP_DAYS) -> int:
    """Delete staging files older than ``keep_days`` days.

    Called once per scrape cycle to prevent unbounded disk growth (ADR-0012).
    Only removes files whose name starts with a parseable Unix timestamp that
    predates the cutoff; other files are left untouched.

    Returns the number of files deleted.
    """
    import time as _time

    if not os.path.exists(scrapes_dir):
        return 0

    cutoff_ts = _time.time() - keep_days * 86400
    deleted = 0
    try:
        for fname in os.listdir(scrapes_dir):
            if not fname.endswith(".db.json") and not fname.endswith(".session.json"):
                continue
            prefix = fname.split(".")[0]
            try:
                file_ts = int(prefix)
            except ValueError:
                continue   # skip files without a numeric timestamp prefix
            if file_ts < cutoff_ts:
                try:
                    os.remove(os.path.join(scrapes_dir, fname))
                    deleted += 1
                except OSError as e:
                    logger.warning("Could not remove old staging file %s: %s", fname, e)
    except OSError as e:
        logger.warning("Could not list scrapes dir for pruning %s: %s", scrapes_dir, e)

    if deleted:
        logger.info("Pruned %d staging file(s) older than %d days", deleted, keep_days)
    return deleted


def get_staged_content_hash(file_path: str, article_id: str):
    """Return the MD5(title + text) hash of a stored article, or None if not found.

    Used by cross-session dedup to detect updated articles: same URL (same id)
    but changed body → different hash → treat as new, re-publish to Curator.

    Returns:
        str: MD5 hex digest of the stored (title + text) if found.
        None: if the article is not in this file, or if the file is unreadable.
    """
    import hashlib
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        records = (
            data.get("_default", {}).values() if isinstance(data, dict) else data
        )
        for rec in records:
            if rec.get("id") == article_id:
                title = rec.get("title", "") or ""
                text  = rec.get("text",  "") or ""
                return hashlib.md5((title + text).encode("utf-8")).hexdigest()
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not read staging file %s: %s", file_path, e)
    return None
