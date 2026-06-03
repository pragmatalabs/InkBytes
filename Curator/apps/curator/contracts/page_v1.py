"""Structured output schema for Skill 3 (SYNTHESIZE)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source_name: str = Field(..., description="Outlet display name")
    url: str
    quote: str = Field(..., max_length=400, description="≤ 400 chars literal quote")


class PageV1(BaseModel):
    """The reader-facing one-pager Synthesize produces."""

    headline: str = Field(..., max_length=140)
    synthesis_md: str = Field(..., description="Markdown, 200–250 words, neutral tone")
    evidence_rail: list[EvidenceItem] = Field(..., min_length=2, max_length=8)
    entities_top: list[str] = Field(default_factory=list, max_length=8)
