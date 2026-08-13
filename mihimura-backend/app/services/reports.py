from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from pydantic import BaseModel, Field

from app.agents.agronomy import retrieve_approved_knowledge
from app.core.ai import get_gemini_client
from app.core.config import settings
from app.db import audit, now_iso
from app.services.climate_history import get_nasa_power
from app.services.conversations import get_memory, report_missing_fields, require_conversation
from app.services.economics import estimate_cultivation_economics
from app.services.market_intelligence import get_market_options
from app.services.resource_planning import build_resource_plan
from app.services.weather import get_weather
from app.services.language import normalize_language, detect_language
from app.supabase_client import service_client

REPORT_SYSTEM = """You are MihiMura Report Composer. Create a comprehensive, practical cultivation + farm-business planning report for a Sri Lankan farmer.

The user asked for a FULL REPORT, so do not collapse the result into a short recommendation. Use the supplied evidence, transparent calculations and explicit assumptions.

LANGUAGE
- TARGET_LANGUAGE will be English, Sinhala or Tamil.
- Write ALL farmer-facing report content in TARGET_LANGUAGE: title, executive summary, section headings, paragraphs, bullets, table column labels/cells, assumptions, limitations and next actions.
- Keep exact source names, scientific names, product/active-ingredient names, dates, numbers and units unchanged when translation could reduce precision.
- Do not switch back to English merely because the evidence bundle uses English machine keys.

SAFETY / TRUTH RULES
- Never invent live prices, official alerts, laboratory results, pesticide/fertilizer rates, product-label claims or guaranteed yield/profit.
- Cost/yield/selling-price numbers in economics are configurable planning scenarios, NOT live market quotations. Label them clearly.
- If a chemical, fertilizer rate, interval or product selection requires an official protocol/label and the supplied evidence does not contain that exact verified instruction, explain what must be verified instead of fabricating it.
- Separate USER-PROVIDED FACTS, VERIFIED/TOOL DATA, PLANNING ESTIMATES and ASSUMPTIONS.
- Season, irrigation, variety or planting date may be unknown. Do NOT refuse the report; provide scenario guidance and mark the unknowns for refinement.
- approved_knowledge may contain hybrid pgvector/FTS RAG excerpts. Use only claims supported by those excerpts, name the authority/document in the relevant section, and preserve page/location labels where available.
- If approved_knowledge.retrieval is approved_source_registry_fallback, those records are links/pointers only; do not imply that their detailed contents were retrieved or verified in this run.
- Give higher evidentiary weight to lower authority_tier values (Tier 1 official, Tier 2 university/research, Tier 3 verified industry, Tier 4 general curated).

REPORT COVERAGE
Include all relevant sections, normally:
1 Executive summary
2 Scenario and assumptions
3 Location / seasonal suitability
4 Crop and variety decision
5 Land preparation
6 Equipment and machinery
7 Hand tools / PPE
8 Seed / establishment
9 Water and irrigation management
10 Nutrient/fertilizer planning
11 Weed management
12 Pest management
13 Disease monitoring/management
14 Chemicals / crop-protection decision protocol (verified-only; no invented rates)
15 Labour plan
16 Crop-stage calendar and tasks
17 Weather/climate/disaster risks
18 Input/resource checklist
19 Cost breakdown
20 Yield/revenue/profit scenarios
21 Break-even analysis
22 Harvest plan
23 Post-harvest handling and quality
24 Storage/transport/logistics
25 Marketing and buyer channels/platforms
26 Selling strategy
27 30/60/90-day actions or stage-based action plan
28 Main risks and mitigations
29 Sources/evidence/verification items
30 Limitations and expert/official checks

OUTPUT REQUIREMENTS
- The API enforces the response structure with a JSON schema; focus on complete, accurate content rather than restating or explaining the schema.
- Populate a stable English machine key for every section_key, while keeping every farmer-facing string in TARGET_LANGUAGE.
- Keep the report comprehensive: normally produce the full coverage above rather than collapsing it to a few sections.
- For a section without a useful table, return an empty table with empty columns and rows.
- Keep all financial values consistent with the supplied economics object.
"""


logger = logging.getLogger(__name__)


