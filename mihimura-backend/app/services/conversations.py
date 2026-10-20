from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from app.db import now_iso
from app.services.platform import get_project_context
from app.services.language import detect_language, normalize_language
from app.supabase_client import first, service_client

CROPS = ["paddy", "rice", "chilli", "chili", "maize", "corn", "tomato", "brinjal", "eggplant", "onion", "tea", "coconut", "banana", "cinnamon"]
DISTRICTS = [
    "Ampara", "Anuradhapura", "Badulla", "Batticaloa", "Colombo", "Galle", "Gampaha", "Hambantota",
    "Jaffna", "Kalutara", "Kandy", "Kegalle", "Kilinochchi", "Kurunegala", "Mannar", "Matale", "Matara",
    "Monaragala", "Mullaitivu", "Nuwara Eliya", "Polonnaruwa", "Puttalam", "Ratnapura", "Trincomalee", "Vavuniya",
]
# District-centre coordinates are used only as a fallback when the user names a district
# but has not supplied a farm/GPS point. Farm coordinates remain preferable.

DISTRICT_ALIASES: dict[str, str] = {
    # English spellings / common variants
    "polannaruwa": "Polonnaruwa", "polonaruwa": "Polonnaruwa", "polonnaruwa": "Polonnaruwa",
    "nuwaraeliya": "Nuwara Eliya", "nuwara eliya": "Nuwara Eliya", "trinco": "Trincomalee",
    # Sinhala district names
    "අම්පාර": "Ampara", "අනුරාධපුර": "Anuradhapura", "බදුල්ල": "Badulla", "මඩකලපුව": "Batticaloa",
    "කොළඹ": "Colombo", "ගාල්ල": "Galle", "ගම්පහ": "Gampaha", "හම්බන්තොට": "Hambantota",
    "යාපනය": "Jaffna", "කළුතර": "Kalutara", "මහනුවර": "Kandy", "කෑගල්ල": "Kegalle",
    "කිලිනොච්චි": "Kilinochchi", "කුරුණෑගල": "Kurunegala", "මන්නාර": "Mannar", "මාතලේ": "Matale",
    "මාතර": "Matara", "මොනරාගල": "Monaragala", "මුලතිව්": "Mullaitivu", "නුවරඑළිය": "Nuwara Eliya",
    "නුවර එළිය": "Nuwara Eliya", "පොළොන්නරුව": "Polonnaruwa", "පුත්තලම": "Puttalam", "රත්නපුර": "Ratnapura",
    "ත්‍රිකුණාමල": "Trincomalee", "වවුනියාව": "Vavuniya",
    # Tamil district names
    "அம்பாறை": "Ampara", "அனுராதபுரம்": "Anuradhapura", "பதுளை": "Badulla", "மட்டக்களப்பு": "Batticaloa",
    "கொழும்பு": "Colombo", "காலி": "Galle", "கம்பஹா": "Gampaha", "அம்பாந்தோட்டை": "Hambantota",
    "யாழ்ப்பாணம்": "Jaffna", "களுத்துறை": "Kalutara", "கண்டி": "Kandy", "கேகாலை": "Kegalle",
    "கிளிநொச்சி": "Kilinochchi", "குருநாகல்": "Kurunegala", "மன்னார்": "Mannar", "மாத்தளை": "Matale",
    "மாத்தறை": "Matara", "மொணராகலை": "Monaragala", "முல்லைத்தீவு": "Mullaitivu", "நுவரெலியா": "Nuwara Eliya",
    "பொலன்னறுவை": "Polonnaruwa", "பொலனறுவை": "Polonnaruwa", "புத்தளம்": "Puttalam", "இரத்தினபுரி": "Ratnapura",
    "திருகோணமலை": "Trincomalee", "வவுனியா": "Vavuniya",
}

