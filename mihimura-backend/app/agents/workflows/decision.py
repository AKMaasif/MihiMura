"""Decision Support agent: answers that may change a real field operation.

Pipeline (each step is deterministic except step 4):

1. Tool Planner   — pick the minimum evidence tools for this intent.
2. Specialists    — run the selected tools (in parallel where possible).
3. Safety + evidence pre-checks — hazard/consequence flags, evidence score.
4. Decision model — Gemini reasons over the evidence (or a localized
   deterministic answer when no model is available).
5. Safety review  — strip unsupported rates, add required warnings and
   confirmation, replace model confidence with evidence-derived confidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents import i18n
from app.agents.contracts import DecisionOutput, finalize_response, step
from app.agents.evidence_sources import evidence_sources
from app.agents.llm import LLMError, LLMUnavailable, generate_structured_with_model
from app.agents.prompts import DECISION_SYSTEM_PROMPT, PROMPT_VERSION
from app.agents.router import RouteDecision
from app.agents.safety import enforce, precheck, review_rates
from app.agents.specialists import Evidence, collect_evidence
from app.agents.turn import Turn
from app.services.evidence_validation import assess_evidence, validate_response_claims
from app.services.language import detect_language, normalize_language
from app.services.tool_planner import build_tool_plan

_FERTILIZER_TERMS = ("fertil", "urea", "nitrogen", "npk", "පොහොර", "යූරියා", "உரம்", "யூரியா")
_RATE_TERMS = ("pesticide", "fungicide", "insecticide", "dose", "rate", "කෘමිනාශක", "දිලීරනාශක", "මාත්‍රාව", "பூச்சிக்கொல்லி", "பூஞ்சைக்கொல்லி", "அளவு")
_PRICE_TERMS = ("price", "rate", "how much", "මිල", "කීයද", "விலை", "எவ்வளவு")


def select_tools(route: RouteDecision, question: str, context: dict[str, Any] | None = None) -> dict[str, bool]:
    """Which evidence tools Decision Support runs for this request."""
    return build_tool_plan(route.intent, "decision_support", question, context or {}).bool_map()


def next_day_rain_probability(weather: dict[str, Any]) -> float:
    values = (weather.get("daily") or {}).get("precipitation_probability_max") or []
    if not values:
        return 0.0
    try:
        return float(values[1 if len(values) > 1 else 0] or 0)
    except (TypeError, ValueError):
        return 0.0


def _show(value: Any) -> Any:
    return value if value is not None else "—"


def fallback_decision(
    question: str,
    ctx: dict[str, Any],
    evidence: Evidence,
    safety: dict[str, Any],
    history: list[dict[str, str]],
    *,
    route: RouteDecision,
    tool_plan: dict[str, bool],
) -> dict[str, Any]:
    """Localized rule-based decision used when no model is available or it fails."""
    lower = question.lower()
    lang = normalize_language(ctx.get("language") or detect_language(question).language)
    text = i18n.bundle("decision_fallback", lang)
    weather, market = evidence.weather, evidence.market
    rain = next_day_rain_probability(weather)
    is_market = route.intent == "market_decision"

    if route.intent == "weather_decision" and weather.get("live"):
        current = weather.get("current") or {}
        action = text["weather_live"].format(
            location=ctx.get("location") or text["location_default"],
            temp=_show(current.get("temperature_2m")),
            humidity=_show(current.get("relative_humidity_2m")),
            wind=_show(current.get("wind_speed_10m")),
            precip=_show(current.get("precipitation")),
        )
        why, level, confirm = text["weather_live_why"], "low", False
    elif is_market:
        if any(x in lower for x in _PRICE_TERMS):
            action, why = text["market_price"], text["market_price_why"]
        else:
            channels = [x.get("channel", "") for x in (market.get("channels") or [])[:6] if x.get("channel")]
            action, why = text["market_channels"], text["market_channels_why"].format(channels="; ".join(channels))
        level, confirm = "watch", False
    elif any(k in lower for k in _FERTILIZER_TERMS) and rain >= 60:
        action, why, level, confirm = text["fertilizer_rain"], text["fertilizer_rain_why"].format(rain=rain), "action", True
    elif any(k in lower for k in _RATE_TERMS):
        action, why, level, confirm = text["rate_sensitive"], text["rate_sensitive_why"], "action", True
    elif route.intent == "weather_decision":
        action, why, level, confirm = text["weather_unavailable"], text["weather_unavailable_why"], "watch", False
    else:
        action, why, level, confirm = text["general"], text["general_why"], "watch", False

    out = {
        "response_type": "confirmation_required" if confirm else "answer",
        "summary": action,
        "recommended_action": action,
        "why": why,
        "alternatives": list(text["alternatives_market" if is_market else "alternatives"]),
        "do_not_do": list(text["do_not_market" if is_market else "do_not"]),
        "sources": evidence_sources(weather, evidence.climate, evidence.knowledge, market_used=bool(tool_plan.get("market"))),
        "confirmation_required": confirm,
        "follow_up": text["follow"],
        "risk_level": level,
        "counterfactual": text["counter"],
        "agent_trace": [],
        "suggested_actions": list(text["suggested_market" if is_market else "suggested"]),
        "clarification_fields": [],
        "memory_patch": {},
        "report_ready": False,
        "auto_generate_report": False,
        "provider": "deterministic-decision-demo",
        "model": "intent-tool-plan+policy",
    }
    return enforce(out, safety)


def _model_payload(turn: Turn, evidence: Evidence, plan_detail: dict[str, Any], quality: dict[str, Any], safety: dict[str, Any]) -> dict[str, Any]:
    plan = plan_detail.get("tools") or {}

    def selected(key: str, value: Any) -> Any:
        return value if (plan.get(key) or {}).get("enabled") else {"status": "not_requested"}

    return {
        "user_message": turn.question,
        "context": turn.model_context(),
        "conversation_memory": turn.model_memory(),
        "recent_history": turn.history[-18:],
        "route": {"intent": turn.route.intent, "reason": turn.route.reason},
        "tool_plan": plan_detail,
        "tool_status": evidence.runtime,
        "weather": selected("weather", evidence.weather),
        "weather_decision": evidence.weather_decision,
        "climate_history": selected("climate", evidence.climate),
        "water_budget_proxy": evidence.water,
        "knowledge": evidence.knowledge,
        "market": evidence.market,
        "economics": evidence.economics,
        "resource_plan": evidence.resources,
        "evidence_quality": quality,
        "safety": safety,
    }


def run_decision(turn: Turn) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    plan = build_tool_plan(turn.route.intent, "decision_support", turn.question, turn.context)
    tool_plan, plan_detail = plan.bool_map(), plan.to_dict()
    evidence = collect_evidence(turn, tool_plan)
    safety = precheck(turn.question, turn.context)
    quality = assess_evidence(
        plan=plan_detail,
        context=turn.context,
        weather_decision=evidence.weather_decision,
        knowledge=evidence.knowledge,
        market=evidence.market,
        economics=evidence.economics,
        water=evidence.water,
        safety=safety,
    )

    provider_error: str | None = None
    try:
        out, model_used = generate_structured_with_model(
            tier="reasoning",
            system=DECISION_SYSTEM_PROMPT,
            payload=_model_payload(turn, evidence, plan_detail, quality, safety),
            schema=DecisionOutput,
            temperature=0.2,
        )
        out = review_rates(out, evidence.knowledge, safety)
        out.update({"provider": "gemini", "model": model_used, "prompt_version": PROMPT_VERSION})
        if not out.get("sources"):
            out["sources"] = evidence_sources(evidence.weather, evidence.climate, evidence.knowledge, market_used=bool(tool_plan.get("market")))
        out = enforce(out, safety)
        if out.get("expert_escalation_recommended") and safety.get("expert_threshold"):
            out["response_type"] = "expert_escalation"
        elif out.get("confirmation_required") and out.get("response_type") in {"answer", "recommendation"}:
            out["response_type"] = "confirmation_required"
    except (LLMUnavailable, LLMError) as exc:
        if isinstance(exc, LLMError):
            provider_error = str(exc)
        out = fallback_decision(turn.question, turn.context, evidence, safety, turn.history, route=turn.route, tool_plan=tool_plan)
        if provider_error:
            out["provider"] = "deterministic-decision-fallback"
            out["provider_error"] = provider_error

    out = finalize_response(out, defaults=i18n.bundle("defaults", turn.language))
    selected = [name for name, spec in plan_detail["tools"].items() if spec.get("enabled")]
    out["agent_trace"] = [
        step("Intent Router", f"Selected Decision Support for {turn.route.intent}"),
        step("Tool Planner", "Selected only: " + ", ".join(selected)),
        step("Farmer Context & Memory", f"Resolved {turn.context.get('context_scope', 'general')} context; {len(turn.history)} recent turn(s)"),
        *evidence.trace,
        step("Decision Model", "Gemini reasoned over the collected evidence" if out.get("provider") == "gemini" else "Localized rule-based decision (model not used)", "complete" if out.get("provider") == "gemini" else "watch"),
        *out["agent_trace"],
        step("Intervention & Safety", "Applied confirmation, rate-sensitive and no-invented-data guardrails"),
    ]
    out = validate_response_claims(out, quality, safety)
    out["tool_plan"] = tool_plan
    out["tool_plan_detail"] = plan_detail
    out["tool_runtime"] = evidence.runtime
    out["weather_decision"] = evidence.weather_decision
    out["economics"] = evidence.economics if tool_plan.get("economics") else {"status": "not_requested"}
    out["resource_plan"] = evidence.resources if tool_plan.get("resources") else {"status": "not_requested"}
    out["generated_at"] = started.isoformat()
    return out
