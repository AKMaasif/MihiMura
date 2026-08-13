from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import _decision_tool_plan
from app.agents.router import route_request


def run() -> None:
    market_route = route_request("where can i sell paddy at the current price?", "auto", {})
    market_plan = _decision_tool_plan(market_route, "where can i sell paddy at the current price?")
    assert market_plan["market"] is True
    assert market_plan["weather"] is False
    assert market_plan["climate"] is False
    assert market_plan["water"] is False

    weather_route = route_request("will it rain tomorrow?", "auto", {})
    weather_plan = _decision_tool_plan(weather_route, "will it rain tomorrow?")
    assert weather_plan["weather"] is True
    assert weather_plan["market"] is False

    input_route = route_request("can i apply fertilizer tomorrow?", "auto", {})
    input_plan = _decision_tool_plan(input_route, "can i apply fertilizer tomorrow?")
    assert input_plan["weather"] is True
    assert input_plan["agronomy"] is True
    assert input_plan["safety"] is True

    irrigation_route = route_request("should i irrigate today?", "auto", {})
    irrigation_plan = _decision_tool_plan(irrigation_route, "should i irrigate today?")
    assert irrigation_plan["weather"] is True
    assert irrigation_plan["water"] is True

    print("MihiMura intent-specific tool-plan regression test: PASS")


if __name__ == "__main__":
    run()
