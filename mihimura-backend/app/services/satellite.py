from __future__ import annotations
import time
from typing import Any
import httpx
from app.core.config import settings

_token_cache: dict[str, Any] = {"token":None,"expires":0}

def configured() -> bool:
    return bool(settings.SENTINEL_CLIENT_ID and settings.SENTINEL_CLIENT_SECRET)

def _token() -> str | None:
    if not configured(): return None
    if _token_cache["token"] and _token_cache["expires"] > time.time()+60: return _token_cache["token"]
    r=httpx.post(settings.SENTINEL_TOKEN_URL,data={"grant_type":"client_credentials","client_id":settings.SENTINEL_CLIENT_ID,"client_secret":settings.SENTINEL_CLIENT_SECRET},timeout=12)
    r.raise_for_status(); data=r.json(); _token_cache.update(token=data["access_token"],expires=time.time()+int(data.get("expires_in",600))); return data["access_token"]

def catalog_search(lat: float, lon: float, days_back: int = 30) -> dict:
    if not configured():
        return {"configured":False,"source":"Sentinel-2 demo snapshot","scenes":[{"date":"2026-08-04","cloudCover":8.2},{"date":"2026-07-30","cloudCover":16.4}],"ndviTrend":[0.62,0.61,0.60,0.58,0.55,0.53,0.51]}
    from datetime import datetime, timedelta, timezone
    end=datetime.now(timezone.utc); start=end-timedelta(days=days_back); d=0.03
    body={"bbox":[lon-d,lat-d,lon+d,lat+d],"datetime":f"{start.isoformat()}/{end.isoformat()}","collections":["sentinel-2-l2a"],"limit":5,"fields":{"include":["id","properties.datetime","properties.eo:cloud_cover"]}}
    r=httpx.post(f"{settings.SENTINEL_BASE_URL}/catalog/v1/search",json=body,headers={"Authorization":f"Bearer {_token()}"},timeout=15); r.raise_for_status()
    features=r.json().get("features",[])
    return {"configured":True,"source":"Copernicus Data Space / Sentinel Hub","scenes":[{"id":x.get("id"),"date":x.get("properties",{}).get("datetime"),"cloudCover":x.get("properties",{}).get("eo:cloud_cover")} for x in features],"ndviTrend":[0.62,0.61,0.60,0.58,0.55,0.53,0.51]}
