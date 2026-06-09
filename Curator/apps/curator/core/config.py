"""Curator config — YAML defaults + env-var overlay + DB settings overlay.

Loading order:
  1. read env.yaml (or whatever was passed via --config)
  2. overlay any env var matching a known mapping (ANTHROPIC_API_KEY,
     OPENAI_API_KEY, DATABASE_URL, RABBITMQ_URL, S3_*)
  3. at runtime, overlay the tunables from `backoffice.curator_settings`
     (the Backoffice-owned row) — see `apply_db_settings()` / ADR-0004.

`__SET_VIA_ENV__` placeholders cause a fail-fast at boot if the
corresponding env var is not set.

Provider API keys are loaded from ENV ONLY (steps 1–2). Curator never reads
or decrypts the Laravel `backoffice.api_keys` table; that table is for the
Backoffice to manage/rotate/test keys. See
`docs/adr/0004-curator-config-from-db-keys-via-env.md`.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PLACEHOLDER = "__SET_VIA_ENV__"

# The columns Curator reads from backoffice.curator_settings, mapped to the
# (section, field) they overlay onto.
_DB_SETTINGS_MAP: dict[str, tuple[str, str]] = {
    "enrich_model":           ("llm", "enrich_model"),
    "synthesize_model":       ("llm", "synthesize_model"),
    "max_tokens_enrich":      ("llm", "max_tokens_enrich"),
    "max_tokens_synth":       ("llm", "max_tokens_synth"),
    "temperature":            ("llm", "temperature"),
    # LLM provider + custom base URL (OpenAI-compatible endpoint override).
    "llm_provider":           ("llm", "provider"),
    "llm_base_url":           ("llm", "base_url"),
    # API keys from Backoffice — override env vars only when non-null AND non-empty.
    # An empty string means "not set in Backoffice" → fall back to env var.
    # (Guarded by _API_KEY_COLUMNS below in apply_db_settings.)
    "anthropic_api_key":      ("llm", "api_key"),
    "openai_api_key":         ("llm", "openai_api_key"),
    "deepseek_api_key":       ("llm", "deepseek_api_key"),
    "embeddings_api_key":     ("embeddings", "api_key"),
    "similarity_threshold":   ("clustering", "similarity_threshold"),
    "entity_overlap_min":     ("clustering", "entity_overlap_min"),
    "min_sources_to_publish": ("clustering", "min_sources_to_publish"),
    "recent_window_hours":    ("clustering", "recent_window_hours"),
    "conclude_after_days":    ("clustering", "conclude_after_days"),
    # Processing kill-switch (Backoffice "Stop Curator").
    "processing_enabled":     ("application", "processing_enabled"),
    # Embeddings (ADR-0004). provider/model/base_url are live-overlaid; the
    # EmbeddingService rebuilds its client on change (with a dim-probe guard).
    # `dimensions` is deliberately NOT here — it's a pgvector column width, a
    # migration concern, not a hot-reload knob.
    "embeddings_provider":    ("embeddings", "provider"),
    "embeddings_model":       ("embeddings", "model"),
    "embeddings_base_url":    ("embeddings", "base_url"),
}

# Schema-qualified: Curator's asyncpg connection defaults to the `public`
# search_path, so the Backoffice-owned table MUST be qualified.
_DB_SETTINGS_TABLE = "backoffice.curator_settings"

# Columns that carry API keys.  An empty string in the DB means "not configured
# in Backoffice — use the env var instead."  We must NOT let "" overwrite a valid
# key that was already injected by _overlay_env (which would silently put the
# LlmService into stub mode).
_API_KEY_COLUMNS: frozenset[str] = frozenset({
    "anthropic_api_key",
    "openai_api_key",
    "deepseek_api_key",
    "embeddings_api_key",
})


class AppCfg(BaseModel):
    name: str = "Curator"
    version: str = "0.1.0"
    mode: str = "development"
    log_level: str = "INFO"
    max_concurrent_articles: int = 4
    # How often (seconds) the consumer re-reads backoffice.curator_settings so
    # an admin change takes effect without a redeploy. 0 disables polling.
    config_refresh_seconds: int = 30
    # Lead-image hotlink guard (ADR-0019): probe each og:image at ingest with a
    # browser request fingerprint and NULL out URLs a cross-origin <img> can't
    # render (CDN hotlink redirects to a 1×1 placeholder). False skips the
    # per-article network probe entirely.
    validate_lead_images: bool = True
    lead_image_probe_timeout_s: float = 4.0
    # Promotional / commerce content filter (ADR-0020): refuse to publish a page
    # whose synthesized headline is ad-style ("X Covers Top Gifts…") or whose
    # source cluster is a strict majority of shopping/affiliate articles (gift
    # guides, product reviews, deals). False disables the gate.
    filter_promotional: bool = True
    # Non-news filler filter (ADR-0021): refuse to publish a page whose cluster is
    # a strict majority horoscope / lottery-result / betting-pick filler, or whose
    # synthesized headline is filler. False disables the gate.
    filter_noise: bool = True
    # Processing kill-switch (Backoffice "Stop Curator"): when False the worker
    # pauses the enrich→cluster→synthesize pipeline — incoming articles are
    # requeued (never lost), the API keeps serving. Live-polled from
    # backoffice.curator_settings via the config-refresh loop (~30s latency).
    processing_enabled: bool = True


class LlmCfg(BaseModel):
    provider: str = "anthropic"
    enrich_model: str = "claude-haiku-4-5"
    synthesize_model: str = "claude-haiku-4-5"
    max_tokens_enrich: int = 1500
    max_tokens_synth: int = 2500
    temperature: float = 0.2
    api_key: str = PLACEHOLDER           # Anthropic key  — env: ANTHROPIC_API_KEY
    openai_api_key: str = PLACEHOLDER    # OpenAI key     — env: OPENAI_API_KEY;    provider=openai
    deepseek_api_key: str = PLACEHOLDER  # DeepSeek key   — env: DEEPSEEK_API_KEY;  provider=deepseek
    # Custom base URL for OpenAI-compatible providers (Groq, Together, DeepSeek, etc.).
    # When set via Backoffice, overrides the provider's built-in default endpoint.
    base_url: str | None = None
    # Standard list prices for cost accounting. Defaults = Claude Haiku 4.5
    # ($1/M input, $5/M output). Override in env if you use batch (~50% off)
    # or switch models. Verify against platform.claude.com/docs pricing.
    price_in_per_mtok: float = 1.0
    price_out_per_mtok: float = 5.0


class EmbedCfg(BaseModel):
    # Local-first default (Curator ADR-0003): a deployed Ollama serves bge-m3
    # (1024-dim, multilingual) over its OpenAI-compatible /v1 endpoint. Set
    # provider=openai (+ OPENAI_API_KEY) to fall back to the hosted vendor.
    provider: str = "ollama"          # ollama | openai
    model: str = "bge-m3"
    dimensions: int = 1024
    api_key: str = PLACEHOLDER        # unused for ollama (server ignores it)
    # Base URL of the OpenAI-compatible embeddings API. Only used for
    # provider=ollama (or any local OpenAI-compatible server). In compose this
    # is http://ollama:11434/v1; on the host it's http://localhost:11434/v1.
    base_url: str | None = "http://localhost:11434/v1"


class ClusterCfg(BaseModel):
    # Tuned for bge-m3 (Ollama, 1024-dim, ADR-0017): 72h of production data
    # showed articles with ≥0.50 cosine similarity are effectively the same
    # story across outlets.  0.62 (calibrated for text-embedding-3-small) was
    # too strict for bge-m3's different similarity distribution — same-event
    # articles were landing below the threshold and spawning separate events.
    # entity_overlap_min ≥ 1 is the quality gate against false merges.
    similarity_threshold: float = 0.50
    min_sources_to_publish: int = 2
    entity_overlap_min: int = 1
    recent_window_hours: int = 48
    # Story arc archive (ADR-0013): events with no new article for this many days
    # are marked 'concluded' and archived to story_arcs.  0 = disabled (default
    # until first paying user validates the feature).
    conclude_after_days: int = 0


class DbCfg(BaseModel):
    url: str = PLACEHOLDER
    pool_min: int = 2
    pool_max: int = 10


class RmqCfg(BaseModel):
    url: str = PLACEHOLDER
    consume_exchange: str = "messor"
    consume_queue: str = "curator.articles-scraped"
    consume_routing_key: str = "event.article.scraped"
    # Scrape-session run summaries (B12.1 / ADR-0006). Messor emits one event
    # per harvest run on the same `messor` exchange; Curator upserts
    # public.scrape_sessions. Bound on a dedicated queue so it never competes
    # with the per-article consumer.
    sessions_queue: str = "curator.scrape-sessions"
    sessions_routing_key: str = "event.scrape.session.completed"
    publish_exchange: str = "curator"
    # Backoffice → Curator moderation commands (Phase 2.3). The Laravel admin
    # publishes page.publish / page.unpublish / page.drop / event.resynthesize
    # / event.recluster to this topic exchange; Curator consumes and applies
    # the writes (Curator owns public.events / public.pages — ADR-0003).
    commands_exchange: str = "curator.commands"
    commands_queue: str = "curator.commands"
    commands_routing_key: str = "#"  # all command routing keys


class SpacesCfg(BaseModel):
    endpoint_url: str = PLACEHOLDER
    access_key: str = PLACEHOLDER
    secret_key: str = PLACEHOLDER
    bucket: str = "inkbytes"
    region: str = "nyc3"


class ApiCfg(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8060
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])


class CuratorConfig(BaseModel):
    application: AppCfg = AppCfg()
    llm: LlmCfg = LlmCfg()
    embeddings: EmbedCfg = EmbedCfg()
    clustering: ClusterCfg = ClusterCfg()
    database: DbCfg = DbCfg()
    rabbitmq: RmqCfg = RmqCfg()
    spaces: SpacesCfg = SpacesCfg()
    api: ApiCfg = ApiCfg()

    @classmethod
    def load(cls, path: str | Path) -> "CuratorConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        raw: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
        cfg = cls.model_validate(raw)
        cfg = _overlay_env(cfg)
        cfg.validate_secrets()
        return cfg

    def validate_secrets(self) -> None:
        """Fail fast on un-overridden placeholders for things we need at boot."""
        # In dev we tolerate LOCAL_DEV_UNSET / __SET_VIA_ENV__ for LLMs
        # (the stubs in services/llm_service.py kick in).
        critical = {
            "database.url": self.database.url,
            "rabbitmq.url": self.rabbitmq.url,
        }
        missing = [k for k, v in critical.items() if v == PLACEHOLDER]
        if missing and self.application.mode != "development":
            raise RuntimeError(
                f"Missing required config in production mode: {missing}. "
                "Set the corresponding environment variables."
            )

    def apply_db_settings(self, row: dict[str, Any] | None) -> bool:
        """Overlay tunables from a `backoffice.curator_settings` row IN PLACE.

        Mutating the existing `self.llm` / `self.clustering` objects (rather
        than rebuilding the config) is what makes refresh take effect without a
        redeploy: the skills and the orchestrator hold references to these same
        objects, so a change here is visible on the next event.

        Args:
            row: a mapping of column → value from the settings table, or None
                 when the table/row is absent (then env/YAML values stand —
                 this is the fallback path).

        Returns:
            True if any field changed, False otherwise (incl. row is None).

        Note: API key columns ARE in _DB_SETTINGS_MAP but empty-string values
        are skipped (see _API_KEY_COLUMNS) so an unset Backoffice field never
        overwrites a valid key that arrived via _overlay_env / env var.
        """
        if not row:
            return False

        changed = False
        for column, (section, field) in _DB_SETTINGS_MAP.items():
            if column not in row or row[column] is None:
                continue
            # For API key columns an empty string means "not configured in
            # Backoffice" — skip so the env-var value (set by _overlay_env)
            # is not silently clobbered, which would put LlmService in stub mode.
            if column in _API_KEY_COLUMNS and row[column] == "":
                continue
            target = getattr(self, section)
            current = getattr(target, field)
            # Coerce to the existing field's type so e.g. Decimal/str from the
            # DB driver compares/stores cleanly as float/int. When the current
            # value is None (e.g. embeddings.base_url under provider=openai) there
            # is no type to coerce to — take the raw DB value as-is.
            new_value = row[column] if current is None else type(current)(row[column])
            if new_value != current:
                setattr(target, field, new_value)
                changed = True
        if changed:
            logger.info("Applied curator_settings from DB (%s).", _DB_SETTINGS_TABLE)
        return changed


def _overlay_env(cfg: CuratorConfig) -> CuratorConfig:
    """Apply env-var overrides. The mapping is intentional + explicit."""
    overrides = {
        "ANTHROPIC_API_KEY": ("llm", "api_key"),
        "OPENAI_API_KEY":    ("embeddings", "api_key"),
        # Embedding provider wiring (ADR-0003). In compose, prod points these at
        # the deployed Ollama; leave unset to use the local-first YAML defaults.
        "EMBEDDINGS_PROVIDER":   ("embeddings", "provider"),
        "EMBEDDINGS_BASE_URL":   ("embeddings", "base_url"),
        "EMBEDDINGS_MODEL":      ("embeddings", "model"),
        "EMBEDDINGS_DIMENSIONS": ("embeddings", "dimensions"),
        "DATABASE_URL":      ("database", "url"),
        "RABBITMQ_URL":      ("rabbitmq", "url"),
        "S3_ENDPOINT":       ("spaces", "endpoint_url"),
        "S3_KEY":            ("spaces", "access_key"),
        "S3_SECRET":         ("spaces", "secret_key"),
        "S3_BUCKET":         ("spaces", "bucket"),
        "CURATOR_LOG_LEVEL": ("application", "log_level"),
        "CURATOR_MODE":      ("application", "mode"),
    }
    data = cfg.model_dump()
    for env_var, (section, key) in overrides.items():
        val = os.environ.get(env_var)
        if val:
            data[section][key] = val
    # Provider-specific API keys feed their dedicated llm.* fields so LlmService
    # can hot-swap between providers via Backoffice (ADR-0004).
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        data["llm"]["openai_api_key"] = openai_key
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if deepseek_key:
        data["llm"]["deepseek_api_key"] = deepseek_key
    return CuratorConfig.model_validate(data)