class ReportTablePayload(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class ReportSectionPayload(BaseModel):
    section_key: str
    heading: str
    paragraphs: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    table: ReportTablePayload = Field(default_factory=ReportTablePayload)


class ReportPayloadSchema(BaseModel):
    title: str
    executive_summary: str
    sections: list[ReportSectionPayload]
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ReportMetaTranslationPayload(BaseModel):
    title: str
    executive_summary: str
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ReportSectionBatchPayload(BaseModel):
    sections: list[ReportSectionPayload]


PDF_LABELS = {
    "English": {
        "executive_summary": "Executive summary", "crop": "Crop", "location": "Location", "area": "Area",
        "season": "Season", "water_source": "Water source", "generated": "Generated", "assumptions": "Assumptions",
        "limitations": "Limitations", "next_actions": "Recommended next actions", "notice": "Decision-support notice",
        "not_set": "Not set", "assumption_not_set": "Assumption / not set",
        "notice_text": "MihiMura supports agricultural decisions and does not impersonate a certified agronomist. Verify consequential rates, restricted products, official alerts, live prices and high-risk field actions against current authoritative guidance before execution.",
    },
    "Sinhala": {
        "executive_summary": "විධායක සාරාංශය", "crop": "බෝගය", "location": "ස්ථානය", "area": "භූමි ප්‍රමාණය",
        "season": "වගා කන්නය", "water_source": "ජල මූලාශ්‍රය", "generated": "සකස් කළ දිනය", "assumptions": "උපකල්පන",
        "limitations": "සීමාවන්", "next_actions": "නිර්දේශිත ඉදිරි පියවර", "notice": "තීරණ සහාය පිළිබඳ දැනුම්දීම",
        "not_set": "සපයා නැත", "assumption_not_set": "උපකල්පනය / සපයා නැත",
        "notice_text": "MihiMura කෘෂිකාර්මික තීරණ සඳහා සහාය දෙන පද්ධතියක් වන අතර සහතික කළ කෘෂි විශේෂඥයෙකු වෙනුවට ක්‍රියා නොකරයි. ප්‍රමාණ, සීමාකළ නිෂ්පාදන, නිල අනතුරු ඇඟවීම්, සජීවී මිල සහ ඉහළ අවදානම් ක්ෂේත්‍ර ක්‍රියාත්මක කිරීමට පෙර වත්මන් බලධාරී මාර්ගෝපදේශ සමඟ තහවුරු කරන්න.",
    },
    "Tamil": {
        "executive_summary": "நிர்வாகச் சுருக்கம்", "crop": "பயிர்", "location": "இடம்", "area": "நிலப்பரப்பு",
        "season": "பருவம்", "water_source": "நீர் மூலம்", "generated": "தயாரிக்கப்பட்ட நேரம்", "assumptions": "கருதுகோள்கள்",
        "limitations": "வரம்புகள்", "next_actions": "பரிந்துரைக்கப்பட்ட அடுத்த நடவடிக்கைகள்", "notice": "முடிவு ஆதரவு அறிவிப்பு",
        "not_set": "வழங்கப்படவில்லை", "assumption_not_set": "கருதுகோள் / வழங்கப்படவில்லை",
        "notice_text": "MihiMura வேளாண் முடிவுகளுக்கு ஆதரவளிக்கிறது; சான்றளிக்கப்பட்ட வேளாண் நிபுணரை மாற்றிப் பதிலாக செயல்படாது. முக்கியமான அளவுகள், கட்டுப்படுத்தப்பட்ட தயாரிப்புகள், அதிகாரப்பூர்வ எச்சரிக்கைகள், நேரடி விலைகள் மற்றும் உயர் ஆபத்து வயல் நடவடிக்கைகளை மேற்கொள்ளும் முன் தற்போதைய அதிகாரப்பூர்வ வழிகாட்டுதலுடன் சரிபார்க்கவும்.",
    },
}


def _pdf_labels(language: str) -> dict[str, str]:
    return PDF_LABELS[normalize_language(language)]


def _first_existing(paths: list[str | None]) -> str | None:
    for value in paths:
        if value and Path(value).exists():
            return str(Path(value))
    return None


def _register_pdf_fonts(language: str) -> tuple[str, str, bool]:
    """Return (regular_font_name, bold_font_name, shaping_enabled).

    English keeps ReportLab's built-in Helvetica. Sinhala/Tamil use a TrueType font
    with the relevant glyphs and ReportLab 4.4+ shaping. Paths can be overridden by
    environment variables for production containers.
    """
    language = normalize_language(language)
    if language == "English":
        return "Helvetica", "Helvetica-Bold", False

    if language == "Sinhala":
        regular_path = _first_existing([
            os.getenv("MIHIMURA_SINHALA_FONT_PATH"), os.getenv("MIHIMURA_UNICODE_FONT_PATH"),
            r"C:\Windows\Fonts\Nirmala.ttc",
            r"C:\Windows\Fonts\Nirmala.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansSinhala-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansSinhala-Regular.ttf",
        ])
        bold_path = _first_existing([
            os.getenv("MIHIMURA_SINHALA_BOLD_FONT_PATH"),
            r"C:\Windows\Fonts\NirmalaB.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansSinhala-SemiBold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansSinhala-Bold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansSinhala-SemiBold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansSinhala-Bold.ttf",
            regular_path,
        ])
        base_name = "MihiSinhala"
    else:
        regular_path = _first_existing([
            os.getenv("MIHIMURA_TAMIL_FONT_PATH"), os.getenv("MIHIMURA_UNICODE_FONT_PATH"),
            r"C:\Windows\Fonts\Nirmala.ttc",
            r"C:\Windows\Fonts\Nirmala.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansTamil-Regular.ttf",
        ])
        bold_path = _first_existing([
            os.getenv("MIHIMURA_TAMIL_BOLD_FONT_PATH"),
            r"C:\Windows\Fonts\NirmalaB.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansTamil-SemiBold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansTamil-SemiBold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansTamil-Bold.ttf",
            regular_path,
        ])
        base_name = "MihiTamil"

    if not regular_path:
        raise RuntimeError(
            f"A Unicode {language} TrueType font was not found. Install Noto Sans {language} or set the corresponding MIHIMURA_*_FONT_PATH environment variable."
        )
    regular_name = base_name
    bold_name = base_name + "Bold"
    if regular_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_name, regular_path))
    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, bold_path or regular_path))
    return regular_name, bold_name, True


