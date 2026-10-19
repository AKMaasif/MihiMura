"""Offline test for the live province situation used by the maps and dashboard."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import dashboard, situation  # noqa: E402

DAYS = 11  # 7 past days + today + 3 forecast days


def location(rain: float, prob: float, humidity: float, soil: float, tmax: float = 31.0) -> dict:
    hours = [f"2026-10-20T{h:02d}:00" for h in range(24)]
    return {
        "current": {"time": "2026-10-20T10:00", "temperature_2m": 28.0, "relative_humidity_2m": humidity},
        "hourly": {"time": hours, "soil_moisture_3_to_9cm": [soil] * 24},
        "daily": {
            "precipitation_sum": [rain] * DAYS,
            "precipitation_probability_max": [prob] * DAYS,
            "temperature_2m_max": [tmax] * DAYS,
            "et0_fao_evapotranspiration": [4.0] * DAYS,
            "wind_speed_10m_max": [15.0] * DAYS,
        },
    }


SCENARIO = {
    # Monsoon-like rain in the south-west.
    "Western": location(rain=30, prob=95, humidity=92, soil=0.42),
    "Sabaragamuwa": location(rain=28, prob=90, humidity=90, soil=0.40),
    # Drought-like conditions in the dry zone.
    "North Central": location(rain=0, prob=5, humidity=55, soil=0.08, tmax=36),
    "Northern": location(rain=0, prob=10, humidity=60, soil=0.10, tmax=35),
}
DEFAULT = location(rain=4, prob=40, humidity=78, soil=0.26)


def fake_get(url, params=None, timeout=None):
    if "power.larc.nasa.gov" in url:
        normals = {m: 5.0 for m in situation.MONTHS}  # 5 mm/day -> 35 mm per week
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"properties": {"parameter": {"PRECTOTCORR": normals}}})
    district_to_province = {d: p for p, info in situation.PROVINCES.items() for d in info["districts"]}
    districts = [d for info in situation.PROVINCES.values() for d in info["districts"]]
    body = [SCENARIO.get(district_to_province[d], DEFAULT) for d in districts]
    return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)


def failing_get(*_args, **_kwargs):
    raise RuntimeError("network down")


def run() -> None:
    situation._community_clusters_by_province = lambda: {"Eastern": 2}  # type: ignore[assignment]

    situation.httpx.get = fake_get  # type: ignore[assignment]
    live = situation.get_province_situation(force=True)
    p = live["provinces"]
    assert live["live"] is True and len(p) == 9

    wet, dry, mid = p["Western"], p["North Central"], p["Central"]
    assert wet["rainfallRisk"] > mid["rainfallRisk"] > dry["rainfallRisk"], (wet, mid, dry)
    assert dry["waterStress"] > mid["waterStress"] > wet["waterStress"]
    assert wet["pestRisk"] > dry["pestRisk"]
    assert "heavy_rain" in wet["alerts"] and "dry_soil" in dry["alerts"] and "heat" in dry["alerts"]
    assert p["Eastern"]["pestRisk"] > mid["pestRisk"], "community clusters raise pest pressure"
    assert wet["rainfallAvgDiff"] > 0 > dry["rainfallAvgDiff"], "rain is compared with climatology"
    assert dry["nextAction"].startswith("Plan irrigation") and wet["nextAction"].startswith("Delay")

    # Different situations must give different map colours.
    from_score = lambda v: "high" if v >= 70 else "moderate" if v >= 45 else "low"  # noqa: E731
    assert len({from_score(x["rainfallRisk"]) for x in p.values()}) >= 2

    # Cache: a second call within 30 minutes does not hit the network again.
    situation.httpx.get = failing_get  # type: ignore[assignment]
    assert situation.get_province_situation()["live"] is True

    # Dashboard is derived from the same live data.
    dashboard.list_tasks = lambda uid: []  # type: ignore[assignment]
    dashboard.list_projects = lambda uid: []  # type: ignore[assignment]
    dashboard._agent_activity = lambda uid: []  # type: ignore[assignment]
    payload = dashboard.get_dashboard_payload("test")
    assert payload["live"] is True and payload["summary"]["activeThreats"] > 0
    assert payload["priorityActions"][0]["province"] in {"North Central", "Northern", "Western", "Sabaragamuwa"}
    assert "yieldProtected" not in payload["summary"], "no invented KPI"

    # Failure gives a clearly labelled, non-current baseline.
    baseline = situation.get_province_situation(force=True)
    assert baseline["live"] is False and "unavailable" in baseline["source"].lower()

    print("MihiMura live province situation test: PASS")


if __name__ == "__main__":
    run()
