"""Editorial service config — YAML + env overlay, pydantic v2 (ADR-0008).

Provider-pluggable LLM (ollama | deepseek | anthropic), same spirit as Curator.
Dev → ollama+gemma4 (Mac); prod → ollama+gemma4 on the Hostinger box, or deepseek
fallback. The provider stays a config flag (independence / data-control), never a
hard choice.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class DbCfg(BaseModel):
    url: str
    pool_min: int = 1
    pool_max: int = 4


class LlmCfg(BaseModel):
    provider: str = "ollama"                       # ollama | deepseek | anthropic
    base_url: str = "http://localhost:11434/v1"    # OpenAI-compatible endpoint
    model: str = "gemma4:12b"
    api_key: str = ""                              # blank for ollama
    temperature: float = 0.55                      # editorial prose: warmer than news
    max_tokens: int = 1400                         # ~600 words + headroom


class EditorialCfg(BaseModel):
    window_hours: int = 24      # "today" = published events in the last N hours
    min_events: int = 3         # skip a theme below this (don't pad thin days)
    max_events: int = 12        # top-N events fed to the model
    languages: list[str] = ["es"]   # start single-language (dominant); add "en" later
    persona_dir: str = "prompts"


class Config(BaseModel):
    database: DbCfg
    llm: LlmCfg = LlmCfg()
    editorial: EditorialCfg = EditorialCfg()

    @classmethod
    def load(cls, path: str) -> "Config":
        raw: dict[str, Any] = {}
        p = Path(path)
        if p.exists():
            raw = yaml.safe_load(p.read_text()) or {}

        # ── env overlay (env wins; never commit secrets) ──
        db = raw.setdefault("database", {})
        if v := os.getenv("DATABASE_URL"):
            db["url"] = v
        if "url" not in db:
            raise ValueError("database.url missing (set it in YAML or DATABASE_URL)")

        llm = raw.setdefault("llm", {})
        for env, key in (
            ("EDITORIAL_LLM_PROVIDER", "provider"),
            ("EDITORIAL_LLM_BASE_URL", "base_url"),
            ("EDITORIAL_LLM_MODEL", "model"),
            ("EDITORIAL_LLM_API_KEY", "api_key"),
        ):
            if v := os.getenv(env):
                llm[key] = v
        # convenience: fall back to the shared provider keys if not set explicitly
        if not llm.get("api_key"):
            prov = llm.get("provider", "ollama")
            if prov == "deepseek" and (k := os.getenv("DEEPSEEK_API_KEY")):
                llm["api_key"] = k
            elif prov == "anthropic" and (k := os.getenv("ANTHROPIC_API_KEY")):
                llm["api_key"] = k

        return cls(**raw)
