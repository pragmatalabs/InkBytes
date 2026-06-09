"""Corpus chat assistant (ADR-0022) — grounded digests & Q&A over PUBLISHED events.

Reuses the synthesis engine unchanged: retrieve published-event sources, hand
them to `LlmService.structured()` with `prompts/assistant.md`, return the cited
answer. Corpus is published events only, so every citation resolves to an
InkBytes event page and filtered junk never surfaces.

Two retrieval modes:
  • digest  ("resume" / "top10") — recent published events, ranked by the LLM.
  • chat    (free-form)          — pgvector ANN over published-event articles.
"""
from __future__ import annotations

import logging
import re

from contracts.answer_v1 import AnswerV1
from core.config import LlmCfg
from services.database_service import DatabaseService, _vector_literal
from services.embedding_service import EmbeddingService
from services.llm_service import LlmService

logger = logging.getLogger(__name__)

# Retrieval caps — keep the prompt (and cost) bounded.
_DIGEST_WINDOW_HOURS = 36
_DIGEST_LIMIT = 50
_CHAT_TOPK = 12
_SUMMARY_CHARS = 280
_MAX_QUESTION_CHARS = 500


class AssistantSkill:
    name = "assistant"

    def __init__(self, llm: LlmService, db: DatabaseService,
                 embed: EmbeddingService, llm_cfg: LlmCfg) -> None:
        self.llm = llm
        self.db = db
        self.embed = embed
        self.llm_cfg = llm_cfg
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        raw = LlmService.load_prompt("assistant")
        # Keep everything above the "## Input format" marker as the system prompt.
        return re.split(r"^## Input format", raw, flags=re.MULTILINE)[0].strip()

    async def answer(self, question: str, mode: str = "chat") -> dict:
        """Return {answer_md, sources:[{n,title,url,event_id,outlet}]}.

        mode: "resume" | "top10" | "chat" (free-form). "top10" carries its
        category in the question text (e.g. "top 10 in technology today").
        """
        question = (question or "").strip()[:_MAX_QUESTION_CHARS]

        if mode in ("resume", "top10"):
            sources = await self._retrieve_digest()
        else:
            sources = await self._retrieve_chat(question)

        if not sources:
            return {
                "answer_md": "I don't have InkBytes coverage on that yet.",
                "sources": [],
            }

        user_content = self._build_user_content(question, mode, sources)
        result = await self.llm.structured(
            model=self.llm_cfg.synthesize_model,
            system_prompt=self._system_prompt,
            user_content=user_content,
            response_model=AnswerV1,
            max_tokens=self.llm_cfg.max_tokens_synth,
        )
        logger.info("ASSISTANT mode=%s q=%r -> %d sources", mode, question[:60], len(sources))
        return {"answer_md": result.answer_md, "sources": sources}

    # ── retrieval ────────────────────────────────────────────────────────────

    async def _retrieve_digest(self) -> list[dict]:
        """Recent published events — the LLM ranks/filters by category."""
        rows = await self.db.pool.fetch(  # type: ignore[union-attr]
            f"""
            SELECT p.event_id,
                   p.headline,
                   LEFT(p.synthesis_md, {_SUMMARY_CHARS}) AS summary,
                   e.topic,
                   e.language,
                   (SELECT a.outlet_name FROM articles a
                     WHERE a.event_id = e.id AND a.outlet_name IS NOT NULL
                     ORDER BY a.scraped_at DESC LIMIT 1) AS outlet
              FROM pages p
              JOIN events e ON e.id = p.event_id
             WHERE p.published_at IS NOT NULL
               AND e.status = 'published'
               AND p.freshness_at > NOW() - INTERVAL '{_DIGEST_WINDOW_HOURS} hours'
             ORDER BY p.freshness_at DESC
             LIMIT {_DIGEST_LIMIT}
            """
        )
        return self._number(rows)

    async def _retrieve_chat(self, question: str) -> list[dict]:
        """pgvector ANN over published-event articles for a free-form question.

        Inner query keeps the NEAREST article per event (DISTINCT ON ordered by
        distance); outer query then ranks events by that nearest distance and
        takes the top-K. Ordering by distance must happen in the outer query —
        DISTINCT ON forces the inner ORDER BY to lead with event_id.
        """
        vec = await self.embed.embed(question)
        rows = await self.db.pool.fetch(  # type: ignore[union-attr]
            f"""
            SELECT event_id, headline, summary, topic, language, outlet
              FROM (
                SELECT DISTINCT ON (p.event_id)
                       p.event_id,
                       p.headline,
                       LEFT(p.synthesis_md, {_SUMMARY_CHARS}) AS summary,
                       e.topic,
                       e.language,
                       a.outlet_name AS outlet,
                       (a.embedding <=> $1::vector) AS dist
                  FROM articles a
                  JOIN events e ON e.id = a.event_id
                  JOIN pages  p ON p.event_id = e.id
                 WHERE p.published_at IS NOT NULL
                   AND e.status = 'published'
                   AND a.embedding IS NOT NULL
                 ORDER BY p.event_id, a.embedding <=> $1::vector ASC
              ) t
             ORDER BY t.dist ASC
             LIMIT {_CHAT_TOPK}
            """,
            _vector_literal(vec),
        )
        return self._number(rows)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _number(rows) -> list[dict]:
        out = []
        for i, r in enumerate(rows, start=1):
            out.append({
                "n": i,
                "event_id": r["event_id"],
                "title": r["headline"],
                "summary": (r["summary"] or "").strip(),
                "topic": r["topic"],
                "outlet": r["outlet"] or "",
                # The Reader links citations to the InkBytes event page.
                "url": f"/event/{r['event_id']}",
            })
        return out

    def _build_user_content(self, question: str, mode: str, sources: list[dict]) -> str:
        if mode == "resume":
            ask = "Give today's news resume from the sources below."
        elif mode == "top10":
            ask = (question or "List the top 10 items to consider today") + \
                  " — pick only from the sources below."
        else:
            ask = question
        lines = [ask, "", "SOURCES:"]
        for s in sources:
            tag = s["topic"] or s["outlet"] or "news"
            lines.append(f"[{s['n']}] {s['title']} — {tag}")
            if s["summary"]:
                lines.append(f"    {s['summary']}")
        return "\n".join(lines)
