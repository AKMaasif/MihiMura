"""Soil & Water tool: a transparent water-context proxy, not an irrigation prescription."""

from __future__ import annotations

from typing import Any

# Soil-moisture proxy bands (%), used only to label the reading.
_LOW_BELOW = 25.0
_HIGH_ABOVE = 45.0


def calculate_water_budget(context: dict[str, Any], weather: dict[str, Any]) -> dict[str, Any]:
    daily = weather.get("daily") or {}
    rain = [float(x or 0) for x in (daily.get("precipitation_sum") or [])[:3]]
    moisture = context.get("soil_moisture")
    status = "unknown"
    if moisture is not None:
        try:
            value = float(moisture)
            status = "low" if value < _LOW_BELOW else "adequate" if value <= _HIGH_ABOVE else "high"
        except (TypeError, ValueError):
            moisture = None
    return {
        "status": "success",
        "forecast_rain_3d_mm": round(sum(rain), 1),
        "forecast_live": bool(weather.get("live")),
        "soil_moisture_proxy": moisture,
        "moisture_status": status,
        "crop_stage": (context.get("stage") or "unknown").lower(),
        "decision_note": (
            "Verify field soil/water condition before scheduling irrigation; this proxy does not "
            "calculate a certified volume without soil and crop coefficients."
        ),
    }
