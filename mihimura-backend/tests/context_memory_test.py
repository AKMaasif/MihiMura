"""Regression tests for deterministic MihiMura conversation fact extraction.

This test does not require Supabase or network access.
Run from mihimura-backend:
    python tests/context_memory_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.conversations import extract_facts, report_missing_fields


def run() -> None:
    facts, intent = extract_facts(
        "i want to plant padddy in polannaruwa areaa.. so can you make full report about this.. "
        "and the inital land about 1 accr and i need whole report"
    )
    assert facts["crop"] == "Paddy", facts
    assert facts["location"] == "Polonnaruwa", facts
    assert facts["area_value"] == 1.0, facts
    assert facts["area_unit"] == "acre", facts
    assert intent == "cultivation_report", intent
    assert report_missing_fields(facts) == []

    follow_up, follow_up_intent = extract_facts("now list what are the details you need")
    assert follow_up.get("language") == "English", follow_up
    assert set(follow_up).issubset({"language", "language_confidence"}), follow_up
    assert follow_up_intent is None

    answers, answers_intent = extract_facts("", {"season": "Maha", "irrigation": "Major irrigation"})
    assert answers["season"] == "Maha"
    assert answers["irrigation"] == "Major irrigation"
    assert answers_intent == "continue_workflow"

    print("MihiMura context-memory regression test: PASS")


if __name__ == "__main__":
    run()
