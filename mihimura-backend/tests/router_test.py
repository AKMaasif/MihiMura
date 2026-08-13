"""Offline intent-router regression tests."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agents.router import route_request


def run() -> None:
    weather = route_request("what will the weather be tomorrow for my paddy field?", "simple_chat", {})
    assert weather.should_switch is True
    assert weather.suggested_mode == "decision_support"


    market = route_request("where can i sell paddy and what is the current price?", "simple_chat", {})
    assert market.should_switch is True
    assert market.suggested_mode == "decision_support"
    assert market.intent == "market_decision"

    report = route_request("make a complete report for 1 acre paddy in Polonnaruwa with costs and profit", "simple_chat", {})
    assert report.should_switch is True
    assert report.suggested_mode == "full_report"

    auto = route_request("make a complete report for 1 acre paddy in Polonnaruwa", "auto", {})
    assert auto.should_switch is False
    assert auto.detected_mode == "full_report"

    general = route_request("explain why paddy fields are levelled", "simple_chat", {})
    assert general.should_switch is False
    assert general.effective_mode == "simple_chat"

    forced = route_request("will it rain tomorrow?", "simple_chat", {}, allow_mode_mismatch=True)
    assert forced.should_switch is False
    assert forced.effective_mode == "simple_chat"

    rag = route_request(
        "According to the indexed rice pest surveillance guidance, what observations should a field officer make when conducting pest surveillance in a rice field? Base your answer on the available source and tell me the document name.",
        "auto",
        {},
    )
    assert rag.detected_mode == "simple_chat"
    assert rag.intent == "general_agriculture_question"

    print("MihiMura intent-router regression test: PASS")


if __name__ == "__main__":
    run()
