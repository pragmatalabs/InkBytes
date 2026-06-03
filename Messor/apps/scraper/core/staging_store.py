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
