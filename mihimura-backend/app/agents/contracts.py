"""Response contracts shared by every MihiMura agent.

Two kinds of contract live here:

* **Model output schemas** (``ChatOutput``, ``DecisionOutput``, ``VisionOutput``):
  what Gemini must return. They deliberately exclude ``confidence`` and
  ``agent_trace`` — confidence is computed from evidence and the trace records
  what the application actually ran, so neither is left to the model.
* **The decision contract** returned by ``/ask-ai``: ``finalize_response`` fills
  every field the web app reads, so each workflow only sets what it knows.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Facts the model may add to conversation memory. Location is excluded on
# purpose: it must come from the deterministic district resolver so that the
# stored coordinates always match the stored place name.
MEMORY_PATCH_KEYS = ("crop", "stage", "season", "variety", "irrigation", "area_value", "area_unit", "planting_date")


class SourceRef(BaseModel):
    name: str
    freshness: str = ""
    url: str | None = None


class FactPatch(BaseModel):
    # Plain string so one bad key never invalidates a whole answer;
    # memory_patch_to_dict() drops anything outside MEMORY_PATCH_KEYS.
    key: str = Field(description="One of: " + ", ".join(MEMORY_PATCH_KEYS))
    value: str


class ChatOutput(BaseModel):
    summary: str
    recommended_action: str = ""
    why: str = ""
    alternatives: list[str] = Field(default_factory=list)
    do_not_do: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    follow_up: str = ""
    risk_level: Literal["low", "watch"] = "low"
    counterfactual: str = ""
    suggested_actions: list[str] = Field(default_factory=list)
    memory_patch: list[FactPatch] = Field(default_factory=list)


class DecisionOutput(BaseModel):
    response_type: Literal["answer", "recommendation", "confirmation_required", "expert_escalation"] = "answer"
    summary: str
    recommended_action: str
    why: str
    alternatives: list[str] = Field(default_factory=list)
    do_not_do: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    confirmation_required: bool = False
    follow_up: str = ""
    risk_level: Literal["low", "watch", "action", "emergency"] = "watch"
    counterfactual: str = ""
    suggested_actions: list[str] = Field(default_factory=list)
    memory_patch: list[FactPatch] = Field(default_factory=list)


class Differential(BaseModel):
    condition: str
    confidence: float
    evidence: str


class VisionOutput(BaseModel):
    crop: str
    crop_confidence: float
    quality: str
    observed_symptoms: list[str] = Field(default_factory=list)
    differential: list[Differential] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    urgency: str = ""
    safe_steps: list[str] = Field(default_factory=list)
    treatment_options: list[str] = Field(default_factory=list)
    expert_review: bool = False
    additional_evidence_needed: list[str] = Field(default_factory=list)
    disclaimer: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def step(agent: str, action: str, status: str = "complete") -> dict[str, str]:
    """One entry of the agent trace shown in the UI."""
    return {"agent": agent, "action": action, "status": status}


def memory_patch_to_dict(patch: Any) -> dict[str, Any]:
    """Convert model ``[{key, value}]`` pairs into a safe known-facts patch."""
    out: dict[str, Any] = {}
    items: list[Any]
    if isinstance(patch, dict):
        items = [{"key": k, "value": v} for k, v in patch.items()]
    elif isinstance(patch, list):
        items = patch
    else:
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        value = item.get("value")
        if key not in MEMORY_PATCH_KEYS or value in (None, "", []):
            continue
        if key == "area_value":
            try:
                value = float(str(value).replace(",", ""))
            except ValueError:
                continue
            if value <= 0:
                continue
        else:
            value = str(value).strip()[:80]
        out[key] = value
    return out


def clamp_confidence(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


_LIST_FIELDS = ("alternatives", "do_not_do", "sources", "agent_trace", "clarification_fields", "suggested_actions")


def finalize_response(out: dict[str, Any], *, defaults: dict[str, str] | None = None) -> dict[str, Any]:
    """Guarantee every field of the decision contract is present and well-typed."""
    defaults = defaults or {}
    out.setdefault("response_type", "answer")
    summary = str(out.get("summary") or out.get("recommended_action") or defaults.get("summary") or "").strip()
    out["summary"] = summary
    out["recommended_action"] = str(out.get("recommended_action") or summary)
    out.setdefault("why", defaults.get("why", ""))
    out["confidence"] = clamp_confidence(out.get("confidence"), 0.5)
    for key in _LIST_FIELDS:
        value = out.get(key)
        out[key] = list(value) if isinstance(value, (list, tuple)) else []
    out["sources"] = [s for s in out["sources"] if isinstance(s, dict) and s.get("name")]
    out["confirmation_required"] = bool(out.get("confirmation_required"))
    out.setdefault("follow_up", defaults.get("follow_up", ""))
    out.setdefault("risk_level", "low")
    out.setdefault("counterfactual", defaults.get("counterfactual", ""))
    out["memory_patch"] = memory_patch_to_dict(out.get("memory_patch"))
    out["report_ready"] = bool(out.get("report_ready"))
    out["auto_generate_report"] = bool(out.get("auto_generate_report"))
    return out
