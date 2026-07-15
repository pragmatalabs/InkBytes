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
    window_hours: int = 24      # morning-briefing cut: cover the prior ~24h
    min_events: int = 3         # skip a theme below this (don't pad thin days)
    max_events: int = 12        # top-N events fed to the model
    languages: list[str] = ["es", "en"]   # "Today's [Topic] Outlook" — bilingual
    persona_dir: str = "prompts"


class TtsCfg(BaseModel):
    """Self-hosted Piper text-to-speech (ADR-0011). $0/char — the same local-first
    call as bge-m3 (Curator ADR-0003), no external voice vendor. A single voice per
    language ("the InkBytes narrator"), synthesized ONCE per column and cached in
    Spaces. Best-effort: a TTS/upload failure never blocks the text batch."""
    enabled: bool = True
    voices: dict[str, str] = {                 # language → Piper voice model id
        "en": "en_US-ryan-medium",             # medium: ~2× faster synth than -high
        "es": "es_MX-ald-medium",              # matched male narrator, LATAM Spanish
    }
    models_dir: str = "/models"                # baked into the image (Dockerfile)
    bitrate: str = "64k"                        # mono speech; small files
    key_prefix: str = "audio/outlook"          # Spaces key: {prefix}/{date}/{theme}-{lang}.mp3
    concurrency: int = 1                        # voice loaded once + onnxruntime uses the --cpus slice per synth


class SpacesCfg(BaseModel):
    """DigitalOcean Spaces (S3) — where the MP3s live, public-read. Reuses the same
    DO_SPACES_* env the Curator container already carries. Dormant (uploads skipped)
    if key/secret are blank — TTS then no-ops rather than failing the batch."""
    endpoint: str = "https://nyc3.digitaloceanspaces.com"
    region: str = "nyc3"
    bucket: str = "inkbytes-prod"
    key: str = ""
    secret: str = ""
    public_base: str = ""   # optional CDN base; blank → {endpoint}/{bucket}


class Config(BaseModel):
    database: DbCfg
    llm: LlmCfg = LlmCfg()
    editorial: EditorialCfg = EditorialCfg()
    tts: TtsCfg = TtsCfg()
    spaces: SpacesCfg = SpacesCfg()

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

        # ── TTS overlay (self-hosted Piper) ──
        # Only write keys that actually have overrides — injecting an empty dict
        # (e.g. voices={}) would OVERRIDE the pydantic model default, not merge.
        tts = raw.setdefault("tts", {})
        if (v := os.getenv("EDITORIAL_TTS_ENABLED")) is not None:
            tts["enabled"] = v.strip().lower() not in ("0", "false", "no", "")
        env_en = os.getenv("EDITORIAL_TTS_VOICE_EN")
        env_es = os.getenv("EDITORIAL_TTS_VOICE_ES")
        if env_en or env_es:
            voices = dict(tts.get("voices") or {})   # merge onto YAML/default, don't clobber
            if env_en:
                voices["en"] = env_en
            if env_es:
                voices["es"] = env_es
            tts["voices"] = voices
        if v := os.getenv("EDITORIAL_TTS_MODELS_DIR"):
            tts["models_dir"] = v
        if v := os.getenv("EDITORIAL_TTS_CONCURRENCY"):
            tts["concurrency"] = int(v)

        # ── Spaces overlay (reuses the shared DO_SPACES_* env) ──
        spaces = raw.setdefault("spaces", {})
        for env, key in (
            ("DO_SPACES_ENDPOINT", "endpoint"),
            ("DO_SPACES_REGION", "region"),
            ("DO_SPACES_BUCKET", "bucket"),
            ("DO_SPACES_KEY", "key"),
            ("DO_SPACES_SECRET", "secret"),
            ("DO_SPACES_PUBLIC_BASE", "public_base"),
        ):
            if v := os.getenv(env):
                spaces[key] = v

        return cls(**raw)
