"""FastAPI surface — /healthz, /readyz, /status, /events, /events/{id}.

The reader (winston-r) will read from these endpoints in D4. For D2 they
are intentionally minimal.
"""
from __future__ import annotations

import datetime as _dt
import json as _json
import logging
from typing import Any

import os

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.application import Application
from services import push_service


# Request bodies for the push endpoints. MUST be module-level: a Pydantic model
# defined inside build_app() is not detected by FastAPI as a body model — it
# falls back to treating the param as a query field (422 "body required").
class PushSubBody(BaseModel):
    subscription: dict[str, Any]           # { endpoint, keys: { p256dh, auth } }
    topics: list[str] = ["outlook-daily"]
    lang: str = "es"
    userAgent: str | None = None


class PushUnsubBody(BaseModel):
    endpoint: str

logger = logging.getLogger(__name__)

# ── Query parameter caps (ADR-0006 §D1) ─────────────────────────────────────
# Prevent runaway DB scans via unbounded caller-supplied values.
_MAX_EVENTS_LIMIT = 500
_MAX_GRAPH_NODES  = 200
_MAX_GRAPH_EDGES  = 500
_MAX_QUESTION_LEN = 500  # assistant /ask question cap (ADR-0022)
# Cross-language dedup (ADR-0037): two events are the same story in different
# languages when their centroids are this close. Measured on prod: EN/ES pairs of
# the same story sit at 0.03–0.06 (bge-m3 is multilingual); distinct stories are
# well above. 0.12 is a safe margin. Only different-language events are grouped.
_CROSSLANG_DUP_DIST = 0.12

# Wire services / outlet bylines that get NER-tagged on every article from that
# source → ubiquitous by event_count but not newsmakers. Excluded from /graph
# nodes (lowercased name match). Keep to clear agencies/outlets — NOT real orgs
# like FIFA/UEFA/EU that are genuine subjects of coverage.
_GRAPH_SOURCE_STOPWORDS = [
    "efe", "ap", "associated press", "the associated press", "reuters", "afp",
    "agence france-presse", "europa press", "europapress", "dpa", "ansa",
    "bloomberg", "bbc", "cnn", "infobae", "reuters news", "ap news",
]


class AskRequest(BaseModel):
    """Body for POST /ask (ADR-0022 corpus chat assistant)."""
    question: str = Field("", max_length=_MAX_QUESTION_LEN)
    mode: str = "chat"  # "resume" | "top10" | "chat"

# ── Broad news categories derived from article-level topic strings ────────────
# Each entry is (category_key, [keywords...]).  First match wins; "world" is
# the catch-all when nothing matches.  Keywords are matched case-insensitively
# as substrings of the topic string.
_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("sports",    ["world cup", "mundial", "fifa", "soccer", "football", "tennis",
                   "basketball", "baseball", "nba", "nfl", "formula 1", "champion",
                   "olympic", "tournament", "stanley cup", "french open", "wimbledon",
                   "league", "grand slam", "atletico", "premier", "serie a",
                   "la liga", "bundesliga", "mls", "copa", "ligue"]),
    ("politics",  ["election", "president", "government", "minister", "congress",
                   "senate", "parliament", "vote", "diplomatic", "diplomacy",
                   "foreign", "sanctions", "military", "war", "conflict", "attack",
                   "iran", "israel", "ukraine", "russia", "nato", "trump", "biden",
                   "zelensky", "ceasefire", "hamas", "hezbollah", "west bank",
                   "coup", "protest", "unrest", "white house", "kremlin",
                   "secretary of state", "pentagon"]),
    ("technology",["ai ", "artificial intelligence", "tech", "software", "spacex",
                   "nasa", "iss ", "satellite", "cyber", "hack", "openai", "robot",
                   "space", "rocket", "launch", "digital", "algorithm", "chip",
                   "semiconductor", "quantum", "llm", "generative"]),
    ("business",  ["stock", "market", "economy", "gdp", "inflation", "trade",
                   "oil price", "oil ", "company", "earnings", "dollar", "peso",
                   "crypto", "bitcoin", "ethereum", "fed ", "interest rate", "bank",
                   "financial", "investment", "revenue", "profit", "startup",
                   "merger", "acquisition", "ipo", "warren buffett", "berkshire",
                   "nasdaq", "s&p", "dow jones", "bond"]),
    ("health",    ["covid", "vaccine", "hospital", "disease", "cancer", "drug",
                   "health", "pandemic", "virus", "outbreak", "patient",
                   "treatment", "fda", "who ", "epidemic", "clinical trial",
                   "pharmaceutical", "mental health"]),
    ("environment",["climate", "weather", "storm", "flood", "earthquake", "wildfire",
                   "hurricane", "drought", "el niño", "la niña", "environment",
                   "carbon", "emissions", "forest", "ocean", "wave", "wind",
                   "temperature", "glacier", "biodiversity", "deforestation"]),
    ("culture",   ["film", "music", "art", "celebrity", "award", "entertainment",
                   "book", "culture", "festival", "pope", "church", "religion",
                   "faith", "social media", "indio solari", "concert", "album",
                   "movie", "television", "streaming"]),
]
_CATCH_ALL = "world"

# The 8 canonical themes written by ENRICH (migration 007). Used to validate
# the ?theme= filter so a bad value is ignored rather than returning [].
# 15 broad themes (Curator ADR-0032 item 1, widened from 8). The original 8
# are a strict subset, so legacy ?theme= chips keep working.
_VALID_THEMES: frozenset[str] = frozenset({
    "politics", "world", "business", "technology", "science",
    "health", "sports", "culture", "entertainment", "environment",
    "crime", "education", "lifestyle", "religion", "disaster",
})

# Junk topic labels excluded from /topics/trending — enrichment artifacts from
# error pages / generic outlet boilerplate (not real stories). Matched
# case-insensitively as full-string or prefix patterns (see the query).
_JUNK_TOPIC_PATTERNS: list[str] = [
    "browser error",
    "cnn breaking news%",
    "cnn news headlines",
    "cnn news%",
    "%error page%",
    "page not found",
    "access denied",
]