def multilingual_pdf_runtime_status() -> dict[str, bool]:
    """Non-sensitive deployment diagnostic for native-language PDF support."""
    try:
        import uharfbuzz  # type: ignore  # noqa: F401
        harfbuzz = True
    except Exception:
        harfbuzz = False

    status: dict[str, bool] = {"harfbuzz": harfbuzz}
    for language in ("Sinhala", "Tamil"):
        try:
            _register_pdf_fonts(language)
            status[f"{language.lower()}_font"] = True
        except Exception:
            status[f"{language.lower()}_font"] = False
    status["ready"] = bool(status.get("sinhala_font") and status.get("tamil_font") and harfbuzz)
    return status


def _table(name: str):
    return service_client().table(name)


def _fmt_lkr(value: Any) -> str:
    try:
        return f"LKR {int(round(float(value))):,}"
    except Exception:
        return "Not available"


def _equipment_table(resources: dict[str, Any]) -> dict[str, Any]:
    return {
        "columns": ["Equipment / machinery", "Need", "Stage"],
        "rows": [[x.get("item", ""), x.get("need", ""), x.get("stage", "")] for x in resources.get("equipment", [])],
    }


def _inputs_table(resources: dict[str, Any]) -> dict[str, Any]:
    return {
        "columns": ["Input category", "Planning rule"],
        "rows": [[x.get("category", ""), x.get("guidance", "")] for x in resources.get("inputs", [])],
    }


def _cost_table(economics: dict[str, Any]) -> dict[str, Any]:
    return {
        "columns": ["Cost item", "Low", "Planning base", "High", "Note"],
        "rows": [
            [
                x.get("item", ""),
                _fmt_lkr(x.get("low_lkr")),
                _fmt_lkr(x.get("base_lkr")),
                _fmt_lkr(x.get("high_lkr")),
                x.get("note", ""),
            ]
            for x in economics.get("cost_items", [])
        ] + ([
            [
                "TOTAL",
                _fmt_lkr((economics.get("total_cost") or {}).get("low_lkr")),
                _fmt_lkr((economics.get("total_cost") or {}).get("base_lkr")),
                _fmt_lkr((economics.get("total_cost") or {}).get("high_lkr")),
                "Illustrative planning range; refresh with current local quotations.",
            ]
        ] if economics.get("cost_items") else []),
    }


def _profit_table(economics: dict[str, Any]) -> dict[str, Any]:
    return {
        "columns": ["Scenario", "Yield", "Selling price", "Revenue", "Cost", "Estimated profit"],
        "rows": [
            [
                x.get("name", ""),
                f"{x.get('yield_kg', '—')} kg",
                f"LKR {x.get('selling_price_lkr_per_kg', '—')}/kg",
                _fmt_lkr(x.get("revenue_lkr")),
                _fmt_lkr(x.get("cost_lkr")),
                _fmt_lkr(x.get("profit_lkr")),
            ]
            for x in economics.get("scenarios", [])
        ],
    }


def _market_table(market: dict[str, Any]) -> dict[str, Any]:
    return {
        "columns": ["Selling channel / platform", "Type", "How to use", "Verify before sale"],
        "rows": [
            [x.get("channel", ""), x.get("type", ""), x.get("how_to_use", ""), x.get("verification", "")]
            for x in market.get("channels", [])
        ],
    }


