"""Intervention & Safety agent.

Three deterministic checks wrap every consequential answer:

1. ``precheck``  — before any model call: is the request hazardous, consequential
   or past the expert-review threshold? (English, Sinhala and Tamil terms.)
2. ``enforce``   — after the answer is built: add the required warnings,
   confirmation and escalation flags.
3. ``review_rates`` — after a *model* answer: remove any application rate/dose
   that is not backed by retrieved, approved evidence.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.contracts import step
from app.services.language import normalize_language

HAZARD_TERMS = {
    # English
    "pesticide", "insecticide", "fungicide", "herbicide", "chemical", "dose", "dosage", "rate", "spray",
    # Sinhala
    "කෘමිනාශක", "දිලීරනාශක", "වල්නාශක", "රසායන", "මාත්‍රාව", "ඉසින්න", "ඉසීම",
    # Tamil
    "பூச்சிக்கொல்லி", "பூஞ்சைக்கொல்லி", "களைக்கொல்லி", "வேதிப்பொருள்", "அளவு", "தெளிக்க", "தெளிப்பு",
}
CONSEQUENTIAL_TERMS = HAZARD_TERMS | {
    # English
    "fertilizer", "fertiliser", "urea", "irrigate", "irrigation", "order", "buy", "purchase",
    # Sinhala
    "පොහොර", "යූරියා", "වාරි", "ජලය දෙන්න", "ඇණවුම්", "මිලදී ගන්න",
    # Tamil
    "உரம்", "யூரியா", "நீர்ப்பாசனம்", "தண்ணீர் விட", "ஆர்டர்", "வாங்க",
}
EXPERT_TRIGGER_TERMS = {
    "dose", "dosage", "rate", "poison", "restricted",
    "මාත්‍රාව", "විෂ", "සීමාකළ",
    "அளவு", "நஞ்சு", "கட்டுப்படுத்தப்பட்ட",
}

LABEL_WARNING = {
    "English": "Do not use a pesticide/fertilizer dose or product choice unless it is verified against the current approved crop label/protocol.",
    "Sinhala": "වත්මන් අනුමත බෝග label/protocol එක සමඟ තහවුරු නොකළ pesticide/fertilizer dose එකක් හෝ product choice එකක් භාවිතා නොකරන්න.",
    "Tamil": "தற்போதைய அங்கீகரிக்கப்பட்ட பயிர் label/protocol உடன் சரிபார்க்காத pesticide/fertilizer dose அல்லது product choice-ஐ பயன்படுத்த வேண்டாம்.",
}

RATE_REMOVED = {
    "English": "[rate removed: check the approved product label]",
    "Sinhala": "[ප්‍රමාණය ඉවත් කළා: අනුමත label එක බලන්න]",
    "Tamil": "[அளவு நீக்கப்பட்டது: அங்கீகரிக்கப்பட்ட label-ஐ பார்க்கவும்]",
}

# A quantity followed by a per-area / per-volume unit, e.g. "50 kg per acre",
# "2.5 ml/L", "1 l/ha", "10g per tank", "25 kg/ac".
_RATE_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*(?:-|–|to)\s*\d+(?:[.,]\d+)?)?\s*"
    r"(?:kg|kilograms?|g|grams?|mg|ml|millilit(?:re|er)s?|l|lit(?:re|er)s?|lbs?|cc)\s*"
    r"(?:/|per\s+|an?\s+)"
    r"(?:acre|ac|ha|hectares?|l|lit(?:re|er)s?|tank|perch(?:es)?|plants?|m2|sq\.?\s?m|bushel)\b",
    re.IGNORECASE,
)
_RATE_FIELDS = ("summary", "recommended_action", "why", "follow_up", "counterfactual")
_RATE_LIST_FIELDS = ("alternatives", "do_not_do", "suggested_actions")


def precheck(question: str, context: dict[str, Any]) -> dict[str, Any]:
    q = question.lower()
    hazard = any(x in q for x in HAZARD_TERMS)
    consequential = any(x in q for x in CONSEQUENTIAL_TERMS)
    return {
        "hazardous_or_rate_sensitive": hazard,
        "consequential": consequential,
        "requires_confirmation": consequential,
        "expert_threshold": hazard and any(x in q for x in EXPERT_TRIGGER_TERMS),
        "language": normalize_language(context.get("language") or "English"),
        "rule": "No unsupported dose, guaranteed diagnosis, silent purchase or irreversible field action.",
    }


def enforce(result: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    result.setdefault("alternatives", [])
    result.setdefault("do_not_do", [])
    lang = normalize_language(check.get("language") or "English")
    if check.get("hazardous_or_rate_sensitive"):
        warning = LABEL_WARNING[lang]
        if warning not in result["do_not_do"]:
            result["do_not_do"].append(warning)
    if check.get("requires_confirmation"):
        result["confirmation_required"] = True
    if check.get("expert_threshold"):
        result["expert_escalation_recommended"] = True
        if result.get("risk_level") != "emergency":
            result["risk_level"] = "action"
    return result


def rates_supported(knowledge: dict[str, Any]) -> bool:
    """A rate may be shown only when approved excerpts were actually retrieved."""
    return knowledge.get("retrieval") == "hybrid_pgvector_fts" and bool(knowledge.get("documents"))


def review_rates(result: dict[str, Any], knowledge: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    """Strip application rates from a model answer when no approved evidence backs them."""
    if rates_supported(knowledge):
        return result
    lang = normalize_language(check.get("language") or "English")
    replacement = RATE_REMOVED[lang]
    removed = 0

    def scrub(text: str) -> str:
        nonlocal removed
        new_text, count = _RATE_PATTERN.subn(replacement, text)
        removed += count
        return new_text

    for key in _RATE_FIELDS:
        if isinstance(result.get(key), str):
            result[key] = scrub(result[key])
    for key in _RATE_LIST_FIELDS:
        if isinstance(result.get(key), list):
            result[key] = [scrub(x) if isinstance(x, str) else x for x in result[key]]

    if removed:
        result["expert_escalation_recommended"] = True
        warning = LABEL_WARNING[lang]
        do_not = result.setdefault("do_not_do", [])
        if warning not in do_not:
            do_not.append(warning)
        result.setdefault("agent_trace", []).append(
            step("Intervention & Safety", f"Removed {removed} application rate(s) not backed by retrieved approved evidence", "watch")
        )
    return result
