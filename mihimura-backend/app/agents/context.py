from __future__ import annotations
from typing import Any
from app.db import row


def load_farmer_context(uid:str, supplied:dict[str,Any]) -> dict[str,Any]:
    """Resolve trusted project/farm context. User-supplied IDs never grant access."""
    project_id=str(supplied.get("project_id") or "").strip()
    trusted:dict[str,Any]={
        "language": supplied.get("language") or "English",
        "location": supplied.get("location") or "Sri Lanka",
        "lat": supplied.get("lat"),
        "lon": supplied.get("lon"),
    }
    if not project_id:
        trusted.update({"crop":supplied.get("crop") or "","stage":supplied.get("stage") or "","context_scope":"general"})
        return trusted
    p=row("""SELECT p.id project_id,p.crop,p.variety,p.stage,p.season,p.irrigation_mode,p.health_score,p.risk_score,
                    f.id farm_id,f.name farm_name,f.district,f.province,f.area,f.water_source,f.soil_type,f.lat,f.lon
             FROM projects p JOIN farms f ON f.id=p.farm_id
             WHERE p.id=? AND p.owner_uid=?""",(project_id,uid))
    if not p:
        trusted.update({"crop":"","stage":"","context_scope":"unverified-project"})
        return trusted
    return {**trusted,**p,"location":p.get("district") or trusted["location"],"lat":p.get("lat") or trusted.get("lat"),"lon":p.get("lon") or trusted.get("lon"),"context_scope":"owned-project"}
