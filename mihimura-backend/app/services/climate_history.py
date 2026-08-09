from __future__ import annotations
from datetime import date, timedelta
import httpx
from app.core.config import settings

def get_nasa_power(lat: float, lon: float, days: int = 30) -> dict:
    end=date.today()-timedelta(days=1); start=end-timedelta(days=max(7,min(days,90)))
    params={"parameters":"PRECTOTCORR,T2M_MAX,T2M_MIN,RH2M,WS2M","community":"AG","longitude":lon,"latitude":lat,"start":start.strftime('%Y%m%d'),"end":end.strftime('%Y%m%d'),"format":"JSON"}
    try:
        r=httpx.get(settings.NASA_POWER_BASE_URL,params=params,timeout=12); r.raise_for_status(); payload=r.json()
        return {"source":"NASA POWER","live":True,"period":{"start":str(start),"end":str(end)},"parameters":payload.get("properties",{}).get("parameter",{})}
    except Exception as exc:
        return {"source":"NASA POWER demo fallback","live":False,"period":{"start":str(start),"end":str(end)},"parameters":{},"error":str(exc)}
