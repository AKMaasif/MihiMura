from __future__ import annotations
from typing import Any
from app.services.weather import get_weather

class ClimateAgent:
    """Deterministic micro-climate feature agent used independently or by tests/tools."""
    def evaluate_weather_risk(self, lat:float, lon:float, upcoming_task:str="", days:int=14) -> dict[str,Any]:
        weather=get_weather(lat,lon,days)
        daily=weather.get("daily") or {}
        probs=[float(v or 0) for v in (daily.get("precipitation_probability_max") or [])]
        peak=max(probs[:3] or [0])
        task=upcoming_task.lower()
        action="routine monitoring"
        level="low"
        if any(k in task for k in ["fertilizer","fertiliser","urea","spray"]) and peak>=60:
            level="action";action="review and potentially delay the exposed operation; verify the next safer window"
        elif peak>=60:
            level="watch";action="prepare drainage / weather protection appropriate to the field"
        return {"source":weather.get("source"),"retrieved_at":weather.get("retrieved_at"),"peak_rain_probability_3d":peak,"risk_level":level,"recommended_operational_check":action,"weather":weather}

climate_agent=ClimateAgent()
