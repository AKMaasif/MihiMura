from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from app.agents.agronomy import retrieve_approved_knowledge
from app.agents.context import load_farmer_context
from app.agents.router import MODE_LABELS, RouteDecision, route_request
from app.agents.safety import enforce, precheck
from app.agents.soil_water import calculate_water_budget
from app.core.ai import get_gemini_client
from app.core.config import settings
from app.services.climate_history import get_nasa_power
from app.services.conversations import clarification_fields, report_missing_fields
from app.services.economics import estimate_cultivation_economics
from app.services.market_intelligence import get_market_options
from app.services.resource_planning import build_resource_plan
from app.services.weather import get_weather
from app.services.tool_planner import build_tool_plan
from app.services.tool_runtime import execute_tool
from app.services.weather_decision import build_weather_decision_context
from app.services.evidence_validation import assess_evidence, validate_response_claims
from app.services.language import detect_language, normalize_language

DECISION_SYSTEM_PROMPT = """You are MihiMura Decision Support, a Sri Lanka-focused, stateful agriculture assistant.
You should feel conversational and context-aware like a modern AI assistant, while grounding time-sensitive or consequential farm decisions in MihiMura's trusted context and tools.

CONVERSATION RULES
- Treat recent_history and conversation_memory as prior turns of the SAME conversation.
- Resolve pronouns and short follow-ups from that history.
- Context precedence is strict: explicit current-message facts > conversation memory > selected owned farm/project > user-profile defaults.
- Never replace an explicitly discussed scenario location with the profile district.
- Preserve durable facts learned from the current turn in memory_patch.

DECISION-SUPPORT RULES
- Give a direct farmer-facing answer first, then explain the evidence and limitations.
- Use supplied live/current tool evidence only for current-condition claims.
- `tool_plan` explicitly shows which tools were selected for this turn. Do not claim that an unselected tool was checked.
- Do not pretend an unavailable data source was checked.
- weather_decision.decision_usable=false means current weather is unavailable; do not present fallback/demo values as live conditions or make a current weather-dependent field recommendation from them.
- evidence_quality is calculated deterministically by the application. Do not invent a separate confidence score; explain limitations consistent with that evidence state.
- If market_intelligence says its live price feed is not connected, never state a current market price as fact; give channel/quotation guidance instead.
- If the question is not consequential, do not manufacture a warning merely because tools were available.
- When approved_knowledge.retrieval is hybrid_pgvector_fts, use only claims supported by the retrieved excerpts and identify the supporting source in the explanation.
- approved_source_registry_fallback contains source pointers, not retrieved source text; do not treat it as evidence that a specific recommendation was verified.

AGRICULTURAL SAFETY
- You support decisions; you do not impersonate a certified agronomist.
- Official emergency warnings and current approved protocols take precedence over model suggestions.
- Never invent pesticide/fertilizer doses, label claims, stock, official alerts, laboratory diagnoses or precise measurements.
- If evidence is insufficient, conflicting, rate-sensitive or potentially harmful, say so and recommend official/expert verification.
- Consequential actions require confirmation.

LANGUAGE
Write farmer-facing content in trusted_context.language while preserving dates, quantities, units and warnings.

Return VALID JSON ONLY with these fields:
response_type: one of answer|recommendation|confirmation_required|expert_escalation
summary: string
recommended_action: string
why: string
confidence: number 0-1
alternatives: array of strings
do_not_do: array of strings
sources: array of objects {name,freshness,url?}
confirmation_required: boolean
follow_up: string
risk_level: low|watch|action|emergency
counterfactual: string
agent_trace: array of objects {agent,action,status}
suggested_actions: array of short strings
memory_patch: object containing only durable facts learned from this turn
"""

SIMPLE_CHAT_PROMPT = """You are MihiMura Simple Chat, the conversational front door of a Sri Lankan agriculture platform.
Answer naturally, clearly and helpfully using the ongoing conversation context. This mode is for explanations, general agriculture questions, navigation and normal conversation.

LANGUAGE
- Write all farmer-facing content in trusted_context.language (English, Sinhala or Tamil).
- If the current user message is in Sinhala or Tamil, answer naturally in that same language unless trusted_context explicitly selects another manual language.
- Preserve dates, quantities, units, scientific names and safety warnings accurately.

IMPORTANT MODE BOUNDARY
- Do not claim to have checked live weather, current farm sensors, current market prices, current official alerts or a field-specific safety decision in Simple Chat.
- If the user explicitly forced this mode for a question that normally needs tools, explain the limitation and give only safe general guidance.
- Do not interrogate the user or create clarification forms for ordinary conversation.
- Keep relevant scenario facts consistent with conversation_memory.
- When approved_knowledge.retrieval is hybrid_pgvector_fts, the application HAS already retrieved indexed evidence for you. Use those excerpts as the primary factual basis and include the relevant source records in sources.
- If approved_knowledge.retrieval is hybrid_pgvector_fts and approved_knowledge.documents is non-empty, NEVER say that you do not have access to the indexed document/source. The retrieved excerpts in approved_knowledge.documents are your access to that source for this turn.
- If the user explicitly asks for a document name/source, name the retrieved title/authority/page when available.
- Do not claim to have read pages or sections that are not included in the retrieved excerpts.
- If only approved_source_registry_fallback is available, treat those entries as reference links rather than evidence for detailed rates or treatment claims.

Return VALID JSON ONLY with:
response_type: "answer"
summary: a useful conversational answer (not merely a one-line status)
recommended_action: short optional next step, or "Continue the conversation"
why: short explanation of the scope/logic when useful
confidence: number 0-1
alternatives: array
do_not_do: array
sources: array (usually empty unless a source was explicitly supplied)
confirmation_required: false
follow_up: natural optional follow-up
risk_level: low|watch
counterfactual: string
agent_trace: array of high-level workflow objects
suggested_actions: array of short strings
memory_patch: object containing only durable facts learned from this turn
"""


def _rain_probability(weather: dict[str, Any]) -> float:
    vals = (weather.get("daily") or {}).get("precipitation_probability_max") or []
    if not vals:
        return 0
    idx = 1 if len(vals) > 1 else 0
    try:
        return float(vals[idx] or 0)
    except Exception:
        return 0


def _source_objects(weather: dict, nasa: dict, knowledge: dict) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if weather.get("source"):
        weather_live = bool(weather.get("live"))
        items.append({
            "name": weather.get("source", "Open-Meteo"),
            "freshness": weather.get("retrieved_at", "current request") if weather_live else "UNAVAILABLE / demo fallback - not valid current weather",
            "source_type": "live_weather" if weather_live else "weather_fallback",
            "status": weather.get("status") or ("success" if weather_live else "unavailable"),
        })
    if nasa.get("source"):
        climate_live = bool(nasa.get("live"))
        items.append({
            "name": nasa.get("source", "NASA POWER"),
            "freshness": (nasa.get("period") or {}).get("end", "recent baseline") if climate_live else "unavailable in this request",
            "source_type": "climate_baseline",
            "status": nasa.get("status") or ("success" if climate_live else "unavailable"),
        })
    retrieval = str(knowledge.get("retrieval") or "")
    for d in knowledge.get("documents", [])[:6]:
        page = d.get("page")
        if retrieval == "hybrid_pgvector_fts" or d.get("source_type") == "hybrid_rag":
            freshness = "indexed evidence" + (f" · {page}" if page else "")
        else:
            freshness = "reference link only · source text not retrieved in this turn"
        items.append({
            "name": f"{d.get('authority')}: {d.get('title')}",
            "freshness": freshness,
            "url": d.get("url"),
            "source_type": d.get("source_type") or retrieval,
            "citation": d.get("citation_label"),
            "authority_tier": d.get("authority_tier"),
        })
    return items


def _mode_switch_response(route: RouteDecision, question: str) -> dict[str, Any]:
    current = MODE_LABELS.get(route.requested_mode, route.requested_mode)
    suggested = MODE_LABELS.get(route.suggested_mode or route.detected_mode, route.detected_mode)
    lang = detect_language(question).language
    if lang == "Sinhala":
        summary = f"මෙම ඉල්ලීම {current} ට වඩා {suggested} ක්‍රමයට වඩා හොඳින් ගැළපේ."
        action = f"නිවැරදි මෙවලම් සහ දත්ත භාවිතා කිරීමට {suggested} වෙත මාරු වන්න."
        follow = "‘Switch & continue’ තෝරන්න, නැතහොත් සාමාන්‍ය පිළිතුරක් පමණක් අවශ්‍ය නම් වත්මන් ක්‍රමයේ සිටින්න."
        alt = f"අඩු හැකියාවන් සමඟ {current} තුළම සිටින්න"
        reason = "ඔබගේ ප්‍රශ්නයේ අර්ථය අනුව සජීවී දත්ත/ක්ෂේත්‍ර තීරණ හෝ සම්පූර්ණ වාර්තා workflow එකක් වඩා සුදුසු බව intent router හඳුනාගෙන ඇත."
        do_not = ["සජීවී දත්ත අවශ්‍ය ප්‍රශ්නයකට Simple Chat පිළිතුරක් field-verified evidence ලෙස භාවිතා නොකරන්න."]
        counter = "ඔබට අවශ්‍ය වන්නේ සාමාන්‍ය පැහැදිලි කිරීමක් පමණක් නම් වත්මන් mode එකේ සිටීම සුදුසු විය හැක."
    elif lang == "Tamil":
        summary = f"இந்த கோரிக்கை {current}-ஐ விட {suggested} முறைக்கு சிறப்பாக பொருந்துகிறது."
        action = f"சரியான கருவிகள் மற்றும் தரவை பயன்படுத்த {suggested} முறைக்கு மாறவும்."
        follow = "‘Switch & continue’ என்பதை தேர்வு செய்யவும்; பொதுவான பதில் மட்டும் வேண்டுமெனில் தற்போதைய முறையில் தொடரலாம்."
        alt = f"குறைந்த திறன்களுடன் {current} முறையில் தொடரவும்"
        reason = "உங்கள் கேள்வியின் நோக்கத்தைப் பார்த்து நேரடி தரவு/வயல் முடிவு அல்லது முழு அறிக்கை workflow சிறந்தது என்று intent router கண்டறிந்துள்ளது."
        do_not = ["நேரடி தரவு தேவைப்படும் கேள்விக்கு Simple Chat பதிலை field-verified evidence என பயன்படுத்த வேண்டாம்."]
        counter = "உங்களுக்கு பொதுவான விளக்கம் மட்டும் தேவைப்பட்டால் தற்போதைய mode-ல் தொடர்வது சரியாக இருக்கலாம்."
    else:
        summary = f"This request fits {suggested} better than {current}."
        action = f"Switch to {suggested} so MihiMura can use the right workflow and tools."
        follow = "Choose Switch & continue, or stay in the current mode if you only want a general answer."
        alt = f"Stay in {current} with reduced capabilities"
        reason = route.reason
        do_not = ["Do not present a simple-chat answer as live or field-verified evidence when the request needs tool-grounded decision support."]
        counter = "If your intent is only a general explanation rather than a real farm decision, staying in Simple Chat may be appropriate."
    return {
        "response_type": "mode_switch",
        "summary": summary,
        "recommended_action": action,
        "why": reason,
        "confidence": route.confidence,
        "alternatives": [alt],
        "do_not_do": do_not,
        "sources": [],
        "confirmation_required": False,
        "follow_up": follow,
        "risk_level": "low",
        "counterfactual": counter,
        "agent_trace": [
            {"agent": "Intent Router", "action": f"Detected {route.intent} and recommended {suggested}", "status": "complete"},
            {"agent": "Mode Guard", "action": "Paused before running unnecessary or unsafe tools", "status": "complete"},
        ],
        "clarification_fields": [],
        "suggested_actions": [f"Switch to {suggested}", f"Stay in {current}"],
        "memory_patch": {},
        "report_ready": False,
        "requested_mode": route.requested_mode,
        "detected_mode": route.detected_mode,
        "effective_mode": route.requested_mode,
        "suggested_mode": route.suggested_mode,
        "detected_intent": route.intent,
        "mode_reason": route.reason,
        "original_question": question,
        "auto_generate_report": False,
        "provider": "intent-router",
        "model": "deterministic-router-v2-multilingual",
    }


