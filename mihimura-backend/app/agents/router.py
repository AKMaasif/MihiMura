from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

VALID_MODES = {"auto", "simple_chat", "decision_support", "full_report"}

MODE_LABELS = {
    "auto": "Auto",
    "simple_chat": "Simple Chat",
    "decision_support": "Decision Support",
    "full_report": "Full Report",
}


@dataclass(frozen=True)
class RouteDecision:
    requested_mode: str
    detected_mode: str
    effective_mode: str
    intent: str
    confidence: float
    reason: str
    should_switch: bool
    suggested_mode: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


GREETINGS = (
    # English
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening", "thanks", "thank you", "ok", "okay", "bye", "goodbye",
    # Sinhala
    "හායි", "හෙලෝ", "ආයුබෝවන්", "සුභ උදෑසනක්", "ස්තුතියි", "බොහොම ස්තුතියි", "හරි", "එහෙනම් හරි",
    # Tamil
    "ஹாய்", "ஹலோ", "வணக்கம்", "காலை வணக்கம்", "நன்றி", "மிக்க நன்றி", "சரி", "பை",
)

REPORT_PHRASES = (
    # English
    "full report", "complete report", "whole report", "detailed report", "comprehensive report", "cultivation report", "cultivation plan", "planting plan", "feasibility report", "business report", "business plan", "farm plan", "full plan", "complete plan", "end to end plan", "end-to-end plan", "profit analysis", "cost and profit", "cost & profit", "budget and profit", "marketing plan", "selling plan", "investment report", "financial report", "project report", "generate report", "make report",
    # Sinhala
    "සම්පූර්ණ වාර්තාව", "විස්තරාත්මක වාර්තාව", "පූර්ණ වාර්තාව", "වගා වාර්තාව", "වගා සැලැස්ම", "වගා කිරීමේ සැලැස්ම", "ව්‍යාපාර වාර්තාව", "ව්‍යාපාර සැලැස්ම", "ලාභ විශ්ලේෂණය", "වියදම් සහ ලාභ", "වියදම සහ ලාභ", "අලෙවි සැලැස්ම", "වෙළඳ සැලැස්ම", "වාර්තාවක් දෙන්න", "වාර්තාව දෙන්න", "වාර්තාව හදන්න",
    # Tamil
    "முழு அறிக்கை", "முழுமையான அறிக்கை", "விரிவான அறிக்கை", "சாகுபடி அறிக்கை", "சாகுபடி திட்டம்", "பயிரிடும் திட்டம்", "வணிக அறிக்கை", "வணிகத் திட்டம்", "லாப பகுப்பாய்வு", "செலவு மற்றும் லாபம்", "செலவும் லாபமும்", "சந்தைப்படுத்தல் திட்டம்", "விற்பனை திட்டம்", "அறிக்கை கொடு", "அறிக்கை தயாரி",
)

REPORT_TERMS = (
    # English
    "equipment", "tools required", "labour cost", "labor cost", "estimated cost", "approximate cost", "profit", "break even", "break-even", "revenue", "market channels", "where can i sell", "where to sell", "marketing platform", "marketplace", "buyer", "buyers",
    # Sinhala
    "උපකරණ", "මෙවලම්", "ශ්‍රම වියදම", "කම්කරු වියදම", "ඇස්තමේන්තු වියදම", "ආසන්න වියදම", "ලාභ", "ආදායම", "වෙළඳ නාලිකා", "කොහෙද විකුණන්නේ", "විකුණන්න පුළුවන්", "වෙළඳපොළ", "ගැනුම්කරු", "ගැනුම්කරුවන්",
    # Tamil
    "உபகரணங்கள்", "கருவிகள்", "தொழிலாளர் செலவு", "மதிப்பிடப்பட்ட செலவு", "சுமார் செலவு", "லாபம்", "வருவாய்", "சந்தை வழிகள்", "எங்கே விற்க", "விற்கலாம்", "சந்தை", "வாங்குபவர்", "வாங்குபவர்கள்",
)

