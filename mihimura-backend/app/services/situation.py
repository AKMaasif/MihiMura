"""Live province situation for the Sri Lanka maps and the national dashboard.

How it works
------------
1. One Open-Meteo request samples all 25 district centres (past 7 days +
   next 3 days of daily weather, current conditions and topsoil moisture).
2. Each district gets transparent 0-100 scores (formulas below).
3. Districts are averaged into the 9 provinces; alerts are combined.
4. Rain is compared with the NASA POWER 1991-2020 monthly climatology.
5. Anonymized community pest/disease clusters raise pest pressure.

Results are cached for ``CACHE_SECONDS``. When live data cannot be fetched,
a clearly labelled baseline is returned (``live: false``) so maps still render
but never pretend to be current.

These are weather-derived decision-support indices, not satellite crop
measurements or official statistics.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.services.conversations import DISTRICT_COORDS

logger = logging.getLogger(__name__)

CACHE_SECONDS = 30 * 60
CLIMATOLOGY_CACHE_SECONDS = 30 * 24 * 3600
NASA_CLIMATOLOGY_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
LITRES_PER_MM_ACRE = 4047  # 1 mm of water over one acre
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

# Province reference data. Districts, ids and main crops are fixed facts;
# cropCoverage and monitored acres are reference planning values, not live data.
PROVINCES: dict[str, dict[str, Any]] = {
    "Western": {"id": "WP", "districts": ["Colombo", "Gampaha", "Kalutara"], "topCrop": "Coconut", "cropCoverage": 45, "monitoredAcres": 60},
    "Central": {"id": "CP", "districts": ["Kandy", "Matale", "Nuwara Eliya"], "topCrop": "Tea", "cropCoverage": 60, "monitoredAcres": 90},
    "Southern": {"id": "SP", "districts": ["Galle", "Matara", "Hambantota"], "topCrop": "Cinnamon", "cropCoverage": 50, "monitoredAcres": 140},
    "Northern": {"id": "NP", "districts": ["Jaffna", "Kilinochchi", "Mannar", "Vavuniya", "Mullaitivu"], "topCrop": "Onion", "cropCoverage": 55, "monitoredAcres": 110},
    "Eastern": {"id": "EP", "districts": ["Ampara", "Batticaloa", "Trincomalee"], "topCrop": "Paddy", "cropCoverage": 71, "monitoredAcres": 240},
    "North Western": {"id": "NW", "districts": ["Kurunegala", "Puttalam"], "topCrop": "Coconut", "cropCoverage": 65, "monitoredAcres": 180},
    "North Central": {"id": "NC", "districts": ["Anuradhapura", "Polonnaruwa"], "topCrop": "Paddy", "cropCoverage": 80, "monitoredAcres": 210},
    "Uva": {"id": "UP", "districts": ["Badulla", "Monaragala"], "topCrop": "Tea", "cropCoverage": 55, "monitoredAcres": 150},
    "Sabaragamuwa": {"id": "SG", "districts": ["Ratnapura", "Kegalle"], "topCrop": "Rubber", "cropCoverage": 65, "monitoredAcres": 100},
}

# Used only when live data is unavailable (shown as "baseline", never as current).
BASELINE: dict[str, dict[str, float]] = {
    "Western": {"healthScore": 78, "rainfallRisk": 35, "pestRisk": 28, "soilMoisture": 40, "rainfall7d": 60},
    "Central": {"healthScore": 74, "rainfallRisk": 45, "pestRisk": 32, "soilMoisture": 38, "rainfall7d": 55},
    "Southern": {"healthScore": 70, "rainfallRisk": 40, "pestRisk": 35, "soilMoisture": 36, "rainfall7d": 50},
    "Northern": {"healthScore": 66, "rainfallRisk": 25, "pestRisk": 38, "soilMoisture": 25, "rainfall7d": 20},
    "Eastern": {"healthScore": 64, "rainfallRisk": 42, "pestRisk": 45, "soilMoisture": 30, "rainfall7d": 40},
    "North Western": {"healthScore": 68, "rainfallRisk": 30, "pestRisk": 40, "soilMoisture": 30, "rainfall7d": 35},
    "North Central": {"healthScore": 65, "rainfallRisk": 28, "pestRisk": 42, "soilMoisture": 26, "rainfall7d": 25},
    "Uva": {"healthScore": 67, "rainfallRisk": 38, "pestRisk": 40, "soilMoisture": 32, "rainfall7d": 40},
    "Sabaragamuwa": {"healthScore": 75, "rainfallRisk": 48, "pestRisk": 30, "soilMoisture": 42, "rainfall7d": 70},
}

_cache: dict[str, Any] = {"at": 0.0, "data": None}
_climatology: dict[str, Any] = {"at": 0.0, "data": {}}
_lock = threading.Lock()


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _num(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _values(series: list[Any] | None) -> list[float]:
    return [v for v in (_num(x) for x in (series or [])) if v is not None]


# ---------------------------------------------------------------------------
# Scoring (per district). All outputs are 0-100 unless stated otherwise.
# ---------------------------------------------------------------------------


def rainfall_risk(next3_prob: float, next3_rain: float, past7_rain: float) -> float:
    """Excess-rain / flood risk: forecast chance, forecast amount, and wet antecedent soil."""
    return _clamp(0.45 * next3_prob + 0.35 * min(100.0, next3_rain * 1.5) + 0.20 * min(100.0, past7_rain * 0.8))


def water_stress(soil_moisture: float | None, past7_rain: float, past7_et0: float) -> float:
    """Dryness: low topsoil moisture (m³/m³) and rain below evaporative demand."""
    deficit = _clamp((past7_et0 - past7_rain) / max(past7_et0, 1.0) * 100.0)
    if soil_moisture is None:
        return deficit
    soil_term = _clamp((0.30 - soil_moisture) / 0.20 * 100.0)  # 0.30+ wet -> 0, 0.10 dry -> 100
    return _clamp(0.7 * soil_term + 0.3 * deficit)


def heat_stress(tmax: float) -> float:
    return _clamp((tmax - 32.0) / 6.0 * 100.0)  # 32 °C -> 0, 38 °C -> 100


def pest_pressure(humidity: float, temperature: float, past7_rain: float, community_clusters: int = 0) -> float:
    """Warm, humid, wet weather favours most fungal diseases and many insect pests."""
    humidity_term = _clamp((humidity - 60.0) / 35.0 * 100.0)
    if 24.0 <= temperature <= 32.0:
        temp_suitability = 100.0
    else:
        temp_suitability = _clamp(100.0 - 12.0 * min(abs(temperature - 24.0), abs(temperature - 32.0)))
    weather = 0.65 * humidity_term * temp_suitability / 100.0 + 0.35 * min(100.0, past7_rain * 1.2)
    return _clamp(weather + min(25.0, 10.0 * community_clusters))


def crop_condition(water: float, rain: float, pest: float, heat: float) -> float:
    return _clamp(100.0 - (0.35 * water + 0.25 * rain + 0.25 * pest + 0.15 * heat))


def _district_metrics(result: dict[str, Any], clusters: int) -> dict[str, Any]:
    daily = result.get("daily") or {}
    current = result.get("current") or {}
    hourly = result.get("hourly") or {}
    rain = _values(daily.get("precipitation_sum"))
    prob = _values(daily.get("precipitation_probability_max"))
    tmax = _values(daily.get("temperature_2m_max"))
    et0 = _values(daily.get("et0_fao_evapotranspiration"))
    wind = _values(daily.get("wind_speed_10m_max"))
    if len(rain) < 8:
        raise ValueError("incomplete daily series")

    past7_rain, next3_rain = sum(rain[:7]), sum(rain[7:10])
    past7_et0 = sum(et0[:7]) if len(et0) >= 7 else 0.0
    next3_prob = max(prob[7:10]) if len(prob) >= 8 else 0.0
    past_tmax = max(tmax[:7]) if len(tmax) >= 7 else 30.0
    next_tmax = max(tmax[7:10]) if len(tmax) >= 8 else past_tmax
    next_wind = max(wind[7:10]) if len(wind) >= 8 else 0.0

    # Topsoil moisture at the current hour (latest non-empty value up to now).
    soil = None
    times = hourly.get("time") or []
    series = hourly.get("soil_moisture_3_to_9cm") or []
    now = str(current.get("time") or "")
    for t, v in zip(times, series):
        if now and str(t) > now:
            break
        if _num(v) is not None:
            soil = _num(v)

    humidity = _num(current.get("relative_humidity_2m")) or 75.0
    temperature = _num(current.get("temperature_2m")) or 28.0

    water = water_stress(soil, past7_rain, past7_et0)
    rain_next = rainfall_risk(next3_prob, next3_rain, past7_rain)
    rain_past = rainfall_risk(0.0, 0.0, past7_rain)
    pest = pest_pressure(humidity, temperature, past7_rain, clusters)
    health_next = crop_condition(water, rain_next, pest, heat_stress(next_tmax))
    health_past = crop_condition(water, rain_past, pest, heat_stress(past_tmax))

    alerts = []
    if next3_rain >= 50 or next3_prob >= 80:
        alerts.append("heavy_rain")
    if next_wind >= 40:
        alerts.append("strong_wind")
    if next_tmax >= 35:
        alerts.append("heat")
    if soil is not None and soil < 0.15:
        alerts.append("dry_soil")
    if pest >= 65:
        alerts.append("pest_pressure")

    return {
        "health": health_next,
        "trend": health_next - health_past,
        "rainfall_risk": rain_next,
        "pest": pest,
        "water": water,
        "heat": heat_stress(next_tmax),
        "soil_pct": None if soil is None else soil * 100.0,
        "past7_rain": past7_rain,
        "past7_et0": past7_et0,
        "next3_rain": next3_rain,
        "next3_prob": next3_prob,
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------


def _fetch_weather(districts: list[str]) -> list[dict[str, Any]]:
    coords = [DISTRICT_COORDS[d] for d in districts]
    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat, _ in coords),
        "longitude": ",".join(f"{lon:.4f}" for _, lon in coords),
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "hourly": "soil_moisture_3_to_9cm",
        "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,et0_fao_evapotranspiration,wind_speed_10m_max",
        "past_days": 7,
        "forecast_days": 4,
        "timezone": "Asia/Colombo",
    }
    response = httpx.get(settings.OPEN_METEO_BASE_URL, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    results = data if isinstance(data, list) else [data]
    if len(results) != len(districts):
        raise ValueError(f"expected {len(districts)} locations, got {len(results)}")
    return results


def _monthly_normal_mm_per_day(province: str, month: str) -> float | None:
    """NASA POWER 1991-2020 climatology at the province's first district (cached for 30 days)."""
    cache = _climatology["data"]
    if time.time() - _climatology["at"] > CLIMATOLOGY_CACHE_SECONDS:
        cache.clear()
        _climatology["at"] = time.time()
    if province not in cache:
        lat, lon = DISTRICT_COORDS[PROVINCES[province]["districts"][0]]
        try:
            response = httpx.get(
                NASA_CLIMATOLOGY_URL,
                params={"parameters": "PRECTOTCORR", "community": "AG", "latitude": lat, "longitude": lon, "format": "JSON"},
                timeout=15,
            )
            response.raise_for_status()
            cache[province] = response.json()["properties"]["parameter"]["PRECTOTCORR"]
        except Exception as exc:
            logger.info("NASA climatology unavailable for %s: %s", province, exc)
            cache[province] = None
    monthly = cache.get(province)
    return _num(monthly.get(month)) if isinstance(monthly, dict) else None