def _clarification_response(trusted: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
    facts = dict(memory.get("known_facts") or {})
    missing = list(memory.get("missing_fields") or report_missing_fields(facts))
    lang = normalize_language(trusted.get("language") or facts.get("language") or "English")

    labels = {
        "English": {"crop": "crop", "location": "location", "area_value": "land area"},
        "Sinhala": {"crop": "බෝගය", "location": "ස්ථානය", "area_value": "ඉඩම් ප්‍රමාණය"},
        "Tamil": {"crop": "பயிர்", "location": "இடம்", "area_value": "நிலப்பரப்பு"},
    }[lang]
    known = []
    for key in ("crop", "location", "area_value"):
        if facts.get(key):
            value = facts[key]
            if key == "area_value":
                value = f"{value} {facts.get('area_unit', '')}".strip()
            known.append(f"{labels[key]}: {value}")

    if lang == "Sinhala":
        known_text = ", ".join(known) if known else "ඔබගේ වාර්තා ඉලක්කය"
        summary = f"මට {known_text} දැනටමත් ලැබී ඇත. පහත වාර්තාව සෑදීමට අත්‍යවශ්‍ය තොරතුරු පමණක් අවශ්‍යයි. කන්නය, වාරි මූලාශ්‍රය, ප්‍රභේදය සහ වගා දිනය නොදන්නා නම් ඒවා උපකල්පන ලෙස පැහැදිලිව දක්වා වාර්තාව ඉදිරියට ගෙන යන්න පුළුවන්."
        action = "පහත අත්‍යවශ්‍ය කොටස් පමණක් සම්පූර්ණ කරන්න. ඉන්පසු අමතර අනිවාර්ය popup නොමැතිව MihiMura වාර්තාව ඉදිරියට ගෙන යයි."
        why = "බෝගය, වගා ස්ථානය සහ ඉඩම් ප්‍රමාණය වගා, සම්පත් සහ මූල්‍ය ගණනයන්ගේ මූලික පරාසය තීරණය කරයි. අනෙක් තොරතුරු පසුව සකස් කළ හැකි උපකල්පන ලෙස තැබිය හැක."
        alternatives = ["අඩු තොරතුර සාමාන්‍ය chat එකෙන්ම ලබා දෙන්න", "එම ක්ෂේත්‍රයට අදාළ සුරකින ලද farm project එකක් සම්බන්ධ කරන්න"]
        follow = "මෙම අත්‍යවශ්‍ය තොරතුරු ලැබුණු පසු සම්පූර්ණ වාර්තාව වහාම සකස් කළ හැක. අනෙක් තොරතුරු පසුව refine කළ හැක."
        suggested = ["වාර්තාව දිගටම", "සුරකින ලද project එකක් භාවිතා කරන්න"]
    elif lang == "Tamil":
        known_text = ", ".join(known) if known else "உங்கள் அறிக்கை நோக்கம்"
        summary = f"என்னிடம் ஏற்கனவே {known_text} உள்ளது. கீழே உள்ள அறிக்கையை உருவாக்கத் தேவையான கட்டாய விவரங்கள் மட்டும் வேண்டும். பருவம், பாசன மூலம், வகை மற்றும் நடவு தேதி தெரியாவிட்டால் அவற்றை தெளிவான கருதுகோள்களாகக் குறிப்பிட்டு அறிக்கையைத் தொடரலாம்."
        action = "கீழே உள்ள கட்டாய புலங்களை மட்டும் நிரப்பவும். அதன் பிறகு கூடுதல் கட்டாய popup இல்லாமல் MihiMura அறிக்கையைத் தொடரும்."
        why = "பயிர், சாகுபடி இடம் மற்றும் நிலப்பரப்பு தான் வேளாண்மை, வளம் மற்றும் நிதி கணக்கீட்டின் அடிப்படை பரப்பை நிர்ணயிக்கின்றன. மற்ற விவரங்களை பின்னர் திருத்தக்கூடிய கருதுகோள்களாக வைத்துக்கொள்ளலாம்."
        alternatives = ["காணாமல் உள்ள விவரத்தை சாதாரண chat-ல் எழுதவும்", "அதே வயலைச் சேர்ந்த சேமிக்கப்பட்ட farm project-ஐ இணைக்கவும்"]
        follow = "இந்த கட்டாய விவரங்கள் கிடைத்ததும் முழு அறிக்கையை உடனே உருவாக்கலாம். மற்ற விவரங்களை பின்னர் refine செய்யலாம்."
        suggested = ["அறிக்கையை தொடரவும்", "சேமித்த project-ஐ பயன்படுத்தவும்"]
    else:
        known_text = ", ".join(known) if known else "your report goal"
        summary = f"I have {known_text}. I only need the report-blocking details below; I can handle season, irrigation, variety and planting date as visible assumptions if you do not know them yet."
        action = "Complete only the required fields below, then MihiMura will continue without additional mandatory popups."
        why = "Crop, location and land area determine the scope of the agronomic, resource and financial calculations. Other unknowns can be shown as assumptions and refined later."
        alternatives = ["Provide the missing detail in normal chat instead of using the form", "Link a saved farm project that already contains it"]
        follow = "After these required details are supplied, the complete report can be generated immediately. Optional details can be refined later."
        suggested = ["Continue report", "Use a saved project"]

    return {
        "response_type": "clarification",
        "summary": summary,
        "recommended_action": action,
        "why": why,
        "confidence": 0.99,
        "alternatives": alternatives,
        "do_not_do": [],
        "sources": [],
        "confirmation_required": False,
        "follow_up": follow,
        "risk_level": "low",
        "counterfactual": "A saved project can satisfy missing fields when it represents the same field being planned.",
        "agent_trace": [
            {"agent": "Intent Router", "action": "Selected Full Report workflow", "status": "complete"},
            {"agent": "Conversation Memory", "action": "Loaded the active planning scenario and previous user-provided facts", "status": "complete"},
            {"agent": "Report Planner", "action": f"Identified only {len(missing)} genuinely blocking report field(s)", "status": "complete"},
        ],
        "clarification_fields": clarification_fields(missing, facts, lang),
        "suggested_actions": suggested,
        "memory_patch": {},
        "report_ready": False,
        "auto_generate_report": False,
    }


def _full_report_response(question: str, trusted: dict[str, Any], memory: dict[str, Any], history: list[dict[str, str]], route: RouteDecision) -> dict[str, Any]:
    facts = dict(memory.get("known_facts") or {})
    missing = list(memory.get("missing_fields") or report_missing_fields(facts))
    if missing:
        return _clarification_response(trusted, memory)

    lang = normalize_language(trusted.get("language") or facts.get("language") or detect_language(question).language)
    economics = estimate_cultivation_economics(facts)
    market = get_market_options(str(facts.get("crop") or ""), str(facts.get("location") or ""))
    resources = build_resource_plan(str(facts.get("crop") or ""))
    report_tool_plan = build_tool_plan(route.intent, "full_report", question, {**trusted, **facts}).to_dict()
    optional_missing = [x for x in ("season", "irrigation", "variety", "planting_date") if not facts.get(x)]
    crop = facts.get("crop", "crop")
    location = facts.get("location", "the selected location")
    area = f"{facts.get('area_value')} {facts.get('area_unit', 'acre')}"
    base = next((x for x in economics.get("scenarios") or [] if x.get("name") == "Planning base"), None)
    base_profit = base.get("profit_lkr") if base else None

    q = (question or "").lower()
    detail_terms = ("detail", "information", "what do you need", "need from me", "missing", "විස්තර", "තොරතුරු", "මොනවද ඕන", "අඩු", "விவரம்", "தகவல்", "என்ன வேண்டும்", "குறைவு")
    equipment_terms = ("equipment", "machine", "machinery", "tool", "උපකරණ", "යන්ත්‍ර", "මෙවලම්", "கருவி", "உபகரணம்", "இயந்திரம்")
    finance_terms = ("cost", "profit", "revenue", "break even", "break-even", "වියදම", "වියදම්", "ලාභ", "ආදායම", "செலவு", "லாபம்", "வருவாய்")
    market_terms = ("sell", "buyer", "market", "marketing", "platform", "විකුණ", "ගැනුම්", "වෙළඳ", "අලෙවි", "விற்க", "வாங்குப", "சந்தை", "சந்தைப்படுத்த")

    if route.intent == "report_follow_up":
        if any(x in q for x in detail_terms):
            optional_text = ", ".join(optional_missing) if optional_missing else "none"
            if lang == "Sinhala":
                follow_summary = f"අනිවාර්ය වාර්තා තොරතුරු කිසිවක් අඩු නැහැ. බෝගය={crop}, ස්ථානය={location}, ඉඩම් ප්‍රමාණය={area} ලෙස සුරැකී ඇත. තව refine කළ හැකි විස්තර: {optional_text}. ඒවා නොදන්නා නම් පැහැදිලි උපකල්පන ලෙස තබා ගන්නම්."
                follow_action = "පවතින වාර්තාව විවෘත කරන්න හෝ කැමති උපකල්පනයක් refine කරන්න."
            elif lang == "Tamil":
                follow_summary = f"கட்டாய அறிக்கை விவரங்கள் எதுவும் குறைவில்லை. பயிர்={crop}, இடம்={location}, நிலப்பரப்பு={area} என சேமிக்கப்பட்டுள்ளது. விருப்பமாக refine செய்யக்கூடியவை: {optional_text}. தெரியாவிட்டால் அவற்றை தெளிவான கருதுகோள்களாக வைத்துக்கொள்கிறேன்."
                follow_action = "தற்போதைய அறிக்கையைத் திறக்கவும் அல்லது ஒரு விருப்ப கருதுகோளை refine செய்யவும்."
            else:
                follow_summary = f"No mandatory report details are missing. I already have crop={crop}, location={location}, and area={area}. Optional refinements still open: {optional_text}. I can keep these as explicit assumptions unless you want to refine them."
                follow_action = "Open the existing report, or refine one of the optional assumptions."
        elif any(x in q for x in equipment_terms):
            equipment = [x.get("item", "") for x in build_resource_plan(str(crop)).get("equipment", [])[:7]]
            items = "; ".join(x for x in equipment if x)
            if lang == "Sinhala":
                follow_summary = f"මෙම සැලැස්මට ප්‍රධාන උපකරණ/සම්පත්: {items}. සම්පූර්ණ වාර්තාවේ කුලියට ගැනීම/අයිතිය සහ ක්‍රමය මත වෙනස්වන අයිතම වෙන වෙනම දක්වයි."
                follow_action = "උපකරණ කොටස භාවිතා කර ප්‍රදේශීය මිල ගණන් එකතු කරන්න."
            elif lang == "Tamil":
                follow_summary = f"இந்தத் திட்டத்தின் முக்கிய உபகரணங்கள்/வளங்கள்: {items}. முழு அறிக்கையில் வாடகை/சொந்தம் மற்றும் முறையைப் பொறுத்த பொருட்கள் தனித்தனியாக காட்டப்படும்."
                follow_action = "உபகரணப் பகுதியைப் பயன்படுத்தி உள்ளூர் விலை மேற்கோள்களைச் சேகரிக்கவும்."
            else:
                follow_summary = f"For this plan, the main equipment/resources are: {items}. The full report separates hire/own and method-dependent items."
                follow_action = "Use the report equipment section to convert these into local quotations."
        elif any(x in q for x in finance_terms):
            if base:
                if lang == "Sinhala":
                    follow_summary = f"{area} {crop} සඳහා දැනට configure කර ඇති planning-base scenario එකේ ඇස්තමේන්තු වියදම LKR {base.get('cost_lkr', 0):,}, ආදායම LKR {base.get('revenue_lkr', 0):,}, සහ ලාභය LKR {base.get('profit_lkr', 0):,} පමණ වේ. මේවා සජීවී මිල ගණන් නොව planning estimates වේ."
                    follow_action = "ආයෝජනයට පෙර ප්‍රදේශීය input, labour, machinery සහ buyer quotations වලින් මෙම උපකල්පන update කරන්න."
                elif lang == "Tamil":
                    follow_summary = f"{area} {crop} க்கான தற்போதைய planning-base scenario-வில் மதிப்பிடப்பட்ட செலவு சுமார் LKR {base.get('cost_lkr', 0):,}, வருவாய் LKR {base.get('revenue_lkr', 0):,}, லாபம் LKR {base.get('profit_lkr', 0):,}. இவை நேரடி விலை மேற்கோள்கள் அல்ல; திட்டமிடல் மதிப்பீடுகள்."
                    follow_action = "முதலீட்டுக்கு முன் உள்ளூர் input, labour, machinery மற்றும் buyer quotations மூலம் இவற்றை புதுப்பிக்கவும்."
                else:
                    follow_summary = f"The configured planning-base scenario for {area} {crop} currently uses estimated cost about LKR {base.get('cost_lkr', 0):,}, revenue about LKR {base.get('revenue_lkr', 0):,}, and profit about LKR {base.get('profit_lkr', 0):,}. These are illustrative planning assumptions, not live quotations."
                    follow_action = "Replace planning assumptions with current local input, labour, machinery and buyer quotations before investing."
            else:
                if lang == "Sinhala":
                    follow_summary, follow_action = "මෙම බෝගයට සත්‍යාපිත මූල්‍ය scenario එකක් configure කර නැති නිසා මම වියදමක් හෝ ලාභයක් හිතාගෙන නිර්මාණය කරන්නේ නැහැ.", "වත්මන් ප්‍රදේශීය මිල ගණන් ලබාගෙන ගණනය නැවත කරන්න."
                elif lang == "Tamil":
                    follow_summary, follow_action = "இந்தப் பயிருக்கான சரிபார்க்கப்பட்ட நிதி scenario அமைக்கப்படவில்லை; எனவே செலவு அல்லது லாப எண்ணை நான் உருவாக்கமாட்டேன்.", "தற்போதைய உள்ளூர் விலை மேற்கோள்களைப் பெற்று கணக்கை மீண்டும் செய்யவும்."
                else:
                    follow_summary, follow_action = "A verified crop-specific financial scenario is not configured, so I will not invent a cost or profit figure.", "Replace planning assumptions with current local quotations."
        elif any(x in q for x in market_terms):
            channels = [x.get("channel", "") for x in market.get("channels", [])[:6]]
            items = "; ".join(x for x in channels if x)
            if lang == "Sinhala":
                follow_summary = f"සලකා බැලිය හැකි අලෙවි නාලිකා: {items}. ගැනුම්කරුවන්ගේ ලබාගත හැකි බව සහ මිල අස්වැන්නට ආසන්නව නැවත තහවුරු කළ යුතුයි."
                follow_action = "වත්මන් quotations එකතු කර ප්‍රවාහනය, grading සහ payment terms පසු net price එක සසඳන්න."
            elif lang == "Tamil":
                follow_summary = f"மதிப்பிட வேண்டிய விற்பனை வழிகள்: {items}. வாங்குபவர் கிடைப்பும் விலையும் அறுவடைக்கு அருகில் மீண்டும் சரிபார்க்க வேண்டும்."
                follow_action = "தற்போதைய quotations சேகரித்து போக்குவரத்து, grading மற்றும் payment terms கழித்த net price-ஐ ஒப்பிடவும்."
            else:
                follow_summary = f"Selling channels to evaluate include: {items}. Buyer availability and prices must be refreshed close to harvest."
                follow_action = "Collect current quotations and compare net price after transport, grading and payment terms."
        else:
            if lang == "Sinhala":
                follow_summary = f"මෙම සංවාදය තවමත් {location} හි {area} {crop} සැලැස්ම භාවිතා කරයි. වාර්තාව නැවත ආරම්භ නොකර වගා, උපකරණ, inputs, වියදම්/ලාභ, අස්වැන්න හෝ අලෙවිය ගැන follow-up අහන්න පුළුවන්."
                follow_action = "බලන්න හෝ refine කරන්න අවශ්‍ය වාර්තා කොටස අහන්න."
            elif lang == "Tamil":
                follow_summary = f"இந்த உரையாடல் இன்னும் {location} பகுதியில் {area} {crop} திட்டத்தையே பயன்படுத்துகிறது. அறிக்கையை மீண்டும் தொடங்காமல் agronomy, equipment, inputs, செலவு/லாபம், அறுவடை அல்லது சந்தை பற்றி follow-up கேட்கலாம்."
                follow_action = "பார்க்க அல்லது refine செய்ய வேண்டிய அறிக்கை பகுதியைக் கேளுங்கள்."
            else:
                follow_summary = f"This conversation is still using the {area} {crop} plan for {location}. I can answer follow-up questions about agronomy, equipment, inputs, costs/profit, harvest or marketing without restarting the report."
                follow_action = "Ask about the report section you want to inspect or refine."

        common = {
            "English": {
                "why": "The report scenario is already stored in conversation memory, so MihiMura can answer section-level follow-ups without generating another PDF or asking for optional fields again.",
                "alternatives": ["Regenerate the report after changing assumptions", "Switch to Decision Support for a live operational decision"],
                "do_not": ["Do not treat illustrative planning prices as live market quotations", "Do not use unverified chemical or fertilizer rates"],
                "follow": "You can continue asking about any section of this same report.",
                "suggested": ["Ask about equipment", "Ask about costs & profit", "Ask about selling channels", "Refine assumptions"],
            },
            "Sinhala": {
                "why": "වාර්තා scenario එක conversation memory තුළ සුරැකී ඇති නිසා, නව PDF එකක් හෝ අනවශ්‍ය අමතර form නොමැතිව කොටස් මට්ටමේ follow-up වලට පිළිතුරු දිය හැක.",
                "alternatives": ["උපකල්පන වෙනස් කළ පසු වාර්තාව නැවත generate කරන්න", "සජීවී ක්ෂේත්‍ර තීරණයක් සඳහා Decision Support භාවිතා කරන්න"],
                "do_not": ["planning prices සජීවී market quotations ලෙස භාවිතා නොකරන්න", "තහවුරු නොකළ රසායනික/පොහොර rate භාවිතා නොකරන්න"],
                "follow": "මෙම වාර්තාවේ ඕනෑම කොටසක් ගැන මේ සංවාදයේම දිගටම අහන්න පුළුවන්.",
                "suggested": ["උපකරණ ගැන අහන්න", "වියදම් හා ලාභ ගැන අහන්න", "අලෙවි නාලිකා ගැන අහන්න", "උපකල්පන refine කරන්න"],
            },
            "Tamil": {
                "why": "அறிக்கை scenario conversation memory-ல் சேமிக்கப்பட்டுள்ளதால், புதிய PDF அல்லது தேவையற்ற கூடுதல் form இல்லாமல் பகுதி அடிப்படையிலான follow-up கேள்விகளுக்கு பதிலளிக்கலாம்.",
                "alternatives": ["கருதுகோள்களை மாற்றிய பின் அறிக்கையை மீண்டும் உருவாக்கவும்", "நேரடி வயல் முடிவுக்கு Decision Support பயன்படுத்தவும்"],
                "do_not": ["planning prices-ஐ நேரடி market quotations என கருத வேண்டாம்", "சரிபார்க்காத chemical/fertilizer rate-ஐ பயன்படுத்த வேண்டாம்"],
                "follow": "இந்த அறிக்கையின் எந்தப் பகுதியைப் பற்றியும் இதே உரையாடலில் தொடர்ந்து கேட்கலாம்.",
                "suggested": ["உபகரணங்கள் பற்றி கேளுங்கள்", "செலவு & லாபம் பற்றி கேளுங்கள்", "விற்பனை வழிகள் பற்றி கேளுங்கள்", "கருதுகோள்களை refine செய்யவும்"],
            },
        }[lang]
        return {
            "response_type": "answer", "summary": follow_summary, "recommended_action": follow_action, "why": common["why"],
            "confidence": 0.92, "alternatives": common["alternatives"], "do_not_do": common["do_not"],
            "sources": [{"name": "MihiMura report scenario memory", "freshness": "current conversation"}, {"name": "MihiMura configurable planning assumptions", "freshness": economics.get("assumption_version") or "local configuration"}],
            "confirmation_required": False, "follow_up": common["follow"], "risk_level": "low",
            "counterfactual": "Live weather, current price, chemical-rate or field-action questions should use Decision Support or verified live data tools.",
            "agent_trace": [{"agent": "Intent Router", "action": "Recognized a follow-up inside the active Full Report workflow", "status": "complete"}, {"agent": "Conversation Memory", "action": f"Reused the saved {crop} / {location} / {area} scenario", "status": "complete"}, {"agent": "Report Navigator", "action": "Answered the requested report section without regenerating the PDF", "status": "complete"}],
            "clarification_fields": [], "suggested_actions": common["suggested"], "memory_patch": {}, "report_ready": True, "auto_generate_report": False,
            "planning_snapshot": {"economics": economics, "market": market, "resources": resources},
            "tool_plan_detail": report_tool_plan,
        }

    optional_text = ", ".join(optional_missing)
    if lang == "Sinhala":
        assumptions_line = f" කන්නය/වාරි/ප්‍රභේදය/වගා දිනය වැනි අමතර තොරතුරු ({optional_text}) නොමැති නිසා ඒවා වාර්තාවේ පැහැදිලි උපකල්පන ලෙස දක්වනු ලැබේ." if optional_missing else " අවශ්‍ය මූලික සහ refine කරන තොරතුරු දැනටමත් ඇත."
        finance_line = f" දැනට configure කර ඇති planning-base scenario එකේ ලාභ ඇස්තමේන්තුව LKR {base_profit:,} පමණයි; මෙය සජීවී market quotation එකක් නොව ඇස්තමේන්තුවක් ලෙස ලකුණු කරනු ඇත." if isinstance(base_profit, int) else " මූල්‍ය කොටස මිල හිතාගෙන නිර්මාණය නොකර දත්ත හිස්තැන් පැහැදිලිව පෙන්වයි."
        summary = f"{location} හි {area} {crop} සඳහා සම්පූර්ණ වගා වාර්තාව සකස් කිරීමට ප්‍රමාණවත් මූලික තොරතුරු මට ඇත.{assumptions_line}{finance_line}"
        action = "වගා සැලැස්ම, උපකරණ/මෙවලම්, inputs, වියදම්-ලාභ, අවදානම්, අස්වැන්න සහ අලෙවිය ඇතුළත් සම්පූර්ණ වාර්තාව දැන් generate කරන්න."
        why = "Full Report mode එක සංකීර්ණ වගා සහ ව්‍යාපාර ඉල්ලීම කෙටි decision card එකකට සීමා නොකර වෙනම report planner workflow එකක් භාවිතා කරයි."
        alternatives = ["වාර්තාවෙන් පසු කන්නය, වාරි මූලාශ්‍රය, ප්‍රභේදය හෝ වගා දිනය refine කරන්න", "සත්‍ය field data භාවිතා කිරීමට saved project එකක් සම්බන්ධ කරන්න"]
        do_not = ["planning cost/yield/selling-price scenarios සජීවී quotations ලෙස සලකන්න එපා", "තහවුරු නොකළ pesticide/fertilizer rate භාවිතා නොකරන්න"]
        follow = "වාර්තාව generate කළ පසු actual quotations, soil test, variety, irrigation details හෝ buyer offers භාවිතා කර ඕනෑම කොටස refine කරන්න පුළුවන්."
        suggested = ["සම්පූර්ණ PDF විවෘත කරන්න", "ප්‍රදේශීය quotations වලින් වියදම් refine කරන්න", "කන්නය / වාරි තොරතුරු refine කරන්න", "farm project එකක් ලෙස සාදන්න"]
    elif lang == "Tamil":
        assumptions_line = f" பருவம்/பாசனம்/வகை/நடவு தேதி போன்ற விருப்ப விவரங்கள் ({optional_text}) இல்லாததால் அவை அறிக்கையில் தெளிவான கருதுகோள்களாகக் காட்டப்படும்." if optional_missing else " தேவையான அடிப்படை மற்றும் refinement விவரங்கள் ஏற்கனவே உள்ளன."
        finance_line = f" தற்போதைய planning-base scenario சுமார் LKR {base_profit:,} லாபத்தை மதிப்பிடுகிறது; இது நேரடி market quotation அல்ல, estimate என்று தெளிவாக குறிக்கப்படும்." if isinstance(base_profit, int) else " நிதிப் பகுதி விலைகளை உருவாக்காமல் உள்ள data gaps-ஐ தெளிவாகக் காட்டும்."
        summary = f"{location} பகுதியில் {area} {crop} க்கான முழுமையான சாகுபடி அறிக்கையை உருவாக்கத் தேவையான அடிப்படை தகவல் உள்ளது.{assumptions_line}{finance_line}"
        action = "சாகுபடி திட்டம், உபகரணங்கள்/கருவிகள், inputs, செலவு-லாபம், அபாயம், அறுவடை மற்றும் சந்தைப்படுத்தலை உள்ளடக்கிய முழு அறிக்கையை இப்போது உருவாக்கவும்."
        why = "Full Report mode சிக்கலான சாகுபடி/வணிக கோரிக்கையை குறுகிய decision card-ஆக சுருக்காமல் தனிப்பட்ட report planner workflow-ஐ பயன்படுத்துகிறது."
        alternatives = ["அறிக்கை உருவான பின் பருவம், பாசனம், வகை அல்லது நடவு தேதியை refine செய்யவும்", "உண்மையான வயல் தரவைப் பயன்படுத்த saved project-ஐ இணைக்கவும்"]
        do_not = ["planning cost/yield/selling-price scenarios-ஐ நேரடி quotations என கருத வேண்டாம்", "சரிபார்க்கப்படாத pesticide/fertilizer rate-ஐ பயன்படுத்த வேண்டாம்"]
        follow = "அறிக்கை உருவான பின் actual quotations, soil test, variety, irrigation details அல்லது buyer offers மூலம் எந்தப் பகுதியையும் refine செய்யலாம்."
        suggested = ["முழு PDF-ஐ திறக்கவும்", "உள்ளூர் quotations மூலம் செலவுகளை refine செய்யவும்", "பருவம் / பாசனத்தை refine செய்யவும்", "farm project ஆக உருவாக்கவும்"]
    else:
        assumptions_line = f" Optional unknowns ({optional_text}) will be shown as assumptions/scenarios rather than blocking the report." if optional_missing else " The core and refinement details are already available."
        finance_line = f" The current configured planning scenario gives a base profit estimate of about LKR {base_profit:,}, but this is not a live market quote and will be labelled as an estimate." if isinstance(base_profit, int) else " Financial sections will identify the current data gaps instead of inventing prices."
        summary = f"I have enough information to build the complete {area} {crop} report for {location}.{assumptions_line}{finance_line}"
        action = "Generate the full report now with agronomy, equipment/tools, input planning, economics, risk, harvest and marketing sections."
        why = "Full Report mode uses a dedicated report planner instead of compressing a complex farm/business request into the short Decision Contract format."
        alternatives = ["Refine the season, irrigation, variety or planting date after generation", "Link a saved project to replace assumptions with actual field data"]
        do_not = ["Do not treat illustrative cost, yield or selling-price scenarios as live quotations", "Do not use an unverified pesticide/fertilizer rate simply because it appears plausible"]
        follow = "After generation, you can ask MihiMura to refine any section using actual quotations, a soil test, variety, irrigation details or buyer offers."
        suggested = ["Open full PDF", "Refine costs with local quotations", "Refine season / irrigation", "Create as farm project"]

    return {
        "response_type": "report_ready", "summary": summary, "recommended_action": action, "why": why, "confidence": 0.93,
        "alternatives": alternatives, "do_not_do": do_not,
        "sources": [{"name": "MihiMura configurable planning assumptions", "freshness": economics.get("assumption_version") or "local configuration"}, {"name": "Approved agronomy source registry", "freshness": "current version must be checked for consequential rates"}],
        "confirmation_required": False, "follow_up": follow, "risk_level": "watch",
        "counterfactual": "Actual field coordinates, soil information, current quotations, season, variety and verified official protocols can materially change the plan and profit range.",
        "agent_trace": [{"agent": "Intent Router", "action": "Selected Full Report workflow", "status": "complete"}, {"agent": "Conversation Memory", "action": f"Loaded {len(history)} recent turn(s) and structured scenario facts", "status": "complete"}, {"agent": "Report Planner", "action": "Planned agronomy, resources, economics, harvest, marketing, risks and evidence sections", "status": "complete"}, {"agent": "Economics Engine", "action": f"Prepared {len(economics.get('scenarios') or [])} transparent planning scenario(s)", "status": "complete"}, {"agent": "Market Intelligence", "action": f"Prepared {len(market.get('channels') or [])} selling-channel categories with verification notes", "status": "complete"}, {"agent": "Resource Planner", "action": f"Prepared {len(resources.get('equipment') or [])} equipment and {len(resources.get('tools') or [])} tool items", "status": "complete"}, {"agent": "Safety Policy", "action": "Marked rate-sensitive chemicals and live-price claims for verified-source handling", "status": "complete"}],
        "clarification_fields": [], "suggested_actions": suggested, "memory_patch": {}, "report_ready": True,
        "auto_generate_report": route.intent in {"cultivation_report", "farm_business_analysis", "continue_report"},
        "planning_snapshot": {"economics": economics, "market": market, "resources": resources},
        "tool_plan_detail": report_tool_plan,
    }


def _simple_demo(question: str, history: list[dict[str, str]], memory: dict[str, Any], language: str = "English") -> dict[str, Any]:
    lang = normalize_language(language or (memory.get("known_facts") or {}).get("language") or detect_language(question).language)
    lower = question.lower().strip()
    if lang == "Sinhala":
        if lower in {"hi", "hello", "hey"} or any(x in question for x in ("ආයුබෝවන්", "හෙලෝ")):
            summary = "ආයුබෝවන්. මම MihiMura. සාමාන්‍ය කෘෂිකාර්මික ප්‍රශ්න මෙහි අහන්න පුළුවන්. සජීවී කාලගුණ/ක්ෂේත්‍ර තීරණ සඳහා Decision Support සහ සම්පූර්ණ වගා-ව්‍යාපාර සැලසුමක් සඳහා Full Report භාවිතා කරන්න."
        else:
            summary = "මෙය Simple Chat තුළ සාමාන්‍ය කෘෂිකාර්මික දැනුම සහ මේ සංවාදයේ පසුබිම භාවිතා කර පැහැදිලි කළ හැක. සජීවී ක්ෂේත්‍ර තීරණයක් නම් Decision Support භාවිතා කරන්න; වියදම්, ලාභ සහ අලෙවිය ඇතුළත් සම්පූර්ණ සැලසුමක් නම් Full Report භාවිතා කරන්න."
        action, why, follow = "සංවාදය දිගටම කරගෙන යන්න", "Simple Chat අනවශ්‍ය සජීවී දත්ත සහ ආරක්ෂක tool calls නොකරයි.", "ස්වභාවිකව ප්‍රශ්නය අහන්න; වෙනත් mode එකක් වඩා සුදුසු නම් intent router එක දැනුම් දෙයි."
        suggestions = ["සාමාන්‍ය ගොවිතැන් ප්‍රශ්නයක් අහන්න", "Decision Support භාවිතා කරන්න", "Full Report එකක් සකස් කරන්න"]
    elif lang == "Tamil":
        if lower in {"hi", "hello", "hey"} or any(x in question for x in ("வணக்கம்", "ஹலோ")):
            summary = "வணக்கம். நான் MihiMura. பொதுவான வேளாண்மை கேள்விகளை இங்கே கேட்கலாம். நேரடி வானிலை/வயல் முடிவுகளுக்கு Decision Support-ஐவும், முழுமையான சாகுபடி-வணிகத் திட்டத்திற்கு Full Report-ஐவும் பயன்படுத்தலாம்."
        else:
            summary = "இதைக் Simple Chat-ல் பொதுவான வேளாண்மை அறிவும் இந்த உரையாடலின் சூழலும் பயன்படுத்தி விளக்கலாம். நேரடி வயல் முடிவு வேண்டுமெனில் Decision Support-ஐ பயன்படுத்தவும்; செலவு, லாபம் மற்றும் சந்தைப்படுத்தலுடன் முழுமையான திட்டம் வேண்டுமெனில் Full Report-ஐ பயன்படுத்தவும்."
        action, why, follow = "உரையாடலைத் தொடரவும்", "Simple Chat தேவையற்ற நேரடி தரவு மற்றும் safety tool calls-ஐ தவிர்க்கிறது.", "இயல்பாக கேளுங்கள்; வேறு mode சிறந்தது என்றால் intent router பரிந்துரைக்கும்."
        suggestions = ["பொதுவான வேளாண்மை கேள்வி கேளுங்கள்", "Decision Support பயன்படுத்தவும்", "Full Report உருவாக்கவும்"]
    else:
        if lower in {"hi", "hello", "hey"}:
            summary = "Hello. I’m MihiMura. You can ask a general agriculture question here, or use Decision Support for live farm/weather decisions and Full Report for complete cultivation and business planning."
        else:
            summary = "I can discuss this in Simple Chat using general agricultural knowledge and the context of this conversation. For a live farm decision, switch to Decision Support; for a comprehensive cultivation/cost/profit/marketing plan, use Full Report."
        action, why, follow = "Continue the conversation", "Simple Chat intentionally avoids unnecessary live-data and safety-tool calls.", "Ask naturally; the intent router will tell you when another mode is a better fit."
        suggestions = ["Ask a general farming question", "Use Decision Support", "Create a Full Report"]
    return {
        "response_type": "answer",
        "summary": summary,
        "recommended_action": action,
        "why": why,
        "confidence": 0.75,
        "alternatives": [],
        "do_not_do": [],
        "sources": [],
        "confirmation_required": False,
        "follow_up": follow,
        "risk_level": "low",
        "counterfactual": "A time-sensitive, farm-specific or report-level request may be better handled in another mode.",
        "agent_trace": [
            {"agent": "Intent Router", "action": "Kept the request in Simple Chat", "status": "complete"},
            {"agent": "Conversation Memory", "action": f"Loaded {len(history)} recent turn(s) without invoking live farm tools", "status": "complete"},
        ],
        "suggested_actions": suggestions,
        "memory_patch": {},
        "report_ready": False,
        "auto_generate_report": False,
        "provider": "deterministic-simple-chat",
        "model": "conversation-policy-multilingual",
    }


def _simple_chat_should_retrieve(route: RouteDecision, question: str, trusted: dict[str, Any]) -> bool:
    """Decide whether Simple Chat should consult the agricultural RAG index.

    This is deliberately broader than the deterministic intent label so source-grounded
    questions still retrieve evidence even when the user's wording is conversational.
    """
    if route.intent == "general_agriculture_question":
        return True
    q = (question or "").lower()
    agriculture_terms = (
        "agricultur", "agronom", "farm", "field", "crop", "paddy", "rice", "seed",
        "pest", "surveillance", "disease", "weed", "irrig", "fertil", "harvest",
        "manual", "guidance", "guideline", "source", "indexed", "recommendation",
        "ගොවි", "ගොවිපල", "බෝග", "කුඹුර", "වී", "බීජ", "පළිබෝධ", "නිරීක්ෂණ",
        "රෝග", "වල්", "වාරි", "පොහොර", "අස්වැන්න", "මූලාශ්‍ර", "මාර්ගෝපදේශ",
        "பண்ணை", "வயல்", "பயிர்", "நெல்", "விதை", "பூச்சி", "கண்காணிப்பு",
        "நோய்", "களை", "நீர்ப்பாசனம்", "உரம்", "அறுவடை", "மூலம்", "வழிகாட்ட",
    )
    return bool(str(trusted.get("crop") or "").strip() or any(term in q for term in agriculture_terms))


def _attach_simple_rag_diagnostics(out: dict[str, Any], knowledge: dict[str, Any]) -> dict[str, Any]:
    retrieval = str(knowledge.get("retrieval") or "not_requested")
    docs = knowledge.get("documents") or []
    trace = out.setdefault("agent_trace", [])
    if retrieval == "hybrid_pgvector_fts" and docs:
        titles = []
        for d in docs:
            title = str(d.get("title") or "").strip()
            if title and title not in titles:
                titles.append(title)
        trace.append({
            "agent": "Agricultural Knowledge RAG",
            "action": f"Retrieved {len(docs)} indexed evidence chunk(s)" + (f" from {', '.join(titles[:3])}" if titles else ""),
            "status": "complete",
        })
        if not out.get("sources"):
            out["sources"] = _source_objects({}, {}, knowledge)
    elif retrieval == "approved_source_registry_fallback":
        trace.append({
            "agent": "Agricultural Knowledge RAG",
            "action": "No indexed evidence match was returned; only approved source pointers were available",
            "status": "watch",
        })
    elif retrieval != "not_requested":
        trace.append({
            "agent": "Agricultural Knowledge RAG",
            "action": f"Knowledge retrieval status: {retrieval}",
            "status": "watch",
        })
    out["rag"] = {
        "retrieval": retrieval,
        "document_count": len(docs),
        "evidence_quality": knowledge.get("evidence_quality") or {},
        "titles": list(dict.fromkeys(str(d.get("title") or "") for d in docs if d.get("title")))[:5],
    }
    return out


def _simple_chat(question: str, trusted: dict[str, Any], history: list[dict[str, str]], memory: dict[str, Any], knowledge: dict[str, Any] | None = None) -> dict[str, Any]:
    client = get_gemini_client()
    if client is None:
        return _simple_demo(question, history, memory, str(trusted.get("language") or "English"))
    knowledge = knowledge or {"documents": [], "retrieval": "not_requested"}
    bundle = {
        "trusted_context": {k: trusted.get(k) for k in ("language", "crop", "stage", "location", "context_scope")},
        "conversation_memory": memory,
        "recent_history": history[-18:],
        "approved_knowledge": knowledge,
    }
    grounding_banner = ""
    if knowledge.get("retrieval") == "hybrid_pgvector_fts" and knowledge.get("documents"):
        grounding_banner = (
            "\nRAG_GROUNDING_STATUS: INDEXED_EVIDENCE_AVAILABLE. "
            "The approved_knowledge.documents array below contains retrieved excerpts from the indexed knowledge base. "
            "Use those excerpts and do not claim that the indexed source is unavailable.\n"
        )
    prompt = SIMPLE_CHAT_PROMPT + grounding_banner + "\nCURRENT_USER_MESSAGE: " + question + "\nCONTEXT: " + json.dumps(bundle, default=str, ensure_ascii=False)
    try:
        response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            text = text[4:].strip() if text.lower().startswith("json") else text
        out = json.loads(text)
        out.setdefault("response_type", "answer")
        out.setdefault("summary", "Continue the conversation.")
        out.setdefault("recommended_action", "Continue the conversation")
        out.setdefault("why", "Simple Chat used conversation context without live decision tools.")
        out.setdefault("confidence", 0.78)
        out.setdefault("alternatives", [])
        out.setdefault("do_not_do", [])
        out.setdefault("sources", [])
        if not out.get("sources") and knowledge.get("retrieval") == "hybrid_pgvector_fts":
            out["sources"] = _source_objects({}, {}, knowledge)
        out.setdefault("confirmation_required", False)
        out.setdefault("follow_up", "Ask another question whenever you are ready.")
        out.setdefault("risk_level", "low")
        out.setdefault("counterfactual", "A live or consequential farm question may need Decision Support.")
        out.setdefault("agent_trace", [])
        out.setdefault("suggested_actions", [])
        out.setdefault("memory_patch", {})
        out.setdefault("report_ready", False)
        out.setdefault("auto_generate_report", False)
        out["provider"] = "gemini"
        out["model"] = settings.GEMINI_MODEL
        out = _attach_simple_rag_diagnostics(out, knowledge)
        return out
    except Exception as exc:
        out = _simple_demo(question, history, memory, str(trusted.get("language") or "English"))
        out["provider"] = "deterministic-simple-fallback"
        out["provider_error"] = str(exc)
        out = _attach_simple_rag_diagnostics(out, knowledge)
        return out


def _decision_tool_plan(route: RouteDecision, question: str) -> dict[str, bool]:
    """Choose only the evidence tools that materially help this Decision Support turn."""
    q = (question or "").lower()
    market = route.intent == "market_decision"
    weather = (not market) and (
        route.intent in {"weather_decision", "input_safety_decision", "crop_health_decision", "time_sensitive_farm_decision", "field_decision"}
        or any(x in q for x in ("weather", "rain", "forecast", "wind", "temperature", "humidity", "tomorrow", "today", "කාලගුණ", "වැසි", "වර්ෂාව", "අනාවැකි", "සුළං", "උෂ්ණත්ව", "ආර්ද්‍රතාව", "හෙට", "අද", "வானிலை", "காலநிலை", "மழை", "முன்னறிவிப்பு", "காற்று", "வெப்பநிலை", "ஈரப்பதம்", "நாளை", "இன்று"))
    )
    climate = (not market) and any(x in q for x in ("drought", "flood", "climate", "seasonal", "heat stress", "rainfall pattern", "baseline", "නියඟ", "ගංවතුර", "දේශගුණ", "උෂ්ණ ආතතිය", "වර්ෂා රටාව", "வறட்சி", "வெள்ளம்", "காலநிலை", "வெப்ப அழுத்தம்", "மழைப்பொழிவு முறை"))
    agronomy = (not market) and (
        route.intent in {"input_safety_decision", "crop_health_decision", "field_decision", "time_sensitive_farm_decision"}
        or any(x in q for x in ("crop", "paddy", "fertil", "pesticide", "fungicide", "insecticide", "herbicide", "disease", "symptom", "harvest", "plant", "බෝග", "වී", "පොහොර", "කෘමිනාශක", "දිලීරනාශක", "වල්නාශක", "රෝග", "ලක්ෂණ", "අස්වැන්න", "වගා", "பயிர்", "நெல்", "உரம்", "பூச்சிக்கொல்லி", "பூஞ்சைக்கொல்லி", "களைக்கொல்லி", "நோய்", "அறிகுறி", "அறுவடை", "சாகுபடி"))
    )
    water = (not market) and any(x in q for x in ("irrig", "water", "soil moisture", "waterlog", "drought", "drainage", "වාරි", "ජලය", "පස තෙතමනය", "ජලයෙන් යට", "නියඟ", "ජලාපවහන", "நீர்ப்பாசனம்", "தண்ணீர்", "மண் ஈரப்பதம்", "நீர்தேக்கம்", "வறட்சி", "வடிகால்"))
    return {
        "weather": weather,
        "climate": climate,
        "agronomy": agronomy,
        "water": water,
        "market": market,
        "safety": True,
    }


def _decision_demo(
    question: str,
    ctx: dict[str, Any],
    weather: dict,
    nasa: dict,
    knowledge: dict,
    water: dict,
    safety: dict,
    history: list[dict[str, str]],
    memory: dict[str, Any],
    *,
    route: RouteDecision,
    tool_plan: dict[str, bool],
    market: dict[str, Any],
) -> dict[str, Any]:
    lower = question.lower()
    lang = normalize_language(ctx.get("language") or detect_language(question).language)
    rain = _rain_probability(weather)
    fertilizer = any(k in lower for k in ["fertil", "urea", "nitrogen", "npk", "පොහොර", "යූරියා", "உரம்", "யூரியா"])

    if route.intent == "weather_decision" and weather.get("live"):
        current = weather.get("current") or {}
        temp = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        precip = current.get("precipitation")
        location = ctx.get("location") or "the resolved location"
        if lang == "Sinhala":
            action = f"{location} සඳහා දැනට උෂ්ණත්වය {temp if temp is not None else '—'}°C, ආර්ද්‍රතාව {humidity if humidity is not None else '—'}%, සුළං වේගය {wind if wind is not None else '—'} km/h සහ වර්ෂාපතනය {precip if precip is not None else '—'} mm ලෙස Open-Meteo දත්ත පෙන්වයි."
            why = "මෙය වත්මන් සම්බන්ධීකරණ අනුව ලබාගත් සජීවී කාලගුණ දත්ත මත පදනම් වේ. ක්ෂේත්‍ර ක්‍රියාවක් කිරීමට පෙර ඉදිරි දින අනාවැකියද බලන්න."
        elif lang == "Tamil":
            action = f"{location} பகுதியில் தற்போது வெப்பநிலை {temp if temp is not None else '—'}°C, ஈரப்பதம் {humidity if humidity is not None else '—'}%, காற்றின் வேகம் {wind if wind is not None else '—'} km/h மற்றும் மழைப்பொழிவு {precip if precip is not None else '—'} mm என Open-Meteo தரவு காட்டுகிறது."
            why = "இது தீர்மானிக்கப்பட்ட இருப்பிடத்தின் நேரடி வானிலைத் தரவை அடிப்படையாகக் கொண்டது. வயல் நடவடிக்கைக்கு முன் அடுத்த நாட்களின் முன்னறிவிப்பையும் சரிபார்க்கவும்."
        else:
            action = f"For {location}, Open-Meteo currently reports about {temp if temp is not None else '—'}°C, {humidity if humidity is not None else '—'}% humidity, wind {wind if wind is not None else '—'} km/h and precipitation {precip if precip is not None else '—'} mm."
            why = "This uses live coordinate-based weather evidence for the resolved location. Check the next-day forecast as well before a weather-sensitive field operation."
        level, conf, confirm = "low", 0.92, False
    elif route.intent == "market_decision":
        channels = [x.get("channel", "") for x in (market.get("channels") or [])[:6] if x.get("channel")]
        asks_price = any(x in lower for x in ("price", "rate", "how much", "මිල", "කීයද", "விலை", "எவ்வளவு"))
        if lang == "Sinhala":
            if asks_price:
                action = "විකුණුම් මිල තීරණය කිරීමට පෙර වත්මන් ගැනුම්කරුවන්ගෙන් quotations ලබාගන්න. මෙම local build එකට තවම සත්‍යාපිත live market-price feed එකක් සම්බන්ධ කර නැහැ."
                why = "MihiMura අලෙවි නාලිකා හඳුනාගත හැකි නමුත් සජීවී සත්‍යාපිත මිල දත්ත නොමැති විට අද බෝග මිලක් හිතාගෙන ප්‍රකාශ නොකරයි."
            else:
                action = "අස්වැන්න විකිණීමට පෙර අදාළ අලෙවි නාලිකා කිහිපයක වත්මන් quotations සසඳන්න."
                why = "සලකා බැලිය හැකි නාලිකා: " + "; ".join(channels) + ". නිශ්චිත ගැනුම්කරුවන් සහ මිල අස්වැන්නට ආසන්නව නැවත තහවුරු කළ යුතුයි."
        elif lang == "Tamil":
            if asks_price:
                action = "விற்பனை விலையை நிர்ணயிக்கும் முன் தற்போதைய வாங்குபவர் quotations-ஐ பெறவும். இந்த local build-ல் இன்னும் சரிபார்க்கப்பட்ட live market-price feed இணைக்கப்படவில்லை."
                why = "MihiMura விற்பனை வழிகளை அடையாளம் காண முடியும்; ஆனால் சரிபார்க்கப்பட்ட நேரடி விலை feed இல்லாதபோது இன்றைய பயிர் விலையை உருவாக்காது."
            else:
                action = "அறுவடையை விற்கும் முன் தொடர்புடைய பல விற்பனை வழிகளின் தற்போதைய quotations-ஐ ஒப்பிடவும்."
                why = "பரிசீலிக்கக்கூடிய வழிகள்: " + "; ".join(channels) + ". குறிப்பிட்ட வாங்குபவர்களும் விலைகளும் விற்பனைக்கு அருகில் மீண்டும் சரிபார்க்கப்பட வேண்டும்."
        else:
            if asks_price:
                action = "Use fresh buyer quotations before setting a selling price; this local build does not yet have a verified live market-price feed."
                why = "MihiMura can identify selling-channel categories, but it must not invent a current crop price when no live verified price connector was checked."
            else:
                action = "Compare current quotations across relevant selling channels before committing the harvest."
                why = "Available channel categories include: " + "; ".join(channels) + ". Specific buyers and prices must be verified close to sale."
        level, conf, confirm = "watch", 0.90, False
    elif fertilizer and rain >= 60:
        if lang == "Sinhala":
            action = "වැසි අවදානම වැඩි නිසා විවෘත පොහොර යෙදීම තාවකාලිකව කල් දමා, අඩු වැසි කවුළුවක් ලැබෙන විට වත්මන් අනුමත බෝග උපදෙස් සමඟ නැවත පරීක්ෂා කරන්න."
            why = f"හෙට සඳහා අනාවැකි වැසි සම්භාවිතාව සම්භාව්‍යයෙන් {rain:.0f}% පමණයි. එය runoff හෝ nutrient-loss අවදානම වැඩි කළ හැක. නිශ්චිත පොහොර rate එක මෙහි හිතාගෙන නිර්මාණය කරන්නේ නැහැ."
        elif lang == "Tamil":
            action = "மழை அபாயம் அதிகமாக இருப்பதால் வெளிப்புற உரப் பயன்பாட்டை தற்காலிகமாக ஒத்திவைத்து, குறைந்த மழை நேரத்தில் தற்போதைய அங்கீகரிக்கப்பட்ட பயிர் வழிகாட்டுதலுடன் மீண்டும் சரிபார்க்கவும்."
            why = f"நாளைய முன்னறிவிப்பு மழை சாத்தியம் சுமார் {rain:.0f}%. இது runoff அல்லது nutrient-loss அபாயத்தை அதிகரிக்கலாம். துல்லியமான உர அளவு இங்கே உருவாக்கப்படாது."
        else:
            action = "Delay the exposed fertilizer task and re-check the next lower-rain operating window against the current approved crop protocol."
            why = f"The next-day forecast rain probability is about {rain:.0f}% for the resolved location, which can increase runoff or nutrient-loss risk. The exact application rate is intentionally not generated."
        level, conf, confirm = "action", 0.88, True
    elif any(k in lower for k in ["pesticide", "fungicide", "insecticide", "dose", "rate", "කෘමිනාශක", "දිලීරනාශක", "මාත්‍රාව", "பூச்சிக்கொல்லி", "பூஞ்சைக்கொல்லி", "அளவு"]):
        if lang == "Sinhala":
            action = "මෙම chat එක පමණක් භාවිතා කර රසායනිකයක් හෝ dose එකක් තෝරා නොගන්න. බෝගය, ඉලක්ක රෝග/පළිබෝධය සහ වත්මන් අනුමත label/protocol එක තහවුරු කරන්න; සැකයක් තිබේ නම් විශේෂඥයෙකු වෙත යොමු කරන්න."
            why = "මෙය rate/treatment-sensitive ඉල්ලීමක් නිසා model explanation එකට පෙර MihiMura deterministic safety gate එක ක්‍රියාත්මක කරයි."
        elif lang == "Tamil":
            action = "இந்த chat மட்டும் வைத்து chemical அல்லது dose-ஐ தேர்வு செய்ய வேண்டாம். பயிர், இலக்கு பிரச்சினை மற்றும் தற்போதைய அங்கீகரிக்கப்பட்ட label/protocol-ஐ உறுதிப்படுத்தவும்; சந்தேகம் இருந்தால் நிபுணரிடம் escalte செய்யவும்."
            why = "இது rate/treatment-sensitive கோரிக்கை என்பதால் model விளக்கத்திற்கு முன் MihiMura deterministic safety gate-ஐ பயன்படுத்துகிறது."
        else:
            action = "Do not select a chemical or dose from this chat alone. Confirm the crop, target problem and current approved label/protocol, and escalate if the condition is uncertain."
            why = "This request is rate- or treatment-sensitive, so MihiMura applies a deterministic safety gate before any model explanation."
        level, conf, confirm = "action", 0.94, True
    elif route.intent == "weather_decision" and not weather.get("live"):
        if lang == "Sinhala":
            action = "සජීවී කාලගුණ තීරණයක් සඳහා නිවැරදි ස්ථානය/coordinates තහවුරු කර නැවත උත්සාහ කරන්න."
            why = "Decision Support වත්මන් කාලගුණ API දත්ත සාර්ථකව ලැබී නැති විට සජීවී කාලගුණය පරීක්ෂා කළා යැයි පෙන්වන්නේ නැහැ."
        elif lang == "Tamil":
            action = "நேரடி வானிலை முடிவுக்கு சரியான இடம்/coordinates-ஐ உறுதிப்படுத்தி மீண்டும் முயற்சிக்கவும்."
            why = "தற்போதைய வானிலை API தரவு வெற்றிகரமாக கிடைக்காதபோது Decision Support நேரடி வானிலை சரிபார்க்கப்பட்டது என்று கூறாது."
        else:
            action = "Confirm the farm/location coordinates and retry before treating this as a live weather decision."
            why = "Decision Support will not pretend to have checked current weather when the live weather API did not return usable data."
        level, conf, confirm = "watch", 0.96, False
    else:
        if lang == "Sinhala":
            action = "ක්ෂේත්‍ර ක්‍රියාව වෙනස් කිරීමට පෙර වත්මන් farm/scenario evidence භාවිතා කරන්න."
            why = "Decision Support මෙම intent එකට අදාළ ලෙස තෝරාගත් evidence tools සහ සක්‍රීය සංවාද/farm context පමණක් භාවිතා කළා."
        elif lang == "Tamil":
            action = "வயல் நடவடிக்கையை மாற்றும் முன் தற்போதைய farm/scenario evidence-ஐ பயன்படுத்தவும்."
            why = "Decision Support இந்த intent-க்கு தேர்ந்தெடுக்கப்பட்ட evidence tools மற்றும் செயலில் உள்ள conversation/farm context-ஐ மட்டுமே பயன்படுத்தியது."
        else:
            action = "Use the current farm/scenario evidence before changing the field operation."
            why = "Decision Support used only the evidence tools selected for this intent, together with the active conversation and farm context."
        level, conf, confirm = "watch", 0.81, False

    sources = _source_objects(weather, nasa, knowledge)
    if tool_plan.get("market"):
        sources.append({"name": "MihiMura market-channel registry", "freshness": "local registry; no live price feed connected"})

    trace = [
        {"agent": "Intent Router", "action": f"Selected Decision Support for {route.intent}", "status": "complete"},
        {"agent": "Conversation Memory", "action": f"Loaded {len(history)} recent turn(s) plus structured working memory", "status": "complete"},
        {"agent": "Farmer Context & Memory", "action": f"Resolved {ctx.get('context_scope', 'general')} context with conversation precedence", "status": "complete"},
    ]
    if tool_plan.get("weather"):
        trace.append({"agent": "Micro-Climate Prediction", "action": "Retrieved current coordinate-based forecast evidence when coordinates were available", "status": "complete"})
    if tool_plan.get("climate"):
        trace.append({"agent": "Climate Baseline", "action": "Retrieved NASA POWER baseline evidence", "status": "complete"})
    if tool_plan.get("water"):
        trace.append({"agent": "Soil & Water", "action": f"Built a water-context proxy; 3-day forecast rain {water.get('forecast_rain_3d_mm', '?')} mm", "status": "complete"})
    if tool_plan.get("agronomy"):
        trace.append({"agent": "Agronomy Knowledge", "action": f"Retrieved {len(knowledge.get('documents', []))} {knowledge.get('retrieval', 'knowledge')} evidence records", "status": "complete"})
    if tool_plan.get("market"):
        trace.append({"agent": "Market Intelligence", "action": f"Loaded {len(market.get('channels') or [])} selling-channel categories and live-data limitations", "status": "complete"})
    trace.append({"agent": "Intervention & Safety", "action": "Applied confirmation, rate-sensitive and no-invented-data guardrails", "status": "complete"})

    if lang == "Sinhala":
        alternatives = ["තවත් field observation එකක් සටහන් කරන්න", "evidence package එක කෘෂිකර්ම උපදේශකයෙකුගෙන් review කරගන්න"] if route.intent != "market_decision" else ["සමූපකාර/processor quotations සසඳන්න", "buyer offers farm project එකේ සටහන් කරන්න"]
        do_not = ["අනිශ්චිත image result එක confirmed diagnosis එකක් ලෙස සලකන්න එපා", "හිතාගෙන නිර්මාණය කළ chemical/fertilizer dose භාවිතා නොකරන්න"] if route.intent != "market_decision" else ["පරණ හෝ තහවුරු නොකළ මිල අද market price ලෙස පෙන්වන්න එපා", "grade, transport සහ payment terms නොසලකා offers සසඳන්න එපා"]
        follow_up = "මෙම සංවාදයේම දිගටම අහන්න; MihiMura සක්‍රීය scenario එක මතක තබා ගනී."
        suggested_actions = ["හේතුව පැහැදිලි කරන්න", "ඉදිරි දින 14 බලන්න"] if route.intent != "market_decision" else ["අලෙවි නාලිකා පෙන්වන්න", "buyer quotations සසඳන්න", "සම්පූර්ණ marketing report එකක් සාදන්න"]
    elif lang == "Tamil":
        alternatives = ["மேலும் ஒரு field observation பதிவு செய்யவும்", "evidence package-ஐ வேளாண்மை ஆலோசகரிடம் review செய்யவும்"] if route.intent != "market_decision" else ["கூட்டுறவு/processor quotations-ஐ ஒப்பிடவும்", "buyer offers-ஐ farm project-ல் பதிவு செய்யவும்"]
        do_not = ["தெளிவில்லாத image result-ஐ confirmed diagnosis என கருத வேண்டாம்", "உருவாக்கப்பட்ட chemical/fertilizer dose-ஐ பயன்படுத்த வேண்டாம்"] if route.intent != "market_decision" else ["பழைய அல்லது சரிபார்க்காத விலையை இன்றைய market price என காட்ட வேண்டாம்", "grade, transport மற்றும் payment terms-ஐ தவிர்த்து offers-ஐ ஒப்பிட வேண்டாம்"]
        follow_up = "இதே உரையாடலில் தொடரவும்; MihiMura செயலில் உள்ள scenario-ஐ நினைவில் வைத்திருக்கும்."
        suggested_actions = ["காரணத்தை விளக்கவும்", "அடுத்த 14 நாட்களை பார்க்கவும்"] if route.intent != "market_decision" else ["விற்பனை வழிகளை காட்டவும்", "buyer quotations ஒப்பிடவும்", "முழு marketing report உருவாக்கவும்"]
    else:
        alternatives = ["Record another field observation before treatment", "Ask an agricultural instructor to review the evidence package"] if route.intent != "market_decision" else ["Compare cooperative/processor quotations", "Record buyer offers in the farm project"]
        do_not = ["Do not treat an uncertain image result as a confirmed diagnosis", "Do not use an invented chemical or fertilizer dose"] if route.intent != "market_decision" else ["Do not present an old or unverified price as today's market price", "Do not compare offers without accounting for grade, transport and payment terms"]
        follow_up = "Continue in this same conversation; MihiMura will retain the active scenario."
        suggested_actions = ["Explain the reasoning", "Check next 14 days"] if route.intent != "market_decision" else ["Show selling channels", "Compare buyer quotations", "Create a full marketing report"]

    return enforce({
        "response_type": "confirmation_required" if confirm else "answer",
        "summary": action,
        "recommended_action": action,
        "why": why,
        "confidence": conf,
        "alternatives": alternatives,
        "do_not_do": do_not,
        "sources": sources,
        "confirmation_required": confirm,
        "follow_up": follow_up,
        "risk_level": level,
        "counterfactual": "Different field evidence, a corrected location, crop stage, forecast or current buyer quotation can change the recommendation.",
        "agent_trace": trace,
        "suggested_actions": suggested_actions,
        "clarification_fields": [],
        "memory_patch": {},
        "report_ready": False,
        "auto_generate_report": False,
        "provider": "deterministic-decision-demo",
        "model": "intent-tool-plan+policy",
        "tool_plan": tool_plan,
    }, safety)

def _normalize_decision(
    out: dict[str, Any],
    weather: dict,
    nasa: dict,
    knowledge: dict,
    safety: dict,
    ctx: dict[str, Any],
    history: list[dict[str, str]],
    *,
    route: RouteDecision,
    tool_plan: dict[str, bool],
    market: dict[str, Any],
) -> dict[str, Any]:
    lang = normalize_language(ctx.get("language") or "English")
    defaults = {
        "English": {
            "summary": "Review the evidence before acting.",
            "why": "The recommendation is based on the available project, conversation and selected evidence tools.",
            "follow": "Continue in this conversation or re-check after conditions change.",
            "counter": "Materially different field, forecast, protocol or market evidence can change this recommendation.",
        },
        "Sinhala": {
            "summary": "ක්‍රියා කිරීමට පෙර ලබාගත හැකි evidence සමාලෝචනය කරන්න.",
            "why": "නිර්දේශය ලබාගත හැකි project, conversation සහ තෝරාගත් evidence tools මත පදනම් වේ.",
            "follow": "මෙම සංවාදයේම දිගටම අහන්න හෝ තත්ත්වය වෙනස් වූ පසු නැවත පරීක්ෂා කරන්න.",
            "counter": "ක්ෂේත්‍ර තොරතුරු, forecast, protocol හෝ market evidence වෙනස් වුවහොත් නිර්දේශයද වෙනස් විය හැක.",
        },
        "Tamil": {
            "summary": "நடவடிக்கை எடுக்கும் முன் கிடைக்கக்கூடிய evidence-ஐ பரிசீலிக்கவும்.",
            "why": "பரிந்துரை கிடைக்கக்கூடிய project, conversation மற்றும் தேர்ந்தெடுக்கப்பட்ட evidence tools அடிப்படையில் உருவாக்கப்பட்டது.",
            "follow": "இதே உரையாடலில் தொடரவும் அல்லது நிலை மாறிய பின் மீண்டும் சரிபார்க்கவும்.",
            "counter": "வயல் தகவல், forecast, protocol அல்லது market evidence மாறினால் பரிந்துரையும் மாறலாம்.",
        },
    }[lang]
    out.setdefault("response_type", "answer")
    out.setdefault("summary", out.get("recommended_action") or defaults["summary"])
    out.setdefault("recommended_action", out["summary"])
    out.setdefault("why", defaults["why"])
    try:
        out["confidence"] = max(0.0, min(1.0, float(out.get("confidence", 0.5))))
    except Exception:
        out["confidence"] = 0.5
    out.setdefault("alternatives", [])
    out.setdefault("do_not_do", [])
    out.setdefault("follow_up", defaults["follow"])
    out.setdefault("risk_level", "watch")
    out.setdefault("counterfactual", defaults["counter"])
    out.setdefault("clarification_fields", [])
    out.setdefault("suggested_actions", [])
    out.setdefault("memory_patch", {})
    out.setdefault("report_ready", False)
    out.setdefault("auto_generate_report", False)
    out["tool_plan"] = tool_plan
    if not out.get("sources"):
        out["sources"] = _source_objects(weather, nasa, knowledge)
        if tool_plan.get("market"):
            out["sources"].append({"name": "MihiMura market-channel registry", "freshness": "local registry; no live price feed connected"})

    trace = out.setdefault("agent_trace", [])
    required = [
        ("Intent Router", f"Selected Decision Support for {route.intent}"),
        ("Conversation Memory", f"Loaded {len(history)} recent conversation turn(s) and structured memory"),
        ("Farmer Context & Memory", f"Trusted context scope: {ctx.get('context_scope', 'general')}"),
    ]
    if tool_plan.get("weather"):
        required.append(("Micro-Climate Prediction", "Current coordinate-based weather retrieved when coordinates were available"))
    if tool_plan.get("climate"):
        required.append(("Climate Baseline", "Recent NASA POWER baseline retrieved"))
    if tool_plan.get("water"):
        required.append(("Soil & Water", "Water-context proxy calculated"))
    if tool_plan.get("agronomy"):
        required.append(("Agronomy Knowledge", f"{knowledge.get('retrieval', 'knowledge')} evidence records: {len(knowledge.get('documents', []))}"))
    if tool_plan.get("market"):
        required.append(("Market Intelligence", f"Selling-channel records loaded: {len(market.get('channels') or [])}; live price feed status={market.get('price_feed','unknown')}"))
    required.append(("Intervention & Safety", "Deterministic safety policy applied after model output"))

    names = {x.get("agent") for x in trace if isinstance(x, dict)}
    for agent, action in required:
        if agent not in names:
            trace.append({"agent": agent, "action": action, "status": "complete"})
    return enforce(out, safety)

def _apply_route(out: dict[str, Any], route: RouteDecision) -> dict[str, Any]:
    out["requested_mode"] = route.requested_mode
    out["detected_mode"] = route.detected_mode
    out["effective_mode"] = route.detected_mode if route.requested_mode == "auto" else route.effective_mode
    out["detected_intent"] = route.intent
    out["mode_reason"] = route.reason
    out.setdefault("suggested_mode", None)
    return out


class OrchestratorAgent:
    def process_farmer_request(
        self,
        question: str,
        context: dict[str, Any],
        uid: str,
        *,
        history: list[dict[str, str]] | None = None,
        memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        history = history or []
        memory = memory or {}
        trusted = load_farmer_context(uid, context)

        route = route_request(
            question,
            str(context.get("interaction_mode") or "auto"),
            memory,
            allow_mode_mismatch=bool(context.get("allow_mode_mismatch")),
        )
        if route.should_switch:
            out = _mode_switch_response(route, question)
            out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            return out

        effective_mode = route.detected_mode if route.requested_mode == "auto" else route.effective_mode

        if effective_mode == "simple_chat":
            simple_knowledge: dict[str, Any] = {"documents": [], "retrieval": "not_requested"}
            if _simple_chat_should_retrieve(route, question, trusted):
                simple_knowledge = retrieve_approved_knowledge(
                    str(trusted.get("crop") or ""),
                    question,
                    language=str(trusted.get("language") or "English"),
                    location=str(trusted.get("location") or ""),
                )
            out = _simple_chat(question, trusted, history, memory, simple_knowledge)
            out = _apply_route(out, route)
            out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            return out

        if effective_mode == "full_report":
            out = _full_report_response(question, trusted, memory, history, route)
            out = _apply_route(out, route)
            out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            out.setdefault("provider", "report-workflow")
            out.setdefault("model", "planner+economics+market")
            return out

        # Phase 3: use a formal deterministic tool plan, execute only selected
        # evidence tools, track tool status/latency, and derive confidence from
        # actual evidence rather than the model's self-rating.
        formal_plan = build_tool_plan(route.intent, effective_mode, question, trusted)
        tool_plan = formal_plan.bool_map()
        tool_plan_detail = formal_plan.to_dict()
        lat = trusted.get("lat")
        lon = trusted.get("lon")
        tool_runtime: dict[str, Any] = {}

        weather: dict[str, Any] = {"status": "not_requested", "live": False, "current": {}, "daily": {}}
        if tool_plan.get("weather"):
            if lat is None or lon is None:
                weather = {"source": "Location required", "status": "unavailable", "live": False, "current": {}, "daily": {}, "error": "Resolved coordinates are required for live weather."}
                tool_runtime["weather"] = {"name": "weather", "status": "unavailable", "latency_ms": 0, "error": weather["error"]}
            else:
                run = execute_tool("weather", get_weather, float(lat), float(lon), 14)
                tool_runtime["weather"] = {k: v for k, v in run.items() if k != "data"}
                weather = run.get("data") or {"status": "unavailable", "live": False, "current": {}, "daily": {}}
        weather_decision = build_weather_decision_context(weather, question) if tool_plan.get("weather") else {"status": "not_requested", "decision_usable": False, "risk_flags": []}

        nasa: dict[str, Any] = {"status": "not_requested", "live": False, "period": {}, "parameters": {}}
        if tool_plan.get("climate"):
            if lat is None or lon is None:
                nasa = {"source": "Location required", "status": "unavailable", "live": False, "period": {}, "parameters": {}, "error": "Resolved coordinates are required for climate history."}
                tool_runtime["climate"] = {"name": "climate", "status": "unavailable", "latency_ms": 0, "error": nasa["error"]}
            else:
                run = execute_tool("climate", get_nasa_power, float(lat), float(lon), 30)
                tool_runtime["climate"] = {k: v for k, v in run.items() if k != "data"}
                nasa = run.get("data") or {"status": "unavailable", "live": False, "period": {}, "parameters": {}}

        knowledge: dict[str, Any] = {"documents": [], "retrieval": "not_requested"}
        if tool_plan.get("agronomy"):
            run = execute_tool(
                "agronomy",
                retrieve_approved_knowledge,
                str(trusted.get("crop") or ""),
                question,
                language=str(trusted.get("language") or "English"),
                location=str(trusted.get("location") or ""),
            )
            tool_runtime["agronomy"] = {k: v for k, v in run.items() if k != "data"}
            knowledge = run.get("data") or {"documents": [], "retrieval": "unavailable"}

        water: dict[str, Any] = {"status": "not_requested"}
        if tool_plan.get("water"):
            run = execute_tool(
                "water",
                calculate_water_budget,
                {**trusted, **{k: v for k, v in context.items() if k in {"soil_moisture"}}},
                weather,
            )
            tool_runtime["water"] = {k: v for k, v in run.items() if k != "data"}
            water = run.get("data") or {"status": "unavailable"}

        market: dict[str, Any] = {"status": "not_requested", "channels": [], "price_feed": "not_requested"}
        if tool_plan.get("market"):
            run = execute_tool("market", get_market_options, str(trusted.get("crop") or ""), str(trusted.get("location") or ""))
            tool_runtime["market"] = {k: v for k, v in run.items() if k != "data"}
            market = run.get("data") or {"status": "unavailable", "channels": [], "price_feed": "unavailable"}

        econ_facts = {**(memory.get("known_facts") or {}), **{k: trusted.get(k) for k in ("crop", "location") if trusted.get(k)}}
        economics: dict[str, Any] = {"status": "not_requested", "scenarios": []}
        if tool_plan.get("economics"):
            run = execute_tool("economics", estimate_cultivation_economics, econ_facts)
            tool_runtime["economics"] = {k: v for k, v in run.items() if k != "data"}
            economics = run.get("data") or {"status": "unavailable", "scenarios": []}

        resources: dict[str, Any] = {"status": "not_requested", "equipment": [], "tools": []}
        if tool_plan.get("resources"):
            run = execute_tool("resources", build_resource_plan, str(trusted.get("crop") or econ_facts.get("crop") or ""))
            tool_runtime["resources"] = {k: v for k, v in run.items() if k != "data"}
            resources = run.get("data") or {"status": "unavailable", "equipment": [], "tools": []}

        safety = precheck(question, trusted)
        evidence_quality = assess_evidence(
            plan=tool_plan_detail,
            context=trusted,
            weather_decision=weather_decision,
            knowledge=knowledge,
            market=market,
            economics=economics,
            water=water,
            safety=safety,
        )

        def finalize_phase3(out: dict[str, Any]) -> dict[str, Any]:
            out = validate_response_claims(out, evidence_quality, safety)
            out["tool_plan"] = tool_plan
            out["tool_plan_detail"] = tool_plan_detail
            out["tool_runtime"] = tool_runtime
            out["weather_decision"] = weather_decision
            out["economics"] = economics if tool_plan.get("economics") else {"status": "not_requested"}
            out["resource_plan"] = resources if tool_plan.get("resources") else {"status": "not_requested"}
            trace = out.setdefault("agent_trace", [])
            selected = [name for name, spec in (tool_plan_detail.get("tools") or {}).items() if spec.get("enabled")]
            trace.insert(1 if trace else 0, {
                "agent": "Tool Planner",
                "action": "Selected only: " + ", ".join(selected),
                "status": "complete",
            })
            for name, runtime in tool_runtime.items():
                trace.append({
                    "agent": f"Tool · {name}",
                    "action": f"status={runtime.get('status')} · latency={runtime.get('latency_ms', 0)} ms" + (f" · {runtime.get('error')}" if runtime.get("error") else ""),
                    "status": "complete" if runtime.get("status") == "success" else "watch",
                })
            return out

        client = get_gemini_client()
        if client is None:
            out = _decision_demo(
                question, trusted, weather, nasa, knowledge, water, safety, history, memory,
                route=route, tool_plan=tool_plan, market=market,
            )
            out = finalize_phase3(out)
            out = _apply_route(out, route)
            out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            return out

        evidence = {
            "trusted_context": trusted,
            "conversation_memory": memory,
            "recent_history": history[-18:],
            "tool_plan": tool_plan_detail,
            "tool_runtime": tool_runtime,
            "weather": weather if tool_plan.get("weather") else {"status": "not_requested"},
            "weather_decision": weather_decision,
            "climate_history": nasa if tool_plan.get("climate") else {"status": "not_requested"},
            "water_budget_proxy": water,
            "approved_knowledge": knowledge,
            "market_intelligence": market,
            "economics": economics,
            "resource_plan": resources,
            "evidence_quality": evidence_quality,
            "safety_precheck": safety,
            "route": route.to_dict(),
        }
        prompt = DECISION_SYSTEM_PROMPT + "\nCURRENT_USER_MESSAGE: " + question + "\nGROUNDING_BUNDLE: " + json.dumps(evidence, default=str, ensure_ascii=False)
        try:
            response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
            text = (response.text or "").strip()
            if text.startswith("```"):
                text = text.strip("`").strip()
                text = text[4:].strip() if text.lower().startswith("json") else text
            out = json.loads(text)
            out = _normalize_decision(out, weather, nasa, knowledge, safety, trusted, history, route=route, tool_plan=tool_plan, market=market)
            out = finalize_phase3(out)
            out = _apply_route(out, route)
            out["provider"] = "gemini"
            out["model"] = settings.GEMINI_MODEL
            out["generated_at"] = datetime.now(timezone.utc).isoformat()
            out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            return out
        except Exception as exc:
            out = _decision_demo(
                question, trusted, weather, nasa, knowledge, water, safety, history, memory,
                route=route, tool_plan=tool_plan, market=market,
            )
            out = finalize_phase3(out)
            out = _apply_route(out, route)
            out["provider"] = "deterministic-decision-fallback"
            out["provider_error"] = str(exc)
            out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            return out


orchestrator = OrchestratorAgent()