def _fallback_report(
    facts: dict[str, Any],
    weather: dict[str, Any],
    climate: dict[str, Any],
    knowledge: dict[str, Any],
    economics: dict[str, Any],
    market: dict[str, Any],
    resources: dict[str, Any],
) -> dict[str, Any]:
    crop = facts.get("crop", "Crop")
    location = facts.get("location", "Sri Lanka")
    area = f"{facts.get('area_value', '')} {facts.get('area_unit', '')}".strip()
    optional_unknowns = [x for x in ("season", "irrigation", "variety", "planting_date") if not facts.get(x)]
    base_scenario = next((x for x in economics.get("scenarios", []) if x.get("name") == "Planning base"), None)
    finance_summary = "A crop-specific cost/yield/price scenario is not configured yet."
    if base_scenario:
        finance_summary = (
            f"The configurable planning-base scenario estimates revenue around {_fmt_lkr(base_scenario.get('revenue_lkr'))}, "
            f"cost around {_fmt_lkr(base_scenario.get('cost_lkr'))}, and profit around {_fmt_lkr(base_scenario.get('profit_lkr'))}. "
            "These figures are illustrative, not current quotations, and must be replaced/refreshed with local prices before investment decisions."
        )

    knowledge_bullets = [
        f"{d.get('authority')}: {d.get('title')} — {d.get('scope')}"
        for d in knowledge.get("documents", [])[:6]
    ]

    sections: list[dict[str, Any]] = [
        {
            "heading": "1. Planning scenario and data status",
            "paragraphs": [
                f"Crop: {crop}. Location: {location}. Area: {area}. Season: {facts.get('season','not supplied')}. Water source: {facts.get('irrigation','not supplied')}. Variety: {facts.get('variety','not supplied')}. Expected planting date: {facts.get('planting_date','not supplied')}.",
                "Current-message and conversation facts take precedence over profile defaults. Unknown refinement details are treated as assumptions rather than blocking the report.",
            ],
            "bullets": [f"Optional details still open: {', '.join(optional_unknowns)}"] if optional_unknowns else ["Core and refinement details supplied."],
        },
        {
            "heading": "2. Executive cultivation strategy",
            "paragraphs": [
                f"Use a stage-based plan for {crop} in {location}: verify seasonal/water suitability, prepare the field, establish the crop with traceable seed/planting material, monitor water and crop condition, apply nutrients/crop protection only from current verified guidance, and plan harvest/marketing before maturity.",
                "The report is a planning framework. Field-specific rates and hazardous treatment decisions require current official/label evidence and may need an agricultural instructor/agronomist.",
            ],
            "bullets": ["Record actual planting date", "Track field observations and weather-sensitive tasks", "Capture costs and buyer quotations as they become available"],
        },
        {
            "heading": "3. Location, season and climate suitability",
            "paragraphs": [
                f"Weather evidence source for the resolved location: {weather.get('source','unavailable')}. Climate baseline source: {climate.get('source','unavailable')}. Re-check live conditions before weather-sensitive operations.",
                "If the season is not yet confirmed, compare the intended establishment window against water availability, rainfall outlook, field drainage and the chosen variety maturity period before fixing the calendar.",
            ],
            "bullets": ["Check drainage/flood exposure", "Check irrigation reliability or rainfed risk", "Use official emergency advisories when available"],
        },
        {
            "heading": "4. Variety, seed and establishment",
            "paragraphs": [
                "Choose a variety using season, maturity duration, water regime, disease/pest considerations, local extension guidance and intended buyer/quality requirements. Certified or otherwise verified seed/planting material should be preferred where applicable.",
                "The exact seed quantity and establishment method should be taken from current crop-specific official guidance when not already stored in the farm project.",
            ],
            "bullets": ["Confirm variety", "Confirm seed source/class", "Choose direct seeding/nursery-transplanting or crop-appropriate method", "Record actual establishment date"],
        },
        {
            "heading": "5. Land preparation",
            "paragraphs": [
                "Prepare the field to support uniform establishment, drainage/water control and safe machinery access. The exact operations depend on soil condition, previous crop, weed pressure and water regime.",
            ],
            "bullets": ["Inspect field access", "Repair bunds/drains where relevant", "Level the field appropriately", "Plan erosion/runoff controls", "Avoid unnecessary passes that increase cost or soil damage"],
        },
        {
            "heading": "6. Equipment and machinery",
            "paragraphs": ["Hire versus own should be decided from local availability, area, timing, transport and total seasonal cost."],
            "bullets": [],
            "table": _equipment_table(resources),
        },
        {
            "heading": "7. Hand tools, PPE and field support items",
            "paragraphs": ["Keep basic field tools ready and match PPE to the actual operation and product label."],
            "bullets": list(resources.get("tools", [])),
        },
        {
            "heading": "8. Water and irrigation management",
            "paragraphs": [
                f"Recorded water source: {facts.get('irrigation','not confirmed')}. If unknown, the report does not assume that irrigation is continuously available.",
                "Use actual field wetness/water depth as relevant, rainfall, drainage and crop stage rather than a fixed generic watering schedule.",
            ],
            "bullets": ["Record water source/reliability", "Check forecast before irrigation", "Inspect after heavy rain", "Avoid both prolonged unnecessary flooding and water stress where crop guidance advises otherwise"],
        },
        {
            "heading": "9. Fertilizer and nutrient planning",
            "paragraphs": [
                "Nutrient planning must follow the current crop/zone/establishment recommendation and available soil information. MihiMura will not fabricate a fertilizer rate when the exact current protocol is not present in verified evidence.",
                "Before a weather-exposed application, Decision Support should check rainfall/runoff risk and the current approved recommendation.",
            ],
            "bullets": ["Verify current official recommendation", "Confirm actual product nutrient analysis", "Record application date/material/quantity", "Re-check weather before application"],
        },
        {
            "heading": "10. Weed, pest, disease and chemical-input plan",
            "paragraphs": [
                "Use prevention, sanitation, crop/field monitoring and non-chemical options where practical. A chemical should be selected only after the target weed/pest/disease is sufficiently identified and a current approved label/protocol is available.",
                "Product name, active ingredient, dose/rate, interval, mixing, pre-harvest interval and PPE must come from a verified current source/label. If that evidence is not available, this report intentionally leaves the rate unspecified.",
            ],
            "bullets": [],
            "table": _inputs_table(resources),
        },
        {
            "heading": "11. Labour and operations plan",
            "paragraphs": ["Labour demand depends on mechanisation, field access, establishment method, weed pressure and harvest arrangement. Confirm local rates before final budgeting."],
            "bullets": list(resources.get("labour_operations", [])),
        },
        {
            "heading": "12. Crop-stage calendar",
            "paragraphs": ["Use a stage-based calendar when exact dates are not yet available. Once the actual establishment date and variety duration are confirmed, convert each stage into dated tasks."],
            "bullets": ["Pre-establishment: land/water/seed readiness", "Establishment: sow/transplant and stand check", "Vegetative: water/nutrient/weed monitoring", "Reproductive: protect flowering/grain/fruit formation and monitor weather risk", "Maturity: harvest-readiness and buyer/logistics confirmation", "Post-harvest: quality, storage, sale and season review"],
        },
        {
            "heading": "13. Cost breakdown",
            "paragraphs": [economics.get("data_status", "No configured planning cost data."), "Use this only as a budgeting framework. Replace every line with current supplier, machinery, labour and transport quotations for the actual location."],
            "bullets": list(economics.get("limitations", [])),
            "table": _cost_table(economics),
        },
        {
            "heading": "14. Yield, revenue and profit scenarios",
            "paragraphs": [finance_summary, "Profit is not guaranteed. Yield, grade, moisture/quality, selling channel, market price and unplanned losses can materially change the result."],
            "bullets": [],
            "table": _profit_table(economics),
        },
        {
            "heading": "15. Break-even analysis",
            "paragraphs": [
                f"Planning break-even selling price: {((economics.get('break_even') or {}).get('selling_price_lkr_per_kg')) or 'not available'} LKR/kg. Planning break-even yield at the configured base price: {((economics.get('break_even') or {}).get('yield_kg')) or 'not available'} kg for this area.",
                "Both values inherit the assumptions in the cost/yield/price scenario and must be recalculated with real quotations before financing or contracting decisions.",
            ],
            "bullets": [],
        },
        {
            "heading": "16. Harvest and post-harvest",
            "paragraphs": ["Plan harvest machinery/labour, field access, bags/containers, handling, quality checks, temporary storage and transport before the crop reaches maturity."],
            "bullets": ["Confirm harvest window against weather", "Confirm machinery/labour booking", "Minimise contamination and avoidable grain/produce loss", "Measure/record quality indicators available to the farmer", "Keep buyer and transport arrangements ready"],
        },
        {
            "heading": "17. Marketing channels and platforms",
            "paragraphs": [
                "Start market discovery before harvest. Compare net realised price after grading, transport, bags, loading and payment delay rather than only the headline price.",
                "This local build does not yet have a live verified national buyer/price feed, so channel availability and current prices must be refreshed before sale.",
            ],
            "bullets": list(market.get("selling_strategy", [])),
            "table": _market_table(market),
        },
        {
            "heading": "18. Weather, climate and disaster risk",
            "paragraphs": ["Re-run Decision Support before fertilizer/crop-protection application, irrigation changes, harvest and other weather-sensitive operations. Official emergency alerts override routine planning."],
            "bullets": ["Heavy rain/runoff/flood risk", "Dry spell/water shortage", "Heat/wind effects on operations", "Field access during extreme weather", "Post-harvest drying/storage exposure"],
        },
        {
            "heading": "19. 30/60/90-day or stage-based action plan",
            "paragraphs": ["If an exact planting date is unavailable, use these as staged actions rather than literal calendar dates."],
            "bullets": ["0–30 days: finalise field/seed/water plan, land preparation, establishment and baseline records", "31–60 days: monitor establishment/vigour, water, weeds and stage-appropriate nutrition using verified guidance", "61–90 days: continue stage-specific monitoring, risk checks and start harvest/market preparation as maturity approaches", "Later: harvest, post-harvest quality, sale, cost/yield reconciliation and season review"],
        },
        {
            "heading": "20. Evidence and sources to verify",
            "paragraphs": ["Consequential recommendations should be traceable to the latest authoritative source, product label or verified operational data."],
            "bullets": knowledge_bullets or ["No approved-source metadata matched the crop; obtain current official crop guidance before rate-sensitive actions."],
        },
    ]

    assumptions = [
        "District-centre coordinates may be used when exact farm GPS coordinates are unavailable.",
        "Any missing season, irrigation, variety or planting date is treated as an open planning assumption, not as a known fact.",
        economics.get("data_status", "Financial data status unavailable."),
    ]
    limitations = [
        "The report does not replace current Department of Agriculture protocols, product labels, soil/lab testing or qualified field assessment.",
        "The local build does not yet provide a live verified buyer/market-price feed.",
        "Financial scenarios are sensitive to actual input prices, labour, yield, grade, transport and sale price.",
    ]
    next_actions = [
        "Replace planning cost lines with current local quotations.",
        "Confirm season, irrigation reliability, variety and planting date when available.",
        "Use Decision Support before weather-sensitive or consequential field operations.",
        "Start buyer discovery before harvest and record at least two or three comparable quotations.",
    ]

    return {
        "title": f"{location} {area} {crop} Complete Cultivation, Cost, Profit & Marketing Report".strip(),
        "executive_summary": f"This report provides an end-to-end planning framework for approximately {area} of {crop} in {location}. It covers agronomy, equipment/tools, inputs, labour, stage planning, weather risk, cost and profit scenarios, harvest/post-harvest, logistics and selling channels. Financial figures are transparent planning estimates rather than live quotations, and chemical/fertilizer rates remain verification-gated.",
        "sections": sections,
        "assumptions": assumptions,
        "limitations": limitations,
        "next_actions": next_actions,
    }


