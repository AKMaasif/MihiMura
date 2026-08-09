from __future__ import annotations
import json
from pathlib import Path
from typing import Any

_SOURCES=json.loads((Path(__file__).resolve().parents[1]/"knowledge"/"approved_sources.json").read_text(encoding="utf-8"))

def retrieve_approved_knowledge(crop:str,question:str) -> dict[str,Any]:
    key=(crop or "").strip().lower()
    selected=list(_SOURCES.get("general",[]))
    if key in _SOURCES: selected.extend(_SOURCES[key])
    return {"query":question,"crop":crop or "not selected","documents":selected,"grounding_rule":"Consequential rates and chemical choices require a current approved source; metadata links are not a substitute for checking the source version."}
