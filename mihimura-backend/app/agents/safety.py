from __future__ import annotations
from typing import Any

HAZARD_TERMS={"pesticide","insecticide","fungicide","herbicide","chemical","dose","dosage","rate","spray"}
CONSEQUENTIAL_TERMS=HAZARD_TERMS|{"fertilizer","fertiliser","urea","irrigate","order","buy","purchase"}

def precheck(question:str,context:dict[str,Any]) -> dict[str,Any]:
    q=question.lower(); hazard=any(x in q for x in HAZARD_TERMS); consequential=any(x in q for x in CONSEQUENTIAL_TERMS)
    return {"hazardous_or_rate_sensitive":hazard,"consequential":consequential,"requires_confirmation":consequential,"expert_threshold":hazard and any(x in q for x in {"dose","dosage","rate","poison","restricted"}),"rule":"No unsupported dose, guaranteed diagnosis, silent purchase or irreversible field action."}

def enforce(result:dict[str,Any],check:dict[str,Any]) -> dict[str,Any]:
    result.setdefault("alternatives",[]);result.setdefault("do_not_do",[])
    if check["hazardous_or_rate_sensitive"]:
        warning="Do not use a pesticide/fertilizer dose or product choice unless it is verified against the current approved crop label/protocol."
        if warning not in result["do_not_do"]: result["do_not_do"].append(warning)
    if check["requires_confirmation"]: result["confirmation_required"]=True
    if check["expert_threshold"]:
        result["expert_escalation_recommended"]=True
        result["risk_level"]="action" if result.get("risk_level") not in {"emergency"} else result["risk_level"]
    return result
