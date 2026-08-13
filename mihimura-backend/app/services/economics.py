from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ASSUMPTIONS_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "planning_assumptions.json"


def _load() -> dict[str, Any]:
    try:
        return json.loads(ASSUMPTIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _acre_factor(area_value: Any, area_unit: str | None) -> float | None:
    try:
        value = float(area_value)
    except Exception:
        return None
    unit = (area_unit or "acre").lower()
    if unit.startswith("acre"):
        return value
    if unit.startswith("hect") or unit == "ha":
        return value * 2.47105
    if unit.startswith("perch"):
        return value / 160.0
    return None


def _money(value: float | None) -> int | None:
    return None if value is None else int(round(value))


def _pct(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def _scenario_metrics(*, yield_kg: float, selling_price: float, cost: float) -> dict[str, Any]:
    revenue = yield_kg * selling_price
    profit = revenue - cost
    return {
        "yield_kg": _money(yield_kg),
        "selling_price_lkr_per_kg": _money(selling_price),
        "revenue_lkr": _money(revenue),
        "cost_lkr": _money(cost),
        "profit_lkr": _money(profit),
        "profit_margin_pct": _pct((profit / revenue * 100) if revenue else None),
        "roi_pct": _pct((profit / cost * 100) if cost else None),
        "cost_per_kg_lkr": round(cost / yield_kg, 2) if yield_kg else None,
    }


def calculate_crop_economics(
    *,
    cost_lkr: float,
    expected_yield_kg: float,
    selling_price_lkr_per_kg: float,
) -> dict[str, Any]:
    """Small deterministic calculator for user-entered/verified values."""
    revenue = expected_yield_kg * selling_price_lkr_per_kg
    profit = revenue - cost_lkr
    return {
        "status": "verified_input_estimate",
        "currency": "LKR",
        "cost_lkr": _money(cost_lkr),
        "yield_kg": _money(expected_yield_kg),
        "selling_price_lkr_per_kg": round(selling_price_lkr_per_kg, 2),
        "revenue_lkr": _money(revenue),
        "profit_lkr": _money(profit),
        "profit_margin_pct": _pct((profit / revenue * 100) if revenue else None),
        "roi_pct": _pct((profit / cost_lkr * 100) if cost_lkr else None),
        "break_even_price_lkr_per_kg": round(cost_lkr / expected_yield_kg, 2) if expected_yield_kg else None,
        "break_even_yield_kg": round(cost_lkr / selling_price_lkr_per_kg, 2) if selling_price_lkr_per_kg else None,
    }


def estimate_cultivation_economics(facts: dict[str, Any]) -> dict[str, Any]:
    crop = str(facts.get("crop") or "").strip().lower()
    assumptions = _load()
    crop_cfg = (assumptions.get("crops") or {}).get(crop)
    area_acres = _acre_factor(facts.get("area_value"), str(facts.get("area_unit") or "acre"))

    if not crop_cfg or area_acres is None:
        return {
            "status": "needs_crop_specific_estimate",
            "crop": facts.get("crop"),
            "area_acres": area_acres,
            "currency": "LKR",
            "data_status": "No configured crop-specific planning estimate is available.",
            "cost_items": [],
            "scenarios": [],
            "break_even": {},
            "source": {"type": "planning_configuration", "version": assumptions.get("version")},
            "limitations": ["Add a verified local cost/yield/price data source or farmer-entered quotations before using financial figures."],
        }

    cost_items = []
    total_low = 0.0
    total_high = 0.0
    for item in crop_cfg.get("costs_per_acre_lkr", []):
        low = float(item.get("low", 0)) * area_acres
        high = float(item.get("high", 0)) * area_acres
        mid = (low + high) / 2
        total_low += low
        total_high += high
        cost_items.append({
            "item": item.get("item"),
            "low_lkr": _money(low),
            "base_lkr": _money(mid),
            "high_lkr": _money(high),
            "note": item.get("note", ""),
            "data_class": "illustrative_estimate",
        })

    total_base = (total_low + total_high) / 2
    yield_cfg = crop_cfg.get("yield_kg_per_acre", {})
    price_cfg = crop_cfg.get("selling_price_lkr_per_kg", {})
    yield_low = float(yield_cfg.get("low", 0)) * area_acres
    yield_base = float(yield_cfg.get("base", (float(yield_cfg.get("low", 0)) + float(yield_cfg.get("high", 0))) / 2)) * area_acres
    yield_high = float(yield_cfg.get("high", 0)) * area_acres
    price_low = float(price_cfg.get("low", 0))
    price_base = float(price_cfg.get("base", (float(price_cfg.get("low", 0)) + float(price_cfg.get("high", 0))) / 2))
    price_high = float(price_cfg.get("high", 0))

    scenarios = [
        {"name": "Conservative", **_scenario_metrics(yield_kg=yield_low, selling_price=price_low, cost=total_high)},
        {"name": "Planning base", **_scenario_metrics(yield_kg=yield_base, selling_price=price_base, cost=total_base)},
        {"name": "Favourable", **_scenario_metrics(yield_kg=yield_high, selling_price=price_high, cost=total_low)},
    ]

    break_even_price = total_base / yield_base if yield_base else None
    break_even_yield = total_base / price_base if price_base else None
    base_metrics = next((x for x in scenarios if x["name"] == "Planning base"), {})

    return {
        "status": "illustrative_planning_estimate",
        "crop": facts.get("crop"),
        "area_acres": round(area_acres, 3),
        "currency": "LKR",
        "data_status": assumptions.get("data_status", "Illustrative planning assumptions; not a live market quote."),
        "data_class": "estimate",
        "cost_items": cost_items,
        "total_cost": {"low_lkr": _money(total_low), "base_lkr": _money(total_base), "high_lkr": _money(total_high)},
        "scenarios": scenarios,
        "base_metrics": {
            "cost_per_acre_lkr": round(total_base / area_acres, 2) if area_acres else None,
            "cost_per_kg_lkr": base_metrics.get("cost_per_kg_lkr"),
            "profit_margin_pct": base_metrics.get("profit_margin_pct"),
            "roi_pct": base_metrics.get("roi_pct"),
        },
        "break_even": {
            "selling_price_lkr_per_kg": round(break_even_price, 2) if break_even_price is not None else None,
            "yield_kg": _money(break_even_yield),
        },
        "assumption_version": assumptions.get("version"),
        "source": {"type": "planning_configuration", "version": assumptions.get("version"), "freshness": "local configured assumptions; replace with current quotations"},
        "limitations": [
            "These are configurable planning scenarios, not verified current quotations.",
            "Replace seed, labour, machinery, input, transport and selling-price assumptions with current local quotations before investment decisions.",
            "Actual yield and price can differ materially because of variety, season, weather, quality, buyer and field management.",
        ],
    }
