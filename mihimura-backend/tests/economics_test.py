"""Offline economics/resource-planning regression tests."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.economics import estimate_cultivation_economics
from app.services.market_intelligence import get_market_options
from app.services.resource_planning import build_resource_plan


def run() -> None:
    facts = {"crop": "Paddy", "location": "Polonnaruwa", "area_value": 1, "area_unit": "acre"}
    economics = estimate_cultivation_economics(facts)
    assert economics["status"] == "illustrative_planning_estimate"
    assert economics["total_cost"]["base_lkr"] > 0
    assert len(economics["scenarios"]) == 3
    assert economics["break_even"]["selling_price_lkr_per_kg"] > 0
    market = get_market_options("Paddy", "Polonnaruwa")
    assert len(market["channels"]) >= 5
    resources = build_resource_plan("Paddy")
    assert len(resources["equipment"]) >= 5
    assert len(resources["inputs"]) >= 4
    print("MihiMura economics/resource regression test: PASS")


if __name__ == "__main__":
    run()
