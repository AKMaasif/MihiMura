"""Offline multilingual regression coverage for MihiMura v6.

No Supabase credentials or network calls are required.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.specialists import Evidence
from app.agents.workflows.chat import fallback_answer as _simple_demo
from app.agents.workflows.decision import fallback_decision, select_tools as _decision_tool_plan
from app.agents.workflows.report import full_report_response as _full_report_response
from app.agents.router import route_request
from app.agents.safety import precheck
from app.services.conversations import extract_facts, report_missing_fields
from app.services.language import detect_language


def run() -> None:
    # Language detection.
    assert detect_language("ගාල්ලේ දැන් කාලගුණය කොහොමද?").language == "Sinhala"
    assert detect_language("காலியில் இப்போது வானிலை எப்படி இருக்கிறது?").language == "Tamil"
    assert detect_language("What is the weather in Galle now?").language == "English"

    # Sinhala weather: district suffix should still resolve Galle and route to Decision Support.
    si_q = "ගාල්ලේ දැන් කාලගුණය කොහොමද?"
    si_facts, si_intent = extract_facts(si_q)
    si_route = route_request(si_q, "auto", {})
    assert si_facts["location"] == "Galle", si_facts
    assert round(float(si_facts["lat"]), 4) == 6.0535
    assert si_intent == "weather_question"
    assert si_route.detected_mode == "decision_support", si_route
    assert si_route.intent == "weather_decision", si_route
    assert _decision_tool_plan(si_route, si_q)["weather"] is True

    # Tamil weather: inflected district should resolve Galle too.
    ta_q = "காலியில் இப்போது வானிலை எப்படி இருக்கிறது?"
    ta_facts, ta_intent = extract_facts(ta_q)
    ta_route = route_request(ta_q, "auto", {})
    assert ta_facts["location"] == "Galle", ta_facts
    assert ta_intent == "weather_question"
    assert ta_route.detected_mode == "decision_support", ta_route
    assert ta_route.intent == "weather_decision", ta_route
    assert _decision_tool_plan(ta_route, ta_q)["weather"] is True

    # Native report requests, including common Sinhala unit-first "අක්කර 1ක" form.
    si_report_q = "පොළොන්නරුවේ අක්කර 1ක වී වගාවට සම්පූර්ණ වාර්තාවක් දෙන්න"
    si_report_facts, si_report_intent = extract_facts(si_report_q)
    si_report_route = route_request(si_report_q, "auto", {})
    assert si_report_facts["location"] == "Polonnaruwa", si_report_facts
    assert si_report_facts["crop"] == "Paddy", si_report_facts
    assert si_report_facts["area_value"] == 1.0, si_report_facts
    assert si_report_facts["area_unit"] == "acre", si_report_facts
    assert si_report_intent == "cultivation_report"
    assert report_missing_fields(si_report_facts) == []
    assert si_report_route.detected_mode == "full_report"

    ta_report_q = "பொலன்னறுவையில் 1 ஏக்கர் நெல் சாகுபடிக்கு முழு அறிக்கை கொடு"
    ta_report_facts, ta_report_intent = extract_facts(ta_report_q)
    ta_report_route = route_request(ta_report_q, "auto", {})
    assert ta_report_facts["location"] == "Polonnaruwa", ta_report_facts
    assert ta_report_facts["crop"] == "Paddy", ta_report_facts
    assert ta_report_facts["area_value"] == 1.0, ta_report_facts
    assert ta_report_facts["area_unit"] == "acre", ta_report_facts
    assert ta_report_intent == "cultivation_report"
    assert ta_report_route.detected_mode == "full_report"

    # Safety detection is multilingual, not just English.
    assert precheck("හෙට පොහොර දාන්න පුළුවන්ද?", {"language": "Sinhala"})["consequential"] is True
    assert precheck("பூச்சிக்கொல்லி அளவு என்ன?", {"language": "Tamil"})["hazardous_or_rate_sensitive"] is True

    # Deterministic fallbacks are also localized if the model/provider fails.
    assert detect_language(_simple_demo("වී වගාව කියන්නේ මොකක්ද?", [], {}, "Sinhala")["summary"]).language == "Sinhala"
    assert detect_language(_simple_demo("நெல் சாகுபடி என்றால் என்ன?", [], {}, "Tamil")["summary"]).language == "Tamil"

    sample_weather = {
        "live": True,
        "source": "Open-Meteo",
        "retrieved_at": "test",
        "current": {"temperature_2m": 29.2, "relative_humidity_2m": 78, "wind_speed_10m": 11.0, "precipitation": 0.3},
        "daily": {"precipitation_probability_max": [40, 55]},
    }
    empty = {"documents": []}
    water = {}
    safety = precheck(si_q, {"language": "Sinhala"})
    si_answer = fallback_decision(
        si_q,
        {"language": "Sinhala", "location": "Galle", "context_scope": "conversation-scenario"},
        Evidence(weather=sample_weather, knowledge=empty, water=water, market={"channels": []}),
        safety,
        [],
        route=si_route,
        tool_plan=_decision_tool_plan(si_route, si_q),
    )
    assert detect_language(si_answer["summary"]).language == "Sinhala", si_answer["summary"]
    assert "29.2" in si_answer["summary"]

    ta_safety = precheck(ta_q, {"language": "Tamil"})
    ta_answer = fallback_decision(
        ta_q,
        {"language": "Tamil", "location": "Galle", "context_scope": "conversation-scenario"},
        Evidence(weather=sample_weather, knowledge=empty, water=water, market={"channels": []}),
        ta_safety,
        [],
        route=ta_route,
        tool_plan=_decision_tool_plan(ta_route, ta_q),
    )
    assert detect_language(ta_answer["summary"]).language == "Tamil", ta_answer["summary"]
    assert "29.2" in ta_answer["summary"]

    # Report-ready chat response should be in the active language too.
    si_memory = {"known_facts": si_report_facts, "missing_fields": [], "active_intent": "cultivation_report"}
    si_ready = _full_report_response(si_report_q, {"language": "Sinhala"}, si_memory, [], si_report_route)
    assert detect_language(si_ready["summary"]).language == "Sinhala", si_ready["summary"]
    assert si_ready["report_ready"] is True

    ta_memory = {"known_facts": ta_report_facts, "missing_fields": [], "active_intent": "cultivation_report"}
    ta_ready = _full_report_response(ta_report_q, {"language": "Tamil"}, ta_memory, [], ta_report_route)
    assert detect_language(ta_ready["summary"]).language == "Tamil", ta_ready["summary"]
    assert ta_ready["report_ready"] is True

    print("MihiMura multilingual agent regression test: PASS")


if __name__ == "__main__":
    run()
