from __future__ import annotations
from app.services.platform import PRODUCTS


def preview_verified_options(crop:str,category:str="") -> list[dict]:
    """Returns neutral demo catalog metadata; never places an order."""
    out=[]
    for p in PRODUCTS:
        if crop and p.get("compatibility") not in {crop,"All crops","Field operations"}: continue
        if category and category.lower() not in p.get("category","").lower(): continue
        out.append({k:p[k] for k in ("id","name","category","supplier","verified","stock","distance","compatibility","safety") if k in p})
    return out[:4]
