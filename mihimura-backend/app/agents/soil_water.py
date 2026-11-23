"""Soil & Water tool: a transparent water-context proxy, not an irrigation prescription."""

from __future__ import annotations

from typing import Any

# Soil-moisture proxy bands (%), used only to label the reading.
_LOW_BELOW = 25.0
_HIGH_ABOVE = 45.0


def _forecast_is_live(weather: dict[str, Any]) -> bool:
    return bool(weather.get("live")) and str(weather.get("status") or "").lower() not in {
        "unavailable",
        "error",
        "fallback_demo",
    }


def _moisture(context: dict[str, Any]) -> tuple[Any, str]:
    moisture = context.get("soil_moisture")
    status = "unknown"
    if moisture is None:
        return None, status
    try:
        value = float(moisture)
    except (TypeError, ValueError):
        return None, status
    if value < _LOW_BELOW:
        status = "low"
    elif value <= _HIGH_ABOVE:
        status = "adequate"
    else:
        status = "high"
    return value, status


def calculate_water_budget(context: dict[str, Any], weather: dict[str, Any]) -> dict[str, Any]:
    moisture, moisture_status = _moisture(context)
    stage = (context.get("stage") or "unknown").lower()
    if not _forecast_is_live(weather):
        return {
            "status": "unavailable",
            "forecast_rain_3d_mm": None,
            "forecast_live": False,
            "soil_moisture_proxy": moisture,
            "moisture_status": moisture_status,
            "crop_stage": stage,
            "reason": "Live rainfall was not available, so demo or missing rainfall was not treated as field evidence.",
            "decision_note": "Do not schedule irrigation from this result. Refresh the live forecast or check the field.",
        }
    daily = weather.get("daily") or {}
    rain = [float(x or 0) for x in (daily.get("precipitation_sum") or [])[:3]]
    return {
        "status": "success",
        "forecast_rain_3d_mm": round(sum(rain), 1),
        "forecast_live": True,
        "soil_moisture_proxy": moisture,
        "moisture_status": moisture_status,
        "crop_stage": stage,
        "decision_note": (
            "Verify field soil/water condition before scheduling irrigation; this proxy does not "
            "calculate a certified volume without soil and crop coefficients."
        ),
    }
