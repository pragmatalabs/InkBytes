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
Theme      = Literal[
    "politics", "business", "technology", "sports",
    "health",   "environment", "culture",  "world",
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
            "Broad thematic bucket. Pick the single best fit from: "
            "politics, business, technology, sports, health, environment, culture, world."
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