CROP_ALIASES: dict[str, str] = {
    "paddy": "Paddy", "rice": "Paddy", "padddy": "Paddy",
    "වී": "Paddy", "වී වගාව": "Paddy", "කුඹුරු": "Paddy",
    "நெல்": "Paddy", "நெற்பயிர்": "Paddy", "அரிசி": "Paddy",
    "chilli": "Chilli", "chili": "Chilli", "මිරිස්": "Chilli", "மிளகாய்": "Chilli",
    "maize": "Maize", "corn": "Maize", "බඩඉරිඟු": "Maize", "சோளம்": "Maize",
    "tomato": "Tomato", "තක්කාලි": "Tomato", "தக்காளி": "Tomato",
    "brinjal": "Brinjal", "eggplant": "Brinjal", "වම්බටු": "Brinjal", "கத்தரிக்காய்": "Brinjal",
    "onion": "Onion", "ලූනු": "Onion", "வெங்காயம்": "Onion",
    "banana": "Banana", "කෙසෙල්": "Banana", "வாழை": "Banana",
    "coconut": "Coconut", "පොල්": "Coconut", "தேங்காய்": "Coconut",
    "tea": "Tea", "තේ": "Tea", "தேயிலை": "Tea",
}

DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    "Ampara": (7.291, 81.674), "Anuradhapura": (8.3114, 80.4037), "Badulla": (6.9934, 81.0550),
    "Batticaloa": (7.7170, 81.7000), "Colombo": (6.9271, 79.8612), "Galle": (6.0535, 80.2210),
    "Gampaha": (7.0873, 80.0144), "Hambantota": (6.1429, 81.1212), "Jaffna": (9.6615, 80.0255),
    "Kalutara": (6.5854, 79.9607), "Kandy": (7.2906, 80.6337), "Kegalle": (7.2513, 80.3464),
    "Kilinochchi": (9.3803, 80.3770), "Kurunegala": (7.4863, 80.3623), "Mannar": (8.9810, 79.9044),
    "Matale": (7.4675, 80.6234), "Matara": (5.9549, 80.5550), "Monaragala": (6.8728, 81.3507),
    "Mullaitivu": (9.2671, 80.8142), "Nuwara Eliya": (6.9497, 80.7891), "Polonnaruwa": (7.9403, 81.0188),
    "Puttalam": (8.0408, 79.8394), "Ratnapura": (6.6828, 80.3992), "Trincomalee": (8.5874, 81.2152),
    "Vavuniya": (8.7514, 80.4971),
}


def _table(name: str):
    return service_client().table(name)


def _one(name: str, **filters: Any) -> dict[str, Any] | None:
    q = _table(name).select("*")
    for key, value in filters.items():
        q = q.eq(key, value)
    return first(q.limit(1).execute().data)


