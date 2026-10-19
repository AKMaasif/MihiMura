"""Mode Guard: pause before running the wrong workflow.

When the user forced a mode (e.g. Simple Chat) but the router is confident the
request needs another one (e.g. a live weather decision), we ask instead of
answering with the wrong tools.
"""

from __future__ import annotations

from typing import Any

from app.agents import i18n
from app.agents.contracts import step
from app.agents.router import MODE_LABELS, RouteDecision
from app.services.language import detect_language


def mode_switch_response(route: RouteDecision, question: str) -> dict[str, Any]:
    current = MODE_LABELS.get(route.requested_mode, route.requested_mode)
    suggested = MODE_LABELS.get(route.suggested_mode or route.detected_mode, route.detected_mode)
    text = i18n.bundle("mode_switch", detect_language(question).language)
    fmt = {"current": current, "suggested": suggested}
    return {
        "response_type": "mode_switch",
        "summary": text["summary"].format(**fmt),
        "recommended_action": text["action"].format(**fmt),
        "why": text["reason"] or route.reason,
        "confidence": route.confidence,
        "alternatives": [text["alternative"].format(**fmt)],
        "do_not_do": list(text["do_not"]),
        "sources": [],
        "confirmation_required": False,
        "follow_up": text["follow"],
        "risk_level": "low",
        "counterfactual": text["counter"],
        "agent_trace": [
            step("Intent Router", f"Detected {route.intent} and recommended {suggested}"),
            step("Mode Guard", "Paused before running unnecessary or unsafe tools"),
        ],
        "clarification_fields": [],
        "suggested_actions": [f"Switch to {suggested}", f"Stay in {current}"],
        "memory_patch": {},
        "report_ready": False,
        "auto_generate_report": False,
        "requested_mode": route.requested_mode,
        "detected_mode": route.detected_mode,
        "effective_mode": route.requested_mode,
        "suggested_mode": route.suggested_mode,
        "detected_intent": route.intent,
        "mode_reason": route.reason,
        "original_question": question,
        "provider": "intent-router",
        "model": "deterministic-router-v2-multilingual",
    }