MARKET_DECISION_PHRASES = (
    # English
    "where can i sell", "where to sell", "who can buy", "current price", "market price", "farm gate price", "farm-gate price", "selling price", "buyer", "buyers", "procurement", "selling channel", "marketplace", "market today",
    # Sinhala
    "කොහෙද විකුණන්නේ", "කොහෙට විකුණන්න", "කවුද ගන්නේ", "වත්මන් මිල", "දැන් මිල", "වෙළඳපොළ මිල", "ගොවිපල මිල", "විකුණුම් මිල", "ගැනුම්කරු", "ගැනුම්කරුවන්", "මිලදී ගැනීම", "විකුණුම් නාලිකාව", "අද වෙළඳපොළ",
    # Tamil
    "எங்கே விற்க", "யாருக்கு விற்க", "யார் வாங்குவார்", "தற்போதைய விலை", "இன்றைய விலை", "சந்தை விலை", "பண்ணை வாயில் விலை", "விற்பனை விலை", "வாங்குபவர்", "வாங்குபவர்கள்", "கொள்முதல்", "விற்பனை வழி", "இன்றைய சந்தை",
)

WEATHER_TERMS = (
    # English
    "weather", "forecast", "rain", "rainfall", "temperature", "humidity", "wind", "flood", "drought", "climate",
    # Sinhala
    "කාලගුණ", "කාලගුණය", "අනාවැකිය", "වැසි", "වර්ෂාව", "උෂ්ණත්වය", "ආර්ද්‍රතාව", "සුළං", "ගංවතුර", "නියඟ", "දේශගුණ",
    # Tamil
    "வானிலை", "காலநிலை", "முன்னறிவிப்பு", "மழை", "மழைப்பொழிவு", "வெப்பநிலை", "ஈரப்பதம்", "காற்று", "வெள்ளம்", "வறட்சி",
)

INPUT_TERMS = (
    # English
    "apply fertilizer", "apply fertiliser", "fertilizer", "fertiliser", "urea", "npk", "pesticide", "fungicide", "insecticide", "herbicide", "spray", "dose", "rate",
    # Sinhala
    "පොහොර", "යූරියා", "රසායන", "කෘමිනාශක", "දිලීරනාශක", "වල්නාශක", "ඉසින්න", "මාත්‍රාව", "ප්‍රමාණය",
    # Tamil
    "உரம்", "யூரியா", "வேதிப்பொருள்", "பூச்சிக்கொல்லி", "பூஞ்சைக்கொல்லி", "களைக்கொல்லி", "தெளிக்க", "அளவு", "மாத்திரை அளவு",
)

CROP_HEALTH_TERMS = (
    # English
    "disease", "symptom", "leaf spot", "wilting", "crop health", "leaf",
    # Sinhala
    "රෝග", "රෝගය", "ලක්ෂණ", "පත්‍ර", "කොළ", "පත්‍ර ලප", "වියළීම", "මැලවීම",
    # Tamil
    "நோய்", "அறிகுறி", "இலை", "இலைப்புள்ளி", "வாடுதல்", "பயிர் நலம்",
)

FIELD_ACTION_TERMS = (
    # English
    "irrigate", "irrigation", "water today", "safe to", "should i", "can i apply", "when should i", "what should i do", "harvest", "plant today", "plant tomorrow", "warning", "alert",
    # Sinhala
    "ජලය දෙන්න", "වාරි", "වාරි ජලය", "ආරක්ෂිතද", "කළ යුතුද", "දාන්න පුළුවන්ද", "මොකද කරන්න ඕන", "අස්වැන්න", "වගා කරන්න", "අනතුරු ඇඟවීම",
    # Tamil
    "நீர்ப்பாசனம்", "தண்ணீர் விட", "பாதுகாப்பானதா", "செய்யலாமா", "போடலாமா", "என்ன செய்ய வேண்டும்", "அறுவடை", "நடவு செய்ய", "எச்சரிக்கை",
)

TIME_MARKERS = (
    "today", "tomorrow", "this week", "next week", "next 7 days", "next 14 days", "current", "now",
    "අද", "හෙට", "මේ සතිය", "ඊළඟ සතිය", "දැන්", "වත්මන්",
    "இன்று", "நாளை", "இந்த வாரம்", "அடுத்த வாரம்", "இப்போது", "தற்போது",
)

