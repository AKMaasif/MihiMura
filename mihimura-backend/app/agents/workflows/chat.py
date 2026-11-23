"""Simple Chat agent: conversation, explanations and general farming knowledge.

No live tools run here. When the question is about agriculture, the indexed
knowledge library is searched first so answers can cite real documents.
"""

from __future__ import annotations

from typing import Any

from app.agents import i18n
from app.agents.agronomy import retrieve_approved_knowledge
from app.agents.contracts import ChatOutput, finalize_response, step
from app.agents.evidence_sources import knowledge_sources
from app.agents.llm import LLMError, LLMUnavailable, generate_structured_with_model
from app.agents.prompts import CHAT_SYSTEM_PROMPT, PROMPT_VERSION
from app.agents.router import RouteDecision
from app.agents.safety import enforce, precheck, rates_supported, review_rates
from app.agents.turn import Turn
from app.services.language import detect_language, normalize_language

_AGRICULTURE_TERMS = (
    "agricultur", "agronom", "farm", "field", "crop", "paddy", "rice", "seed",
    "pest", "surveillance", "disease", "weed", "irrig", "fertil", "harvest",
    "manual", "guidance", "guideline", "source", "indexed", "recommendation",
    "ගොවි", "ගොවිපල", "බෝග", "කුඹුර", "වී", "බීජ", "පළිබෝධ", "නිරීක්ෂණ",
    "රෝග", "වල්", "වාරි", "පොහොර", "අස්වැන්න", "මූලාශ්‍ර", "මාර්ගෝපදේශ",
    "பண்ணை", "வயல்", "பயிர்", "நெல்", "விதை", "பூச்சி", "கண்காணிப்பு",
    "நோய்", "களை", "நீர்ப்பாசனம்", "உரம்", "அறுவடை", "மூலம்", "வழிகாட்ட",
)

# Deterministic confidence: chat answers are general knowledge, a little higher
# when grounded in retrieved library excerpts.
_CONFIDENCE_GROUNDED = 0.85
_CONFIDENCE_GENERAL = 0.72
_CONFIDENCE_FALLBACK = 0.75


def should_retrieve(route: RouteDecision, question: str, context: dict[str, Any]) -> bool:
    """Search the knowledge library for any agriculture question, however it is phrased."""
    if route.intent == "general_agriculture_question":
        return True
    q = (question or "").lower()
    return bool(str(context.get("crop") or "").strip() or any(term in q for term in _AGRICULTURE_TERMS))


def fallback_answer(question: str, history: list[dict[str, str]], memory: dict[str, Any], language: str = "English") -> dict[str, Any]:
    """Answer without a model (demo mode or provider failure), in the user's language."""
    lang = normalize_language(language or (memory.get("known_facts") or {}).get("language") or detect_language(question).language)
    text = i18n.bundle("chat_fallback", lang)
    lower = question.lower().strip()
    greeting = lower in {"hi", "hello", "hey"} or any(word in question for word in text["greeting_words"] if not word.isascii())
    return {
        "response_type": "answer",
        "summary": text["greeting"] if greeting else text["general"],
        "recommended_action": text["action"],
        "why": text["why"],
        "confidence": _CONFIDENCE_FALLBACK,
        "alternatives": [],
        "do_not_do": [],
        "sources": [],
        "confirmation_required": False,
        "follow_up": text["follow"],
        "risk_level": "low",
        "counterfactual": "A time-sensitive, farm-specific or report-level request may be better handled in another mode.",
        "agent_trace": [
            step("Intent Router", "Kept the request in Simple Chat"),
            step("Conversation Memory", f"Loaded {len(history)} recent turn(s) without invoking live farm tools"),
        ],
        "suggested_actions": list(text["suggested"]),
        "memory_patch": {},
        "report_ready": False,
        "auto_generate_report": False,
        "provider": "deterministic-simple-chat",
        "model": "conversation-policy-multilingual",
    }


