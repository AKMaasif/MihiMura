"""Regression checks for confirmed reliability defects.

Offline: no Supabase, Gemini, or weather network calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents import llm  # noqa: E402
from app.agents.orchestrator import orchestrator  # noqa: E402
from app.agents.router import detect_mode  # noqa: E402
from app.agents.safety import precheck  # noqa: E402
from app.agents.soil_water import calculate_water_budget  # noqa: E402
from app.agents.specialists import Evidence  # noqa: E402
from app.agents.vision import analyze_crop_images  # noqa: E402
from app.agents.workflows.decision import fallback_decision  # noqa: E402
from app.services.evidence_validation import assess_evidence  # noqa: E402
from app.services.knowledge_base import _citation_row_allowed  # noqa: E402
from app.services.language import detect_language  # noqa: E402
from app.services.weather import DEMO  # noqa: E402
from app.agents.router import route_request  # noqa: E402


class FakeClient:
    def __init__(self, reply: dict) -> None:
        self.models = SimpleNamespace(generate_content=lambda **_: SimpleNamespace(parsed=None, text=json.dumps(reply)))


def _decision(question: str, weather: dict) -> dict:
    route = route_request(question, "auto", {})
    evidence = Evidence(weather=weather, knowledge={"documents": [], "retrieval": "approved_source_registry_fallback"})
    return fallback_decision(
        question,
        {"language": "English", "location": "Galle"},
        evidence,
        precheck(question, {"language": "English"}),
        [],
        route=route,
        tool_plan={"market": False},
    )


def run() -> None:
    question = "can I apply fertilizer tomorrow?"
    blocked = _decision(question, dict(DEMO))
    assert "Delay the exposed fertilizer" not in blocked["summary"], blocked["summary"]
    assert "82" not in blocked["summary"]

    live = {
        **DEMO,
        "live": True,
        "status": "success",
        "source": "Open-Meteo",
        "daily": {"precipitation_probability_max": [10, 82]},
    }
    allowed = _decision(question, live)
    assert "Delay the exposed fertilizer" in allowed["summary"], allowed["summary"]

    water = calculate_water_budget({"stage": "vegetative"}, dict(DEMO))
    assert water["status"] == "unavailable"
    assert water["forecast_rain_3d_mm"] is None
    assert water["forecast_live"] is False

    economics = assess_evidence(
        plan={"tools": {"economics": {"enabled": True}}, "intent": "cultivation_report"},
        context={"crop": "Paddy", "location": "Galle"},
        economics={"status": "illustrative_planning_estimate"},
    )
    check = next(item for item in economics["checks"] if item["name"] == "Deterministic economics")
    assert check["passed"] is False and check["status"] == "limited"

    assert not _citation_row_allowed({"approval_status": "draft", "title": "Unreleased note"})
    assert _citation_row_allowed({"title": "Department of Agriculture rice guide"})

    mode, intent, _, _ = detect_mode("pohora danna puluvanda?")
    assert mode == "decision_support" and intent == "input_safety_decision"
    mode, intent, _, _ = detect_mode("vaanilai eppadi irukku?")
    assert mode == "decision_support" and intent == "weather_decision"
    assert detect_language("pohora danna puluvanda").language == "Sinhala"
    assert detect_language("what is paddy levelling").language == "English"
    assert detect_language("வணக்கம்").language == "Tamil"

    llm.get_gemini_client = lambda: None  # type: ignore[assignment]
    vision = analyze_crop_images([(b"fake", "image/jpeg")], "Paddy")
    assert vision["provider"] == "demo"
    assert vision["expert_review"] is True
    assert vision["crop_confidence"] <= 0.55
    assert vision["differential"][0]["confidence"] < 0.5

    hello = orchestrator.process_farmer_request("hello", {"language": "English"}, "test-user")
    trace = hello["workflow_trace"]
    assert trace["route"] == "simple_chat"
    assert trace["outcome"] == hello["response_type"]
    assert isinstance(trace["elapsed_ms"], int) and trace["elapsed_ms"] >= 0
    assert trace["agents"]

    llm.get_gemini_client = lambda: FakeClient(  # type: ignore[assignment]
        {
            "summary": "The Department bulletin says to spray 2.5 g per litre tomorrow.",
            "recommended_action": "Spray 2.5 g per litre.",
            "why": "Invented.",
            "sources": [{"name": "Invented Department Bulletin", "freshness": "2024"}],
        }
    )
    chat = orchestrator.process_farmer_request(
        "what fungicide dose should I spray on chilli?",
        {"language": "English", "interaction_mode": "simple_chat", "allow_mode_mismatch": True},
        "test-user",
    )
    names = " ".join(str(item.get("name") or "") for item in chat["sources"])
    assert "Invented Department Bulletin" not in names
    assert "2.5 g per litre" not in f"{chat['summary']} {chat['recommended_action']}"
    assert chat["expert_escalation_recommended"] is True

    llm.get_gemini_client = lambda: None  # type: ignore[assignment]
    print("MihiMura reliability regression test: PASS")


if __name__ == "__main__":
    run()
