from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.economics import estimate_cultivation_economics
from app.services.market_intelligence import get_market_options
from app.services.reports import _build_pdf, _fallback_report
from app.services.resource_planning import build_resource_plan


def run() -> None:
    facts = {"crop": "Paddy", "location": "Polonnaruwa", "area_value": 1.0, "area_unit": "acre"}
    economics = estimate_cultivation_economics(facts)
    market = get_market_options("Paddy", "Polonnaruwa")
    resources = build_resource_plan("Paddy")
    report = _fallback_report(
        facts,
        {"source": "test weather", "live": False},
        {"source": "test climate", "live": False},
        {"documents": []},
        economics,
        market,
        resources,
    )
    headings = " ".join(x.get("heading", "").lower() for x in report["sections"])
    for required in ("equipment", "fertilizer", "chemical", "cost", "profit", "harvest", "market"):
        assert required in headings, required
    pdf = _build_pdf(report, facts)
    assert pdf.startswith(b"%PDF") and len(pdf) > 10_000
    print("MihiMura comprehensive PDF fallback test: PASS")


if __name__ == "__main__":
    run()
