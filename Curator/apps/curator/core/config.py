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
    # Concurrent in-flight articles in the live consume path AND the batch
    # reprocess paths. The slow stage is the enrich LLM call (8-17s of network
    # wait on DeepSeek), which parallelises freely; the embed (CPU Ollama) and
    # cluster-attach stages are serialised by dedicated locks regardless of
    # this value (see Application._embed_sem / _cluster_lock).
    max_concurrent_articles: int = 8
    # Stale-message intake gate: ack-and-drop a queued article whose scraped_at
    # is older than this many hours, BEFORE spending an LLM call. The Reader
    # feed window is 48h (Messor ADR-0015), so older articles can't surface
    # anyway. Protects against queue floods (105k-msg incident, 2026-06-09).
    # 0 disables the gate.
    max_article_age_hours: int = 48
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
    # ADR-0033 P0 event lifecycle. When True the /events feed ranks by the
    # material clock (last_material_update_at) and is scoped to feed_window_hours,
    # so a tangential attach can't re-float a stale event and old events fall out
    # of the live feed (into the vault once concluded). False → legacy behaviour
    # (rank by pages.freshness_at = max scraped_at, no window). Default off so
    # this ships dormant and is shadow-measured before flipping.
    lifecycle_feed: bool = False
    feed_window_hours: int = 72


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
    # Per-Mtok list prices for cost accounting (ADR-0028). Defaults =
    # deepseek-v4-flash, the production model as of 2026-06 (verified against
    # the DeepSeek invoice). DeepSeek bills CACHED input tokens ~50x cheaper
    # than uncached, so input is split: price_in_per_mtok is the cache-MISS
    # (uncached) rate, price_cache_hit_per_mtok the cache-HIT rate. Ignoring the
    # split previously overstated cost ~13x. Override in env per provider/model.
    price_in_per_mtok: float = 0.14            # cache-miss input  ($0.14/M)
    price_cache_hit_per_mtok: float = 0.0028   # cache-hit input   ($0.0028/M)
    price_out_per_mtok: float = 0.28           # output            ($0.28/M)


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


class TriageCfg(BaseModel):
    # Pre-enrich triage gate (ADR-0030): a small LOCAL model (Hostinger Ollama)
    # classifies each to-be-enriched article as keep | junk, so obvious filler
    # (horoscopes, lottery/betting, pure deals/affiliate, error/login pages,
    # contentless stubs) is dropped BEFORE the paid DeepSeek enrich call.
    # Off by default; enable in prod once the model is pulled.
    enabled: bool = False
    # Shadow mode: run + LOG the verdict but DO NOT actually drop — measure
    # precision against real enrich for a day before enforcing. When False, a
    # `junk` verdict skips enrich/cluster/synth (the article stays stored raw).
    shadow: bool = True
    provider: str = "ollama"
    base_url: str | None = "http://localhost:11434/v1"
    model: str = "llama3.2:3b"
    # Tolerant timeout: a warm 3B classify is ~1-3s, but the shared CPU box can
    # be busy with embeddings or cold-load the model (~20s). On timeout the gate
    # fails OPEN (keep), so a high cap only delays; it never drops wrongly.
    timeout_s: float = 12.0
    # Bound concurrent triage calls so 8 in-flight articles don't hammer the
    # 4-CPU box with 8 parallel generations (same lesson as _embed_sem).
    max_concurrent: int = 2


