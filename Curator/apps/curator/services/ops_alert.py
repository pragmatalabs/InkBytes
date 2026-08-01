"""Ops alerting — best-effort phone-push webhook for operational incidents (ADR-0044).

A tiny, dependency-free notifier so the pipeline can page a human BEFORE (low
balance) or AT (both providers quota-exhausted) a feed freeze. Env-configured;
inert (logs only) when no webhook is set, so it never affects generation.

    OPS_ALERT_WEBHOOK_URL        the endpoint (Slack incoming webhook, a Telegram
                                 sendMessage URL, or any JSON {"text":...} sink)
    OPS_ALERT_WEBHOOK_KIND       slack (default) | telegram | generic
    OPS_ALERT_TELEGRAM_CHAT_ID   required when kind=telegram
    OPS_ALERT_COOLDOWN_SECONDS   per-key re-alert throttle (default 10800 = 3h)

Best-effort by contract: any send failure is swallowed + logged. `alert()` is
SYNCHRONOUS (a short urllib POST) so it is safe to call from a sync callback
(e.g. the worker's on_quota_exhausted) as well as from an async loop.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request

logger = logging.getLogger(__name__)

_DEFAULT_COOLDOWN_S = 10800  # 3h — long enough that a persistent low balance nags, not spams


class OpsAlerter:
    def __init__(self, url: str | None = None, kind: str | None = None,
                 telegram_chat_id: str | None = None,
                 cooldown_s: int | None = None) -> None:
        self._url = (url if url is not None else os.getenv("OPS_ALERT_WEBHOOK_URL", "")).strip()
        self._kind = (kind or os.getenv("OPS_ALERT_WEBHOOK_KIND", "slack")).strip().lower()
        self._chat_id = (telegram_chat_id
                         if telegram_chat_id is not None
                         else os.getenv("OPS_ALERT_TELEGRAM_CHAT_ID", "")).strip()
        self._cooldown_s = int(cooldown_s if cooldown_s is not None
                               else os.getenv("OPS_ALERT_COOLDOWN_SECONDS", _DEFAULT_COOLDOWN_S))
        self._last: dict[str, float] = {}
        if not self._url:
            logger.info("OpsAlerter: no OPS_ALERT_WEBHOOK_URL — alerts will log only")

    @property
    def enabled(self) -> bool:
        return bool(self._url)

    def _payload(self, text: str) -> dict:
        # Slack + generic both accept {"text": ...}. Telegram sendMessage needs a chat_id.
        if self._kind == "telegram":
            body: dict[str, str] = {"text": text}
            if self._chat_id:
                body["chat_id"] = self._chat_id
            return body
        return {"text": text}

    def alert(self, key: str, text: str, cooldown_s: int | None = None) -> None:
        """Send an alert, throttled per `key`. Never raises.

        `key` groups alerts for cooldown (e.g. "deepseek-low-balance"); a given
        key re-fires at most once per cooldown window so a standing condition
        nags instead of flooding.
        """
        now = time.time()
        window = self._cooldown_s if cooldown_s is None else cooldown_s
        if now - self._last.get(key, 0.0) < window:
            return
        self._last[key] = now
        if not self._url:
            logger.warning("OPS ALERT [%s] (no webhook configured): %s", key, text)
            return
        try:
            data = json.dumps(self._payload(text)).encode("utf-8")
            req = urllib.request.Request(
                self._url, data=data,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            urllib.request.urlopen(req, timeout=10).read()
            logger.info("ops alert sent [%s]", key)
        except Exception as exc:  # noqa: BLE001 — alerting must never break the pipeline
            logger.warning("ops alert send failed [%s]: %s", key, exc)
