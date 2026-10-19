"""Sentinel-2 scene catalog (Copernicus Data Space).

Without credentials, or when the service fails, a clearly labelled demo
snapshot is returned so the Satellite page keeps working. The NDVI trend is
always a demonstration series until an NDVI statistics job is connected.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DEMO_NDVI_TREND = [0.62, 0.61, 0.60, 0.58, 0.55, 0.53, 0.51]
_BBOX_HALF_SIZE_DEG = 0.03
_token_cache: dict[str, Any] = {"token": None, "expires": 0.0}


def configured() -> bool:
    return bool(settings.SENTINEL_CLIENT_ID and settings.SENTINEL_CLIENT_SECRET)


def _token() -> str:
    if _token_cache["token"] and _token_cache["expires"] > time.time() + 60:
        return str(_token_cache["token"])
    response = httpx.post(
        settings.SENTINEL_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.SENTINEL_CLIENT_ID,
            "client_secret": settings.SENTINEL_CLIENT_SECRET,
        },
        timeout=12,
    )
    response.raise_for_status()
    data = response.json()
    _token_cache.update(token=data["access_token"], expires=time.time() + int(data.get("expires_in", 600)))
    return str(data["access_token"])


def _demo(reason: str) -> dict[str, Any]:
    return {
        "configured": configured(),
        "live": False,
        "source": "Sentinel-2 demo snapshot",
        "reason": reason,
        "scenes": [{"date": "2026-08-04", "cloudCover": 8.2}, {"date": "2026-07-30", "cloudCover": 16.4}],
        "ndviTrend": DEMO_NDVI_TREND,
        "ndviTrendSource": "demo",
    }


def catalog_search(lat: float, lon: float, days_back: int = 30) -> dict[str, Any]:
    if not configured():
        return _demo("Sentinel credentials are not configured")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    d = _BBOX_HALF_SIZE_DEG
    body = {
        "bbox": [lon - d, lat - d, lon + d, lat + d],
        "datetime": f"{start.isoformat()}/{end.isoformat()}",
        "collections": ["sentinel-2-l2a"],
        "limit": 5,
        "fields": {"include": ["id", "properties.datetime", "properties.eo:cloud_cover"]},
    }
    try:
        response = httpx.post(
            f"{settings.SENTINEL_BASE_URL}/catalog/v1/search",
            json=body,
            headers={"Authorization": f"Bearer {_token()}"},
            timeout=15,
        )
        response.raise_for_status()
        features = response.json().get("features", [])
    except Exception as exc:
        logger.warning("Sentinel catalog search failed: %s", exc)
        return _demo("Sentinel catalog could not be reached for this request")

    return {
        "configured": True,
        "live": True,
        "source": "Copernicus Data Space / Sentinel Hub",
        "scenes": [
            {
                "id": feature.get("id"),
                "date": (feature.get("properties") or {}).get("datetime"),
                "cloudCover": (feature.get("properties") or {}).get("eo:cloud_cover"),
            }
            for feature in features
        ],
        "ndviTrend": DEMO_NDVI_TREND,
        "ndviTrendSource": "demo",
    }