def _payload_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="python")
    if isinstance(value, dict):
        return value
    return {}


def _strip_json_fence(text: str) -> str:
    value = (text or "").strip()
    if value.startswith("```"):
        value = value.strip("`").strip()
        if value.lower().startswith("json"):
            value = value[4:].strip()
    return value


def _structured_generate(
    client: Any,
    prompt: str,
    schema: type[BaseModel],
    *,
    max_output_tokens: int = 32768,
    temperature: float = 0.15,
) -> dict[str, Any]:
    """Generate and validate JSON with Gemini structured output.

    The primary path uses response_schema. A JSON-mime fallback is retained for
    compatibility with a configured model/runtime that rejects response_schema,
    but Pydantic validation is still mandatory before data enters the report path.
    """
    errors: list[str] = []

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": schema,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            },
        )
        parsed = getattr(response, "parsed", None)
        payload = _payload_dict(parsed)
        if payload:
            return payload
        validated = schema.model_validate_json(_strip_json_fence(response.text or ""))
        return validated.model_dump(mode="python")
    except Exception as exc:
        errors.append(f"schema mode: {exc}")

    # Compatibility fallback: still request JSON and validate against the same
    # Pydantic model. This avoids the old unvalidated json.loads-only behaviour.
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            },
        )
        validated = schema.model_validate_json(_strip_json_fence(response.text or ""))
        return validated.model_dump(mode="python")
    except Exception as exc:
        errors.append(f"json mode: {exc}")

    raise RuntimeError("; ".join(errors))


