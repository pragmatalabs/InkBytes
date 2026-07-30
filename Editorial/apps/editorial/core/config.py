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
    voices: dict[str, str] = {                 # language → Piper voice id (provenance;
                                               # the tts-server owns the actual voice)
        "en": "en_US-ryan-high",               # -high: better quality (synth is off-box now)
        "es": "es_MX-claude-high",             # LATAM Spanish, high quality
    }
    models_dir: str = "/models"                # baked into the image (local mode only)
    bitrate: str = "64k"                        # mono speech; small files (local mode)
    key_prefix: str = "audio/outlook"          # Spaces key: {prefix}/{date}/{theme}-{lang}.mp3
    concurrency: int = 1                        # sequential synth (one call fills the CPU slice)
    # Remote synthesis (ADR-0011): the droplet is RAM-starved for onnxruntime, so
    # prod POSTs to a Piper microservice on the 16 GB box. Set → synth is remote and
    # no local Piper/ffmpeg/voices are needed; blank → local Piper (dev / the box).
    remote_url: str = ""                        # e.g. https://tts.inkbytes.news
    remote_secret: str = ""                     # X-TTS-Token shared with the service


class SpacesCfg(BaseModel):
    """DigitalOcean Spaces (S3) — where the MP3s + covers live, public-read. Reuses
    the same DO_SPACES_* env the Curator container already carries. Dormant (uploads
    skipped) if key/secret are blank — audio/covers then no-op rather than failing."""
    endpoint: str = "https://nyc3.digitaloceanspaces.com"
    region: str = "nyc3"
    bucket: str = "inkbytes-prod"
    key: str = ""
    secret: str = ""
    public_base: str = ""   # optional CDN base; blank → {endpoint}/{bucket}


class CoversCfg(BaseModel):
    """Stylized AI hero covers for Outlook columns (ADR-0012) via OpenAI
    gpt-image-1-mini. One cover per (theme, edition_date), language-neutral, cached
    in Spaces. Best-effort: a failure never blocks text/audio. Cost-capped:
    generation stops once this month's spend (distinct covers × unit_cost) hits
    monthly_cap_usd, and `enabled=false` is a hard kill-switch."""
    enabled: bool = True
    model: str = "gpt-image-1-mini"
    size: str = "1536x1024"                     # landscape hero
    quality: str = "low"                         # cheapest tier; still clean illustration
    output_format: str = "webp"                  # small files, direct from the API
    compression: int = 80                        # webp quality/size trade
    key_prefix: str = "covers/outlook"           # Spaces key: {prefix}/{date}/{theme}.webp
    monthly_cap_usd: float = 10.0                # hard ceiling on image spend / month
    unit_cost_usd: float = 0.008                 # ~gpt-image-1-mini low 1536x1024
    api_key: str = ""                            # OPENAI_API_KEY (never committed)


class Config(BaseModel):
    database: DbCfg
    llm: LlmCfg = LlmCfg()
    editorial: EditorialCfg = EditorialCfg()
    tts: TtsCfg = TtsCfg()
    spaces: SpacesCfg = SpacesCfg()
    covers: CoversCfg = CoversCfg()

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
        if v := os.getenv("EDITORIAL_TTS_URL"):
            tts["remote_url"] = v
        if v := os.getenv("EDITORIAL_TTS_SECRET"):
            tts["remote_secret"] = v

        # ── Covers overlay (stylized AI hero images) ──
        covers = raw.setdefault("covers", {})
        if (v := os.getenv("EDITORIAL_COVERS_ENABLED")) is not None:
            covers["enabled"] = v.strip().lower() not in ("0", "false", "no", "")
        if v := os.getenv("EDITORIAL_COVERS_MODEL"):
            covers["model"] = v
        if v := os.getenv("EDITORIAL_COVERS_QUALITY"):
            covers["quality"] = v
        if v := os.getenv("EDITORIAL_COVERS_MONTHLY_CAP_USD"):
            covers["monthly_cap_usd"] = float(v)
        if v := os.getenv("EDITORIAL_COVERS_UNIT_COST_USD"):
            covers["unit_cost_usd"] = float(v)
        # image gen uses OpenAI; accept a dedicated key or the shared OPENAI_API_KEY
        if v := (os.getenv("EDITORIAL_COVERS_API_KEY") or os.getenv("OPENAI_API_KEY")):
            covers["api_key"] = v

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
