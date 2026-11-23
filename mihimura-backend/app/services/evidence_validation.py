from __future__ import annotations

from typing import Any


def _tool_enabled(plan: dict[str, Any], name: str) -> bool:
    tools = plan.get("tools") or {}
    item = tools.get(name)
    if isinstance(item, dict):
        return bool(item.get("enabled"))
    return bool(item)


def assess_evidence(
    *,
    plan: dict[str, Any],
    context: dict[str, Any],
    weather_decision: dict[str, Any] | None = None,
    knowledge: dict[str, Any] | None = None,
    market: dict[str, Any] | None = None,
    economics: dict[str, Any] | None = None,
    water: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate confidence from observed evidence rather than model self-rating."""
    weather_decision = weather_decision or {}
    knowledge = knowledge or {}
    market = market or {}
    economics = economics or {}
    water = water or {}
    safety = safety or {}

    checks: list[dict[str, Any]] = []
    score = 0.20
    max_score = 0.20

    def add(name: str, required: bool, passed: bool, weight: float, detail: str, status: str | None = None) -> None:
        nonlocal score, max_score
        if required:
            max_score += weight
            if passed:
                score += weight
        checks.append({
            "name": name,
            "required": required,
            "passed": passed,
            "status": status or ("pass" if passed else "missing"),
            "detail": detail,
            "weight": weight if required else 0.0,
        })

    location_known = bool(context.get("location") and str(context.get("location")).lower() not in {"sri lanka", "unknown"})
    add("Resolved location", True, location_known, 0.10, f"location={context.get('location') or 'missing'}")

    crop_required = _tool_enabled(plan, "agronomy") or _tool_enabled(plan, "economics") or _tool_enabled(plan, "resources")
    crop_known = bool(context.get("crop"))
    add("Crop context", crop_required, crop_known, 0.10, f"crop={context.get('crop') or 'missing'}")

    if _tool_enabled(plan, "weather"):
        live = bool(weather_decision.get("decision_usable"))
        add("Live weather", True, live, 0.25, "Current weather/forecast retrieved." if live else "Live weather unavailable; current-condition recommendation must be limited.", "pass" if live else "unavailable")

    if _tool_enabled(plan, "agronomy"):
        docs = knowledge.get("documents") or []
        retrieval = knowledge.get("retrieval")
        grounded = retrieval == "hybrid_pgvector_fts" and len(docs) > 0
        add("Agronomy evidence", True, grounded, 0.25, f"retrieval={retrieval}; evidence_chunks={len(docs)}", "pass" if grounded else "weak")

    if _tool_enabled(plan, "market"):
        live_price = str(market.get("price_feed") or "").lower() in {"connected", "live", "success"}
        channels = bool(market.get("channels"))
        # A non-live channel registry is useful for channel planning but not price claims.
        add("Market channels", True, channels, 0.10, f"channels={len(market.get('channels') or [])}")
        add("Live market price", bool((plan.get("intent") or "") == "market_decision"), live_price, 0.15, f"price_feed={market.get('price_feed','not_connected')}", "pass" if live_price else "unavailable")

    if _tool_enabled(plan, "economics"):
        status = str(economics.get("status") or "")
        verified = status == "verified_input_estimate"
        illustrative = status == "illustrative_planning_estimate"
        add(
            "Deterministic economics",
            True,
            verified,
            0.10,
            f"status={status or 'not_available'}",
            "pass" if verified else "limited" if illustrative else "missing",
        )

    if _tool_enabled(plan, "water"):
        usable = water.get("status") not in {None, "not_requested", "unavailable", "error"}
        add("Water context", True, usable, 0.10, f"status={water.get('status','unknown')}")

    normalized = max(0.0, min(1.0, score / max_score if max_score else 0.5))
    if normalized >= 0.82:
        level = "high"
    elif normalized >= 0.62:
        level = "moderate"
    elif normalized >= 0.42:
        level = "low"
    else:
        level = "insufficient"

    blockers = [x for x in checks if x["required"] and not x["passed"] and x["status"] in {"missing", "unavailable"}]
    hazard = bool(safety.get("hazardous_or_rate_sensitive"))
    if hazard and not any(x["name"] == "Agronomy evidence" and x["passed"] for x in checks):
        blockers.append({"name": "Verified treatment evidence", "detail": "Rate-sensitive request lacks retrieved approved agronomy evidence.", "status": "missing", "required": True, "passed": False})
        normalized = min(normalized, 0.45)
        level = "low" if normalized >= 0.42 else "insufficient"

    return {
        "score": round(normalized, 3),
        "level": level,
        "checks": checks,
        "blocking_issues": blockers,
        "can_make_current_decision": not any(x.get("name") == "Live weather" for x in blockers),
        "can_make_rate_sensitive_recommendation": not hazard or not any(x.get("name") == "Verified treatment evidence" for x in blockers),
        "method": "deterministic_evidence_weighting_v1",
    }


def validate_response_claims(result: dict[str, Any], evidence: dict[str, Any], safety: dict[str, Any]) -> dict[str, Any]:
    """Apply evidence-derived confidence and add guardrails to a generated response."""
    model_confidence = result.get("confidence")
    try:
        model_confidence = float(model_confidence)
    except Exception:
        model_confidence = None

    result["model_confidence"] = model_confidence
    result["confidence"] = evidence.get("score", 0.5)
    result["evidence_quality"] = evidence

    result.setdefault("do_not_do", [])
    lang = str(safety.get("language") or "English")
    weather_warning = {
        "Sinhala": "demo/fallback කාලගුණ දත්ත වත්මන් ක්ෂේත්‍ර තත්ත්වයක් ලෙස භාවිතා නොකරන්න. ක්‍රියා කිරීමට පෙර සජීවී කාලගුණය නැවත පරීක්ෂා කරන්න.",
        "Tamil": "demo/fallback வானிலை தரவை தற்போதைய வயல் நிலையாக பயன்படுத்த வேண்டாம். நடவடிக்கை எடுக்கும் முன் நேரடி வானிலையை மீண்டும் சரிபார்க்கவும்.",
        "English": "Do not treat fallback/demo weather as a current field-condition observation. Re-check live weather before acting.",
    }.get(lang, "Do not treat fallback/demo weather as a current field-condition observation. Re-check live weather before acting.")
    rate_warning = {
        "Sinhala": "වත්මන් අනුමත බෝග/product protocol හෝ label එකෙන් පැහැදිලිව තහවුරු නොකළ නිශ්චිත treatment rate එකක් භාවිතා නොකරන්න.",
        "Tamil": "தற்போதைய அங்கீகரிக்கப்பட்ட பயிர்/product protocol அல்லது label தெளிவாக ஆதரிக்காத துல்லியமான treatment rate-ஐ பயன்படுத்த வேண்டாம்.",
        "English": "Do not use an exact treatment rate unless the current approved crop/product protocol or label explicitly supports it.",
    }.get(lang, "Do not use an exact treatment rate unless the current approved crop/product protocol or label explicitly supports it.")
    if not evidence.get("can_make_current_decision", True):
        if weather_warning not in result["do_not_do"]:
            result["do_not_do"].append(weather_warning)
    if safety.get("hazardous_or_rate_sensitive") and not evidence.get("can_make_rate_sensitive_recommendation", False):
        if rate_warning not in result["do_not_do"]:
            result["do_not_do"].append(rate_warning)
        result["expert_escalation_recommended"] = True

    trace = result.setdefault("agent_trace", [])
    trace.append({
        "agent": "Evidence Validator",
        "action": f"Evidence quality={evidence.get('level')} ({round(float(evidence.get('score',0))*100)}%); blocking issues={len(evidence.get('blocking_issues') or [])}",
        "status": "complete" if evidence.get("level") in {"high", "moderate"} else "watch",
    })
    trace.append({
        "agent": "Confidence Engine",
        "action": "Replaced model self-confidence with deterministic evidence-derived confidence.",
        "status": "complete",
    })
    return result
