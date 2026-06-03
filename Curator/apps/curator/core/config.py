"""Curator config — YAML defaults + env-var overlay (pydantic-settings).

Loading order:
  1. read env.yaml (or whatever was passed via --config)
  2. overlay any env var matching a known mapping (ANTHROPIC_API_KEY,
     OPENAI_API_KEY, DATABASE_URL, RABBITMQ_URL, S3_*)

`__SET_VIA_ENV__` placeholders cause a fail-fast at boot if the
corresponding env var is not set.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

PLACEHOLDER = "__SET_VIA_ENV__"


class AppCfg(BaseModel):
    name: str = "Curator"
    version: str = "0.1.0"
    mode: str = "development"
    log_level: str = "INFO"
    max_concurrent_articles: int = 4


class LlmCfg(BaseModel):
    provider: str = "anthropic"
    enrich_model: str = "claude-haiku-4-5"
    synthesize_model: str = "claude-haiku-4-5"
    max_tokens_enrich: int = 600
    max_tokens_synth: int = 900
    temperature: float = 0.2
    api_key: str = PLACEHOLDER
    # Standard list prices for cost accounting. Defaults = Claude Haiku 4.5
    # ($1/M input, $5/M output). Override in env if you use batch (~50% off)
    # or switch models. Verify against platform.claude.com/docs pricing.
    price_in_per_mtok: float = 1.0
    price_out_per_mtok: float = 5.0


class EmbedCfg(BaseModel):
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    api_key: str = PLACEHOLDER


class ClusterCfg(BaseModel):
    similarity_threshold: float = 0.78
    min_sources_to_publish: int = 2
    entity_overlap_min: int = 2
    recent_window_hours: int = 48


class DbCfg(BaseModel):
    url: str = PLACEHOLDER
    pool_min: int = 2
    pool_max: int = 10


class RmqCfg(BaseModel):
    url: str = PLACEHOLDER
    consume_exchange: str = "messor"
    consume_queue: str = "curator.articles-scraped"
    consume_routing_key: str = "event.article.scraped"
    publish_exchange: str = "curator"


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


def _overlay_env(cfg: CuratorConfig) -> CuratorConfig:
    """Apply env-var overrides. The mapping is intentional + explicit."""
    overrides = {
        "ANTHROPIC_API_KEY": ("llm", "api_key"),
        "OPENAI_API_KEY":    ("embeddings", "api_key"),
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
    return CuratorConfig.model_validate(data)