# Trending near-duplicate collapsing (ADR-0027). The LLM emits free-text topic
# labels, so one story fragments across variants ("Pope Leo XIV Visit to
# Barcelona / Madrid / Spain"). We collapse same-language variants by token
# overlap, keeping the highest-coverage variant as the representative (so its
# count still matches its ?topic= drill-down — no mismatch). Cross-language
# dupes (EN vs ES) don't share tokens and remain separate — acceptable for a
# bilingual product; a deeper fix is topic normalization at enrichment time.
_TOPIC_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "and", "with",
    "from", "by", "vs", "over", "amid", "as", "after", "before",
    "de", "la", "el", "en", "y", "los", "las", "del", "un", "una", "por",
    "con", "para", "tras", "ante", "su", "al",
})


def _topic_tokens(topic: str) -> set[str]:
    import re
    return {
        w for w in re.findall(r"[a-z0-9áéíóúñü]+", topic.lower())
        if len(w) > 1 and w not in _TOPIC_STOPWORDS
    }


def _dedupe_trending(rows: list[dict], limit: int, threshold: float = 0.5) -> list[dict]:
    """Collapse near-duplicate topic labels; keep top `limit` distinct concepts.

    Input is ordered by event_count DESC, so the first variant seen for a
    concept is its highest-coverage label — we keep it and drop later variants
    whose token-set Jaccard ≥ threshold.
    """
    kept: list[tuple[set[str], dict]] = []
    for d in rows:
        toks = _topic_tokens(d["topic"])
        if any(toks and ks and len(toks & ks) / len(toks | ks) >= threshold
               for ks, _ in kept):
            continue
        kept.append((toks, d))
        if len(kept) >= limit:
            break
    return [d for _, d in kept]


def _derive_category(topic: str | None) -> str:
    """Map a story-level topic string to one of the broad category keys.

    Returns the first matching category or "world" as a catch-all.
    """
    if not topic:
        return _CATCH_ALL
    t = topic.lower()
    for cat, keywords in _CATEGORY_RULES:
        if any(kw in t for kw in keywords):
            return cat
    return _CATCH_ALL


def _decode_json_col(v: Any) -> list:
    """Parse a JSON_AGG column returned by asyncpg (ADR-0006).

    asyncpg returns ``json``-typed columns (e.g. from JSON_AGG) as raw JSON
    strings.  ``jsonb`` columns arrive already decoded.  This helper normalises
    both so callers always receive a Python list.
    """
    if v is None:
        return []
    if isinstance(v, str):
        return _json.loads(v)
    return v  # already decoded (jsonb)


