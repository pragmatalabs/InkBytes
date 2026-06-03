"""
Messor scraper API router.

Endpoints
---------
WS  /api/scrape/ws             Real-time scrape trigger + log streaming
GET /api/scrape/status         Real scraper state (running, last run, counts)
GET /api/scrapesessions        Paginated scraping history from staging files
GET /api/outlets               Outlet catalogue from outlets.json
POST /api/scrape/session/{id}/view  View counter

Author: juliandelarosa@icloud.com
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import queue
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

import __main__
from api.utils.api_security import _api_key_is_valid

router = APIRouter()

# ── helpers ──────────────────────────────────────────────────────────────────

SCRAPES_DIR  = Path(__file__).resolve().parents[2] / "data" / "scrapes"
OUTLETS_FILE = Path(__file__).resolve().parents[2] / "data" / "outlets" / "outlets.json"

_session_views: Dict[str, Dict] = {}


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
        views_info = _session_views.get(session_id, {})

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
            "views":               views_info.get("views", 0),
            "last_viewed":         views_info.get("last_viewed"),
        })

    return sessions


# ── WebSocket (scrape trigger + live logs) ────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self.message_queues: Dict[WebSocket, queue.Queue] = {}

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active_connections.append(ws)
        self.message_queues[ws] = queue.Queue()

    def disconnect(self, ws: WebSocket) -> None:
        self.active_connections.discard(ws) if hasattr(self.active_connections, "discard") \
            else (self.active_connections.remove(ws) if ws in self.active_connections else None)
        self.message_queues.pop(ws, None)

    def queue_message(self, msg: str, ws: WebSocket) -> None:
        if ws in self.message_queues:
            self.message_queues[ws].put(msg)

    async def flush_queue(self, ws: WebSocket) -> None:
        q = self.message_queues.get(ws)
        if not q:
            return
        while not q.empty():
            try:
                await ws.send_text(q.get_nowait())
                q.task_done()
            except Exception:
                break

    async def send(self, msg: str, ws: WebSocket) -> None:
        try:
            await ws.send_text(msg)
        except Exception:
            pass


manager = ConnectionManager()


class _WsLogger:
    """Intercepts scraper log calls and queues them for the WebSocket."""
    def __init__(self, original, ws: WebSocket) -> None:
        self._orig = original
        self._ws = ws
        self._n = 0

    def _fwd(self, level: str, msg: str) -> None:
        getattr(self._orig, level)(msg)
        self._n += 1
        manager.queue_message(f"{level.upper()} #{self._n}: {msg}", self._ws)

    def info(self, msg: str) -> None:    self._fwd("info", msg)
    def error(self, msg: str) -> None:   self._fwd("error", msg)
    def warning(self, msg: str) -> None: self._fwd("warning", msg)


async def _queue_processor(ws: WebSocket) -> None:
    try:
        while True:
            await manager.flush_queue(ws)
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        await manager.flush_queue(ws)
        raise


async def _run_scrape(ws: WebSocket) -> None:
    await manager.send("Scrape initiated", ws)
    try:
        scraper = __main__.app.command_processor.scraper_service
        orig_logger = scraper.logger

        def _work():
            scraper.logger = _WsLogger(orig_logger, ws)
            try:
                return scraper.execute_scraping_process()
            finally:
                scraper.logger = orig_logger

        t0 = time.time()
        result = await asyncio.get_event_loop().run_in_executor(None, _work)
        elapsed = time.time() - t0

        await manager.send(f"Scraping completed in {elapsed:.1f}s", ws)
        if result:
            await manager.send(f"Scraped {len(result)} outlets", ws)
    except Exception as exc:
        await manager.send(f"Error: {exc}", ws)
    finally:
        await manager.send("Scraping process finished", ws)


@router.websocket("/api/scrape/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        api_key = websocket.query_params.get("api_key", "")
        if not api_key or not _api_key_is_valid(api_key):
            await manager.send("Invalid API key", websocket)
            await websocket.close()
            return

        await manager.send("Connected to Messor scraper", websocket)
        processor = asyncio.create_task(_queue_processor(websocket))

        try:
            while True:
                try:
                    data = await websocket.receive_text()
                    if data == "start_scrape":
                        await manager.send("Received start_scrape command", websocket)
                        asyncio.create_task(_run_scrape(websocket))
                        await manager.send("Scrape started in background", websocket)
                    else:
                        await manager.send(f"Unknown command: {data}", websocket)
                except WebSocketDisconnect:
                    break
        finally:
            processor.cancel()
            try:
                await processor
            except asyncio.CancelledError:
                pass
    except Exception as exc:
        pass
    finally:
        manager.disconnect(websocket)


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.get("/api/scrape/status")
async def scrape_status() -> Dict[str, Any]:
    """Real scraper state: running flag, last run, totals."""
    sessions = _read_staging_sessions()
    running = False
    try:
        running = bool(__main__.app._scraping_active)
    except AttributeError:
        pass

    last_session = sessions[0] if sessions else None
    return {
        "running":          running,
        "last_run_at":      last_session["start_time"] if last_session else None,
        "outlets_scraped":  last_session["total_outlets"] if last_session else 0,
        "articles_collected": last_session["total_articles"] if last_session else 0,
        "total_sessions":   len(sessions),
        "status":           "Running" if running else ("Idle" if sessions else "No data yet"),
    }


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


@router.post("/api/scrape/session/{session_id}/view")
async def record_view(session_id: str) -> Dict[str, Any]:
    if session_id not in _session_views:
        _session_views[session_id] = {"views": 0, "last_viewed": None}
    _session_views[session_id]["views"] += 1
    _session_views[session_id]["last_viewed"] = datetime.now(tz=timezone.utc).isoformat()
    return {"session_id": session_id, **_session_views[session_id]}


@router.get("/api/scrape/results")
async def scrape_results() -> Dict[str, Any]:
    """Latest scraping session — kept for backwards compatibility."""
    sessions = _read_staging_sessions()
    if not sessions:
        return {"error": "No scraping sessions found. Run a scraping cycle first."}
    s = sessions[0]
    return {
        "id":                    s["id"],
        "start_time":            s["start_time"],
        "end_time":              s["end_time"],
        "total_outlets_scraped": s["total_outlets"],
        "total_articles_scraped":s["total_articles"],
        "overall_success_rate":  s["success_rate"],
        "duration":              s["duration"],
        "views":                 s["views"],
        "last_viewed":           s["last_viewed"],
        "results": [
            {
                "outlet": {"name": o["name"], "url": f"https://{o['slug']}.com", "type": "news"},
                "total_articles":      o["articles"],
                "successful_scrapes":  o["articles"],
                "failed_scrapes":      0,
                "duration":            s["duration"] / max(s["total_outlets"], 1),
                "errors":              [],
            }
            for o in s["outlets"]
        ],
    }