def _community_clusters_by_province() -> dict[str, int]:
    try:
        from app.services.platform import list_community_reports

        district_to_province = {d: p for p, info in PROVINCES.items() for d in info["districts"]}
        counts: dict[str, int] = {}
        for cluster in list_community_reports():
            province = district_to_province.get(str(cluster.get("district") or ""))
            if province:
                counts[province] = counts.get(province, 0) + 1
        return counts
    except Exception:  # database not configured: weather-only pest pressure
        return {}


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

NEXT_ACTIONS = {
    "rain": "Delay exposed field work; clear drainage",
    "water": "Plan irrigation; check soil moisture",
    "pest": "Scout fields for pests and disease",
    "heat": "Irrigate early or late; limit heat exposure",
    "none": "Routine monitoring",
}


def _next_action(rain: float, water: float, pest: float, heat: float) -> str:
    risks = {"rain": rain, "water": water, "pest": pest, "heat": heat}
    key, value = max(risks.items(), key=lambda kv: kv[1])
    return NEXT_ACTIONS[key] if value >= 55 else NEXT_ACTIONS["none"]


def _province_entry(name: str, metrics: list[dict[str, Any]], normal_per_day: float | None) -> dict[str, Any]:
    info = PROVINCES[name]

    def avg(key: str) -> float:
        vals = [m[key] for m in metrics if m.get(key) is not None]
        return sum(vals) / len(vals) if vals else 0.0

    health, rain, pest, water, heat = avg("health"), avg("rainfall_risk"), avg("pest"), avg("water"), avg("heat")
    past7 = avg("past7_rain")
    soil_values = [m["soil_pct"] for m in metrics if m.get("soil_pct") is not None]
    alerts = sorted({a for m in metrics for a in m["alerts"]})
    normal7 = normal_per_day * 7 if normal_per_day else None
    return {
        "id": info["id"],
        "name": name,
        "healthScore": round(health),
        "trend": round(_clamp(avg("trend"), -20, 20)),
        "rainfallRisk": round(rain),
        "pestRisk": round(pest),
        "waterStress": round(water),
        "heatStress": round(heat),
        "activeAlerts": len(alerts),
        "alerts": alerts,
        "rainfall7d": round(past7),
        "rainfallAvgDiff": round((past7 - normal7) / normal7 * 100) if normal7 else None,
        "rainfallNext3d": round(avg("next3_rain")),
        "rainProbabilityNext3d": round(avg("next3_prob")),
        "cropCoverage": info["cropCoverage"],
        "atRiskArea": round(info["monitoredAcres"] * (100 - health) / 100),
        "soilMoisture": round(sum(soil_values) / len(soil_values)) if soil_values else None,
        "topCrop": info["topCrop"],
        "nextAction": _next_action(rain, water, pest, heat),
        "irrigationDeficitMmPerDay": round(max(0.0, avg("past7_et0") - past7) / 7, 1),
        "districtsSampled": len(metrics),
    }