SIMPLE_LEARNING_PHRASES = (
    # English
    "what is", "explain", "teach me", "difference between", "meaning of", "how does", "why does", "define", "example of", "summarize", "summarise",
    # Sinhala
    "මොකක්ද", "කියන්නේ මොකක්ද", "පැහැදිලි කරන්න", "විස්තර කරන්න", "උගන්වන්න", "වෙනස", "තේරුම", "කොහොමද වැඩ කරන්නේ", "ඇයි", "නිර්වචනය", "උදාහරණයක්", "සාරාංශ කරන්න",
    # Tamil
    "என்ன", "என்பது என்ன", "விளக்கவும்", "விளக்கு", "கற்றுக்கொடு", "வேறுபாடு", "அர்த்தம்", "எப்படி வேலை செய்கிறது", "ஏன்", "வரையறு", "உதாரணம்", "சுருக்கமாக",
)

FARM_CONTEXT_TERMS = (
    "farm", "crop", "field", "paddy", "rice", "water", "fertil", "harvest", "plant", "acre", "hectare",
    "ගොවිපල", "බෝග", "කුඹුර", "වී", "පොහොර", "අස්වැන්න", "වගා", "අක්කර", "හෙක්ටයාර්",
    "பண்ணை", "பயிர்", "வயல்", "நெல்", "உரம்", "அறுவடை", "சாகுபடி", "ஏக்கர்", "ஹெக்டேர்",
)


# Knowledge/RAG-oriented questions can be phrased without classic "what is/explain"
# wording. These terms keep source-grounded agriculture questions in Simple Chat
# while ensuring the RAG layer is actually invoked. Time-sensitive / consequential
# terms are handled earlier by the Decision Support rules above.
KNOWLEDGE_QUERY_TERMS = (
    # English
    "according to", "indexed knowledge", "indexed guidance", "available source",
    "available sources", "show the source", "tell me the document", "document name",
    "guidance", "guideline", "manual", "surveillance", "monitoring", "pest",
    "agronomy", "recommendation", "recommended practice", "best practice",
    # Sinhala
    "මූලාශ්‍ර", "මූලාශ්‍රය", "මාර්ගෝපදේශ", "මාර්ගෝපදේශය", "අත්පොත",
    "නිරීක්ෂණ", "අධීක්ෂණ", "පළිබෝධ", "නිර්දේශ", "නිර්දේශය", "වගා දැනුම",
    # Tamil
    "மூலம்", "ஆதாரம்", "வழிகாட்ட", "கையேடு", "கண்காணிப்பு", "பூச்சி",
    "வேளாண் அறிவு", "பரிந்துரை", "பரிந்துரைக்கப்பட்ட",
)


def _is_greeting(text: str) -> bool:
    stripped = re.sub(r"[\s!?.,…]+", " ", (text or "").strip().lower()).strip()
    return stripped in GREETINGS


