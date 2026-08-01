"""LLM service — wraps Anthropic, OpenAI, or DeepSeek via `instructor` for structured outputs.

If the relevant API key is not set, falls back to a deterministic stub so the
pipeline can be developed offline (D2). Real calls land on D3.

Providers
---------
anthropic (default) — AsyncAnthropic via instructor.from_anthropic.
openai              — AsyncOpenAI via instructor.from_openai. Switch via
                      llm.provider=openai in config or the Backoffice live
                      setting `llm_provider`. Key: OPENAI_API_KEY (env only).
deepseek            — AsyncOpenAI pointed at https://api.deepseek.com/v1 (OpenAI-
                      compatible endpoint). Key: DEEPSEEK_API_KEY (env only).
                      Models: deepseek-v4-flash, deepseek-v4-pro.
openrouter          — AsyncOpenAI pointed at https://openrouter.ai/api/v1 (OpenAI-
                      compatible aggregator). Key: OPENROUTER_API_KEY (env only).
                      Namespaced models, e.g. deepseek/deepseek-v4-flash. Used to
                      route to DeepSeek (or any model) through one account for
                      quota resilience. JSON mode, like deepseek.

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


def _signature(cfg: LlmCfg) -> tuple:
    """Return the fields that identify a unique client configuration.

    Used by `LlmService.reconfigure` to detect whether a rebuild is needed:
    if the signature is the same the provider/models haven't changed (only
    api_key / price fields might have drifted, which are applied in-place).

    base_url MUST be in the signature: it is baked into the AsyncOpenAI client
    at build time, so a base_url-only change (e.g. flipping the endpoint when
    switching provider via Backoffice) has to force a client rebuild. Omitting
    it meant a live provider flip could keep pointing at the OLD endpoint until
    a container restart — the OpenRouter switch hit exactly this (2026-07-28).
    """
    return (cfg.provider, cfg.enrich_model, cfg.synthesize_model, cfg.base_url)


def _build_client(cfg: LlmCfg):
    """Factory: build an instructor-wrapped async LLM client from cfg.

    Supports provider='anthropic' (default) and provider='openai'.
    Returns None when the relevant API key is a placeholder (stub mode).
    Raises if an unsupported provider is requested.
    """
    provider = cfg.provider

    if provider == "anthropic":
        if cfg.api_key in (PLACEHOLDER, "LOCAL_DEV_UNSET", ""):
            return None  # stub mode
        import instructor
        from anthropic import AsyncAnthropic, BadRequestError
        from tenacity import Retrying, retry_if_not_exception_type, stop_after_attempt

        logger.info("LlmService using Anthropic provider (model=%s)", cfg.enrich_model)
        # Build without passing max_retries as a kwarg — instructor 1.15 leaks
        # kwarg-max_retries into the underlying Anthropic SDK call, causing a
        # "multiple values" TypeError. Set it as an attribute after construction.
        client = instructor.from_anthropic(AsyncAnthropic(api_key=cfg.api_key))
        # Do NOT retry HTTP 400 errors (BadRequestError) — they are permanent
        # failures (usage limits, invalid prompts). Only transient errors retry.
        client.max_retries = Retrying(
            stop=stop_after_attempt(3),
            retry=retry_if_not_exception_type(BadRequestError),
            reraise=True,
        )
        return client

    # ── OpenAI-compatible providers (openai, deepseek, groq, together, …) ──────
    # All non-Anthropic providers use the AsyncOpenAI client. The API key and
    # base_url are resolved per provider, with cfg.base_url as a DB override that
    # takes precedence over the provider's built-in default endpoint.
    if provider == "deepseek":
        api_key   = cfg.deepseek_api_key
        # DeepSeek default; overridden by cfg.base_url if the admin set one.
        base_url  = cfg.base_url or "https://api.deepseek.com/v1"
    elif provider == "openrouter":
        # OpenRouter (https://openrouter.ai) is an OpenAI-compatible aggregator.
        # Same wire protocol as OpenAI; models are namespaced ("deepseek/deepseek-v4-flash").
        # Key: OPENROUTER_API_KEY (env only). Lets us route to DeepSeek (or any
        # OpenRouter model) through a single account for quota resilience.
        api_key   = cfg.openrouter_api_key
        base_url  = cfg.base_url or "https://openrouter.ai/api/v1"
    else:
        # openai, groq, together, mistral, or any other OpenAI-compatible provider.
        api_key   = cfg.openai_api_key
        base_url  = cfg.base_url or None   # None → AsyncOpenAI uses its built-in default

    if api_key in (PLACEHOLDER, "LOCAL_DEV_UNSET", "", None):
        return None  # stub mode — no key configured

    import instructor
    from openai import AsyncOpenAI, BadRequestError as OpenAIBadRequestError
    from tenacity import Retrying, retry_if_not_exception_type, stop_after_attempt

    # DeepSeek R1 (deepseek-reasoner) uses "thinking mode" which rejects
    # tool_choice — the default instructor Mode.TOOLS won't work. Use
    # Mode.JSON for all DeepSeek models so both deepseek-chat (V3) and
    # deepseek-reasoner (R1) are supported. OpenAI and other providers keep
    # the default TOOLS mode.
    if provider in ("deepseek", "openrouter"):
        # DeepSeek models reject tool_choice (thinking mode); we route DeepSeek
        # via OpenRouter too, so JSON mode is the safe default for both.
        mode = instructor.Mode.JSON
    else:
        mode = instructor.Mode.TOOLS   # OpenAI default; supports tool_choice

    logger.info(
        "LlmService using %s provider (model=%s, base_url=%s, mode=%s)",
        provider, cfg.enrich_model, base_url or "default", mode.value,
    )
    oa_kwargs: dict = {"api_key": api_key}
    if base_url:
        oa_kwargs["base_url"] = base_url
    client = instructor.from_openai(AsyncOpenAI(**oa_kwargs), mode=mode)
    client.max_retries = Retrying(
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type(OpenAIBadRequestError),
        reraise=True,
    )
    return client


_UNSET = {PLACEHOLDER, "LOCAL_DEV_UNSET", "", None}

def _is_stub_mode(cfg: LlmCfg) -> bool:
    """Return True when the relevant API key is unset for the chosen provider."""
    if cfg.provider == "anthropic":
        return cfg.api_key in _UNSET
    if cfg.provider == "deepseek":
        return cfg.deepseek_api_key in _UNSET
    if cfg.provider == "openrouter":
        return cfg.openrouter_api_key in _UNSET
    # openai, groq, together, mistral, and any other OpenAI-compatible provider.
    return cfg.openai_api_key in _UNSET


class LlmService:
    def __init__(self, cfg: LlmCfg) -> None:
        self.cfg = cfg
        # Lazily-built direct-DeepSeek client for the OpenRouter→DeepSeek provider
        # fallback (built on first quota failure; rebuilt if the key/base_url change).
        self._fallback_client = None
        self._fallback_client_sig: tuple | None = None
        self._stub_mode = _is_stub_mode(cfg)
        self._signature = _signature(cfg)
        self.meter = CostMeter(
            cfg.price_in_per_mtok,
            cfg.price_out_per_mtok,
            getattr(cfg, "price_cache_hit_per_mtok", None),
            peak_pricing=getattr(cfg, "deepseek_peak_pricing", False),
            model_prices=getattr(cfg, "model_prices", None),
        )
        if self._stub_mode:
            logger.warning(
                "LlmService running in STUB mode (no API key for provider=%s)",
                cfg.provider,
            )
            self._client = None
        else:
            self._client = _build_client(cfg)

    async def close(self) -> None:
        """Close the underlying HTTP transport.

        instructor wraps a provider SDK (AsyncOpenAI / AsyncAnthropic).  Those
        clients hold an httpx AsyncClient whose transport must be explicitly
        closed — otherwise the event loop emits
        'RuntimeWarning: coroutine AsyncClient.aclose was never awaited'
        on shutdown.  instructor exposes the raw provider client as .client.
        """
        if self._client is None:
            return
        inner = getattr(self._client, "client", None)
        if inner is None:
            return
        aclose = getattr(inner, "aclose", None) or getattr(
            getattr(inner, "_client", None), "aclose", None
        )
        if callable(aclose):
            try:
                await aclose()
            except Exception:  # pragma: no cover — best-effort cleanup
                pass

    def reconfigure(self, cfg: LlmCfg) -> dict:
        """Hot-swap the LLM client when the provider or models change.

        Mirrors the pattern in EmbeddingService.reconfigure (ADR-0004).
        Synchronous — no network probe needed for the LLM client.

        Returns:
            {"changed": False}                                — same signature
            {"changed": True, "applied": True}               — rebuilt OK
            {"changed": True, "applied": False, "reason": "build_failed",
             "error": str}                                    — rebuild failed
        """
        new_sig = _signature(cfg)
        if new_sig == self._signature:
            # Signature unchanged — update cfg in place (refreshes api keys).
            # Re-evaluate stub mode: the API key may have been set or cleared
            # without changing the provider/model (the signature fields).
            old_stub = self._stub_mode
            self.cfg = cfg
            new_stub = _is_stub_mode(cfg)
            if new_stub != old_stub:
                self._stub_mode = new_stub
                if not new_stub:
                    # Key arrived — build a real client now.
                    try:
                        self._client = _build_client(cfg)
                        logger.info(
                            "LlmService exited STUB mode: key set for provider=%s"
                            " (enrich=%s synth=%s stub=False)",
                            cfg.provider, cfg.enrich_model, cfg.synthesize_model,
                        )
                    except Exception as exc:
                        # Keep stub running rather than crashing.
                        self._stub_mode = True
                        logger.error(
                            "LlmService failed to exit stub mode (provider=%s): %s",
                            cfg.provider, exc,
                        )
                else:
                    # Key was cleared — drop back to stub.
                    self._client = None
                    logger.warning(
                        "LlmService entered STUB mode: key cleared for provider=%s",
                        cfg.provider,
                    )
            return {"changed": False}

        # Signature changed — attempt to rebuild the client.
        try:
            new_client = _build_client(cfg)
            new_stub = _is_stub_mode(cfg)
        except Exception as exc:
            logger.error(
                "LlmService reconfigure failed (provider=%s): %s",
                cfg.provider, exc,
            )
            return {"changed": True, "applied": False, "reason": "build_failed", "error": str(exc)}

        self._client = new_client
        self._stub_mode = new_stub
        self._signature = new_sig
        self.cfg = cfg
        logger.info(
            "LlmService reconfigured: provider=%s enrich_model=%s synthesize_model=%s stub=%s",
            cfg.provider, cfg.enrich_model, cfg.synthesize_model, new_stub,
        )
        return {"changed": True, "applied": True}

    # ------------------------------------------------------------------
    @staticmethod
    def load_prompt(name: str) -> str:
        """Load a prompt file from prompts/<name>.md."""
        here = Path(__file__).resolve().parent.parent
        p = here / "prompts" / f"{name}.md"
        return p.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        """True when an exception looks like provider quota / credit exhaustion.

        Covers Anthropic ("usage limits", "you have reached"), OpenAI
        ("exceeded ... quota", "insufficient_quota") and OpenRouter
        ("insufficient credits", HTTP 402). NOT transient rate limits (429) —
        those are left to the tenacity retry.
        """
        raw = str(exc).lower()
        return (
            "usage limits" in raw
            or "you have reached" in raw
            or ("exceeded" in raw and "quota" in raw)
            or "insufficient_quota" in raw
            or "insufficient credits" in raw
            or "insufficient_credits" in raw
            or ("402" in raw and ("credit" in raw or "quota" in raw or "payment" in raw))
        )

    def _deepseek_fallback_client(self):
        """Lazily build + cache a DIRECT-DeepSeek instructor client, used as a
        provider-level fallback when OpenRouter is out of credits/quota.

        Returns None when the fallback is disabled or no DeepSeek key is set.
        Rebuilt when the key/base_url change (tracked via a small signature) so a
        Backoffice key rotation is picked up on the next call.
        """
        if not getattr(self.cfg, "openrouter_deepseek_fallback", False):
            return None
        key = self.cfg.deepseek_api_key
        if key in _UNSET:
            return None
        base = getattr(self.cfg, "deepseek_fallback_base_url", None) or "https://api.deepseek.com/v1"
        sig = (key, base)
        if self._fallback_client is not None and self._fallback_client_sig == sig:
            return self._fallback_client
        import instructor
        from openai import AsyncOpenAI, BadRequestError as OpenAIBadRequestError
        from tenacity import Retrying, retry_if_not_exception_type, stop_after_attempt
        client = instructor.from_openai(
            AsyncOpenAI(api_key=key, base_url=base), mode=instructor.Mode.JSON
        )
        client.max_retries = Retrying(
            stop=stop_after_attempt(2),
            retry=retry_if_not_exception_type(OpenAIBadRequestError),
            reraise=True,
        )
        self._fallback_client = client
        self._fallback_client_sig = sig
        logger.info("Built direct-DeepSeek fallback client (base_url=%s)", base)
        return client

    def _deepseek_fallback_model(self, model: str) -> str:
        """Translate an OpenRouter slug to its direct-DeepSeek id.

        `deepseek/deepseek-v4-flash` → `deepseek-v4-flash`. A non-DeepSeek
        OpenRouter model has no direct equivalent → use the configured default.
        """
        if model and model.startswith("deepseek/"):
            return model.split("/", 1)[1]
        return getattr(self.cfg, "deepseek_fallback_model", None) or "deepseek-v4-flash"

    def _build_call_kwargs(self, provider: str, model: str, *, system_prompt: str,
                           user_content: str, response_model, max_tokens: int,
                           label: str) -> dict:
        """Build provider-correct call kwargs. Anthropic takes a top-level
        `system=`; OpenAI-compatible providers fold it into the messages. When
        the (fallback) provider is OpenRouter, attach the per-task `models` array
        so OpenRouter itself degrades across the chain. Used for BOTH the primary
        call and the ADR-0044 failover call so a cross-provider failover is
        wire-correct (e.g. deepseek → openrouter)."""
        if provider == "anthropic":
            messages = [{"role": "user", "content": user_content}]
            extra = {"system": system_prompt}
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            extra = {}
        kwargs = dict(
            model=model, max_tokens=max_tokens, temperature=self.cfg.temperature,
            messages=messages, response_model=response_model, **extra,
        )
        if provider == "openrouter":
            fallbacks = (
                self.cfg.enrich_fallbacks if label == "enrich"
                else self.cfg.synthesize_fallbacks
            )
            chain = [model, *[m for m in (fallbacks or []) if m and m != model]]
            if len(chain) > 1:
                kwargs["extra_body"] = {"models": chain}
        return kwargs

    def _fallback_model(self, model: str) -> str:
        """Translate the active model to the generic fallback provider's id.

        openrouter → namespace a bare id (`deepseek-chat` → `deepseek/deepseek-chat`);
        deepseek/openai → strip a namespace; anthropic → a Haiku default. An
        explicit cfg.fallback_model always wins.
        """
        explicit = getattr(self.cfg, "fallback_model", "") or ""
        if explicit:
            return explicit
        fb = (getattr(self.cfg, "fallback_provider", "") or "").lower()
        if fb == "openrouter":
            return model if "/" in model else f"deepseek/{model}"
        if fb in ("deepseek", "openai"):
            return model.split("/", 1)[1] if "/" in model else model
        if fb == "anthropic":
            return "claude-haiku-4-5"
        return model

    def _resolve_fallback(self, model: str):
        """Return (client, fb_provider, fb_model) for a quota/credit failover, or
        None. Prefers the generic ADR-0044 fallback_provider (any primary → a
        different account); falls back to the legacy openrouter→direct-DeepSeek
        path when only that is configured."""
        primary = (self.cfg.provider or "").lower()
        fb = (getattr(self.cfg, "fallback_provider", "") or "").lower()
        # Generic failover (ADR-0044): active provider → configured fallback.
        if fb and fb != primary:
            # Build a provider-swapped cfg copy and reuse _build_client. Clear
            # base_url — it is the PRIMARY provider's endpoint; the fallback must
            # use its own default (or its own override, absent here).
            fb_cfg = self.cfg.model_copy(update={"provider": fb, "base_url": None})
            if _is_stub_mode(fb_cfg):   # fallback provider has no API key set
                logger.warning("ADR-0044 fallback_provider=%s set but has no API key — "
                               "cannot fail over", fb)
                return None
            sig = ("gen", fb, fb_cfg.deepseek_api_key, fb_cfg.openrouter_api_key,
                   fb_cfg.api_key, fb_cfg.openai_api_key)
            if self._fallback_client is None or self._fallback_client_sig != sig:
                self._fallback_client = _build_client(fb_cfg)
                self._fallback_client_sig = sig
                logger.info("Built '%s' fallback client (ADR-0044 generic failover)", fb)
            return (self._fallback_client, fb, self._fallback_model(model))
        # Legacy failover: OpenRouter primary out of credits → direct DeepSeek.
        if primary == "openrouter":
            legacy = self._deepseek_fallback_client()
            if legacy is not None:
                return (legacy, "deepseek", self._deepseek_fallback_model(model))
        return None

    async def _run_structured(self, client, kwargs: dict, label: str,
                              model: str, event_id: str | None):
        """Execute one structured call on `client`, metering token usage."""
        messages_api = client.messages
        if hasattr(messages_api, "create_with_completion"):
            result, completion = await messages_api.create_with_completion(**kwargs)
            self._record_usage(completion, label, model, event_id)
            return result
        return await messages_api.create(**kwargs)

    def _record_usage(self, completion, label: str, model: str,
                      event_id: str | None) -> None:
        """Read the provider's token usage off a completion and meter it."""
        try:
            usage = completion.usage
            # Anthropic: input_tokens/output_tokens · OpenAI: prompt/completion_tokens
            in_tok = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", 0)
            out_tok = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", 0)
            # Cache-hit input tokens, billed cheaper (ADR-0028). DeepSeek:
            # prompt_cache_hit_tokens · OpenAI-compat: prompt_tokens_details.cached_tokens
            # · Anthropic: cache_read_input_tokens.
            details = getattr(usage, "prompt_tokens_details", None)
            cache_hit = (
                getattr(usage, "prompt_cache_hit_tokens", None)
                if getattr(usage, "prompt_cache_hit_tokens", None) is not None
                else getattr(details, "cached_tokens", None)
                if details is not None
                else getattr(usage, "cache_read_input_tokens", None)
            ) or 0
            self.meter.record(
                label, in_tok, out_tok,
                cache_hit_tokens=int(cache_hit), model=model, event_id=event_id,
            )
        except Exception:
            logger.debug("token usage unavailable on completion", exc_info=True)

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

        provider = (self.cfg.provider or "anthropic").lower()
        label = _CALL_LABELS.get(response_model.__name__, response_model.__name__)
        kwargs = self._build_call_kwargs(
            provider, model, system_prompt=system_prompt, user_content=user_content,
            response_model=response_model, max_tokens=max_tokens, label=label,
        )

        # Prefer create_with_completion (real token usage for cost accounting);
        # _run_structured falls back to plain create() if unavailable.
        try:
            return await self._run_structured(self._client, kwargs, label, model, event_id)
        except Exception as exc:
            is_quota = self._is_quota_error(exc)
            # ADR-0044 provider-level failover: the active provider hit a credit/
            # quota wall → retry the SAME call on a DIFFERENT account (generic
            # fallback_provider, or the legacy openrouter→deepseek path). This is
            # what keeps the feed alive when e.g. the DeepSeek balance hits $0
            # (the 2026-08-01 freeze) instead of halting the worker.
            if is_quota:
                resolved = self._resolve_fallback(model)
                if resolved is not None:
                    fb_client, fb_provider, fb_model = resolved
                    fb_kwargs = self._build_call_kwargs(
                        fb_provider, fb_model, system_prompt=system_prompt,
                        user_content=user_content, response_model=response_model,
                        max_tokens=max_tokens, label=label,
                    )
                    logger.warning(
                        "Provider '%s' quota/credit wall — failing over to '%s' "
                        "(model=%s). cause=%s", provider, fb_provider, fb_model,
                        str(exc)[:160],
                    )
                    try:
                        return await self._run_structured(
                            fb_client, fb_kwargs, label, fb_model, event_id)
                    except Exception as exc2:
                        if self._is_quota_error(exc2):
                            raise LlmQuotaError(
                                f"'{provider}' primary AND '{fb_provider}' fallback "
                                f"BOTH quota-exhausted: {exc2}"
                            ) from exc2
                        raise
                # No fallback available — surface a hard quota wall as
                # LlmQuotaError. Caller requeues the article + pauses the worker.
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
            theme="world",
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