def _baseline(reason: str) -> dict[str, Any]:
    provinces = {}
    for name, info in PROVINCES.items():
        base = BASELINE[name]
        provinces[name] = {
            "id": info["id"], "name": name, "healthScore": base["healthScore"], "trend": 0,
            "rainfallRisk": base["rainfallRisk"], "pestRisk": base["pestRisk"], "waterStress": None, "heatStress": None,
            "activeAlerts": 0, "alerts": [], "rainfall7d": base["rainfall7d"], "rainfallAvgDiff": None, "rainfallNext3d": None, "rainProbabilityNext3d": None,
            "cropCoverage": info["cropCoverage"], "atRiskArea": round(info["monitoredAcres"] * (100 - base["healthScore"]) / 100),
            "soilMoisture": base["soilMoisture"], "topCrop": info["topCrop"], "nextAction": NEXT_ACTIONS["none"],
            "irrigationDeficitMmPerDay": None, "districtsSampled": 0,
        }
    return {
        "live": False,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Baseline reference values (live weather unavailable)",
        "reason": reason,
        "provinces": provinces,
    }


def _compute() -> dict[str, Any]:
    districts = [d for info in PROVINCES.values() for d in info["districts"]]
    try:
        results = _fetch_weather(districts)
    except Exception as exc:
        logger.warning("live province situation unavailable: %s", exc)
        return _baseline(str(exc))

    clusters = _community_clusters_by_province()
    by_district = dict(zip(districts, results))
    month = MONTHS[datetime.now(timezone.utc).month - 1]
    provinces: dict[str, Any] = {}
    for name, info in PROVINCES.items():
        metrics = []
        for district in info["districts"]:
            try:
                metrics.append(_district_metrics(by_district[district], clusters.get(name, 0)))
            except Exception as exc:
                logger.info("district %s skipped: %s", district, exc)
        if not metrics:
            return _baseline(f"no usable weather for {name}")
        provinces[name] = _province_entry(name, metrics, _monthly_normal_mm_per_day(name, month))
    return {
        "live": True,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Open-Meteo forecast and soil moisture (25 districts) · NASA POWER climatology · community reports",
        "method": "Weather-derived risk indices (0-100); not satellite or official crop statistics.",
        "provinces": provinces,
    }


def get_province_situation(force: bool = False) -> dict[str, Any]:
    with _lock:
        fresh = _cache["data"] is not None and time.time() - _cache["at"] < CACHE_SECONDS
        if fresh and not force:
            return _cache["data"]
        data = _compute()
        # Keep a failed refresh short-lived so the next request retries soon.
        _cache.update(at=time.time() if data["live"] else time.time() - CACHE_SECONDS + 120, data=data)
        return data
