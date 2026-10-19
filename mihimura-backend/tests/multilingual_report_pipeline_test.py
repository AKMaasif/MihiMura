"""Offline regression test for the multilingual report localization pipeline.

Uses a fake Gemini client so no API key/network/Supabase connection is required.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.reports import (
    ReportMetaTranslationPayload,
    ReportSectionBatchPayload,
    _report_language_matches,
    _translate_report_payload,
)


class FakeModels:
    def generate_content(self, *, model, contents, config):
        schema = config.get("response_schema")
        target = "Tamil" if "into Tamil" in config["system_instruction"] else "Sinhala"
        data = json.loads(contents.split("\n", 1)[1])
        if schema is ReportMetaTranslationPayload:
            native = "தமிழ் அறிக்கை" if target == "Tamil" else "සිංහල වාර්තාව"
            parsed = schema(
                title=native,
                executive_summary=native + " සාරාංශය" if target == "Sinhala" else native + " சுருக்கம்",
                assumptions=[native],
                limitations=[native],
                next_actions=[native],
            )
            return SimpleNamespace(parsed=parsed, text=parsed.model_dump_json())

        if schema is ReportSectionBatchPayload:
            source = data["source_sections"]
            if target == "Tamil":
                heading = "தமிழ் சாகுபடி திட்டம்"
                paragraph = "நெல் சாகுபடி நடவடிக்கைகளை திட்டமிட்டு செயல்படுத்தவும்."
                bullet = "வயல் நிலையை பதிவு செய்யவும்"
            else:
                heading = "සිංහල වගා සැලැස්ම"
                paragraph = "වී වගා කටයුතු සැලසුම් කර ක්‍රියාත්මක කරන්න."
                bullet = "ක්ෂේත්‍ර තත්ත්වය සටහන් කරන්න"
            parsed = schema(
                sections=[
                    {
                        "section_key": item["section_key"],
                        "heading": heading,
                        "paragraphs": [paragraph],
                        "bullets": [bullet],
                        "table": {"columns": [], "rows": []},
                    }
                    for item in source
                ]
            )
            return SimpleNamespace(parsed=parsed, text=parsed.model_dump_json())

        raise AssertionError(f"Unexpected schema: {schema}")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def source_report() -> dict:
    return {
        "title": "English report",
        "executive_summary": "English summary",
        "sections": [
            {
                "section_key": f"section_{i:02d}",
                "heading": f"Section {i}",
                "paragraphs": ["English paragraph"],
                "bullets": ["English bullet"],
                "table": {"columns": [], "rows": []},
            }
            for i in range(1, 10)
        ],
        "assumptions": ["English assumption"],
        "limitations": ["English limitation"],
        "next_actions": ["English action"],
    }


def run() -> None:
    client = FakeClient()
    for language in ("Sinhala", "Tamil"):
        translated = _translate_report_payload(client, source_report(), language)
        assert translated is not None
        assert len(translated["sections"]) == 9
        assert [s["section_key"] for s in translated["sections"]] == [f"section_{i:02d}" for i in range(1, 10)]
        assert _report_language_matches(translated, language), translated
    print("MihiMura multilingual report pipeline regression test: PASS")


if __name__ == "__main__":
    run()
