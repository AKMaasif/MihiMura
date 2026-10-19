"""Report Planner agent: complete cultivation / business reports.

Three outcomes, all deterministic (the report text itself is generated later by
``app.services.reports``):

* **clarification** — a report-blocking fact (crop, location, area) is missing;
  return a small localized form for only those fields.
* **follow-up** — the report scenario already exists; answer a section question
  (equipment, finance, market, missing details) from memory without a new PDF.
* **ready** — everything needed is known; the endpoint generates the PDF.
"""

from __future__ import annotations

from typing import Any

from app.agents import i18n
from app.agents.contracts import step
from app.agents.router import RouteDecision
from app.services.conversations import clarification_fields, report_missing_fields
from app.services.economics import estimate_cultivation_economics
from app.services.language import detect_language, normalize_language
from app.services.market_intelligence import get_market_options
from app.services.resource_planning import build_resource_plan
from app.services.tool_planner import build_tool_plan

OPTIONAL_FIELDS = ("season", "irrigation", "variety", "planting_date")
AUTO_GENERATE_INTENTS = {"cultivation_report", "farm_business_analysis", "continue_report"}

_DETAIL_TERMS = ("detail", "information", "what do you need", "need from me", "missing", "විස්තර", "තොරතුරු", "මොනවද ඕන", "අඩු", "விவரம்", "தகவல்", "என்ன வேண்டும்", "குறைவு")
_EQUIPMENT_TERMS = ("equipment", "machine", "machinery", "tool", "උපකරණ", "යන්ත්‍ර", "මෙවලම්", "கருவி", "உபகரணம்", "இயந்திரம்")
_FINANCE_TERMS = ("cost", "profit", "revenue", "break even", "break-even", "වියදම", "වියදම්", "ලාභ", "ආදායම", "செலவு", "லாபம்", "வருவாய்")
_MARKET_TERMS = ("sell", "buyer", "market", "marketing", "platform", "විකුණ", "ගැනුම්", "වෙළඳ", "අලෙවි", "விற்க", "வாங்குப", "சந்தை", "சந்தைப்படுத்த")


def _language(trusted: dict[str, Any], facts: dict[str, Any], question: str = "") -> str:
    explicit = trusted.get("language") or facts.get("language")
    return normalize_language(explicit or detect_language(question).language)