def _ensure_section_keys(report: dict[str, Any]) -> dict[str, Any]:
    result = dict(report)
    sections: list[dict[str, Any]] = []
    for index, raw in enumerate(result.get("sections") or [], start=1):
        section = dict(raw or {})
        section["section_key"] = str(section.get("section_key") or f"section_{index:02d}")
        table = dict(section.get("table") or {})
        table["columns"] = [str(x) for x in (table.get("columns") or [])]
        table["rows"] = [
            [str(cell) for cell in (row if isinstance(row, (list, tuple)) else [row])]
            for row in (table.get("rows") or [])
        ]
        section["table"] = table
        section["heading"] = str(section.get("heading") or f"Section {index}")
        section["paragraphs"] = [str(x) for x in (section.get("paragraphs") or [])]
        section["bullets"] = [str(x) for x in (section.get("bullets") or [])]
        sections.append(section)
    result["sections"] = sections
    result["title"] = str(result.get("title") or "MihiMura Complete Cultivation Report")
    result["executive_summary"] = str(result.get("executive_summary") or "")
    for key in ("assumptions", "limitations", "next_actions"):
        result[key] = [str(x) for x in (result.get(key) or [])]
    return result


def _report_language_matches(report: dict[str, Any], target_language: str) -> bool:
    target = normalize_language(target_language)
    if target == "English":
        return True
    sample_parts = [str(report.get("title") or ""), str(report.get("executive_summary") or "")]
    for section in (report.get("sections") or [])[:12]:
        sample_parts.append(str(section.get("heading") or ""))
        sample_parts.extend(str(x) for x in (section.get("paragraphs") or [])[:2])
        sample_parts.extend(str(x) for x in (section.get("bullets") or [])[:2])
    detected = detect_language(" ".join(sample_parts), fallback=target)
    return detected.language == target and detected.confidence >= 0.72


def _translate_report_meta(client: Any, report: dict[str, Any], target: str) -> dict[str, Any]:
    source = {
        "title": report.get("title") or "",
        "executive_summary": report.get("executive_summary") or "",
        "assumptions": report.get("assumptions") or [],
        "limitations": report.get("limitations") or [],
        "next_actions": report.get("next_actions") or [],
    }
    prompt = f"""Translate the farmer-facing MihiMura report metadata below into {target}.
Translate title, executive summary, assumptions, limitations and next actions completely.
Preserve exact numbers, dates, units, source/authority names, scientific names, active ingredients and product names where translation could reduce precision.
Do not summarize, omit, add recommendations, or return commentary.
SOURCE_METADATA: {json.dumps(source, default=str, ensure_ascii=False)}"""
    return _structured_generate(
        client,
        prompt,
        ReportMetaTranslationPayload,
        max_output_tokens=10000,
        temperature=0.05,
    )


