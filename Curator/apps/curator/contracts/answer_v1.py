"""Structured output schema for the corpus chat assistant (ADR-0022).

The LLM returns ONLY the prose (`answer_md`) with `[n]` citation markers. The
numbered source list is assembled deterministically by AssistantSkill from the
retrieved published-event candidates — the model never emits URLs, so it cannot
hallucinate a source.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AnswerV1(BaseModel):
    """LLM output: a grounded answer citing sources by number, e.g. '… [2][5]'."""

    answer_md: str = Field(
        ...,
        description="Markdown answer grounded ONLY in the provided sources, "
                    "citing them inline as [n]. Plain prose / bullet list.",
    )
