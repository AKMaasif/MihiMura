from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import httpx

from app.core.config import settings


def get_nasa_power(lat: float, lon: float, days: int = 30) -> dict:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=max(7, min(days, 90)))
    params = {
        "parameters": "PRECTOTCORR,T2M_MAX,T2M_MIN,RH2M,WS2M",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    retrieved_at = datetime.now(timezone.utc).isoformat()
    try:
        r = httpx.get(settings.NASA_POWER_BASE_URL, params=params, timeout=12)
        r.raise_for_status()
        payload = r.json()
        return {
            "source": "NASA POWER",
            "status": "success",
            "live": True,
            "retrieved_at": retrieved_at,
            "period": {"start": str(start), "end": str(end)},
            "parameters": payload.get("properties", {}).get("parameter", {}),
        }
    except Exception as exc:
        return {
            "source": "NASA POWER",
            "status": "unavailable",
            "live": False,
            "retrieved_at": retrieved_at,
            "period": {"start": str(start), "end": str(end)},
            "parameters": {},
            "error": str(exc),
        }
