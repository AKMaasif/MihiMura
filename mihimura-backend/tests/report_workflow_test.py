from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.workflows.report import full_report_response as _full_report_response
from app.agents.router import RouteDecision


def route(intent: str) -> RouteDecision:
    return RouteDecision(
        requested_mode="auto",
        detected_mode="full_report",
        effective_mode="full_report",
        intent=intent,
        confidence=0.99,
        reason="test",
        should_switch=False,
        suggested_mode=None,
    )


def run() -> None:
    memory = {
        "known_facts": {
            "crop": "Paddy",
            "location": "Polonnaruwa",
            "area_value": 1.0,
            "area_unit": "acre",
        },
        "missing_fields": [],
    }
    trusted = {"language": "English"}

    initial = _full_report_response(
        "Create a complete paddy cultivation report for my 1 acre in Polonnaruwa",
        trusted,
        memory,
        [],
        route("cultivation_report"),
    )
    assert initial["response_type"] == "report_ready"
    assert initial["auto_generate_report"] is True
    assert initial["clarification_fields"] == []

    details = _full_report_response(
        "what other details do you need?",
        trusted,
        memory,
        [],
        route("report_follow_up"),
    )
    assert details["response_type"] == "answer"
    assert details["auto_generate_report"] is False
    assert "No mandatory report details are missing" in details["summary"]

    equipment = _full_report_response(
        "what equipment do I need?",
        trusted,
        memory,
        [],
        route("report_follow_up"),
    )
    assert "Tractor" in equipment["summary"]
    assert equipment["auto_generate_report"] is False

    print("MihiMura Full Report workflow regression test: PASS")


if __name__ == "__main__":
    run()