class NerCfg(BaseModel):
    # spaCy NER pre-pass (ADR-0032 item 2): a language-routed, deterministic NER
    # pass extracts typed entities (PERSON/ORG/LOC) BEFORE enrich and injects
    # them into the enrich prompt as MUST_COVER hints, so the LLM can't
    # under-extract. Free/CPU, multilingual, fail-OPEN (any error → LLM-only).
    #
    # OFF by default. Two independent gates keep it safe: this runtime flag AND
    # the build-time `INSTALL_NER_MODELS` Docker arg (models are NOT in the
    # default image). Enable only once the curator-worker has memory headroom.
    enabled: bool = False
    # Per-language spaCy package. Defaults are MEMORY-SAFE for the 1.5GB worker —
    # measured peak RSS (loading both, in-process): en_core_web_md + es_core_news_md
    # ≈ 0.69 GB, vs es_core_news_lg which pushes the pair to ≈ 1.24 GB and breaches
    # the cap once an IllustrateSkill Chromium run overlaps. The es md→lg NER gap is
    # small (the extra ~560MB is lg's static-vector table, which the NER head barely
    # uses — and it can't be excluded: dropping vectors crashes the es models).
    # Opt up to es_core_news_lg via NER_ES_MODEL only on a ≥16GB box. Any absent
    # model is skipped (that language falls back to LLM-only).
    models: dict[str, str] = Field(default_factory=lambda: {
        "en": "en_core_web_md",
        "es": "es_core_news_md",
    })
    # The md models are still noisy on news copy — keep only the most frequent
    # surface forms per type so the prompt isn't flooded.
    max_entities_per_type: int = 8
    # NER over the article head is enough; the full body is slow on larger models.
    max_chars: int = 4000
    # spaCy is synchronous + CPU-heavy: each call runs in a worker thread and
    # concurrency is bounded (the _embed_sem lesson) so N in-flight articles
    # don't saturate the shared box. Keep <= CPU cores - 2.
    max_concurrent: int = 2
    # Per-document wall-clock cap (thread). On overrun the pass fails OPEN.
    timeout_s: float = 8.0


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
    # Story arc archive (ADR-0013): events with no *material* update for this many
    # days are marked 'concluded' and archived to story_arcs (then drop out of the
    # live feed, which filters status='published'). 0 = disabled (default).
    # Under ADR-0033 the quiet test now uses last_material_update_at, so a stream
    # of tangential re-mentions no longer keeps a dead story out of the vault.
    conclude_after_days: int = 0
    # ADR-0033 P0: an attach is a *material* update (bumps last_material_update_at,
    # can re-float the event) only when its cluster distance ≤ this. Tangential
    # attaches (this < distance ≤ 1−similarity_threshold) still join the event but
    # do NOT re-float it. Default = the attach threshold (1−0.50 = 0.50) → no
    # behaviour change until lowered (e.g. 0.40) once validated.
    material_max_distance: float = 0.50
    # ADR-0031 clustering precision (mega-bucket fix). When True, replace
    # single-linkage with **centroid-linkage + an entity-specificity gate**: an
    # article attaches to the nearest event *centroid* (events.centroid) only if
    # distance < precision_distance AND it shares ≥1 *specific* entity (one in
    # ≤ specificity_cap of the recent pool) — a ubiquitous mega-entity ("Mundial
    # 2026") alone can't merge unrelated stories. Off → legacy single-linkage.
    # Requires events.centroid backfilled (scripts/backfill_event_centroids.py)
    # before flipping. Tightened bar (2026-06-25, dev corpus validation): at the
    # original distance 0.48 + 1-shared-entity gate the World Cup still rebuilt a
    # 363-article blob from scratch (same-genre match reports are embedding-near
    # and a big cluster's *accumulating* specific-entity union becomes a magnet).
    # distance 0.34 + requiring ≥2 shared specific entities splits it per match
    # (Portugal-Uzbekistán, Ronaldo's record, Colombia elections each stand alone).
    precision_mode: bool = False
    precision_distance: float = 0.34
    specificity_cap: float = 0.05
    # min count of *specific* entities an article must share with an event to
    # attach (was implicitly 1). ≥2 stops the accumulating-union magnet.
    specificity_min_shared: int = 2
    # Breaking-news detector (ADR-0024 + 2026-06-12 fix): an event is breaking
    # when ≥2 distinct pulse outlets (outlets.pulse) have articles whose
    # scraped_at fall within breaking_window_minutes OF EACH OTHER (a coverage
    # surge), anchored at the most recent pulse article. The original keyed the
    # window off the event's first_seen_at vs processing-time NOW(), which
    # pipeline lag made impossible to satisfy — it never fired. breaking_recency_
    # hours guards against retro-flagging old surges during reprocessing: the
    # latest pulse article must be within this many hours of now. The flag
    # auto-expires breaking_ttl_hours later. breaking_window_minutes = 0 disables.
    breaking_window_minutes: int = 60
    breaking_ttl_hours: int = 2
    breaking_recency_hours: int = 3