def clarification_response(trusted: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
    facts = dict(memory.get("known_facts") or {})
    missing = list(memory.get("missing_fields") or report_missing_fields(facts))
    lang = _language(trusted, facts)
    text = i18n.bundle("clarify", lang)

    known: list[str] = []
    for key in ("crop", "location", "area_value"):
        if facts.get(key):
            value = facts[key]
            if key == "area_value":
                value = f"{value} {facts.get('area_unit', '')}".strip()
            known.append(f"{text['labels'][key]}: {value}")

    return {
        "response_type": "clarification",
        "summary": text["summary"].format(known=", ".join(known) if known else text["known_default"]),
        "recommended_action": text["action"],
        "why": text["why"],
        "confidence": 0.99,
        "alternatives": list(text["alternatives"]),
        "do_not_do": [],
        "sources": [],
        "confirmation_required": False,
        "follow_up": text["follow"],
        "risk_level": "low",
        "counterfactual": "A saved project can satisfy missing fields when it represents the same field being planned.",
        "agent_trace": [
            step("Intent Router", "Selected Full Report workflow"),
            step("Conversation Memory", "Loaded the active planning scenario and previous user-provided facts"),
            step("Report Planner", f"Identified only {len(missing)} genuinely blocking report field(s)"),
        ],
        "clarification_fields": clarification_fields(missing, facts, lang),
        "suggested_actions": list(text["suggested"]),
        "memory_patch": {},
        "report_ready": False,
        "auto_generate_report": False,
    }


def _base_scenario(economics: dict[str, Any]) -> dict[str, Any] | None:
    return next((x for x in economics.get("scenarios") or [] if x.get("name") == "Planning base"), None)


def _follow_up_text(question: str, lang: str, facts: dict[str, Any], economics: dict[str, Any], market: dict[str, Any], optional_missing: list[str]) -> tuple[str, str]:
    text = i18n.bundle("report_follow", lang)
    q = (question or "").lower()
    crop = facts.get("crop", "crop")
    location = facts.get("location", "the selected location")
    area = f"{facts.get('area_value')} {facts.get('area_unit', 'acre')}"

    if any(x in q for x in _DETAIL_TERMS):
        optional = ", ".join(optional_missing) if optional_missing else "none"
        return text["detail"].format(crop=crop, location=location, area=area, optional=optional), text["detail_action"]
    if any(x in q for x in _EQUIPMENT_TERMS):
        equipment = [x.get("item", "") for x in build_resource_plan(str(crop)).get("equipment", [])[:7]]
        return text["equipment"].format(items="; ".join(x for x in equipment if x)), text["equipment_action"]
    if any(x in q for x in _FINANCE_TERMS):
        base = _base_scenario(economics)
        if not base:
            return text["finance_missing"], text["finance_missing_action"]
        return (
            text["finance"].format(
                area=area, crop=crop,
                cost=base.get("cost_lkr", 0), revenue=base.get("revenue_lkr", 0), profit=base.get("profit_lkr", 0),
            ),
            text["finance_action"],
        )
    if any(x in q for x in _MARKET_TERMS):
        channels = [x.get("channel", "") for x in market.get("channels", [])[:6]]
        return text["market"].format(items="; ".join(x for x in channels if x)), text["market_action"]
    return text["general"].format(area=area, crop=crop, location=location), text["general_action"]


def full_report_response(question: str, trusted: dict[str, Any], memory: dict[str, Any], history: list[dict[str, str]], route: RouteDecision) -> dict[str, Any]:
    facts = dict(memory.get("known_facts") or {})
    missing = list(memory.get("missing_fields") or report_missing_fields(facts))
    if missing:
        return clarification_response(trusted, memory)

    lang = _language(trusted, facts, question)
    economics = estimate_cultivation_economics(facts)
    market = get_market_options(str(facts.get("crop") or ""), str(facts.get("location") or ""))
    resources = build_resource_plan(str(facts.get("crop") or ""))
    plan_detail = build_tool_plan(route.intent, "full_report", question, {**trusted, **facts}).to_dict()
    optional_missing = [x for x in OPTIONAL_FIELDS if not facts.get(x)]
    crop = facts.get("crop", "crop")
    location = facts.get("location", "the selected location")
    area = f"{facts.get('area_value')} {facts.get('area_unit', 'acre')}"
    snapshot = {"economics": economics, "market": market, "resources": resources}
    assumption_source = {"name": "MihiMura configurable planning assumptions", "freshness": economics.get("assumption_version") or "local configuration"}

    if route.intent == "report_follow_up":
        summary, action = _follow_up_text(question, lang, facts, economics, market, optional_missing)
        text = i18n.bundle("report_follow", lang)
        return {
            "response_type": "answer",
            "summary": summary,
            "recommended_action": action,
            "why": text["why"],
            "confidence": 0.92,
            "alternatives": list(text["alternatives"]),
            "do_not_do": list(text["do_not"]),
            "sources": [{"name": "MihiMura report scenario memory", "freshness": "current conversation"}, assumption_source],
            "confirmation_required": False,
            "follow_up": text["follow"],
            "risk_level": "low",
            "counterfactual": "Live weather, current price, chemical-rate or field-action questions should use Decision Support or verified live data tools.",
            "agent_trace": [
                step("Intent Router", "Recognized a follow-up inside the active Full Report workflow"),
                step("Conversation Memory", f"Reused the saved {crop} / {location} / {area} scenario"),
                step("Report Navigator", "Answered the requested report section without regenerating the PDF"),
            ],
            "clarification_fields": [],
            "suggested_actions": list(text["suggested"]),
            "memory_patch": {},
            "report_ready": True,
            "auto_generate_report": False,
            "planning_snapshot": snapshot,
            "tool_plan_detail": plan_detail,
        }

    text = i18n.bundle("report_ready", lang)
    base = _base_scenario(economics)
    base_profit = base.get("profit_lkr") if base else None
    assumptions = text["assumptions"].format(optional=", ".join(optional_missing)) if optional_missing else text["assumptions_none"]
    finance = text["finance"].format(profit=base_profit) if isinstance(base_profit, int) else text["finance_none"]
    return {
        "response_type": "report_ready",
        "summary": text["summary"].format(area=area, crop=crop, location=location, assumptions=assumptions, finance=finance),
        "recommended_action": text["action"],
        "why": text["why"],
        "confidence": 0.93,
        "alternatives": list(text["alternatives"]),
        "do_not_do": list(text["do_not"]),
        "sources": [assumption_source, {"name": "Approved agronomy source registry", "freshness": "current version must be checked for consequential rates"}],
        "confirmation_required": False,
        "follow_up": text["follow"],
        "risk_level": "watch",
        "counterfactual": "Actual field coordinates, soil information, current quotations, season, variety and verified official protocols can materially change the plan and profit range.",
        "agent_trace": [
            step("Intent Router", "Selected Full Report workflow"),
            step("Conversation Memory", f"Loaded {len(history)} recent turn(s) and structured scenario facts"),
            step("Report Planner", "Planned agronomy, resources, economics, harvest, marketing, risks and evidence sections"),
            step("Economics Engine", f"Prepared {len(economics.get('scenarios') or [])} transparent planning scenario(s)"),
            step("Market Intelligence", f"Prepared {len(market.get('channels') or [])} selling-channel categories with verification notes"),
            step("Resource Planner", f"Prepared {len(resources.get('equipment') or [])} equipment and {len(resources.get('tools') or [])} tool items"),
            step("Safety Policy", "Marked rate-sensitive chemicals and live-price claims for verified-source handling"),
        ],
        "clarification_fields": [],
        "suggested_actions": list(text["suggested"]),
        "memory_patch": {},
        "report_ready": True,
        "auto_generate_report": route.intent in AUTO_GENERATE_INTENTS,
        "planning_snapshot": snapshot,
        "tool_plan_detail": plan_detail,
    }


def run_report(turn: Any) -> dict[str, Any]:
    out = full_report_response(turn.question, turn.context, turn.memory, turn.history, turn.route)
    out.setdefault("provider", "report-workflow")
    out.setdefault("model", "planner+economics+market")
    return out
