from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def detect_field_operation(question: str) -> str:
    q = (question or "").lower()
    if any(x in q for x in ("fertil", "urea", "npk", "පොහොර", "යූරියා", "உரம்", "யூரியா")):
        return "fertilizer_application"
    if any(x in q for x in ("pesticide", "fungicide", "insecticide", "herbicide", "spray", "කෘමිනාශක", "දිලීරනාශක", "වල්නාශක", "ඉසි", "பூச்சிக்கொல்லி", "பூஞ்சைக்கொல்லி", "களைக்கொல்லி", "தெளி")):
        return "crop_protection_application"
    if any(x in q for x in ("irrig", "water", "වාරි", "ජලය", "நீர்ப்பாசனம்", "தண்ணீர்")):
        return "irrigation"
    if any(x in q for x in ("harvest", "අස්වැන්න", "அறுவடை")):
        return "harvest"
    if any(x in q for x in ("plant", "sow", "seed", "transplant", "වගා", "බීජ", "சாகுபடி", "விதை", "நடவு")):
        return "planting_establishment"
    return "general_weather"


def build_weather_decision_context(weather: dict[str, Any], question: str) -> dict[str, Any]:
    operation = detect_field_operation(question)
    live = bool(weather.get("live")) and str(weather.get("status") or "").lower() not in {"unavailable", "error", "fallback_demo"}
    current = weather.get("current") or {}
    daily = weather.get("daily") or {}
    times = daily.get("time") or []
    target_idx = 1 if any(x in (question or "").lower() for x in ("tomorrow", "හෙට", "நாளை")) and len(times) > 1 else 0

    def pick(name: str) -> Any:
        vals = daily.get(name) or []
        return vals[target_idx] if target_idx < len(vals) else None

    rain_prob = _num(pick("precipitation_probability_max"))
    rain_mm = _num(pick("precipitation_sum"))
    tmax = _num(pick("temperature_2m_max"))
    tmin = _num(pick("temperature_2m_min"))
    wind = _num(current.get("wind_speed_10m"))
    current_rain = _num(current.get("precipitation"))

    flags: list[dict[str, Any]] = []
    def flag(code: str, severity: str, reason: str) -> None:
        flags.append({"code": code, "severity": severity, "reason": reason})

    if not live:
        flag("live_weather_unavailable", "high", "The weather payload is not verified live data and must not be used for a current field decision.")
    else:
        if rain_prob is not None and rain_prob >= 70:
            flag("high_rain_probability", "high", f"Forecast rain probability is {rain_prob:.0f}% for the target day.")
        elif rain_prob is not None and rain_prob >= 45:
            flag("moderate_rain_probability", "watch", f"Forecast rain probability is {rain_prob:.0f}% for the target day.")
        if rain_mm is not None and rain_mm >= 20:
            flag("heavy_rain_forecast", "high", f"Forecast precipitation is about {rain_mm:.1f} mm for the target day.")
        elif rain_mm is not None and rain_mm >= 10:
            flag("meaningful_rain_forecast", "watch", f"Forecast precipitation is about {rain_mm:.1f} mm for the target day.")
        if current_rain is not None and current_rain > 0:
            flag("raining_now", "watch", f"Current precipitation is {current_rain:.1f} mm.")
        if wind is not None and wind >= 25:
            flag("strong_wind_current", "high", f"Current wind speed is about {wind:.1f} km/h.")
        elif wind is not None and wind >= 18:
            flag("elevated_wind_current", "watch", f"Current wind speed is about {wind:.1f} km/h.")
        if tmax is not None and tmax >= 35:
            flag("high_temperature", "watch", f"Forecast maximum temperature is about {tmax:.1f} °C.")

        codes = {x["code"] for x in flags}
        if operation == "fertilizer_application" and codes & {"high_rain_probability", "heavy_rain_forecast", "meaningful_rain_forecast"}:
            flag("fertilizer_weather_loss_risk", "high", "Meaningful rainfall around fertilizer application can increase runoff/leaching/loss risk; timing should be checked against crop-specific guidance.")
        if operation == "crop_protection_application" and codes & {"high_rain_probability", "heavy_rain_forecast", "raining_now", "strong_wind_current", "elevated_wind_current"}:
            flag("spray_conditions_need_label_check", "high", "Rain/wind conditions may make spraying unsuitable. Product-label weather limits must be verified before application.")
        if operation == "harvest" and codes & {"high_rain_probability", "heavy_rain_forecast", "meaningful_rain_forecast"}:
            flag("harvest_weather_quality_risk", "watch", "Rain near harvest can affect field access, grain/crop moisture and post-harvest quality.")

    severity_rank = {"none": 0, "watch": 1, "high": 2}
    overall = "none"
    for item in flags:
        if severity_rank.get(item["severity"], 0) > severity_rank.get(overall, 0):
            overall = item["severity"]

    return {
        "status": "success" if live else "unavailable",
        "decision_usable": live,
        "operation": operation,
        "target_date": times[target_idx] if target_idx < len(times) else None,
        "current": {
            "temperature_c": _num(current.get("temperature_2m")),
            "humidity_pct": _num(current.get("relative_humidity_2m")),
            "precipitation_mm": current_rain,
            "wind_kmh": wind,
        },
        "target_day": {
            "rain_probability_pct": rain_prob,
            "rain_mm": rain_mm,
            "temperature_max_c": tmax,
            "temperature_min_c": tmin,
        },
        "risk_level": overall,
        "risk_flags": flags,
        "source": {
            "name": weather.get("source") or "weather service",
            "live": live,
            "retrieved_at": weather.get("retrieved_at"),
            "status": weather.get("status") or ("success" if live else "unavailable"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Weather heuristics flag operational risk; they do not replace crop/product-specific agronomic guidance or product-label restrictions.",
            "Re-check the forecast close to the actual field operation because conditions can change.",
        ],
    }
