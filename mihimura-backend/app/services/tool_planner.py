from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSelection:
    enabled: bool
    reason: str
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolPlan:
    intent: str
    mode: str
    tools: dict[str, ToolSelection]
    requires_safety_validation: bool
    consequence_level: str

    def bool_map(self) -> dict[str, bool]:
        return {name: selection.enabled for name, selection in self.tools.items()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "mode": self.mode,
            "tools": {name: selection.to_dict() for name, selection in self.tools.items()},
            "requires_safety_validation": self.requires_safety_validation,
            "consequence_level": self.consequence_level,
        }


def _has(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def build_tool_plan(intent: str, mode: str, question: str, context: dict[str, Any] | None = None) -> ToolPlan:
    """Deterministically select the minimum useful tool set for a turn.

    The planner is intentionally rule based for auditability. The LLM reasons over
    tool outputs, but it does not decide which live evidence sources were checked.
    """
    context = context or {}
    q = (question or "").lower()

    is_market = intent == "market_decision" or _has(
        q,
        "market price", "selling price", "buyer", "buyers", "where can i sell", "where to sell",
        "වෙළඳපොළ මිල", "විකුණුම් මිල", "ගැනුම්කරු", "විකුණන්න",
        "சந்தை விலை", "விற்பனை விலை", "வாங்குபவர்", "எங்கே விற்க",
    )
    weather = (not is_market) and (
        intent in {"weather_decision", "input_safety_decision", "crop_health_decision", "time_sensitive_farm_decision", "field_decision"}
        or _has(q, "weather", "rain", "forecast", "wind", "temperature", "humidity", "today", "tomorrow",
                "කාලගුණ", "වැසි", "වර්ෂාව", "සුළං", "උෂ්ණත්ව", "ආර්ද්‍රතාව", "අද", "හෙට",
                "வானிலை", "மழை", "முன்னறிவிப்பு", "காற்று", "வெப்பநிலை", "ஈரப்பதம்", "இன்று", "நாளை")
    )
    climate = (not is_market) and _has(
        q, "climate", "drought", "flood", "seasonal", "heat stress", "rainfall pattern", "baseline",
        "දේශගුණ", "නියඟ", "ගංවතුර", "වර්ෂා රටාව", "උෂ්ණ ආතතිය",
        "காலநிலை", "வறட்சி", "வெள்ளம்", "மழைப்பொழிவு முறை", "வெப்ப அழுத்தம்",
    )
    agronomy = (not is_market) and (
        intent in {"input_safety_decision", "crop_health_decision", "field_decision", "time_sensitive_farm_decision"}
        or _has(q, "crop", "paddy", "rice", "fertil", "pesticide", "fungicide", "insecticide", "herbicide", "disease", "symptom", "harvest", "plant",
                "බෝග", "වී", "පොහොර", "කෘමිනාශක", "දිලීරනාශක", "වල්නාශක", "රෝග", "ලක්ෂණ", "අස්වැන්න", "වගා",
                "பயிர்", "நெல்", "உரம்", "பூச்சிக்கொல்லி", "பூஞ்சைக்கொல்லி", "களைக்கொல்லி", "நோய்", "அறிகுறி", "அறுவடை", "சாகுபடி")
    )
    water = (not is_market) and _has(
        q, "irrig", "water", "soil moisture", "waterlog", "drainage", "drought",
        "වාරි", "ජලය", "පස තෙතමනය", "ජලාපවහන", "නියඟ",
        "நீர்ப்பாசனம்", "தண்ணீர்", "மண் ஈரப்பதம்", "வடிகால்", "வறட்சி",
    )
    economics = mode == "full_report" or intent in {"farm_business_analysis", "cultivation_report"} or _has(
        q, "cost", "profit", "revenue", "roi", "break even", "break-even", "budget",
        "වියදම", "වියදම්", "ලාභ", "ආදායම",
        "செலவு", "லாபம்", "வருவாய்",
    )
    resources = mode == "full_report" or _has(
        q, "equipment", "machinery", "machine", "tools required", "resource plan",
        "උපකරණ", "යන්ත්‍ර", "මෙවලම්",
        "உபகரணங்கள்", "இயந்திர", "கருவிகள்",
    )

    consequence_level = "high" if intent in {"input_safety_decision", "field_decision", "time_sensitive_farm_decision"} else "medium" if mode == "decision_support" else "low"
    tools = {
        "farm_context": ToolSelection(True, "Resolve user, conversation and selected farm/project context.", required=True),
        "weather": ToolSelection(weather, "Current/forecast weather materially affects this request." if weather else "No current weather claim is needed.", required=weather and mode == "decision_support"),
        "climate": ToolSelection(climate, "Historical climate baseline is relevant to the requested risk/seasonal analysis." if climate else "No climate-baseline analysis requested."),
        "agronomy": ToolSelection(agronomy, "Agronomic evidence is required for the field/crop question." if agronomy else "No crop-specific evidence retrieval required."),
        "water": ToolSelection(water, "Water/soil-moisture context is directly relevant." if water else "No water-balance decision requested."),
        "market": ToolSelection(is_market or mode == "full_report", "Buyer/channel evidence is relevant to this request." if (is_market or mode == "full_report") else "No market evidence requested.", required=is_market),
        "economics": ToolSelection(economics, "Deterministic cost/revenue/profit calculations are relevant." if economics else "No financial calculation requested."),
        "resources": ToolSelection(resources, "Equipment/tools/labour planning is relevant." if resources else "No resource plan requested."),
        "safety": ToolSelection(mode == "decision_support" or consequence_level != "low", "Consequential recommendations require deterministic safety validation.", required=mode == "decision_support"),
    }
    return ToolPlan(
        intent=intent,
        mode=mode,
        tools=tools,
        requires_safety_validation=tools["safety"].enabled,
        consequence_level=consequence_level,
    )
