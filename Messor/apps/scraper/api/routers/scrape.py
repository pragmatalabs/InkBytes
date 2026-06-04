"""
Messor scraper API router.

Endpoints
---------
GET /api/scrapesessions        Paginated scraping history from staging files
GET /api/outlets               Outlet catalogue from outlets.json

History
-------
The legacy Messor React client (`Messor/client`, :5174) and its WebSocket
scrape-trigger / live-log endpoints were decommissioned in B12.3 once the
Laravel Backoffice fully replaced them. The Backoffice consumes only
`/api/scrapesessions` (run history B4, health B6, alerts B11) and
`/api/outlets`. The client-only endpoints (`/api/scrape/ws`,
`/api/scrape/status`, `/api/scrape/results`, `/api/scrape/session/{id}/view`)
were removed. See docs/adr/0001 and docs/adr/0006.

Author: juliandelarosa@icloud.com
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Request

router = APIRouter()

# ── helpers ──────────────────────────────────────────────────────────────────

SCRAPES_DIR  = Path(__file__).resolve().parents[2] / "data" / "scrapes"
OUTLETS_FILE = Path(__file__).resolve().parents[2] / "data" / "outlets" / "outlets.json"


def _read_staging_sessions() -> List[Dict[str, Any]]:
    """
    Parse all staging files, group by timestamp prefix, return one record
    per scraping session ordered newest-first.

    File naming: {unix_ts}.{outlet_slug}.db.json
    File content: {"_default": {"1": {...article...}, ...}} (TinyDB format)
    """
    if not SCRAPES_DIR.exists():
        return []

    by_ts: Dict[str, Dict] = {}

    for f in SCRAPES_DIR.glob("*.db.json"):
        if f.stat().st_size == 0:
            continue
        # Filename format: {unix_ts}.{outlet_slug}.db.json
        # f.name examples: "1754280000.apnews.db.json", "1775952000.AP News.db.json"
        name_parts = f.name.split(".")
        if len(name_parts) < 4:
            continue
        ts_str = name_parts[0]
        # outlet slug is everything between the timestamp and ".db.json"
        # i.e. join parts[1:-2] to handle slugs with dots (rare but safe)
        outlet_slug = ".".join(name_parts[1:-2])
        if not ts_str.isdigit() or not outlet_slug:
            continue

        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if isinstance(raw, dict) and "_default" in raw:
            articles = list(raw["_default"].values())
        elif isinstance(raw, list):
            articles = raw
        else:
            continue

        count = len(articles)
        if ts_str not in by_ts:
            try:
                dt = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
            except (ValueError, OSError):
                continue
            by_ts[ts_str] = {
                "ts": int(ts_str),
                "start_time": dt.isoformat(),
                "outlets": [],
                "total_articles": 0,
                "successful_articles": 0,
            }

        # Pick display name from outlets.json if available (case-insensitive slug match)
        display_name = outlet_slug.replace("-", " ").replace("_", " ").title()
        if OUTLETS_FILE.exists():
            try:
                cfg_list = json.loads(OUTLETS_FILE.read_text(encoding="utf-8"))
                slug_lower = outlet_slug.lower().replace(" ", "")
                match = next(
                    (o for o in cfg_list
                     if o.get("name", "").lower().replace(" ", "") == slug_lower
                     or o.get("id", "").lower().replace(" ", "") == slug_lower),
                    None,
                )
                if match:
                    display_name = match.get("display_name", display_name)
            except Exception:
                pass

        by_ts[ts_str]["outlets"].append({
            "name": display_name,
            "slug": outlet_slug,
            "articles": count,
        })
        by_ts[ts_str]["total_articles"] += count
        by_ts[ts_str]["successful_articles"] += count  # staging only stores successes

    sessions = []
    for ts_str, s in sorted(by_ts.items(), key=lambda x: -x[1]["ts"]):
        n_outlets = len(s["outlets"])
        total = s["total_articles"]
        # Estimate duration: ~2 s per article attempted, capped at 30 min
        est_duration = min(total * 0.5, 1800)
        end_dt = datetime.fromtimestamp(s["ts"] + est_duration, tz=timezone.utc)

        session_id = f"session-{ts_str}"

        sessions.append({
            "id":                  session_id,
            "documentId":          session_id,
            "start_time":          s["start_time"],
            "end_time":            end_dt.isoformat(),
            "total_articles":      total,
            "successful_articles": s["successful_articles"],
            "failed_articles":     0,
            "duration":            est_duration,
            "success_rate":        1.0 if total > 0 else 0.0,
            "outlet":              ", ".join(o["name"] for o in s["outlets"][:3])
                                   + (f" +{n_outlets - 3} more" if n_outlets > 3 else ""),
            "outlets":             s["outlets"],
            "total_outlets":       n_outlets,
            "views":               0,
            "last_viewed":         None,
        })

    return sessions


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.get("/api/scrapesessions")
async def list_sessions(request: Request) -> Dict[str, Any]:
    """
    Paginated scraping history built from local staging files.

    Query params (simple, not Strapi-style):
      page, limit, outlet, today (bool)

    Also accepts Strapi-style params for backwards compatibility:
      pagination[page], pagination[pageSize], filters[outlet][$eq]
    """
    params = dict(request.query_params)

    # Support both simple and Strapi-style params
    page     = int(params.get("page", params.get("pagination[page]", 1)))
    limit    = int(params.get("limit", params.get("pagination[pageSize]", 10)))
    outlet_f = (params.get("outlet") or params.get("filters[outlet][$eq]") or "").strip()
    today_f  = params.get("today", "").lower() in ("1", "true", "yes")

    sessions = _read_staging_sessions()

    # Apply outlet filter
    if outlet_f and outlet_f.lower() not in ("all outlets", "all", ""):
        sessions = [s for s in sessions
                    if outlet_f.lower() in s["outlet"].lower()]

    # Apply today filter
    if today_f:
        today_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        sessions = [s for s in sessions if s["start_time"].startswith(today_str)]

    total   = len(sessions)
    pages   = max(1, (total + limit - 1) // limit)
    page    = max(1, min(page, pages))
    start   = (page - 1) * limit
    page_sessions = sessions[start: start + limit]

    return {
        "data": page_sessions,
        "meta": {
            "pagination": {
                "page":      page,
                "pageSize":  limit,
                "pageCount": pages,
                "total":     total,
            }
        },
    }


@router.get("/api/outlets")
async def list_outlets() -> List[Dict[str, Any]]:
    """Outlet catalogue from outlets.json, active outlets only."""
    if not OUTLETS_FILE.exists():
        return []
    try:
        data = json.loads(OUTLETS_FILE.read_text(encoding="utf-8"))
        return [o for o in data if o.get("active", True)]
    except Exception:
        return []
