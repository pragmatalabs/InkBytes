"""Pydantic v2 models for the cross-service event contracts.

These mirror what each upstream service produces. We don't import them
from a shared package because Messor's shared package is pydantic v1 and
Curator runs on v2 — a deliberate boundary (see ADR-0001).
"""
from contracts.article_v1 import ArticleV1, ArticleScrapedEvent
from contracts.enriched_v1 import EnrichmentResult, Entity
from contracts.page_v1 import EvidenceItem, PageV1

__all__ = [
    "ArticleV1",
    "ArticleScrapedEvent",
    "EnrichmentResult",
    "Entity",
    "EvidenceItem",
    "PageV1",
]
