"""Offline Unicode PDF rendering smoke test for Sinhala and Tamil."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.reports import _build_pdf


def sample_report(language: str) -> tuple[dict, dict]:
    if language == "Sinhala":
        report = {
            "title": "පොළොන්නරුව අක්කර 1 වී වගා වාර්තාව",
            "executive_summary": "මෙය වී වගාව, වියදම්, අස්වැන්න සහ අලෙවිය සඳහා සාරාංශ පරීක්ෂණ වාර්තාවකි.",
            "sections": [{"heading": "1. වගා සැලැස්ම", "paragraphs": ["භූමිය සකස් කර ජලය සහ කාලගුණය අනුව වගා කටයුතු සැලසුම් කරන්න."], "bullets": ["බීජ මූලාශ්‍රය තහවුරු කරන්න", "වියදම් සටහන් කරන්න"], "table": {"columns": ["අයිතමය", "සටහන"], "rows": [["බීජ", "තහවුරු කළ මූලාශ්‍රයක්"]]}}],
            "assumptions": ["කන්නය තවම තහවුරු කර නැත."], "limitations": ["සජීවී මිල දත්ත මෙහි නොමැත."], "next_actions": ["ප්‍රදේශීය මිල ගණන් ලබාගන්න."],
        }
    else:
        report = {
            "title": "பொலன்னறுவை 1 ஏக்கர் நெல் சாகுபடி அறிக்கை",
            "executive_summary": "இது நெல் சாகுபடி, செலவு, அறுவடை மற்றும் சந்தைப்படுத்தலுக்கான சுருக்கமான சோதனை அறிக்கை.",
            "sections": [{"heading": "1. சாகுபடி திட்டம்", "paragraphs": ["நிலத்தை தயார் செய்து நீர் மற்றும் வானிலை நிலைக்கு ஏற்ப வயல் பணிகளை திட்டமிடவும்."], "bullets": ["விதை மூலத்தை சரிபார்க்கவும்", "செலவுகளை பதிவு செய்யவும்"], "table": {"columns": ["பொருள்", "குறிப்பு"], "rows": [["விதை", "சரிபார்க்கப்பட்ட மூலம்"]]}}],
            "assumptions": ["பருவம் இன்னும் உறுதிப்படுத்தப்படவில்லை."], "limitations": ["நேரடி சந்தை விலை தரவு இதில் இல்லை."], "next_actions": ["உள்ளூர் விலை மேற்கோள்களைப் பெறவும்."],
        }
    facts = {"language": language, "crop": "Paddy", "location": "Polonnaruwa", "area_value": 1, "area_unit": "acre"}
    return report, facts


def run() -> None:
    for language in ("Sinhala", "Tamil"):
        report, facts = sample_report(language)
        data = _build_pdf(report, facts)
        assert data.startswith(b"%PDF"), language
        assert len(data) > 5000, (language, len(data))
    print("MihiMura Sinhala/Tamil Unicode PDF smoke test: PASS")


if __name__ == "__main__":
    run()
