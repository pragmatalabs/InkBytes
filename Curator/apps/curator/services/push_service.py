"""Web Push (VAPID) for the PWA — "Daily Outlook ready" notifications (ADR-R-0012).

Curator owns push: it stores browser subscriptions, holds the VAPID keys, and
fans out notifications. The Reader proxies subscribe/unsubscribe here; the
Editorial cron triggers the daily broadcast after it generates the columns.

VAPID keys come from env (never committed):
  VAPID_PUBLIC_KEY   base64url applicationServerKey (also served to the browser)
  VAPID_PRIVATE_KEY  base64url raw private scalar (backend secret)
  VAPID_SUBJECT      mailto: contact (push services require it)
Push is a no-op (logged) when keys are absent, so the API stays up without them.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def vapid_public_key() -> str:
    return os.getenv("VAPID_PUBLIC_KEY", "")


def _vapid_claims() -> dict[str, str]:
    return {"sub": os.getenv("VAPID_SUBJECT", "mailto:hello@inkbytes.org")}


def push_enabled() -> bool:
    return bool(os.getenv("VAPID_PUBLIC_KEY") and os.getenv("VAPID_PRIVATE_KEY"))


def send_one(sub: dict[str, Any], payload: dict[str, Any]) -> int:
    """Send one Web Push. Returns the HTTP status (0 on library/other error).
    A 404/410 means the subscription is dead and should be pruned by the caller.
    Synchronous (pywebpush) — call via asyncio.to_thread from async code."""
    from pywebpush import WebPushException, webpush  # lazy: keep import cost off boot

    try:
        webpush(
            subscription_info={
                "endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
            },
            data=json.dumps(payload),
            vapid_private_key=os.getenv("VAPID_PRIVATE_KEY", ""),
            vapid_claims=dict(_vapid_claims()),   # webpush mutates the dict (adds exp)
            ttl=3600,
        )
        return 201
    except WebPushException as e:
        status = getattr(e.response, "status_code", 0) or 0
        if status not in (404, 410):
            logger.warning("web-push failed (%s): %s", status, e)
        return status
    except Exception as e:  # noqa: BLE001 — one bad sub must not abort the batch
        logger.warning("web-push error: %s", e)
        return 0
