"""RevenueCat entitlement check for the macOS app.

The server asks RevenueCat directly (REST v1, secret key) whether an app user
id holds the `meetspot_pro` entitlement. The client only sends its id; it never gets to
claim it paid.
"""

import os
import time
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.logger import logger

RC_API = "https://api.revenuecat.com/v1/subscribers/"
ENTITLEMENT_ID = "meetspot_pro"
CACHE_TTL = 60
CACHE_MAX = 500

# Only positive answers are cached: a cached "no" would block the retry that
# runs right after a purchase.
_cache: dict[str, float] = {}


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _is_active(entitlement: dict) -> bool:
    expires = _parse(entitlement.get("expires_date"))
    if expires is None:  # lifetime / non-expiring purchase
        return True
    grace = _parse(entitlement.get("grace_period_expires_date"))
    return max(expires, grace or expires) > datetime.now(timezone.utc)


async def has_pro(app_user_id: str) -> bool:
    secret = os.getenv("REVENUECAT_SECRET_KEY", "")
    if not secret or not app_user_id:
        return False

    hit = _cache.get(app_user_id)
    if hit and time.monotonic() - hit < CACHE_TTL:
        return True

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                RC_API + quote(app_user_id, safe=""),
                headers={"Authorization": f"Bearer {secret}"},
            )
        resp.raise_for_status()
        entitlement = resp.json()["subscriber"]["entitlements"].get(ENTITLEMENT_ID)
    except Exception as e:
        logger.warning(f"revenuecat_lookup_failed: {type(e).__name__}: {e}")
        return False

    active = bool(entitlement) and _is_active(entitlement)
    logger.info(f"revenuecat_entitlement user={app_user_id} pro={active}")
    if active:
        if len(_cache) >= CACHE_MAX:
            _cache.clear()  # ponytail: crude bound, fine for a demo-scale user count
        _cache[app_user_id] = time.monotonic()
    return active