def create_conversation(uid: str, project_id: str | None = None, title: str | None = None) -> dict[str, Any]:
    if project_id and not get_project_context(uid, project_id):
        raise PermissionError("Project not found or not accessible")
    cid = f"conv_{uuid4().hex[:12]}"
    payload = {
        "id": cid,
        "owner_uid": uid,
        "project_id": project_id or None,
        "title": (title or "New farm conversation")[:120],
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    _table("conversations").insert(payload).execute()
    _table("conversation_memory").insert({
        "conversation_id": cid,
        "owner_uid": uid,
        "summary": "",
        "active_intent": "general",
        "known_facts": {},
        "missing_fields": [],
        "updated_at": now_iso(),
    }).execute()
    return payload


def list_conversations(uid: str, limit: int = 50) -> list[dict[str, Any]]:
    data = _table("conversations").select("*").eq("owner_uid", uid).execute().data or []
    return sorted(list(data), key=lambda x: str(x.get("updated_at") or ""), reverse=True)[:limit]


def require_conversation(uid: str, conversation_id: str) -> dict[str, Any]:
    conv = _one("conversations", id=conversation_id, owner_uid=uid)
    if not conv:
        raise PermissionError("Conversation not found or not accessible")
    return conv


def archive_conversation(uid: str, conversation_id: str) -> dict[str, Any]:
    require_conversation(uid, conversation_id)
    _table("conversations").update({"status": "archived", "updated_at": now_iso()}).eq("id", conversation_id).eq("owner_uid", uid).execute()
    return require_conversation(uid, conversation_id)


def append_message(uid: str, conversation_id: str, role: str, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    require_conversation(uid, conversation_id)
    mid = f"msg_{uuid4().hex[:14]}"
    payload = {
        "id": mid,
        "conversation_id": conversation_id,
        "owner_uid": uid,
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "created_at": now_iso(),
    }
    _table("messages").insert(payload).execute()
    _table("conversations").update({"updated_at": payload["created_at"]}).eq("id", conversation_id).eq("owner_uid", uid).execute()
    return payload


def list_messages(uid: str, conversation_id: str, limit: int = 100) -> list[dict[str, Any]]:
    require_conversation(uid, conversation_id)
    data = _table("messages").select("*").eq("conversation_id", conversation_id).eq("owner_uid", uid).execute().data or []
    return sorted(list(data), key=lambda x: str(x.get("created_at") or ""))[-limit:]


def recent_history(uid: str, conversation_id: str, limit: int = 18) -> list[dict[str, str]]:
    return [{"role": str(m.get("role")), "content": str(m.get("content") or "")} for m in list_messages(uid, conversation_id, limit=limit)]


def get_memory(uid: str, conversation_id: str) -> dict[str, Any]:
    require_conversation(uid, conversation_id)
    memory = _one("conversation_memory", conversation_id=conversation_id, owner_uid=uid)
    return memory or {
        "conversation_id": conversation_id,
        "owner_uid": uid,
        "summary": "",
        "active_intent": "general",
        "known_facts": {},
        "missing_fields": [],
    }


def update_memory(uid: str, conversation_id: str, *, known_facts: dict[str, Any] | None = None, active_intent: str | None = None, summary: str | None = None, missing_fields: list[str] | None = None) -> dict[str, Any]:
    current = get_memory(uid, conversation_id)
    merged = dict(current.get("known_facts") or {})
    for key, value in (known_facts or {}).items():
        if value not in (None, "", []):
            merged[key] = value
    patch = {
        "known_facts": merged,
        "active_intent": active_intent or current.get("active_intent") or "general",
        "summary": summary if summary is not None else current.get("summary") or "",
        "missing_fields": missing_fields if missing_fields is not None else current.get("missing_fields") or [],
        "updated_at": now_iso(),
    }
    _table("conversation_memory").upsert({"conversation_id": conversation_id, "owner_uid": uid, **patch}).execute()
    return {**current, **patch, "conversation_id": conversation_id, "owner_uid": uid}


def _extract_area(text: str) -> tuple[float, str] | None:
    """Extract common English/Sinhala/Tamil land-area expressions.

    Supports both number-first (``1 acre``, ``1 අක්කර``, ``1 ஏக்கர்``) and
    native unit-first forms commonly used in Sri Lankan chat (``අක්කර 1ක``,
    ``හෙක්ටයාර් 2``, ``ஏக்கர் 1``). A trailing Sinhala case marker such as ``ක``
    is accepted after the number.
    """
    # English number-first forms, including casual spelling such as "1 accr".
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(ac+r(?:e?s?)?|hectares?|ha|perches?|perch)\b", text, flags=re.I)
    if match:
        value = float(match.group(1))
        unit_text = match.group(2).lower()
        if unit_text.startswith("ac"):
            return value, "acre"
        if unit_text.startswith("hect") or unit_text == "ha":
            return value, "hectare"
        return value, "perch"

    native_units = r"(අක්කර(?:යක්|ය)?|හෙක්ටයාර්(?:යක්|ය)?|පර්චස්?|පර්ච්|ஏக்கர்(?:கள்)?|ஹெக்டேர்(?:கள்)?|பேர்ச்)"

    # Number first: 1 අක්කර / 1 ஏக்கர் / 2 හෙක්ටයාර්.
    match = re.search(rf"(\d+(?:\.\d+)?)\s*{native_units}", text)
    if match:
        value = float(match.group(1))
        unit_text = match.group(2)
    else:
        # Unit first: අක්කර 1ක / හෙක්ටයාර් 2 / ஏக்கர் 1.
        match = re.search(rf"{native_units}\s*(\d+(?:\.\d+)?)(?:\s*ක)?", text)
        if not match:
            return None
        unit_text = match.group(1)
        value = float(match.group(2))

    if "හෙක්ට" in unit_text or "ஹெக்ட" in unit_text:
        return value, "hectare"
    if "පර්ච" in unit_text or "பேர்ச்" in unit_text:
        return value, "perch"
    return value, "acre"


def extract_facts(question: str, answers: dict[str, Any] | None = None) -> tuple[dict[str, Any], str | None]:
    text = question.strip()
    lower = text.lower()
    facts: dict[str, Any] = {}
    intent: str | None = None

    # Script-based language detection is independent of the UI toggle. It also lets
    # reports remember the language of the active conversation.
    detected = detect_language(text)
    facts["language"] = detected.language
    facts["language_confidence"] = round(detected.confidence, 3)

    matched_district = None
    # Native-script names often carry grammatical suffixes (e.g. ගාල්ලේ / காலியில்),
    # so substring matching is deliberate. English aliases keep word-boundary matching.
    for alias, canonical in DISTRICT_ALIASES.items():
        if any("\u0d80" <= ch <= "\u0dff" or "\u0b80" <= ch <= "\u0bff" for ch in alias):
            if alias in text:
                matched_district = canonical
                break
        elif re.search(rf"\b{re.escape(alias.lower())}\b", lower):
            matched_district = canonical
            break
    if not matched_district:
        for district in DISTRICTS:
            if re.search(rf"\b{re.escape(district.lower())}\b", lower):
                matched_district = district
                break
    if matched_district:
        facts["location"] = matched_district
        facts["district"] = matched_district
        lat, lon = DISTRICT_COORDS[matched_district]
        facts["lat"] = lat
        facts["lon"] = lon
        facts["location_source"] = "explicit-conversation"

    for alias, canonical in CROP_ALIASES.items():
        if any("\u0d80" <= ch <= "\u0dff" or "\u0b80" <= ch <= "\u0bff" for ch in alias):
            if alias in text:
                facts["crop"] = canonical
                break
        elif re.search(rf"\b{re.escape(alias.lower())}\b", lower):
            facts["crop"] = canonical
            break

    area = _extract_area(text)
    if area:
        facts["area_value"], facts["area_unit"] = area

    if re.search(r"\bmaha\b", lower) or "මහ කන්න" in text or "මහ කන්නය" in text or "மகா" in text:
        facts["season"] = "Maha"
    elif re.search(r"\byala\b", lower) or "යල කන්න" in text or "යල කන්නය" in text or "யால" in text:
        facts["season"] = "Yala"

    if any(x in lower for x in ["major irrigation", "canal", "irrigation scheme"]) or any(x in text for x in ["ප්‍රධාන වාරි", "ඇළ", "பெரும் பாசனம்", "கால்வாய்"]):
        facts["irrigation"] = "Major irrigation"
    elif any(x in lower for x in ["minor irrigation", "tank irrigation"]) or any(x in text for x in ["සුළු වාරි", "වැව", "சிறு பாசனம்", "குளம்"]):
        facts["irrigation"] = "Minor irrigation"
    elif any(x in lower for x in ["rainfed", "rain-fed"]) or any(x in text for x in ["වර්ෂාපෝෂිත", "மழை சார்ந்த"]):
        facts["irrigation"] = "Rainfed"
    elif any(x in lower for x in ["well", "pump"]) or any(x in text for x in ["ළිඳ", "පොම්ප", "கிணறு", "பம்ப்"]):
        facts["irrigation"] = "Well / pump"

    report_terms = [
        "full report", "whole report", "complete report", "cultivation report", "cultivation plan", "planting plan", "full plan",
        "සම්පූර්ණ වාර්තාව", "විස්තරාත්මක වාර්තාව", "වගා වාර්තාව", "වගා සැලැස්ම", "වාර්තාවක් දෙන්න",
        "முழு அறிக்கை", "முழுமையான அறிக்கை", "விரிவான அறிக்கை", "சாகுபடி அறிக்கை", "சாகுபடி திட்டம்",
    ]
    weather_terms = [
        "weather", "rain", "temperature", "forecast", "climate",
        "කාලගුණ", "වැසි", "වර්ෂාව", "උෂ්ණත්ව", "අනාවැකි", "දේශගුණ",
        "வானிலை", "காலநிலை", "மழை", "வெப்பநிலை", "முன்னறிவிப்பு",
    ]
    health_terms = [
        "disease", "symptom", "leaf", "spot", "wilting",
        "රෝග", "ලක්ෂණ", "කොළ", "පත්‍ර", "මැලව",
        "நோய்", "அறிகுறி", "இலை", "புள்ளி", "வாட",
    ]
    if any(x in lower for x in report_terms if x.isascii()) or any(x in text for x in report_terms if not x.isascii()):
        intent = "cultivation_report"
    elif any(x in lower for x in weather_terms if x.isascii()) or any(x in text for x in weather_terms if not x.isascii()):
        intent = "weather_question"
    elif any(x in lower for x in health_terms if x.isascii()) or any(x in text for x in health_terms if not x.isascii()):
        intent = "crop_health"

    if answers:
        for key, value in answers.items():
            if value not in (None, "", []):
                facts[key] = value
        if answers and not intent:
            intent = "continue_workflow"

    return facts, intent


def report_missing_fields(facts: dict[str, Any]) -> list[str]:
    """Return only report-blocking fields.

    Season, irrigation, variety and planting date improve a report, but they no longer
    block generation. When they are absent, the report must state assumptions and
    scenario alternatives instead of interrupting the farmer with unnecessary forms.
    """
    required = ["crop", "location", "area_value"]
    return [x for x in required if facts.get(x) in (None, "", [])]


def clarification_fields(missing: list[str], facts: dict[str, Any], language: str | None = None) -> list[dict[str, Any]]:
    """Build the minimal blocking form in the farmer-facing response language.

    Machine keys and canonical option values stay stable in English so existing API
    handling does not change; labels/display labels are localized.
    """
    lang = normalize_language(language or facts.get("language") or "English")
    copy = {
        "English": {
            "crop": "Crop", "location": "Cultivation district / location", "area": "Land area", "unit": "Area unit",
            "crop_options": [("Paddy", "Paddy"), ("Chilli", "Chilli"), ("Maize", "Maize"), ("Onion", "Onion"), ("Tomato", "Tomato"), ("Brinjal", "Brinjal"), ("Other", "Other")],
            "unit_options": [("acre", "acre"), ("hectare", "hectare"), ("perch", "perch")],
        },
        "Sinhala": {
            "crop": "බෝගය", "location": "වගා කරන දිස්ත්‍රික්කය / ස්ථානය", "area": "ඉඩම් ප්‍රමාණය", "unit": "ප්‍රමාණ ඒකකය",
            "crop_options": [("Paddy", "වී"), ("Chilli", "මිරිස්"), ("Maize", "බඩඉරිඟු"), ("Onion", "ලූනු"), ("Tomato", "තක්කාලි"), ("Brinjal", "වම්බටු"), ("Other", "වෙනත්")],
            "unit_options": [("acre", "අක්කර"), ("hectare", "හෙක්ටයාර්"), ("perch", "පර්චස්")],
        },
        "Tamil": {
            "crop": "பயிர்", "location": "சாகுபடி மாவட்டம் / இடம்", "area": "நிலப்பரப்பு", "unit": "பரப்பு அலகு",
            "crop_options": [("Paddy", "நெல்"), ("Chilli", "மிளகாய்"), ("Maize", "சோளம்"), ("Onion", "வெங்காயம்"), ("Tomato", "தக்காளி"), ("Brinjal", "கத்தரிக்காய்"), ("Other", "மற்றவை")],
            "unit_options": [("acre", "ஏக்கர்"), ("hectare", "ஹெக்டேர்"), ("perch", "பேர்ச்")],
        },
    }[lang]

    def opts(values: list[tuple[str, str]]) -> list[dict[str, str]]:
        return [{"value": value, "label": label} for value, label in values]

    fields: list[dict[str, Any]] = []
    if "crop" in missing:
        fields.append({"key": "crop", "label": copy["crop"], "type": "select", "required": True, "options": opts(copy["crop_options"])})
    if "location" in missing:
        fields.append({"key": "location", "label": copy["location"], "type": "select", "required": True, "options": DISTRICTS})
    if "area_value" in missing:
        fields.append({"key": "area_value", "label": copy["area"], "type": "number", "required": True, "placeholder": "1"})
        fields.append({"key": "area_unit", "label": copy["unit"], "type": "select", "required": True, "options": opts(copy["unit_options"])})
    return fields[:5]


def resolve_conversation_context(uid: str, conversation_id: str, question: str, supplied: dict[str, Any], profile: dict[str, Any], answers: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    conv = require_conversation(uid, conversation_id)
    memory = get_memory(uid, conversation_id)
    patch, detected_intent = extract_facts(question, answers)
    facts = dict(memory.get("known_facts") or {})
    facts.update({k: v for k, v in patch.items() if v not in (None, "", [])})

    selected_project_id = supplied.get("project_id") or conv.get("project_id")
    project = get_project_context(uid, str(selected_project_id)) if selected_project_id else None

    # Priority: explicit/current chat facts > conversation memory > selected project > profile defaults.
    requested_language_mode = str(supplied.get("language_mode") or "auto").strip().lower()
    supplied_language = normalize_language(supplied.get("language"), normalize_language(profile.get("language"), "English"))
    detected_language = detect_language(question, fallback=supplied_language)
    # In Auto mode, a confident current-message script wins. In manual mode, respect
    # the chosen language while still returning the detected language for UI telemetry.
    response_language = detected_language.language if requested_language_mode == "auto" else supplied_language
    facts["language"] = response_language
    facts["detected_language"] = detected_language.language

    resolved: dict[str, Any] = {
        "language": response_language,
        "detected_language": detected_language.language,
        "language_confidence": round(detected_language.confidence, 3),
        "language_mode": requested_language_mode,
        "location": profile.get("district") or "Sri Lanka",
        "district": profile.get("district"),
        "lat": profile.get("lat"),
        "lon": profile.get("lon"),
        "crop": "",
        "stage": "",
        "context_scope": "profile-default",
    }
    if project:
        resolved.update({k: v for k, v in project.items() if v not in (None, "")})
        resolved["location"] = project.get("district") or resolved["location"]
        resolved["context_scope"] = "owned-project"

    # A district chosen in the UI (e.g. a province selected on the map) is a
    # scenario location. Only known districts are accepted, with their own
    # coordinates; anything stated in the message itself still wins below.
    selected_district = str(supplied.get("district") or "").strip()
    if selected_district in DISTRICT_COORDS and not facts.get("location"):
        lat, lon = DISTRICT_COORDS[selected_district]
        resolved.update({"location": selected_district, "district": selected_district, "lat": lat, "lon": lon})
        resolved["context_scope"] = "selected-region"

    for key in ["crop", "stage", "season", "variety", "irrigation", "area_value", "area_unit", "location", "district", "lat", "lon", "planting_date", "language"]:
        if facts.get(key) not in (None, "", []):
            resolved[key] = facts[key]
    if facts:
        resolved["context_scope"] = "conversation-scenario"

    current_intent = detected_intent or "follow_up"
    previous_intent = memory.get("active_intent") or "general"
    interaction_mode = str(supplied.get("interaction_mode") or "auto")
    # Full Report mode explicitly activates the report workflow even when the user's
    # latest turn is a short continuation such as "include equipment too".
    if interaction_mode == "full_report":
        active_intent = "cultivation_report"
    elif detected_intent == "cultivation_report":
        active_intent = "cultivation_report"
    elif detected_intent == "continue_workflow" and previous_intent:
        active_intent = previous_intent
    elif previous_intent == "cultivation_report":
        active_intent = "cultivation_report"
    else:
        active_intent = detected_intent or previous_intent
    missing = report_missing_fields(facts) if active_intent == "cultivation_report" else []
    summary_parts = []
    for key, label in [("crop", "crop"), ("location", "location"), ("area_value", "area"), ("season", "season"), ("irrigation", "irrigation")]:
        if facts.get(key):
            value = facts[key]
            if key == "area_value":
                value = f"{value} {facts.get('area_unit', '')}".strip()
            summary_parts.append(f"{label}: {value}")
    summary = "; ".join(summary_parts)
    memory = update_memory(uid, conversation_id, known_facts=facts, active_intent=active_intent, summary=summary, missing_fields=missing)
    resolved["conversation_memory"] = memory
    resolved["active_intent"] = active_intent
    resolved["current_intent"] = current_intent
    resolved["interaction_mode"] = interaction_mode
    return resolved, memory



def update_conversation_project(uid: str, conversation_id: str, project_id: str | None) -> dict[str, Any]:
    require_conversation(uid, conversation_id)
    if project_id and not get_project_context(uid, project_id):
        raise PermissionError("Project not found or not accessible")
    _table("conversations").update({"project_id": project_id or None, "updated_at": now_iso()}).eq("id", conversation_id).eq("owner_uid", uid).execute()
    return require_conversation(uid, conversation_id)

def update_conversation_title(uid: str, conversation_id: str, title: str) -> dict[str, Any]:
    require_conversation(uid, conversation_id)
    _table("conversations").update({"title": title[:120], "updated_at": now_iso()}).eq("id", conversation_id).eq("owner_uid", uid).execute()
    return require_conversation(uid, conversation_id)
