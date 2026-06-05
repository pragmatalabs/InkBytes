"""LLM service — wraps Anthropic via `instructor` for structured outputs.

If ANTHROPIC_API_KEY is not set, falls back to a deterministic stub so the
pipeline can be developed offline (D2). Real calls land on D3.

Error taxonomy
--------------
LlmQuotaError   — monthly spend cap reached (HTTP 400 "usage limits").
                  Non-retryable; raised immediately without hitting instructor's
                  retry loop. The caller should requeue the article and stop
                  consuming until the quota resets.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from core.config import LlmCfg, PLACEHOLDER
from services.cost_meter import CostMeter

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LlmQuotaError(RuntimeError):
    """Raised immediately when the Anthropic API monthly spend limit is reached.

    Not retryable — the limit is a hard wall until the reset date embedded in
    the error message. Callers should requeue pending work and stop consuming.
    """

# Map response_model -> short call label for cost attribution.
_CALL_LABELS = {"EnrichmentResult": "enrich", "PageV1": "synth"}


class LlmService:
    def __init__(self, cfg: LlmCfg) -> None:
        self.cfg = cfg
        self._client = None
        self._stub_mode = cfg.api_key in (PLACEHOLDER, "LOCAL_DEV_UNSET", "")
        self.meter = CostMeter(cfg.price_in_per_mtok, cfg.price_out_per_mtok)
        if self._stub_mode:
            logger.warning("LlmService running in STUB mode (no ANTHROPIC_API_KEY)")
        else:
            self._client = self._build_client()

    def _build_client(self):
        # Late import so the package installs without anthropic when stubbing.
        # AsyncAnthropic (not Anthropic) so we can `await client.messages.create(...)`.
        import instructor
        from anthropic import AsyncAnthropic, BadRequestError
        from tenacity import retry_if_not_exception_type, stop_after_attempt

        # Do NOT retry HTTP 400 errors (BadRequestError) — they are permanent
        # failures: usage limits, invalid requests, bad prompts.  Only transient
        # errors (network blips, 5xx) should be retried.
        return instructor.from_anthropic(
            AsyncAnthropic(api_key=self.cfg.api_key),
            max_retries=instructor.Retrying(
                stop=stop_after_attempt(3),
                retry=retry_if_not_exception_type(BadRequestError),
                reraise=True,
            ),
        )

    # ------------------------------------------------------------------
    @staticmethod
    def load_prompt(name: str) -> str:
        """Load a prompt file from prompts/<name>.md."""
        here = Path(__file__).resolve().parent.parent
        p = here / "prompts" / f"{name}.md"
        return p.read_text(encoding="utf-8")

    async def structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_content: str,
        response_model: type[T],
        max_tokens: int,
        event_id: str | None = None,
    ) -> T:
        """Run a structured LLM call. Returns a validated `response_model` instance.

        `event_id` is optional context recorded with the call's token usage
        (Phase 2.2). It is None for enrich (no event exists yet) and the
        cluster's event id for synthesize.
        """
        if self._stub_mode:
            return _stub_response(response_model, user_content)

        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            temperature=self.cfg.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            response_model=response_model,
        )
        label = _CALL_LABELS.get(response_model.__name__, response_model.__name__)

        # Prefer create_with_completion so we can read real token usage for cost
        # accounting. Fall back to plain create() if this instructor build lacks
        # it — accounting must never break a real call.
        messages_api = self._client.messages  # type: ignore[union-attr]
        try:
            if hasattr(messages_api, "create_with_completion"):
                result, completion = await messages_api.create_with_completion(**kwargs)
                try:
                    usage = completion.usage
                    self.meter.record(
                        label, usage.input_tokens, usage.output_tokens,
                        model=model, event_id=event_id,
                    )
                except Exception:
                    logger.debug("token usage unavailable on completion", exc_info=True)
                return result

            return await messages_api.create(**kwargs)

        except Exception as exc:
            # Surface API quota exhaustion as LlmQuotaError immediately — no
            # point retrying a hard monthly spend cap (the retry config already
            # skips BadRequestError, but instructor may wrap it).
            raw = str(exc).lower()
            if "usage limits" in raw or "you have reached" in raw:
                raise LlmQuotaError(str(exc)) from exc
            raise


# ─────────────────────────────────────────────── stubs ──────────────
def _stub_response(model: type[T], user_content: str) -> T:
    """Deterministic, schema-valid stub response for offline dev."""
    # We rely on the response model being one of the two we know about.
    from contracts.enriched_v1 import EnrichmentResult, Entity
    from contracts.page_v1 import PageV1, EvidenceItem

    if model is EnrichmentResult:
        return EnrichmentResult(  # type: ignore[return-value]
            topic="General News",
            summary_50w=(user_content[:200].replace("\n", " ").strip() + "...")[:300],
            sentiment="neutral",
            factuality=0.7,
            keywords_canonical=["news", "stub"],
            entities=[Entity(name="Stubbed Entity", type="OTHER", salience=0.3)],
        )
    if model is PageV1:
        return PageV1(  # type: ignore[return-value]
            headline="Stub one-pager (offline dev)",
            synthesis_md=(
                "_Curator is running in offline-stub mode because "
                "ANTHROPIC_API_KEY is not set. Real synthesis lands on D3._\n\n"
                + user_content[:500]
            ),
            evidence_rail=[
                EvidenceItem(
                    source_name="Stub Source 1",
                    url="https://example.com/1",
                    quote="Quote from source 1.",
                ),
                EvidenceItem(
                    source_name="Stub Source 2",
                    url="https://example.com/2",
                    quote="Quote from source 2.",
                ),
            ],
            entities_top=["Stub Entity"],
        )
    raise NotImplementedError(f"No stub for response_model={model!r}")
