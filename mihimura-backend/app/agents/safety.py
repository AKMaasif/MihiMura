from __future__ import annotations
from typing import Any

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


def precheck(question: str, context: dict[str, Any]) -> dict[str, Any]:
    q = question.lower()
    hazard = any(x in q for x in HAZARD_TERMS)
    consequential = any(x in q for x in CONSEQUENTIAL_TERMS)
    lang = normalize_language(context.get("language") or "English")
    return {
        "hazardous_or_rate_sensitive": hazard,
        "consequential": consequential,
        "requires_confirmation": consequential,
        "expert_threshold": hazard and any(x in q for x in EXPERT_TRIGGER_TERMS),
        "language": lang,
        "rule": "No unsupported dose, guaranteed diagnosis, silent purchase or irreversible field action.",
    }


def enforce(result: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    result.setdefault("alternatives", [])
    result.setdefault("do_not_do", [])
    lang = normalize_language(check.get("language") or "English")
    if check.get("hazardous_or_rate_sensitive"):
        warning = {
            "English": "Do not use a pesticide/fertilizer dose or product choice unless it is verified against the current approved crop label/protocol.",
            "Sinhala": "වත්මන් අනුමත බෝග label/protocol එක සමඟ තහවුරු නොකළ pesticide/fertilizer dose එකක් හෝ product choice එකක් භාවිතා නොකරන්න.",
            "Tamil": "தற்போதைய அங்கீகரிக்கப்பட்ட பயிர் label/protocol உடன் சரிபார்க்காத pesticide/fertilizer dose அல்லது product choice-ஐ பயன்படுத்த வேண்டாம்.",
        }[lang]
        if warning not in result["do_not_do"]:
            result["do_not_do"].append(warning)
    if check.get("requires_confirmation"):
        result["confirmation_required"] = True
    if check.get("expert_threshold"):
        result["expert_escalation_recommended"] = True
        result["risk_level"] = "action" if result.get("risk_level") not in {"emergency"} else result["risk_level"]
    return result