def _translate_section_batch(client: Any, sections: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    prompt = f"""Translate these MihiMura report sections into {target}.
Translate every farmer-facing heading, paragraph, bullet, table column label and table cell.
Keep each section_key exactly unchanged and keep the sections in the same order.
Preserve exact numbers, dates, units, source/authority names, scientific names, active ingredients and product names where translation could reduce precision.
Do not summarize, omit rows, merge sections, add commentary, or change the meaning.
For a source section with no table, return an empty table with empty columns and rows.
SOURCE_SECTIONS: {json.dumps(sections, default=str, ensure_ascii=False)}"""
    payload = _structured_generate(
        client,
        prompt,
        ReportSectionBatchPayload,
        max_output_tokens=14000,
        temperature=0.05,
    )
    translated = list(payload.get("sections") or [])
    if len(translated) != len(sections):
        raise ValueError(f"Expected {len(sections)} translated sections, received {len(translated)}")
    for source, output in zip(sections, translated):
        # Machine keys are not farmer-facing and must never be translated.
        output["section_key"] = str(source.get("section_key") or "")
    return translated


def _translate_report_payload(client: Any, report: dict[str, Any], target_language: str) -> dict[str, Any] | None:
    """Localize a report without sending one huge translation request.

    Metadata is translated separately and sections are translated in small batches.
    If a batch fails, each section in that batch is retried individually. This is
    slower only on the failure path, but prevents one truncated response from
    invalidating an otherwise complete Sinhala/Tamil PDF.
    """
    target = normalize_language(target_language)
    source = _ensure_section_keys(report)
    if target == "English":
        return source

    try:
        meta = _translate_report_meta(client, source, target)
        translated_sections: list[dict[str, Any]] = []
        sections = list(source.get("sections") or [])
        batch_size = 4
        for offset in range(0, len(sections), batch_size):
            batch = sections[offset : offset + batch_size]
            try:
                translated_sections.extend(_translate_section_batch(client, batch, target))
            except Exception as batch_exc:
                logger.warning(
                    "multilingual report batch translation failed language=%s offset=%s error=%s; retrying section-by-section",
                    target,
                    offset,
                    batch_exc,
                )
                for section in batch:
                    translated_sections.extend(_translate_section_batch(client, [section], target))

        translated_report = _ensure_section_keys({
            **meta,
            "sections": translated_sections,
        })
        if len(translated_sections) != len(sections):
            raise ValueError("Localized report section count changed")
        if not _report_language_matches(translated_report, target):
            raise ValueError(f"Localized report did not validate as {target}")
        return translated_report
    except Exception as exc:
        logger.exception("multilingual report translation failed language=%s error=%s", target, exc)
        return None


def _report_payload(
    facts: dict[str, Any],
    weather: dict[str, Any],
    climate: dict[str, Any],
    knowledge: dict[str, Any],
    economics: dict[str, Any],
    market: dict[str, Any],
    resources: dict[str, Any],
) -> dict[str, Any]:
    client = get_gemini_client()
    fallback = _ensure_section_keys(_fallback_report(facts, weather, climate, knowledge, economics, market, resources))
    target_language = normalize_language(facts.get("language") or "English")
    if client is None:
        if target_language == "English":
            return fallback
        raise RuntimeError(
            f"{target_language} report generation requires GEMINI_API_KEY because the deterministic report source is English and must be localized safely."
        )

    evidence = {
        "scenario": facts,
        "weather": weather,
        "climate_history": climate,
        "approved_knowledge": knowledge,
        "resource_plan": resources,
        "economics": economics,
        "market_intelligence": market,
        # This gives the model a complete deterministic coverage baseline without
        # relying on it to invent missing report sections.
        "deterministic_fallback_structure": fallback,
    }
    candidate: dict[str, Any] | None = None
    try:
        candidate = _structured_generate(
            client,
            REPORT_SYSTEM
            + f"\nTARGET_LANGUAGE: {target_language}"
            + "\nEVIDENCE: "
            + json.dumps(evidence, default=str, ensure_ascii=False),
            ReportPayloadSchema,
            max_output_tokens=32768,
            temperature=0.15,
        )
        candidate = _ensure_section_keys(candidate)
        if len(candidate.get("sections") or []) < 8:
            raise ValueError("Report model response was too incomplete")
        if _report_language_matches(candidate, target_language):
            return candidate
        logger.warning("report model returned wrong/weak language language=%s; localizing candidate", target_language)
        translated_candidate = _translate_report_payload(client, candidate, target_language)
        if translated_candidate:
            return translated_candidate
    except Exception as exc:
        logger.warning("structured report composition failed language=%s error=%s", target_language, exc)

    # English remains fully deterministic if Gemini is unavailable or malformed.
    if target_language == "English":
        return fallback

    # Sinhala/Tamil fallback is localized in validated chunks rather than as one
    # enormous JSON blob. Never silently return an English PDF for a native-language request.
    translated_fallback = _translate_report_payload(client, fallback, target_language)
    if translated_fallback:
        return translated_fallback

    raise RuntimeError(
        f"MihiMura could not generate a complete {target_language} report. The PDF was not created because returning an English report would violate the selected language."
    )


def _paragraph_cell(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text or "")), style)


def _render_section_table(table_spec: dict[str, Any], body: ParagraphStyle, small: ParagraphStyle) -> Table | None:
    columns = [str(x) for x in (table_spec.get("columns") or [])]
    rows = table_spec.get("rows") or []
    if not columns or not rows:
        return None
    data = [[_paragraph_cell(c, small) for c in columns]]
    for row in rows:
        values = list(row) if isinstance(row, (list, tuple)) else [row]
        values = values[: len(columns)] + [""] * max(0, len(columns) - len(values))
        data.append([_paragraph_cell(v, body) for v in values])
    usable = 174 * mm
    col_width = usable / len(columns)
    table = Table(data, colWidths=[col_width] * len(columns), repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf4ed")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#285f3e")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccd9cf")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dde6df")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _build_pdf(report: dict[str, Any], facts: dict[str, Any]) -> bytes:
    language = normalize_language(facts.get("language") or "English")
    labels = _pdf_labels(language)
    regular_font, bold_font, shaping = _register_pdf_fonts(language)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    brand = ParagraphStyle("MihiBrand", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=24, alignment=TA_CENTER, spaceAfter=12)
    report_title = ParagraphStyle("MihiReportTitle", parent=styles["Heading2"], fontName=bold_font, fontSize=13.5, leading=19, alignment=TA_CENTER, spaceAfter=8, shaping=1 if shaping else 0)
    h = ParagraphStyle("MihiH", parent=styles["Heading2"], fontName=bold_font, fontSize=12.5, leading=17, spaceBefore=10, spaceAfter=5, shaping=1 if shaping else 0)
    body = ParagraphStyle("MihiBody", parent=styles["BodyText"], fontName=regular_font, fontSize=9.8, leading=15, spaceAfter=6, shaping=1 if shaping else 0)
    bullet = ParagraphStyle("MihiBullet", parent=body, leftIndent=12, firstLineIndent=-7, bulletIndent=4, shaping=1 if shaping else 0)
    small = ParagraphStyle("MihiSmall", parent=body, fontSize=8.2, leading=12, textColor=colors.HexColor("#5f6f64"), shaping=1 if shaping else 0)
    meta_label = ParagraphStyle("MihiMetaLabel", parent=small, fontName=bold_font, shaping=1 if shaping else 0)

    story: list[Any] = [
        Paragraph(escape("MihiMura"), brand),
        Paragraph(escape(str(report.get("title") or "Cultivation Intelligence Report")), report_title),
    ]
    not_set = labels["not_set"]
    assumption_not_set = labels["assumption_not_set"]
    meta = [
        [_paragraph_cell(labels["crop"], meta_label), _paragraph_cell(facts.get("crop") or not_set, body), _paragraph_cell(labels["location"], meta_label), _paragraph_cell(facts.get("location") or not_set, body)],
        [_paragraph_cell(labels["area"], meta_label), _paragraph_cell(f"{facts.get('area_value','')} {facts.get('area_unit','')}".strip() or not_set, body), _paragraph_cell(labels["season"], meta_label), _paragraph_cell(facts.get("season") or assumption_not_set, body)],
        [_paragraph_cell(labels["water_source"], meta_label), _paragraph_cell(facts.get("irrigation") or assumption_not_set, body), _paragraph_cell(labels["generated"], meta_label), _paragraph_cell(now_iso()[:19].replace("T", " ") + " UTC", body)],
    ]
    meta_table = Table(meta, colWidths=[25 * mm, 52 * mm, 25 * mm, 60 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f8f5")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e4db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e3ebe5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([
        meta_table, Spacer(1, 8 * mm),
        Paragraph(escape(labels["executive_summary"]), h),
        Paragraph(escape(str(report.get("executive_summary") or "")), body),
    ])

    for section in report.get("sections") or []:
        story.append(Paragraph(escape(str(section.get("heading") or "Section")), h))
        for paragraph in section.get("paragraphs") or []:
            story.append(Paragraph(escape(str(paragraph)), body))
        for item in section.get("bullets") or []:
            story.append(Paragraph(escape(f"• {item}"), bullet))
        rendered = _render_section_table(section.get("table") or {}, body, small)
        if rendered is not None:
            story.extend([Spacer(1, 2 * mm), rendered, Spacer(1, 3 * mm)])

    for heading, key in [(labels["assumptions"], "assumptions"), (labels["limitations"], "limitations"), (labels["next_actions"], "next_actions")]:
        items = report.get(key) or []
        if items:
            story.append(Paragraph(escape(heading), h))
            for item in items:
                story.append(Paragraph(escape(f"• {item}"), bullet))

    story.extend([
        Spacer(1, 6 * mm),
        Paragraph(escape(labels["notice"]), h),
        Paragraph(escape(labels["notice_text"]), small),
    ])
    doc.build(story)
    return buffer.getvalue()