def build_app(app: Application) -> FastAPI:
    api = FastAPI(title=f"{app.NAME} API", version=app.VERSION)

    api.add_middleware(
        CORSMiddleware,
        allow_origins=app.cfg.api.cors_allow_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @api.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True, "service": app.NAME, "version": app.VERSION}

    @api.get("/readyz")
    async def readyz() -> dict[str, Any]:
        db_ok = await app.db.healthcheck()
        if not db_ok:
            raise HTTPException(503, "database not ready")
        return {"ok": True, "checks": {"database": db_ok}}

    @api.get("/status")
    async def status() -> dict[str, Any]:
        # Two queries instead of six sequential fetchvals — saves ~4 DB
        # round-trips on every /status poll (ADR-0006 §D3).
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            # Query 1: article-level counts in one table scan
            art = await conn.fetchrow(
                """
                SELECT
                    COUNT(*)                                          AS total,
                    COUNT(*) FILTER (WHERE enriched_at IS NOT NULL)  AS enriched,
                    COUNT(*) FILTER (WHERE embedding  IS NOT NULL)   AS embedded,
                    COUNT(*) FILTER (WHERE triage_dropped_at IS NOT NULL) AS triage_dropped,
                    -- True backlog: not enriched AND not triage-dropped (ADR-0030).
                    COUNT(*) FILTER (WHERE enriched_at IS NULL
                                       AND triage_dropped_at IS NULL)  AS pending
                  FROM articles
                """
            )
            # Query 2: event + page counts via a single LEFT JOIN
            evp = await conn.fetchrow(
                """
                SELECT
                    COUNT(DISTINCT e.id)                                        AS events_total,
                    COUNT(DISTINCT e.id) FILTER (WHERE e.status = 'published')  AS events_published,
                    COUNT(DISTINCT p.id) FILTER (WHERE p.published_at IS NOT NULL)
                                                                                AS pages_published
                  FROM events e
                  LEFT JOIN pages p ON p.event_id = e.id
                """
            )

        articles_total    = art["total"]
        articles_enriched = art["enriched"]
        articles_embedded = art["embedded"]
        articles_triage_dropped = art["triage_dropped"]
        events_total      = evp["events_total"]
        events_published  = evp["events_published"]
        pages_published   = evp["pages_published"]
        # True pending = unenriched AND not triage-dropped (ADR-0030). Computed
        # in SQL so dropped junk never inflates the backlog counter.
        articles_pending  = max(0, art["pending"] or 0)

        return {
            "articles_total":    articles_total,
            "articles_enriched": articles_enriched,
            "articles_embedded": articles_embedded,
            "articles_pending":  articles_pending,
            "articles_triage_dropped": articles_triage_dropped,
            "events_total":      events_total,
            "events_published":  events_published,
            "pages_published":   pages_published,
            # Live pipeline state — via Application properties (ADR-0006 §D5)
            "synths_in_flight":  app.synths_in_flight,
            # Processing kill-switch (Backoffice "Stop Curator", ADR-0023) — the
            # live value the worker is honoring (reflects the ~30s refresh lag).
            "processing_enabled": app.cfg.application.processing_enabled,
            # LLM tier (live — hot-reloaded by reconfigure)
            "llm": {
                "provider":         app.cfg.llm.provider,
                "enrich_model":     app.cfg.llm.enrich_model,
                "synthesize_model": app.cfg.llm.synthesize_model,
                "base_url":         app.cfg.llm.base_url,
            },
            # Embedding tier + reconfigure status (ADR-0004)
            "embeddings": {
                "provider":    app.cfg.embeddings.provider,
                "model":       app.cfg.embeddings.model,
                "dimensions":  app.cfg.embeddings.dimensions,
                "stale":       app.embeddings_stale,
                "blocked":     app.embeddings_blocked,
                "reembedding": app.reembedding,
            },
        }

    @api.get("/events")
    async def list_events(
        response: Response,
        limit: int = 500,
        theme: str | None = None,
        category: str | None = None,
        topic: str | None = None,
    ) -> list[dict[str, Any]]:
        """List published events, newest-first (global-first ranking, ADR-0017).

        Optional taxonomy filters (task 6a / ADR-0027), all AND-combined:
          theme=    one of the 15 canonical themes (ADR-0032); matches the
                    event's majority-vote article theme. Invalid values ignored.
          category= a granular category (articles.article_category) — the
                    normalized 33-cat label once an article is (re-)enriched
                    under ADR-0032, else the legacy Messor section; event
                    matches if any of its articles carries that value.
          topic=    a story topic label (articles.topic); event matches if any
                    article carries it (used by the trending-topics drill-down).
        """
        limit = min(limit, _MAX_EVENTS_LIMIT)  # ADR-0006 §D1
        # Ignore an unknown theme rather than silently returning [] — keeps the
        # Reader resilient to a stale/typo'd chip.
        theme_filter = theme if theme in _VALID_THEMES else None
        category_filter = (category or "").strip() or None
        topic_filter = (topic or "").strip() or None
        # Filtered responses vary by query string; keep the short TTL but mark
        # them private-ish so a CDN doesn't serve one theme's page for another.
        response.headers["Cache-Control"] = "public, max-age=30"
        # ADR-0033 P0: flag-gated feed ranking by the material clock + recency
        # window. Off → legacy behaviour (rank by p.freshness_at, no window). The
        # window int is config-sourced (not user input), so formatting it into the
        # SQL is safe. occurred_at (first_seen_at) is always exposed so the Reader
        # can show the real date, never "today" for an old story.
        if app.cfg.application.lifecycle_feed:
            _win = int(app.cfg.application.feed_window_hours)
            _window_clause = f"AND e.last_material_update_at > NOW() - INTERVAL '{_win} hours'"
            _order_col = "COALESCE(e.last_material_update_at, p.freshness_at)"
        else:
            _window_clause, _order_col = "", "p.freshness_at"
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                ("""
                SELECT p.id, p.headline, p.freshness_at, p.published_at,
                       e.first_seen_at AS occurred_at, e.last_material_update_at,
                       e.source_count, e.article_count, e.language,
                       e.cover_image,   -- ADR-0034 Tier 2 license-clean cover (JSONB)

                       -- Topic: prefer the event-level topic (set by synthesize);
                       -- fall back to the most common article-level topic derived
                       -- during ENRICH.  events.topic is often NULL before the
                       -- synthesize skill explicitly sets it, so the fallback
                       -- ensures every page surfaces a meaningful topic label.
                       COALESCE(
                           NULLIF(TRIM(e.topic), ''),
                           (SELECT a.topic
                              FROM articles a
                             WHERE a.event_id = e.id
                               AND a.topic IS NOT NULL
                               AND TRIM(a.topic) <> ''
                             GROUP BY a.topic
                             ORDER BY COUNT(*) DESC
                             LIMIT 1)
                       ) AS topic,

                       -- Theme: majority-vote across article-level LLM themes
                       -- (computed in the `th` LATERAL join below so it can be
                       -- referenced in WHERE for the ?theme= filter). Falls back
                       -- to NULL for legacy rows pre-migration 007 →
                       -- _derive_category() in Python.
                       th.theme AS theme,

                       -- Outlet avatar stack (up to 5 distinct names)
                       ARRAY(
                         SELECT DISTINCT a.outlet_name
                           FROM articles a
                          WHERE a.event_id = e.id AND a.outlet_name IS NOT NULL
                          LIMIT 5
                       ) AS outlet_names,

                       -- Dek: first ~180 chars of synthesis; Reader trims to
                       -- the first sentence boundary (./?/!) before rendering.
                       LEFT(p.synthesis_md, 180) AS synthesis_excerpt,

                       -- Factuality: average per-article score scaled 0–100.
                       -- NULL when no articles have been enriched yet.
                       (SELECT ROUND(AVG(a.factuality) * 100)::int
                          FROM articles a
                         WHERE a.event_id = e.id
                           AND a.factuality IS NOT NULL
                       ) AS avg_factuality,

                       -- Cover image: freshest lead_image among the event's CORE
                       -- members (ADR-0021). The cluster attach threshold is 0.50
                       -- cosine distance; a marginal member (e.g. distance 0.47) can be
                       -- loosely related yet supply the only image, hijacking the hero
                       -- with an off-topic photo (a Stevie Nicks photo on a conductor's
                       -- obituary). Gating to cluster_distance <= 0.45 keeps the hero
                       -- on-topic; events whose only image sits on an outlier go
                       -- text-only rather than show a wrong photo.
                       -- ADR-0016: COALESCE with events.hero_image (best YouTube
                       -- thumbnail written by IllustrateSkill) as fallback when the
                       -- outlet og:image was NULL, hotlink-blocked, or an author photo.
                       COALESCE(
                           (SELECT a.lead_image
                              FROM articles a
                             WHERE a.event_id = e.id
                               AND a.lead_image IS NOT NULL
                               AND a.lead_image <> ''
                               AND a.cluster_distance <= 0.45
                             ORDER BY a.scraped_at DESC
                             LIMIT 1),
                           e.hero_image
                       ) AS lead_image,

                       -- Coverage sparkline: 7 data-points at 6-hour intervals
                       -- over the last 42 h.  Gives the Reader a mini area chart
                       -- showing how article volume evolved since the story broke.
                       ARRAY(
                         SELECT COUNT(a2.id)::int
                           FROM generate_series(
                                  NOW() - INTERVAL '42 hours',
                                  NOW() - INTERVAL '6 hours',
                                  INTERVAL '6 hours'
                                ) AS bucket
                           LEFT JOIN articles a2
                                  ON a2.event_id = e.id
                                 AND a2.scraped_at >= bucket
                                 AND a2.scraped_at <  bucket + INTERVAL '6 hours'
                          GROUP BY bucket
                          ORDER BY bucket
                       ) AS coverage_spark,

                       -- Global-first ranking (ADR-0017): true when at least one
                       -- article in this event came from a global-region outlet
                       -- (region = 'global': AP, Reuters, BBC, CNN, NPR …).
                       -- Used in ORDER BY to give global stories a +6h freshness
                       -- bonus so they stay above regional-only stories across
                       -- multiple harvest cycles.  Also returned to the Reader so
                       -- it can render a "Regional" section divider.
                       gflag.has_global_outlet

                  FROM pages p
                  JOIN events e ON e.id = p.event_id
                  -- Lateral join computes has_global_outlet once per event row;
                  -- referenced in both SELECT and ORDER BY without repeating the
                  -- subquery.  LEFT JOIN so events with no articles still appear.
                  LEFT JOIN LATERAL (
                      SELECT EXISTS (
                          SELECT 1
                            FROM articles a_gf
                            JOIN outlets o_gf ON o_gf.id = a_gf.outlet_id
                           WHERE a_gf.event_id = e.id
                             AND o_gf.region = 'global'
                      ) AS has_global_outlet
                  ) gflag ON true
                  -- Majority-vote theme, lifted out of SELECT so the ?theme=
                  -- filter in WHERE can reference it.
                  LEFT JOIN LATERAL (
                      SELECT a.theme
                        FROM articles a
                       WHERE a.event_id = e.id AND a.theme IS NOT NULL
                       GROUP BY a.theme
                       ORDER BY COUNT(*) DESC
                       LIMIT 1
                  ) th ON true
                 WHERE p.published_at IS NOT NULL
                   AND e.status = 'published'
                   __WINDOW_CLAUSE__
                   AND ($2::text IS NULL OR th.theme = $2)
                   AND ($3::text IS NULL OR EXISTS (
                         SELECT 1 FROM articles a
                          WHERE a.event_id = e.id AND a.article_category = $3))
                   AND ($4::text IS NULL OR EXISTS (
                         SELECT 1 FROM articles a
                          WHERE a.event_id = e.id AND a.topic = $4))
                 ORDER BY (
                     __ORDER_COL__
                     + CASE WHEN gflag.has_global_outlet
                           THEN INTERVAL '6 hours'
                           ELSE INTERVAL '0'
                       END
                 ) DESC NULLS LAST
                 LIMIT $1
                """).replace("__WINDOW_CLAUSE__", _window_clause).replace("__ORDER_COL__", _order_col),
                limit, theme_filter, category_filter, topic_filter,
            )
            # Cross-language dedup (ADR-0037): for each event, find its same-story
            # OTHER-language siblings by centroid proximity. `has_better` → a richer
            # sibling exists, so this one is NOT the group's primary; `also_languages`
            # maps each sibling language → its (richest) page id. pgvector does the
            # distance in C (one self-join over the windowed set), so the Reader can
            # collapse the "All" view to primaries + link "also in {lang}". Gated on
            # the lifecycle window so the self-join stays bounded to recent events.
            dup_rows = []
            if app.cfg.application.lifecycle_feed and rows:
                dup_rows = await conn.fetch(
                    f"""
                    WITH win AS (
                        SELECT e.id, e.language, e.centroid, e.source_count
                          FROM events e JOIN pages p ON p.event_id = e.id
                         WHERE p.published_at IS NOT NULL AND e.status = 'published'
                           AND e.centroid IS NOT NULL
                           {_window_clause}
                    )
                    SELECT a.id,
                           jsonb_object_agg(b.language, b.id ORDER BY b.source_count, b.id)
                               AS also_languages,
                           bool_or((b.source_count, b.id) > (a.source_count, a.id))
                               AS has_better
                      FROM win a JOIN win b
                        ON a.id <> b.id AND a.language <> b.language
                       AND (a.centroid <=> b.centroid) < {_CROSSLANG_DUP_DIST}
                     GROUP BY a.id
                    """
                )
        dup_map = {r["id"]: r for r in dup_rows}
        result = []
        for r in rows:
            d = dict(r)
            # Use the LLM-derived theme rolled up from article-level enrichment
            # (migration 007+). Fall back to keyword matching on the topic string
            # for older articles that pre-date the theme column.
            raw_theme = d.get("theme")
            d["category"] = raw_theme if raw_theme else _derive_category(d.get("topic"))
            d["cover_image"] = _decode_json_col(d.get("cover_image"))  # ADR-0034 Tier 2
            # ADR-0037 cross-language dedup tags (default: unique, primary).
            dr = dup_map.get(d["id"])
            d["primary"] = not (dr and dr["has_better"])
            d["also_languages"] = _decode_json_col(dr["also_languages"]) if dr else {}
            result.append(d)
        return result

    @api.get("/topics/trending")
    async def trending_topics(
        response: Response, window_hours: int = 48, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Top story topics over the last `window_hours`, recency-weighted.

        Powers the Reader "Trending" surface (task 6b). Ranked by a "hotness"
        score = coverage breadth (distinct published events) decayed by how long
        since the topic's most recent article (HN/Reddit-style gravity). This
        keeps big stories high while surfacing fresh topics toward the FRONT of
        the carousel — pure event-count ordering buried newly-emerging topics at
        the end (they haven't accumulated events yet). Junk enrichment artifacts
        are excluded via _JUNK_TOPIC_PATTERNS. Drill-down via /events?topic=.
        """
        window_hours = min(max(window_hours, 1), 168)  # clamp 1h–7d
        limit = min(max(limit, 1), 100)
        # Over-fetch so near-duplicate collapsing (_dedupe_trending) still
        # leaves `limit` distinct concepts.
        candidate_limit = min(limit * 4, 200)
        # Build "topic NOT ILIKE p1 AND topic NOT ILIKE p2 ..." from the
        # blocklist; patterns use % so prefix/substring forms work.
        junk_clause = " ".join(
            f"AND lower(a.topic) NOT LIKE ${i + 3}"
            for i in range(len(_JUNK_TOPIC_PATTERNS))
        )
        # Count over events that have a PUBLISHED PAGE (same population as
        # /events?topic=) so a chip's number matches the drill-down result.
        sql = f"""
            SELECT a.topic,
                   COUNT(DISTINCT a.event_id) AS event_count,
                   COUNT(*)                   AS article_count,
                   -- Representative theme for the chip's color accent: the most
                   -- common article-level theme among this topic's articles.
                   MODE() WITHIN GROUP (ORDER BY a.theme)
                     FILTER (WHERE a.theme IS NOT NULL) AS theme,
                   MAX(a.scraped_at) AS latest
              FROM articles a
              JOIN pages pg ON pg.event_id = a.event_id
                           AND pg.published_at IS NOT NULL
             WHERE a.topic IS NOT NULL AND TRIM(a.topic) <> ''
               AND a.scraped_at > NOW() - ($1 || ' hours')::interval
               {junk_clause}
             GROUP BY a.topic
             -- Hotness = coverage / (hours_since_latest + 2)^1.2 — recent +
             -- well-covered topics rank highest; topics decay as they age so a
             -- fresh story surfaces toward the front of the carousel.
             ORDER BY (
                 COUNT(DISTINCT a.event_id)::float
                 / power(
                     EXTRACT(EPOCH FROM (NOW() - MAX(a.scraped_at))) / 3600.0 + 2,
                     1.2
                   )
             ) DESC, event_count DESC
             LIMIT $2
        """
        response.headers["Cache-Control"] = "public, max-age=120"
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                sql, str(window_hours), candidate_limit, *_JUNK_TOPIC_PATTERNS
            )
        # Collapse same-story label variants, then trim to the requested limit.
        return _dedupe_trending([dict(r) for r in rows], limit)

    @api.get("/outlook")
    async def get_outlook(response: Response, theme: str, lang: str = "es",
                          date: str | None = None) -> dict[str, Any]:
        """Today's [Topic] Outlook — the daily editorial column (ADR-0008) for a
        theme + language, plus the day's cited-events timeline (chronological) and
        the archive of available edition dates. `date` (YYYY-MM-DD) reads a past
        edition; default = the latest. Returns {} if no edition (editorial not run)."""
        response.headers["Cache-Control"] = "public, max-age=300"
        # asyncpg needs a real date object for the DATE column param, not the
        # raw query string (a str raises DataError). Malformed → ignore the
        # filter and fall back to the latest edition.
        d3: _dt.date | None = None
        if date:
            try:
                d3 = _dt.date.fromisoformat(date)
            except ValueError:
                d3 = None
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            if not await conn.fetchval("SELECT to_regclass('public.editorials')"):
                return {}
            ed = await conn.fetchrow(
                "SELECT theme, language, edition_date, persona, headline, body_md, "
                "       event_ids, model "
                "  FROM editorials WHERE theme=$1 AND language=$2 "
                + ("AND edition_date=$3 " if d3 else "")
                + "ORDER BY edition_date DESC LIMIT 1",
                *( (theme, lang, d3) if d3 else (theme, lang) ))
            if not ed:
                return {}
            dates = await conn.fetch(
                "SELECT edition_date FROM editorials WHERE theme=$1 AND language=$2 "
                "ORDER BY edition_date DESC LIMIT 30", theme, lang)
            eids = list(ed["event_ids"] or [])
            tl = await conn.fetch(
                "SELECT p.id, p.headline, p.freshness_at, e.source_count "
                "  FROM pages p JOIN events e ON e.id = p.event_id "
                " WHERE p.id = ANY($1::text[]) ORDER BY p.freshness_at ASC", eids) if eids else []
        return {
            "theme": ed["theme"], "language": ed["language"],
            "edition_date": str(ed["edition_date"]), "persona": ed["persona"],
            "headline": ed["headline"], "body_md": ed["body_md"], "model": ed["model"],
            "timeline": [{"id": r["id"], "headline": r["headline"],
                          "freshness_at": r["freshness_at"], "source_count": r["source_count"]}
                         for r in tl],
            "available_dates": [str(r["edition_date"]) for r in dates],
        }

    @api.get("/outlook/available")
    async def outlook_available(response: Response, lang: str = "es") -> dict[str, Any]:
        """Topics that have a published edition (latest per theme) — the Outlook index/nav."""
        response.headers["Cache-Control"] = "public, max-age=300"
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            if not await conn.fetchval("SELECT to_regclass('public.editorials')"):
                return {"topics": []}
            rows = await conn.fetch(
                "SELECT DISTINCT ON (theme) theme, edition_date, headline, persona "
                "FROM editorials WHERE language=$1 ORDER BY theme, edition_date DESC", lang)
        return {"topics": [{"theme": r["theme"], "edition_date": str(r["edition_date"]),
                            "headline": r["headline"], "persona": r["persona"]} for r in rows]}

    @api.get("/outlook/archive")
    async def outlook_archive(response: Response, lang: str = "es",
                              days: int = 14) -> dict[str, Any]:
        """Every published edition over the last `days` days (newest first) — the
        date-grouped Outlook timeline. The Reader groups these by edition_date so
        the reader can browse day-by-day. `days` is clamped to 1..60."""
        response.headers["Cache-Control"] = "public, max-age=300"
        days = max(1, min(days, 60))
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            if not await conn.fetchval("SELECT to_regclass('public.editorials')"):
                return {"editions": []}
            rows = await conn.fetch(
                "SELECT edition_date, theme, headline, persona FROM editorials "
                "WHERE language=$1 AND edition_date >= CURRENT_DATE - $2::int "
                "ORDER BY edition_date DESC, theme ASC", lang, days)
        return {"editions": [{"edition_date": str(r["edition_date"]), "theme": r["theme"],
                              "headline": r["headline"], "persona": r["persona"]}
                             for r in rows]}

    # ── Web Push: "Daily Outlook ready" PWA notifications (ADR-R-0012) ────────
    @api.get("/push/vapid")
    async def push_vapid() -> dict[str, str]:
        """The VAPID public key (applicationServerKey) for the browser to subscribe."""
        return {"publicKey": push_service.vapid_public_key()}

    @api.post("/push/subscribe")
    async def push_subscribe(body: PushSubBody) -> dict[str, Any]:
        sub = body.subscription or {}
        keys = sub.get("keys") or {}
        endpoint = sub.get("endpoint")
        if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
            raise HTTPException(422, "invalid subscription")
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                """
                INSERT INTO push_subscriptions (endpoint, p256dh, auth, topics, lang, user_agent)
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (endpoint) DO UPDATE
                  SET p256dh=EXCLUDED.p256dh, auth=EXCLUDED.auth,
                      topics=EXCLUDED.topics, lang=EXCLUDED.lang,
                      user_agent=EXCLUDED.user_agent
                """,
                endpoint, keys["p256dh"], keys["auth"],
                body.topics or ["outlook-daily"], body.lang, body.userAgent)
        return {"ok": True}

    @api.post("/push/unsubscribe")
    async def push_unsubscribe(body: PushUnsubBody) -> dict[str, Any]:
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute("DELETE FROM push_subscriptions WHERE endpoint=$1", body.endpoint)
        return {"ok": True}

    async def _broadcast_outlook() -> None:
        """Fan out the daily notification to every 'outlook-daily' subscriber,
        pruning dead subscriptions (404/410). Runs off the request (background)."""
        import asyncio
        if not push_service.push_enabled():
            logger.warning("push broadcast skipped — VAPID keys not configured")
            return
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            subs = await conn.fetch(
                "SELECT endpoint, p256dh, auth, lang FROM push_subscriptions "
                "WHERE 'outlook-daily' = ANY(topics)")
        payload_es = {"title": "Los Outlooks de hoy están listos",
                      "body": "Una columna editorial por tema, recién publicada.",
                      "url": "/outlook", "tag": "outlook-daily"}
        payload_en = {"title": "Today's Outlooks are ready",
                      "body": "A fresh editorial column for every topic.",
                      "url": "/outlook", "tag": "outlook-daily"}
        sent = dead = 0
        for s in subs:
            payload = payload_en if s["lang"] == "en" else payload_es
            status = await asyncio.to_thread(push_service.send_one, dict(s), payload)
            if status in (404, 410):
                dead += 1
                async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
                    await conn.execute("DELETE FROM push_subscriptions WHERE endpoint=$1", s["endpoint"])
            elif status:
                sent += 1
        logger.info("push broadcast: %d sent, %d pruned, %d total", sent, dead, len(subs))

    @api.post("/push/broadcast-outlook")
    async def push_broadcast_outlook(
        background: BackgroundTasks,
        x_push_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Trigger the daily broadcast (called by the Editorial cron after it
        generates the columns). Token-guarded so it isn't publicly abusable."""
        secret = os.getenv("PUSH_TRIGGER_SECRET", "")
        if not secret or x_push_token != secret:
            raise HTTPException(403, "forbidden")
        background.add_task(_broadcast_outlook)
        return {"ok": True, "queued": True}

    @api.get("/outlets")
    async def list_outlets() -> list[dict[str, Any]]:
        return await app.db.get_outlets_with_stats()

    @api.get("/events/{event_id}")
    async def get_event(event_id: str) -> dict[str, Any]:
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                """
                SELECT p.*, e.source_count, e.article_count, e.topic,
                       e.first_seen_at AS occurred_at,   -- "Started" date (event page)
                       -- Majority article theme → drives the procedural cover color
                       -- (ADR-0034) + the category chip on the event page.
                       e.cover_image,   -- ADR-0034 Tier 2 license-clean cover (JSONB)
                       (SELECT a.theme FROM articles a
                         WHERE a.event_id = e.id AND a.theme IS NOT NULL
                         GROUP BY a.theme ORDER BY COUNT(*) DESC LIMIT 1) AS theme,

                       -- Cover image: same rollup as the /events list endpoint
                       -- with ADR-0016 COALESCE fallback to events.hero_image.
                       COALESCE(
                           (SELECT a.lead_image
                              FROM articles a
                             WHERE a.event_id = e.id
                               AND a.lead_image IS NOT NULL
                               AND a.lead_image <> ''
                               AND a.cluster_distance <= 0.45
                             ORDER BY a.scraped_at DESC
                             LIMIT 1),
                           e.hero_image
                       ) AS lead_image,

                       -- Timeline: article publication order, showing how the
                       -- story was picked up outlet by outlet over time.
                       -- Ordered by published_at so the Reader can render a
                       -- chronological development strip.
                       (
                         SELECT jsonb_agg(
                                  jsonb_build_object(
                                    'outlet_name', a.outlet_name,
                                    'title',       a.title,
                                    'published_at', a.published_at,
                                    'scraped_at',   a.scraped_at
                                  )
                                  ORDER BY a.published_at ASC NULLS LAST
                                )
                           FROM (
                                  SELECT outlet_name, title, published_at, scraped_at
                                    FROM articles
                                   WHERE event_id = e.id
                                   ORDER BY published_at ASC NULLS LAST
                                   LIMIT 20
                                ) a
                       ) AS timeline

                  FROM pages p JOIN events e ON e.id = p.event_id
                 WHERE p.id = $1
                   AND p.published_at IS NOT NULL
                   AND e.status IN ('published', 'concluded')
                """,
                event_id,
            )
        if not row:
            raise HTTPException(404, f"event {event_id} not found")
        result = dict(row)
        # asyncpg returns jsonb_agg as a raw JSON string; normalise to a list.
        result["timeline"]      = _decode_json_col(result.get("timeline"))
        result["media_rail"]    = _decode_json_col(result.get("media_rail"))
        result["title_history"] = _decode_json_col(result.get("title_history"))  # ADR-0035
        result["cover_image"]   = _decode_json_col(result.get("cover_image"))    # ADR-0034
        # category = LLM theme (else keyword-derived) — same as the feed; drives
        # the procedural cover color + the event-page chip (ADR-0034).
        result["category"] = result.get("theme") or _derive_category(result.get("topic"))
        return result

    @api.get("/graph")
    async def get_graph(
        response: Response,
        min_event_count: int = 2,
        limit_nodes: int = 80,
        min_edge_weight: int = 2,
        limit_edges: int = 250,
    ) -> dict[str, Any]:
        """Entity co-occurrence graph for the /entities page (ADR-0005 Approach A).

        Nodes  — entities that appear in ≥ min_event_count published events.
        Edges  — entity pairs that co-appear in ≥ min_edge_weight events.

        Uses articles.entities (has type from ENRICH) rather than pages.entities
        (which only stores bare names). Deduplicates to one row per
        (event, entity_name_lower) before the self-join so edge weight counts
        distinct events, not article repetitions.
        """
        limit_nodes = min(limit_nodes, _MAX_GRAPH_NODES)  # ADR-0006 §D1
        limit_edges = min(limit_edges, _MAX_GRAPH_EDGES)
        response.headers["Cache-Control"] = "public, max-age=120"
        # Per-type quotas so the graph is a balanced NEWSMAKER network, not a list
        # of ubiquitous countries: ranking purely by event_count let places
        # (estados unidos, españa, méxico) + wire services crowd out people/orgs
        # → "People = 1". PERSON/ORG lead; LOC/EVENT are context. (2026-06-26)
        person_cap = max(1, round(limit_nodes * 0.45))
        org_cap    = max(1, round(limit_nodes * 0.30))
        loc_cap    = max(1, round(limit_nodes * 0.18))
        event_cap  = max(1, round(limit_nodes * 0.07))
        other_cap  = max(1, round(limit_nodes * 0.04))
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                f"""
                WITH published AS (
                    SELECT e.id       AS event_id,
                           p.id       AS page_id,
                           p.headline,
                           p.freshness_at,
                           e.source_count
                      FROM events e
                      JOIN pages p ON p.event_id = e.id
                     WHERE p.published_at IS NOT NULL
                       AND e.status = 'published'
                ),
                -- One row per (event_id, entity_name_lower) — deduplicates
                -- articles that share the same entity within one event. Keeps the
                -- highest-salience mention's display name.
                ev_ents AS (
                    SELECT DISTINCT ON (a.event_id, LOWER(ent.name))
                           a.event_id,
                           pub.page_id,
                           pub.headline,
                           pub.freshness_at,
                           pub.source_count,
                           LOWER(ent.name)       AS name_key,
                           ent.name              AS name_orig
                      FROM articles a
                      JOIN published pub ON pub.event_id = a.event_id
                      JOIN entities  ent ON ent.article_id = a.id
                     WHERE LENGTH(ent.name) >= 2
                     ORDER BY a.event_id, LOWER(ent.name), ent.salience DESC
                ),
                -- Dominant type per entity from RAW mentions (not the per-event
                -- collapse), tiebreak prefers concrete types over OTHER. Fixes the
                -- old alphabetical tiebreak that demoted PERSON (sorts last).
                dom_type AS (
                    SELECT DISTINCT ON (name_key) name_key, type
                      FROM (
                               SELECT LOWER(ent.name) AS name_key,
                                      UPPER(ent.type)  AS type,
                                      COUNT(*)         AS cnt
                                 FROM entities ent
                                 JOIN articles  a   ON a.id = ent.article_id
                                 JOIN published pub ON pub.event_id = a.event_id
                                GROUP BY 1, 2
                           ) t
                     ORDER BY name_key, cnt DESC,
                              (CASE type WHEN 'PERSON' THEN 0 WHEN 'ORG' THEN 1
                                         WHEN 'LOC' THEN 2 WHEN 'EVENT' THEN 3 ELSE 4 END)
                ),
                counts AS (
                    SELECT name_key, COUNT(DISTINCT event_id) AS event_count
                      FROM ev_ents GROUP BY name_key
                ),
                -- Rank WITHIN type, drop wire-service/outlet bylines (they tag
                -- every article from that source → ubiquitous but not newsmakers).
                ranked AS (
                    SELECT c.name_key, c.event_count, dt.type,
                           ROW_NUMBER() OVER (PARTITION BY dt.type
                                              ORDER BY c.event_count DESC) AS rn
                      FROM counts c
                      JOIN dom_type dt USING (name_key)
                     WHERE c.event_count >= $1
                       AND c.name_key <> ALL($5::text[])
                ),
                -- Per-type quota → balanced node set
                node_cands AS (
                    SELECT name_key, type, event_count
                      FROM ranked
                     WHERE (type = 'PERSON' AND rn <= {person_cap})
                        OR (type = 'ORG'    AND rn <= {org_cap})
                        OR (type = 'LOC'    AND rn <= {loc_cap})
                        OR (type = 'EVENT'  AND rn <= {event_cap})
                        OR (type = 'OTHER'  AND rn <= {other_cap})
                     ORDER BY event_count DESC
                     LIMIT $2
                ),
                -- Full node rows with page summaries for the side panel
                nodes_agg AS (
                    SELECT nc.name_key                                       AS id,
                           MIN(ee.name_orig)                                 AS label,
                           nc.type                                           AS type,
                           nc.event_count,
                           -- Wikidata/Commons photo + description (ADR-0034
                           -- companion); NULL until the entity-photo backfill
                           -- resolves it. blocked rows are excluded by the join.
                           em.thumb_url                                      AS image,
                           em.description                                    AS description,
                           em.attribution                                    AS image_attribution,
                           em.source_url                                     AS image_source,
                           JSON_AGG(DISTINCT
                               JSONB_BUILD_OBJECT(
                                   'id',           ee.page_id,
                                   'headline',     ee.headline,
                                   'source_count', ee.source_count,
                                   'freshness_at', ee.freshness_at
                               )
                           )                                                  AS pages
                      FROM node_cands nc
                      JOIN ev_ents    ee ON ee.name_key = nc.name_key
                      LEFT JOIN entity_media em
                             ON em.name_norm = nc.name_key AND em.blocked = FALSE
                     GROUP BY nc.name_key, nc.event_count, nc.type,
                              em.thumb_url, em.description, em.attribution, em.source_url
                ),
                -- Edges: entity pairs co-appearing in the same event
                edges_agg AS (
                    SELECT LEAST(a.name_key, b.name_key)    AS source,
                           GREATEST(a.name_key, b.name_key) AS target,
                           COUNT(DISTINCT a.event_id)        AS weight
                      FROM ev_ents a
                      JOIN ev_ents b
                           ON  a.event_id  = b.event_id
                           AND a.name_key  < b.name_key
                     WHERE a.name_key IN (SELECT name_key FROM node_cands)
                       AND b.name_key IN (SELECT name_key FROM node_cands)
                     GROUP BY 1, 2
                    HAVING COUNT(DISTINCT a.event_id) >= $3
                     ORDER BY weight DESC
                     LIMIT $4
                )
                SELECT
                    COALESCE((SELECT JSON_AGG(n) FROM nodes_agg n), '[]'::json) AS nodes,
                    COALESCE((SELECT JSON_AGG(e) FROM edges_agg e), '[]'::json) AS edges,
                    (SELECT COUNT(*) FROM node_cands)                            AS node_count,
                    (SELECT COUNT(*) FROM edges_agg)                             AS edge_count,
                    (SELECT COUNT(*) FROM published)                             AS event_count
                """,
                min_event_count, limit_nodes, min_edge_weight, limit_edges,
                _GRAPH_SOURCE_STOPWORDS,
            )
        return {
            "nodes": _decode_json_col(row["nodes"]),
            "edges": _decode_json_col(row["edges"]),
            "meta": {
                "node_count":  row["node_count"],
                "edge_count":  row["edge_count"],
                "event_count": row["event_count"],
            },
        }

    @api.get("/events/{event_id}/related")
    async def get_related_events(
        event_id: str,
        limit: int = 5,
        min_score: float = 0.4,
    ) -> list[dict[str, Any]]:
        """Return events related to `event_id` by entity + topic overlap.

        Score = entity_overlap_coefficient × topic_multiplier  (ADR-0005)

          entity_overlap = |shared entity names| / max(|A|, |B|, 1)
          topic_multiplier = 1.3 if same non-null topic, else 1.0

        Returns events with score ≥ min_score, ordered by score desc.
        Returns 404 when event_id does not exist or is not published (ADR-0006 §D2).
        """
        async with app.db.pool.acquire() as conn:  # type: ignore[union-attr]
            # Pre-flight: fast PK lookup before the heavy scoring CTE.
            # Consistent with GET /events/{id} which also 404s for unknown IDs.
            exists = await conn.fetchval(
                "SELECT EXISTS("
                "  SELECT 1 FROM pages"
                "  WHERE id = $1 AND published_at IS NOT NULL"
                ")",
                event_id,
            )
            if not exists:
                raise HTTPException(404, f"event {event_id} not found")
            rows = await conn.fetch(
                """
                WITH target AS (
                    SELECT
                        p.id,
                        -- Normalise to lowercase so "DONALD TRUMP" = "Donald Trump"
                        ARRAY(
                            SELECT LOWER(ent->>'name')
                              FROM jsonb_array_elements(p.entities) ent
                             WHERE ent->>'name' IS NOT NULL
                        ) AS entity_names,
                        ev.topic,
                        ev.language
                      FROM pages p
                      JOIN events ev ON ev.id = p.event_id
                     WHERE p.id = $1
                       AND p.published_at IS NOT NULL
                ),
                candidates AS (
                    SELECT
                        p.id,
                        p.headline,
                        p.freshness_at,
                        p.published_at,
                        e.source_count,
                        e.article_count,
                        e.topic,
                        e.language,
                        ARRAY(
                            SELECT LOWER(ent->>'name')
                              FROM jsonb_array_elements(p.entities) ent
                             WHERE ent->>'name' IS NOT NULL
                        ) AS entity_names,
                        ARRAY(
                            SELECT DISTINCT a.outlet_name
                              FROM articles a
                             WHERE a.event_id = e.id
                               AND a.outlet_name IS NOT NULL
                             LIMIT 5
                        ) AS outlet_names
                      FROM pages p
                      JOIN events e ON e.id = p.event_id
                     WHERE p.id      != $1
                       AND p.published_at IS NOT NULL
                       AND e.status   = 'published'
                ),
                scored AS (
                    SELECT
                        c.*,
                        -- Overlap coefficient: shared / max(|A|, |B|).
                        -- Both sides are already lowercased — comparison is exact.
                        CASE
                            WHEN GREATEST(
                                     cardinality(t.entity_names),
                                     cardinality(c.entity_names)
                                 ) = 0 THEN 0.0
                            ELSE (
                                SELECT COUNT(*)::float
                                  FROM unnest(c.entity_names) n
                                 WHERE n = ANY(t.entity_names)
                            ) / GREATEST(
                                    cardinality(t.entity_names),
                                    cardinality(c.entity_names)
                                )
                        END
                        -- Topic multiplier: same non-null topic boosts by 30 %.
                        * CASE
                            WHEN t.topic IS NOT NULL
                             AND c.topic IS NOT NULL
                             AND c.topic = t.topic THEN 1.3
                            ELSE 1.0
                          END AS score
                      FROM candidates c, target t
                )
                SELECT
                    id, headline, freshness_at, published_at,
                    source_count, article_count, topic, language,
                    outlet_names,
                    ROUND(score::numeric, 4) AS score
                  FROM scored
                 WHERE score >= $2
                 ORDER BY score DESC
                 LIMIT $3
                """,
                event_id, min_score, limit,
            )
        return [dict(r) for r in rows]

    @api.post("/ask")
    async def ask(body: AskRequest) -> dict[str, Any]:
        """Corpus chat assistant (ADR-0022) — grounded digest / Q&A.

        Answers ONLY from published events; returns markdown + numbered sources
        that resolve to InkBytes event pages. mode: resume | top10 | chat.
        """
        mode = body.mode if body.mode in ("resume", "top10", "chat") else "chat"
        if mode == "chat" and not body.question.strip():
            raise HTTPException(400, "question required for chat mode")
        return await app.assistant.answer(body.question, mode)

    return api