class DbCfg(BaseModel):
    url: str = PLACEHOLDER
    pool_min: int = 2
    pool_max: int = 10


class RmqCfg(BaseModel):
    url: str = PLACEHOLDER
    consume_exchange: str = "messor"
    consume_queue: str = "curator.articles-scraped"
    consume_routing_key: str = "event.article.scraped"
    # Unacked messages delivered concurrently to the article consumer. With 1
    # (the pre-2026-06-11 value) the whole pipeline is serial and throughput is
    # capped by the enrich LLM round-trip (~4 articles/min → a permanent
    # multi-hour queue backlog). Should be >= application.max_concurrent_articles.
    prefetch_count: int = 8
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
    triage: TriageCfg = TriageCfg()
    ner: NerCfg = NerCfg()

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
        # Pre-enrich triage gate (ADR-0030). Enable + point at the Hostinger
        # Ollama in prod via infra/.env; bool/str coerced by re-validation.
        "TRIAGE_ENABLED":    ("triage", "enabled"),
        "TRIAGE_SHADOW":     ("triage", "shadow"),
        "TRIAGE_BASE_URL":   ("triage", "base_url"),
        "TRIAGE_MODEL":      ("triage", "model"),
        # spaCy NER pre-pass (ADR-0032 item 2). Off by default; enable in prod
        # via infra/.env once models are baked (INSTALL_NER_MODELS) + memory ok.
        "NER_ENABLED":       ("ner", "enabled"),
        # Event lifecycle (ADR-0033 P0). Enable in prod via infra/.env to flip the
        # feed to the material clock + window, archive quiet stories, and gate
        # re-floating. All default to legacy behaviour until set.
        "LIFECYCLE_FEED":    ("application", "lifecycle_feed"),
        "FEED_WINDOW_HOURS": ("application", "feed_window_hours"),
        "CONCLUDE_AFTER_DAYS":  ("clustering", "conclude_after_days"),
        "MATERIAL_MAX_DISTANCE": ("clustering", "material_max_distance"),
        # ADR-0031 clustering precision. Off by default; enable after backfilling
        # events.centroid. PRECISION_DISTANCE / SPECIFICITY_CAP tune the gate.
        "PRECISION_MODE":      ("clustering", "precision_mode"),
        "PRECISION_DISTANCE":  ("clustering", "precision_distance"),
        "SPECIFICITY_CAP":     ("clustering", "specificity_cap"),
        "SPECIFICITY_MIN_SHARED": ("clustering", "specificity_min_shared"),
    }
    data = cfg.model_dump()
    for env_var, (section, key) in overrides.items():
        val = os.environ.get(env_var)
        if val:
            data[section][key] = val
    # Per-language NER model overrides land in the nested `ner.models` dict, so
    # a memory-constrained box can drop es to es_core_news_md without code edits.
    for env_var, lang in (("NER_EN_MODEL", "en"), ("NER_ES_MODEL", "es")):
        mv = os.environ.get(env_var)
        if mv:
            data["ner"]["models"][lang] = mv
    # Provider-specific API keys feed their dedicated llm.* fields so LlmService
    # can hot-swap between providers via Backoffice (ADR-0004).
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        data["llm"]["openai_api_key"] = openai_key
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if deepseek_key:
        data["llm"]["deepseek_api_key"] = deepseek_key
    return CuratorConfig.model_validate(data)