def _signed_url(bucket: str, path: str, expires: int = 3600) -> str | None:
    response = service_client().storage.from_(bucket).create_signed_url(path, expires)
    if isinstance(response, dict):
        return response.get("signedURL") or response.get("signedUrl") or response.get("signed_url")
    data = getattr(response, "data", None)
    if isinstance(data, dict):
        return data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
    return None


def generate_conversation_report(uid: str, conversation_id: str) -> dict[str, Any]:
    conv = require_conversation(uid, conversation_id)
    memory = get_memory(uid, conversation_id)
    facts = dict(memory.get("known_facts") or {})
    missing = report_missing_fields(facts)
    if missing:
        raise ValueError("Report is not ready. Missing: " + ", ".join(missing))

    lat, lon = facts.get("lat"), facts.get("lon")
    weather = get_weather(float(lat), float(lon), 14) if lat is not None and lon is not None else {"source": "Location unavailable", "live": False}
    climate = get_nasa_power(float(lat), float(lon), 30) if lat is not None and lon is not None else {"source": "Location unavailable", "live": False}
    knowledge = retrieve_approved_knowledge(
        str(facts.get("crop") or ""),
        "complete cultivation equipment cost profit marketing report "
        + str(facts.get("crop") or "")
        + " "
        + str(facts.get("location") or ""),
        language=str(facts.get("language") or "English"),
        location=str(facts.get("location") or ""),
    )
    economics = estimate_cultivation_economics(facts)
    market = get_market_options(str(facts.get("crop") or ""), str(facts.get("location") or ""))
    resources = build_resource_plan(str(facts.get("crop") or ""))
    report = _report_payload(facts, weather, climate, knowledge, economics, market, resources)
    pdf_bytes = _build_pdf(report, facts)

    rid = f"report_{uuid4().hex[:12]}"
    path = f"{uid}/{rid}.pdf"
    service_client().storage.from_(settings.SUPABASE_REPORTS_BUCKET).upload(
        path=path,
        file=pdf_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )
    row = {
        "id": rid,
        "owner_uid": uid,
        "conversation_id": conversation_id,
        "project_id": conv.get("project_id"),
        "report_type": "complete_cultivation_business_plan",
        "title": report.get("title") or "MihiMura Complete Cultivation Report",
        "status": "ready",
        "parameters": {**facts, "economics_status": economics.get("status"), "market_price_feed": market.get("price_feed")},
        "summary": report.get("executive_summary") or "",
        "storage_path": path,
        "created_at": now_iso(),
    }
    _table("reports").insert(row).execute()
    audit(uid, "generate_report", rid, {"conversation_id": conversation_id, "report_type": row["report_type"]})
    return {
        **row,
        "download_url": _signed_url(settings.SUPABASE_REPORTS_BUCKET, path),
        "economics": economics,
        "market": market,
        "assumptions": report.get("assumptions") or [],
        "limitations": report.get("limitations") or [],
    }


def list_reports(uid: str) -> list[dict[str, Any]]:
    data = _table("reports").select("*").eq("owner_uid", uid).execute().data or []
    out = []
    for item in sorted(list(data), key=lambda x: str(x.get("created_at") or ""), reverse=True):
        out.append({**item, "download_url": _signed_url(settings.SUPABASE_REPORTS_BUCKET, str(item.get("storage_path") or "")) if item.get("storage_path") else None})
    return out
