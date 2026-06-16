"""Structured output schema for Skill 1 (ENRICH).

The Haiku call returns one of these. `instructor` validates the JSON
against this model and re-prompts on failure, so we don't have to
hand-write JSON parsers.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EntityType = Literal["PERSON", "ORG", "LOC", "EVENT", "OTHER"]
Sentiment  = Literal["positive", "neutral", "negative"]
# Broad UI-facing buckets. Widened 8 → 15 (Curator ADR-0032, item 1) using
# Julian's IPTC-aligned ontology: tech split into technology+science, culture
# split into culture+entertainment, plus crime/education/lifestyle/religion/
# disaster. The original 8 are all a strict subset, so legacy rows stay valid.
Theme      = Literal[
    "politics", "world", "business", "technology", "science",
    "health", "sports", "culture", "entertainment", "environment",
    "crime", "education", "lifestyle", "religion", "disaster",
]


class Entity(BaseModel):
    name: str = Field(..., max_length=120, description="Canonical surface form")
    type: EntityType
    salience: float = Field(default=0.5, ge=0.0, le=1.0)


class EnrichmentResult(BaseModel):
    """What ENRICH produces per article."""

    theme: Theme = Field(
        ...,
        description=(
            "Broad thematic bucket. Pick the single best fit from: politics, "
            "world, business, technology, science, health, sports, culture, "
            "entertainment, environment, crime, education, lifestyle, religion, "
            "disaster."
        ),
    )
    # Granular IPTC-grounded category (Julian's 33-cat ontology, Curator
    # ADR-0032 item 1). Free text so `instructor` never re-prompts on a near-
    # miss; normalized to the canonical 33 set in Python (services/taxonomy.py)
    # before persistence, with the 634→33 bridge as the deterministic fallback
    # when the model abstains (null). Drives Backoffice / future per-category
    # drill-down — distinct from the broad `theme`.
    article_category: str | None = Field(
        default=None,
        max_length=60,
        description=(
            "Granular news category, picked from the supplied 33-category list "
            "(use the broadest fitting label). Return null if none clearly fits."
        ),
    )
    topic: str = Field(..., max_length=80, description="One short topic label. Title case.")
    summary_50w: str = Field(..., description="≤ 50-word neutral summary")
    sentiment: Sentiment
    factuality: float = Field(
        ..., ge=0.0, le=1.0,
        description="0=pure opinion, 1=fully sourced factual reporting",
    )
    keywords_canonical: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Up to 10 lowercase short phrases describing what the article is about.",
    )
    entities: list[Entity] = Field(default_factory=list, max_length=30)
