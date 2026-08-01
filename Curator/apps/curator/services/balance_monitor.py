"""Proactive DeepSeek balance monitor (ADR-0044).

Polls DeepSeek's `GET /user/balance` and pages a human via OpsAlerter BEFORE the
balance hits $0 and the pipeline 402-freezes (as it did on 2026-08-01). Runs as a
SINGLE instance — started only from the `--api-only` container — so N workers do
not each poll/alert. Best-effort: any error is logged and the loop continues.

Env:
    OPS_BALANCE_POLL_SECONDS   poll interval (default 1800 = 30 min)
    DEEPSEEK_LOW_BALANCE_USD   alert threshold in USD (default 2.0)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request

from services.ops_alert import OpsAlerter

logger = logging.getLogger(__name__)

_BALANCE_URL = "https://api.deepseek.com/user/balance"
_UNSET = {"", "__SET_VIA_ENV__", "CHANGEME"}


def _fetch_balance(api_key: str) -> tuple[float | None, bool]:
    """Return (total_balance_usd, is_available). Blocking — call in a thread.

    total_balance is None when the response can't be parsed (treated as "unknown",
    not "low", so a transient API hiccup never pages).
    """
    req = urllib.request.Request(
        _BALANCE_URL, headers={"Authorization": f"Bearer {api_key}",
                               "Accept": "application/json"},
    )
    raw = urllib.request.urlopen(req, timeout=10).read()
    data = json.loads(raw)
    is_available = bool(data.get("is_available", True))
    total: float | None = None
    for info in (data.get("balance_infos") or []):
        # Prefer USD; fall back to the first entry. total_balance is a STRING.
        if str(info.get("currency", "")).upper() == "USD" or total is None:
            try:
                total = float(info.get("total_balance"))
            except (TypeError, ValueError):
                continue
            if str(info.get("currency", "")).upper() == "USD":
                break
    return total, is_available


async def run(alerter: OpsAlerter, llm_cfg, *, poll_seconds: int | None = None,
              threshold_usd: float | None = None) -> None:
    """Poll forever. Inert (returns) when no DeepSeek key is configured."""
    key = getattr(llm_cfg, "deepseek_api_key", "") or ""
    if key in _UNSET:
        logger.info("balance monitor: no DeepSeek key — not starting")
        return
    interval = int(poll_seconds if poll_seconds is not None
                   else os.getenv("OPS_BALANCE_POLL_SECONDS", 1800))
    threshold = float(threshold_usd if threshold_usd is not None
                      else os.getenv("DEEPSEEK_LOW_BALANCE_USD", 2.0))
    logger.info("balance monitor started (every %ds, alert < $%.2f)", interval, threshold)
    while True:
        try:
            total, available = await asyncio.to_thread(_fetch_balance, key)
            if not available:
                alerter.alert(
                    "deepseek-unavailable",
                    "🚨 InkBytes: DeepSeek reports balance UNAVAILABLE — the pipeline "
                    "will 402-freeze. Top up now.",
                )
            elif total is not None and total < threshold:
                alerter.alert(
                    "deepseek-low-balance",
                    f"⚠️ InkBytes: DeepSeek balance ${total:.2f} is below ${threshold:.2f}. "
                    f"Top up before the feed freezes (a $0 balance stalls enrich/synth).",
                )
            else:
                logger.debug("balance monitor: DeepSeek balance ok (%s)",
                             f"${total:.2f}" if total is not None else "unknown")
        except Exception as exc:  # noqa: BLE001 — never let the monitor crash the API
            logger.warning("balance monitor poll failed: %s", exc)
        await asyncio.sleep(interval)