def _attach_rag(out: dict[str, Any], knowledge: dict[str, Any]) -> dict[str, Any]:
    retrieval = str(knowledge.get("retrieval") or "not_requested")
    docs = knowledge.get("documents") or []
    titles = list(dict.fromkeys(str(d.get("title") or "") for d in docs if d.get("title")))
    trace = out.setdefault("agent_trace", [])
    if retrieval == "hybrid_pgvector_fts" and docs:
        detail = f" from {', '.join(titles[:3])}" if titles else ""
        trace.append(step("Agricultural Knowledge RAG", f"Retrieved {len(docs)} indexed evidence chunk(s){detail}"))
    elif retrieval == "approved_source_registry_fallback":
        trace.append(step("Agricultural Knowledge RAG", "No indexed evidence match was returned; only approved source pointers were available", "watch"))
    elif retrieval != "not_requested":
        trace.append(step("Agricultural Knowledge RAG", f"Knowledge retrieval status: {retrieval}", "watch"))
    # Drop model-authored citations. Registry rows stay, and they are labeled as pointers rather than retrieved text.
    out["sources"] = knowledge_sources(knowledge) if retrieval != "not_requested" else []
    out["rag"] = {
        "retrieval": retrieval,
        "document_count": len(docs),
        "evidence_quality": knowledge.get("evidence_quality") or {},
        "titles": titles[:5],
    }
    return out


def run_chat(turn: Turn) -> dict[str, Any]:
    knowledge: dict[str, Any] = {"documents": [], "retrieval": "not_requested"}
    if should_retrieve(turn.route, turn.question, turn.context):
        knowledge = retrieve_approved_knowledge(turn.crop, turn.question, language=turn.language, location=turn.location)

    grounded = knowledge.get("retrieval") == "hybrid_pgvector_fts" and bool(knowledge.get("documents"))
    payload = {
        "user_message": turn.question,
        "context": turn.model_context(),
        "conversation_memory": turn.model_memory(),
        "recent_history": turn.history[-18:],
        "knowledge": knowledge,
    }
    try:
        out, model_used = generate_structured_with_model(
            system=CHAT_SYSTEM_PROMPT, payload=payload, schema=ChatOutput, tier="fast", temperature=0.4
        )
    except LLMUnavailable:
        return _attach_rag(fallback_answer(turn.question, turn.history, turn.memory, turn.language), knowledge)
    except LLMError as exc:
        out = fallback_answer(turn.question, turn.history, turn.memory, turn.language)
        out["provider"] = "deterministic-simple-fallback"
        out["provider_error"] = str(exc)
        return _attach_rag(out, knowledge)

    out = finalize_response(
        {**out, "response_type": "answer", "confirmation_required": False},
        defaults={
            "follow_up": "Ask another question whenever you are ready.",
            "counterfactual": "A live or consequential farm question may need Decision Support.",
        },
    )
    safety = precheck(turn.question, turn.context)
    out["agent_trace"] = [
        step("Intent Router", f"Kept the request in Simple Chat ({turn.route.intent})"),
        step("Conversation Memory", f"Used {min(len(turn.history), 18)} recent turn(s) and saved scenario facts"),
    ]
    out = review_rates(out, knowledge, safety)
    consequential = bool(safety.get("hazardous_or_rate_sensitive") or (safety.get("consequential") and not grounded))
    if consequential:
        out = enforce(out, safety)
    if safety.get("hazardous_or_rate_sensitive") and not rates_supported(knowledge):
        out["expert_escalation_recommended"] = True
        if out.get("response_type") == "answer":
            out["response_type"] = "expert_escalation" if safety.get("expert_threshold") else "confirmation_required"
    out["confidence"] = _CONFIDENCE_GROUNDED if grounded else _CONFIDENCE_GENERAL
    if safety.get("hazardous_or_rate_sensitive") and not grounded:
        out["confidence"] = min(float(out["confidence"]), 0.4)
    if safety.get("hazardous_or_rate_sensitive") or safety.get("consequential"):
        out["agent_trace"].append(
            step(
                "Intervention & Safety",
                "Checked this chat answer for unsupported rates before it could be treated as a field instruction",
                "watch" if consequential else "complete",
            )
        )
    out["provider"] = "gemini"
    out["model"] = model_used
    out["prompt_version"] = PROMPT_VERSION
    return _attach_rag(out, knowledge)
