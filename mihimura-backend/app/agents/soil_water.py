from __future__ import annotations
from typing import Any


def calculate_water_budget(context:dict[str,Any],weather:dict[str,Any]) -> dict[str,Any]:
    daily=weather.get("daily") or {}
    rain=[float(x or 0) for x in (daily.get("precipitation_sum") or [])[:3]]
    forecast3=round(sum(rain),1)
    moisture=context.get("soil_moisture")
    stage=(context.get("stage") or "unknown").lower()
    # Transparent decision-support proxy only; not an irrigation prescription.
    status="unknown"
    if moisture is not None:
        m=float(moisture);status="low" if m<25 else "adequate" if m<=45 else "high"
    return {"status":"success","forecast_rain_3d_mm":forecast3,"soil_moisture_proxy":moisture,"moisture_status":status,"crop_stage":stage,"decision_note":"Verify field soil/water condition before scheduling irrigation; this proxy does not calculate a certified volume without soil and crop coefficients."}