def detect_mode(question: str, memory: dict[str, Any] | None = None) -> tuple[str, str, float, str]:
    """Return (mode, intent, confidence, reason) for English, Sinhala and Tamil.

    Routing stays deterministic for auditable high-confidence cases. The actual answer
    is still generated by the selected workflow/model. Native-script substring matching
    intentionally tolerates Sinhala/Tamil grammatical suffixes (e.g. ගාල්ලේ / காலியில்).
    """
    text = (question or "").strip().lower()
    memory = memory or {}
    active_intent = str(memory.get("active_intent") or "")

    if not text:
        if active_intent == "cultivation_report":
            return "full_report", "continue_report", 0.95, "The active conversation is a cultivation-report workflow."
        return "simple_chat", "conversation", 0.65, "No new workflow-specific request was detected."

    if _contains_any(text, REPORT_PHRASES):
        return "full_report", "cultivation_report", 0.99, "The request explicitly asks for a comprehensive planning/report workflow."

    if _contains_any(text, MARKET_DECISION_PHRASES):
        return "decision_support", "market_decision", 0.95, "The request depends on current buyer/price/channel evidence and belongs in Decision Support."

    if _contains_any(text, REPORT_TERMS) and _contains_any(text, FARM_CONTEXT_TERMS):
        return "full_report", "farm_business_analysis", 0.94, "The request needs a structured agronomic + financial/market analysis rather than a short answer."

    continuation_phrases = (
        "requested details", "here are the requested details", "continue report", "continue the report",
        "ඉල්ලූ විස්තර", "වාර්තාව දිගටම", "වාර්තාව ඉදිරියට",
        "கேட்ட விவரங்கள்", "அறிக்கையை தொடர", "அறிக்கை தொடர",
    )
    if active_intent == "cultivation_report" and _contains_any(text, continuation_phrases):
        return "full_report", "continue_report", 0.98, "The user is supplying details for the active Full Report workflow."

    if _contains_any(text, WEATHER_TERMS):
        return "decision_support", "weather_decision", 0.98, "The request asks about current/forecast weather or climate evidence and belongs in Decision Support."

    if _contains_any(text, INPUT_TERMS):
        return "decision_support", "input_safety_decision", 0.97, "The request concerns fertilizer/crop-protection input use and may change a real field action."

    if _contains_any(text, CROP_HEALTH_TERMS):
        return "decision_support", "crop_health_decision", 0.96, "The request concerns crop symptoms/health and benefits from farm-specific evidence and safety controls."

    if _contains_any(text, FIELD_ACTION_TERMS):
        return "decision_support", "field_decision", 0.95, "The request could change a real field operation and belongs in Decision Support."

    if _contains_any(text, TIME_MARKERS) and _contains_any(text, FARM_CONTEXT_TERMS):
        return "decision_support", "time_sensitive_farm_decision", 0.88, "The request is time-sensitive and farm-specific, so tool-grounded decision support is safer."

    if _is_greeting(text):
        return "simple_chat", "conversation", 0.99, "This is a conversational message and does not require live farm tools."

    # Source-grounded / manual / pest-surveillance questions often do not use
    # classic explanatory wording. Route them explicitly as agriculture knowledge
    # questions so Simple Chat invokes the RAG retriever.
    if _contains_any(text, KNOWLEDGE_QUERY_TERMS):
        return "simple_chat", "general_agriculture_question", 0.94, "The request asks for agricultural knowledge or source-grounded guidance and should use the indexed knowledge base."

    if _contains_any(text, SIMPLE_LEARNING_PHRASES):
        return "simple_chat", "general_agriculture_question", 0.86, "The request is explanatory and does not clearly require live farm evidence."

    # A non-time-sensitive farm/crop knowledge question should also be eligible for
    # RAG even if it is phrased conversationally rather than as 'what is/explain'.
    if _contains_any(text, FARM_CONTEXT_TERMS):
        return "simple_chat", "general_agriculture_question", 0.82, "The request is agriculture-specific and can benefit from indexed agronomy knowledge."

    if active_intent == "cultivation_report" and len(text.split()) <= 12:
        return "full_report", "report_follow_up", 0.72, "This short follow-up is likely connected to the active report workflow."

    return "simple_chat", "general_conversation", 0.62, "No high-confidence decision-support or full-report trigger was detected."


def route_request(
    question: str,
    requested_mode: str | None,
    memory: dict[str, Any] | None = None,
    *,
    allow_mode_mismatch: bool = False,
) -> RouteDecision:
    requested = (requested_mode or "auto").strip().lower()
    if requested not in VALID_MODES:
        requested = "auto"

    detected_mode, intent, confidence, reason = detect_mode(question, memory)
    effective = detected_mode if requested == "auto" else requested

    mismatch = requested != "auto" and requested != detected_mode and confidence >= 0.80
    should_switch = bool(mismatch and not allow_mode_mismatch)
    suggested = detected_mode if should_switch else None

    return RouteDecision(
        requested_mode=requested,
        detected_mode=detected_mode,
        effective_mode=effective,
        intent=intent,
        confidence=confidence,
        reason=reason,
        should_switch=should_switch,
        suggested_mode=suggested,
    )
