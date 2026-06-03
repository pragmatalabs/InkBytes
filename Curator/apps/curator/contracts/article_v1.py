"""inkbytes.article.v1 — Messor → Curator event contract.

See Messor/docs/contracts.md §1 and §2 for the authoritative spec.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class _Outlet(BaseModel):
    id: str
    name: str


class ArticleV1(BaseModel):
    """The article payload Messor produces. Subset of the kitchen-sink
    Article model in the shared inkbytes package."""

    id: str
    outlet: _Outlet

    url: str
    canonical_url: str | None = None
    title: str
    text: str
    language: str
    published_at: datetime | None = None
    scraped_at: datetime
    word_count: int

    authors: list[str] = Field(default_factory=list)
    meta_categories: list[str] = Field(default_factory=list)
    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArticleScrapedEvent(BaseModel):
    """The RabbitMQ envelope on `event.article.scraped`."""

    schema_: str = Field(alias="schema", default="inkbytes.article.v1")
    session_id: str
    article: ArticleV1
    spaces_key: str

    model_config = {"populate_by_name": True}
