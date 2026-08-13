from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import httpx

from app.core.config import settings


DEMO = {
    "source": "demo-fallback",
    "status": "fallback_demo",
    "live": False,
    "decision_usable": False,
    "current": {"temperature_2m": 31.2, "relative_humidity_2m": 72, "precipitation": 0.0, "wind_speed_10m": 11.5},
    "daily": {
        "time": [str(date.today() + timedelta(days=i)) for i in range(14)],
        "precipitation_sum": [8, 42, 28, 9, 4, 16, 7, 5, 3, 12, 19, 6, 4, 9],
        "precipitation_probability_max": [45, 82, 67, 39, 27, 51, 35, 31, 26, 48, 59, 33, 29, 41],
        "temperature_2m_max": [32, 30, 31, 33, 34, 32, 31, 33, 34, 32, 31, 33, 34, 32],
        "temperature_2m_min": [25, 24, 24, 25, 25, 25, 24, 25, 25, 24, 24, 25, 25, 24],
    },
}


def get_weather(lat: float, lon: float, days: int = 14) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min",
        "forecast_days": max(1, min(days, 16)),
        "timezone": "Asia/Colombo",
    }
    retrieved_at = datetime.now(timezone.utc).isoformat()
    try:
        r = httpx.get(settings.OPEN_METEO_BASE_URL, params=params, timeout=8)
        r.raise_for_status()
        return {
            "source": "Open-Meteo",
            "status": "success",
            "live": True,
            "decision_usable": True,
            "retrieved_at": retrieved_at,
            "coordinates": {"lat": lat, "lon": lon},
            **r.json(),
        }
    except Exception as exc:
        # Keep demo values available for UI/demo continuity, but mark them explicitly
        # non-decision-usable so the agent cannot present them as current observations.
        return {
            **DEMO,
            "retrieved_at": retrieved_at,
            "coordinates": {"lat": lat, "lon": lon},
            "error": str(exc),
            "limitations": [
                "Open-Meteo could not be reached for this request.",
                "Demo fallback values must never be presented as current field weather or used for consequential decisions.",
            ],
        }
