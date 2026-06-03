"""Real LLM token-usage and cost accounting.

Records the `usage` reported by each Anthropic completion and logs a running
total plus a projected cost-per-1000-articles. "Articles" is inferred from the
number of ENRICH calls (the pipeline runs exactly one ENRICH per article), so
the projection converges to the true per-1000 figure as a real harvest runs.

Costs use the per-model list prices in LlmCfg (price_in/out_per_mtok). Switch
those to your batch rates if you run via the Batch API.

This replaces the char-count estimate with measured tokens. See cost
discussion / incident notes 2026-06-02.

Phase 2.2: in addition to the in-memory totals + log line (unchanged), each
completed call is persisted to `backoffice.model_usage` via an optional async
DB sink. The DB write is fire-and-forget and fully non-fatal — a logging/DB
failure must never break the pipeline.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# Async sink that persists one completed call. Signature mirrors
# DatabaseService.record_model_usage's keyword args.
UsageSink = Callable[..., Awaitable[None]]


@dataclass
class _Bucket:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class CostMeter:
    """Thread-safe accumulator of token usage and cost, by call label.

    Besides accumulating in memory and logging (the original behaviour), it can
    persist each call to a DB via an optional async ``sink`` set with
    :meth:`set_sink`. The sink is invoked fire-and-forget on the running event
    loop; any failure is logged and swallowed so accounting never breaks a
    real LLM call.
    """

    def __init__(self, price_in_per_mtok: float, price_out_per_mtok: float) -> None:
        self._in_price = price_in_per_mtok
        self._out_price = price_out_per_mtok
        self._lock = threading.Lock()
        self._buckets: dict[str, _Bucket] = {}
        self._sink: Optional[UsageSink] = None

    def set_sink(self, sink: Optional[UsageSink]) -> None:
        """Register (or clear) the async DB sink for per-call persistence."""
        self._sink = sink

    def _call_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            (input_tokens / 1_000_000) * self._in_price
            + (output_tokens / 1_000_000) * self._out_price
        )

    def record(
        self,
        label: str,
        input_tokens: int,
        output_tokens: int,
        *,
        model: str | None = None,
        event_id: str | None = None,
    ) -> None:
        """Record one completed call: in-memory totals + log line + DB sink.

        The in-memory accumulation and the COST log line are unchanged from the
        original meter. The DB persistence is ADDED alongside them and is
        non-fatal.
        """
        with self._lock:
            b = self._buckets.setdefault(label, _Bucket())
            b.calls += 1
            b.input_tokens += input_tokens
            b.output_tokens += output_tokens
            total = self._total_cost_locked()
            articles = self._buckets.get("enrich", _Bucket()).calls
            projected = (total / articles * 1000) if articles else 0.0
            logger.info(
                "COST %-6s in=%-6d out=%-5d | run-total=$%.4f over %d article(s)"
                " | projected $%.2f / 1000 articles",
                label, input_tokens, output_tokens, total, articles, projected,
            )

        # DB sink — outside the lock, fire-and-forget, never fatal.
        self._persist(label, input_tokens, output_tokens, model, event_id)

    def _persist(
        self,
        label: str,
        input_tokens: int,
        output_tokens: int,
        model: str | None,
        event_id: str | None,
    ) -> None:
        """Schedule the async DB write without blocking; swallow all errors."""
        sink = self._sink
        if sink is None:
            return
        cost = self._call_cost(input_tokens, output_tokens)

        async def _run() -> None:
            try:
                await sink(
                    call_label=label,
                    model=model or "unknown",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=round(cost, 6),
                    event_id=event_id,
                )
            except Exception:  # pragma: no cover - defensive
                logger.warning(
                    "model_usage persist failed for label=%s model=%s — "
                    "accounting only, pipeline unaffected.",
                    label, model, exc_info=True,
                )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (e.g. a sync test). Nothing to schedule onto;
            # the in-memory total + log already happened, so just skip the
            # DB write rather than block.
            logger.debug("no running event loop — skipping model_usage DB write")
            return
        loop.create_task(_run())

    def _bucket_cost(self, b: _Bucket) -> float:
        return (
            (b.input_tokens / 1_000_000) * self._in_price
            + (b.output_tokens / 1_000_000) * self._out_price
        )

    def _total_cost_locked(self) -> float:
        return sum(self._bucket_cost(b) for b in self._buckets.values())

    def snapshot(self) -> dict:
        """Return current totals (safe to expose via /status)."""
        with self._lock:
            articles = self._buckets.get("enrich", _Bucket()).calls
            total = self._total_cost_locked()
            return {
                "total_cost_usd": round(total, 4),
                "articles_seen": articles,
                "projected_usd_per_1000_articles": round(total / articles * 1000, 2)
                if articles else None,
                "by_label": {
                    label: {
                        "calls": b.calls,
                        "input_tokens": b.input_tokens,
                        "output_tokens": b.output_tokens,
                        "cost_usd": round(self._bucket_cost(b), 4),
                    }
                    for label, b in self._buckets.items()
                },
            }
