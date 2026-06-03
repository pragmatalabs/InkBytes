"""Real LLM token-usage and cost accounting.

Records the `usage` reported by each Anthropic completion and logs a running
total plus a projected cost-per-1000-articles. "Articles" is inferred from the
number of ENRICH calls (the pipeline runs exactly one ENRICH per article), so
the projection converges to the true per-1000 figure as a real harvest runs.

Costs use the per-model list prices in LlmCfg (price_in/out_per_mtok). Switch
those to your batch rates if you run via the Batch API.

This replaces the char-count estimate with measured tokens. See cost
discussion / incident notes 2026-06-02.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class _Bucket:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class CostMeter:
    """Thread-safe accumulator of token usage and cost, by call label."""

    def __init__(self, price_in_per_mtok: float, price_out_per_mtok: float) -> None:
        self._in_price = price_in_per_mtok
        self._out_price = price_out_per_mtok
        self._lock = threading.Lock()
        self._buckets: dict[str, _Bucket] = {}

    def record(self, label: str, input_tokens: int, output_tokens: int) -> None:
        """Record one completed call and log the running cost."""
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
