"""National dashboard built from the live province situation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.platform import list_projects, list_tasks
from app.services.situation import LITRES_PER_MM_ACRE, get_province_situation

ALERT_LABELS = {
    "heavy_rain": "heavy rain expected",
    "strong_wind": "strong wind expected",
    "heat": "high temperature expected",
    "dry_soil": "dry topsoil",
    "pest_pressure": "high pest/disease pressure",
}


def _severity(province: dict[str, Any]) -> str:
    worst = max(province["rainfallRisk"], province["pestRisk"], 100 - province["healthScore"])
    return "Critical" if worst >= 75 else "High" if worst >= 55 else "Medium"


def _priority_actions(provinces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(provinces, key=lambda p: (p["healthScore"], -p["activeAlerts"]))
    actions = []
    for index, p in enumerate(ranked[:3]):
        alerts = ", ".join(ALERT_LABELS.get(a, a) for a in p["alerts"]) or "no active weather alert"
        evidence = f"Rainfall risk {p['rainfallRisk']}/100 · pest pressure {p['pestRisk']}/100"
        if p.get("soilMoisture") is not None:
            evidence += f" · topsoil moisture {p['soilMoisture']}%"
        actions.append({
            "id": f"a{index + 1}",
            "severity": _severity(p),
            "title": p["nextAction"],
            "province": p["name"],
            "deadline": "Within 24h" if _severity(p) == "Critical" else "Within 48h",
            "description": f"Crop condition index {p['healthScore']}/100 ({alerts}).",
            "reason": f"Lowest crop condition indices nationally ({alerts}).",
            "evidence": evidence,
            "impact": "Reduce avoidable crop loss",
            "buttonText": "Review action",
        })
    return actions


def _changes(provinces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    worsening = sorted((p for p in provinces if p["trend"] < 0), key=lambda p: p["trend"])
    improving = sorted((p for p in provinces if p["trend"] > 0), key=lambda p: -p["trend"])
    for p in worsening[:2]:
        changes.append({
            "id": f"w-{p['id']}", "tone": "danger" if p["trend"] <= -8 else "warning",
            "title": f"{p['name']} conditions worsening ({p['trend']} pts)",
            "detail": f"The coming days look worse than the past week: {p['nextAction'].lower()}.",
            "province": p["name"],
        })
    for p in improving[:1]:
        changes.append({
            "id": f"i-{p['id']}", "tone": "positive",
            "title": f"{p['name']} conditions improving (+{p['trend']} pts)",
            "detail": "Forecast conditions are better than the past week.",
            "province": p["name"],
        })
    for p in provinces:
        if "heavy_rain" in p["alerts"]:
            changes.append({
                "id": f"r-{p['id']}", "tone": "warning", "title": f"Heavy rain expected in {p['name']}",
                "detail": f"About {p['rainfallNext3d']} mm forecast over the next 3 days.", "province": p["name"],
            })
    return changes[:4]


def _ago(iso: str) -> str:
    try:
        seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(str(iso).replace("Z", "+00:00"))).total_seconds()
    except ValueError:
        return ""
    if seconds < 3600:
        return f"{max(1, int(seconds // 60))}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


def _agent_activity(uid: str) -> list[dict[str, Any]]:
    """The user's own most recent agent runs (real activity, not sample text)."""
    try:
        from app.services.platform import _many, _sort

        runs = _sort(_many("agent_runs", owner_uid=uid))[:4]
    except Exception:
        return []
    out = []
    for run in runs:
        output = run.get("output") or {}
        mode = str(output.get("effective_mode") or "assistant").replace("_", " ").title()
        out.append({
            "id": str(run.get("id")),
            "agent": mode,
            "action": str(run.get("request") or "")[:90],
            "time": _ago(str(run.get("created_at") or "")),
            "status": "complete",
        })
    return out


def get_dashboard_payload(uid: str) -> dict[str, Any]:
    situation = get_province_situation()
    provinces = list(situation["provinces"].values())
    acres = sum(p["atRiskArea"] for p in provinces)
    health = round(sum(p["healthScore"] for p in provinces) / len(provinces))
    water = [p["waterStress"] for p in provinces if p.get("waterStress") is not None]
    irrigation_litres = sum(
        (p.get("irrigationDeficitMmPerDay") or 0) * p["atRiskArea"] * LITRES_PER_MM_ACRE for p in provinces
    )
    return {
        "generatedAt": situation["generatedAt"],
        "source": situation["source"],
        "live": situation["live"],
        "reportingPeriod": "Past 7 days and next 3 days" if situation["live"] else "Baseline reference",
        "confidence": situation.get("method") or "Baseline values — live weather unavailable",
        "summary": {
            "cropHealth": health,
            "cropHealthChange": round(sum(p["trend"] for p in provinces) / len(provinces), 1),
            "atRiskArea": acres,
            "newlyAtRiskArea": sum(round(p["atRiskArea"] * max(0, -p["trend"]) / 100) for p in provinces),
            "waterDeficit": round(sum(water) / len(water)) if water else 0,
            "irrigationNeed": round(irrigation_litres),
            "activeThreats": sum(p["activeAlerts"] for p in provinces),
            "criticalThreats": sum(1 for p in provinces if _severity(p) == "Critical"),
            "provincesNeedingAction": sum(1 for p in provinces if p["healthScore"] < 60),
        },
        "provinces": situation["provinces"],
        "priorityActions": _priority_actions(provinces),
        "changes": _changes(provinces),
        "agentActivity": _agent_activity(uid),
        "taskCount": len(list_tasks(uid)),
        "projectCount": len(list_projects(uid)),
    }
