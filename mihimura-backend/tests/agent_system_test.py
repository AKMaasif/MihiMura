"""End-to-end regression test for the redesigned agent system.

Runs offline: external data services fail closed, and the model is either
absent (deterministic paths) or a fake client that returns scripted JSON.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DEMO_MODE", "true")

from app.agents import llm  # noqa: E402
from app.agents.orchestrator import orchestrator  # noqa: E402
from app.agents.vision import analyze_crop_images  # noqa: E402

KNOWN_DECISION_FIELDS = {
    "response_type", "summary", "recommended_action", "why", "confidence", "alternatives", "do_not_do",
    "sources", "confirmation_required", "follow_up", "risk_level", "counterfactual", "agent_trace",
    "clarification_fields", "suggested_actions", "memory_patch", "report_ready", "auto_generate_report",
    "requested_mode", "detected_mode", "effective_mode", "detected_intent", "provider", "latency_ms",
}


class FakeClient:
    """Mimics ``google.genai.Client`` closely enough for ``generate_structured``."""

    def __init__(self, reply: dict) -> None:
        self.reply = reply
        self.calls: list[dict] = []
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(parsed=None, text=json.dumps(self.reply))


def ask(question: str, *, mode: str = "auto", context: dict | None = None, memory: dict | None = None) -> dict:
    ctx = {"language": "English", "interaction_mode": mode, **(context or {})}
    return orchestrator.process_farmer_request(question, ctx, "test-user", history=[], memory=memory or {})


def assert_contract(out: dict) -> None:
    missing = KNOWN_DECISION_FIELDS - set(out)
    assert not missing, f"missing contract fields: {missing}"
    assert 0.0 <= out["confidence"] <= 1.0
    assert all(isinstance(s, dict) and s.get("name") for s in out["sources"])


def with_model(reply: dict):
    fake = FakeClient(reply)
    llm.get_gemini_client = lambda: fake  # type: ignore[assignment]
    return fake


def without_model() -> None:
    llm.get_gemini_client = lambda: None  # type: ignore[assignment]


def run() -> None:
    # --- No model configured: every workflow still answers -------------------
    without_model()
    hello = ask("hello")
    assert_contract(hello)
    assert hello["effective_mode"] == "simple_chat" and hello["provider"] == "deterministic-simple-chat"

    weather = ask("will it rain tomorrow?", context={"location": "Galle"})
    assert_contract(weather)
    assert weather["effective_mode"] == "decision_support"
    agents = [x["agent"] for x in weather["agent_trace"]]
    # Honest trace: no coordinates were given, so weather must be reported as not live.
    weather_steps = [x for x in weather["agent_trace"] if x["agent"] == "Micro-Climate Prediction"]
    assert weather_steps and weather_steps[0]["status"] == "watch", weather_steps
    assert "Market Intelligence" not in agents, "market tool must not appear when it did not run"
    assert weather["evidence_quality"]["can_make_current_decision"] is False

    switch = ask("will it rain tomorrow?", mode="simple_chat")
    assert switch["response_type"] == "mode_switch" and switch["suggested_mode"] == "decision_support"

    memory = {"known_facts": {"crop": "Paddy", "location": "Polonnaruwa", "area_value": 1.0, "area_unit": "acre"}, "missing_fields": [], "active_intent": "cultivation_report"}
    report = ask("make a complete report for 1 acre paddy in Polonnaruwa", memory=memory)
    assert_contract(report)
    assert report["response_type"] == "report_ready" and report["auto_generate_report"] is True

    clarify = ask("give me a full cultivation report", memory={"known_facts": {"crop": "Paddy"}, "active_intent": "cultivation_report"})
    assert clarify["response_type"] == "clarification"
    assert {f["key"] for f in clarify["clarification_fields"]} >= {"location", "area_value"}

    # --- Model invents a dose and tries to overwrite location ----------------
    fake = with_model({
        "response_type": "answer",
        "summary": "Spray mancozeb at 2.5 g per litre tomorrow morning.",
        "recommended_action": "Apply 50 kg per acre of urea after the rain.",
        "why": "Leaf spot is likely.",
        "alternatives": ["Use 1-2 ml/L of a fungicide"],
        "do_not_do": [],
        "sources": [],
        "confirmation_required": False,
        "follow_up": "",
        "risk_level": "low",
        "counterfactual": "",
        "suggested_actions": [],
        "memory_patch": [{"key": "crop", "value": "Chilli"}, {"key": "area_value", "value": "2"}],
    })
    risky = ask("what fungicide dose should I spray on my chilli tomorrow?", context={"location": "Galle", "lat": 6.05, "lon": 80.22})
    assert_contract(risky)
    assert risky["provider"] == "gemini"
    text = " ".join([risky["summary"], risky["recommended_action"], *risky["alternatives"]])
    for invented in ("2.5 g per litre", "50 kg per acre", "1-2 ml/L"):
        assert invented not in text, f"unsupported rate leaked: {invented}"
    assert risky["expert_escalation_recommended"] is True
    assert risky["confirmation_required"] is True
    assert risky["response_type"] in {"confirmation_required", "expert_escalation"}
    assert risky["memory_patch"] == {"crop": "Chilli", "area_value": 2.0}
    # The model never sees internal plumbing, and instructions stay separate from data.
    call = fake.calls[-1]
    assert "system_instruction" in call["config"] and "TURN_DATA" in call["contents"]
    assert '"lat"' not in call["contents"].split('"context"')[1].split("}")[0]

    # --- Model failure falls back to the localized deterministic answer ------
    llm.get_gemini_client = lambda: SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_: (_ for _ in ()).throw(RuntimeError("quota"))))  # type: ignore[assignment]
    failed = ask("can i apply fertilizer tomorrow?", context={"location": "Galle"})
    assert_contract(failed)
    assert failed["provider"] == "deterministic-decision-fallback" and "quota" in failed["provider_error"]

    # --- Chat with the model ------------------------------------------------------
    with_model({"summary": "Paddy fields are levelled so water stands evenly.", "memory_patch": [{"key": "location", "value": "Jaffna"}]})
    chat = ask("explain why paddy fields are levelled")
    assert_contract(chat)
    assert chat["provider"] == "gemini" and chat["memory_patch"] == {}, "location must never come from the model"

    # --- Vision: weak differential is always sent to an expert -------------------
    try:
        import google.genai.types  # noqa: F401
    except ImportError:  # SDK not installed in this environment: provide the one helper used
        import types as _types

        fake_types = _types.ModuleType("google.genai.types")
        fake_types.Part = SimpleNamespace(from_bytes=lambda data, mime_type: {"mime_type": mime_type, "size": len(data)})
        sys.modules.setdefault("google", _types.ModuleType("google"))
        sys.modules.setdefault("google.genai", _types.ModuleType("google.genai"))
        sys.modules["google.genai"].types = fake_types  # type: ignore[attr-defined]
        sys.modules["google.genai.types"] = fake_types
    with_model({
        "crop": "Chilli", "crop_confidence": 1.4, "quality": "blurred",
        "differential": [{"condition": "leaf spot", "confidence": 0.45, "evidence": "spots"}, {"condition": "nutrient stress", "confidence": 0.40, "evidence": "yellowing"}],
        "expert_review": False,
    })
    vision = analyze_crop_images([(b"fake-bytes", "image/jpeg")], "Chilli")
    assert vision["crop_confidence"] == 1.0 and vision["expert_review"] is True and vision["image_count"] == 1

    # --- Model fallback: an unavailable flagship is skipped automatically -----
    from app.agents.llm import models_for

    tried: list[str] = []

    def flaky_generate(*, model, contents, config):
        tried.append(model)
        if model == models_for("reasoning")[0]:
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota limit 0 for this model")
        return SimpleNamespace(parsed=None, text=json.dumps({"summary": "ok", "recommended_action": "ok", "why": "ok"}))

    llm.get_gemini_client = lambda: SimpleNamespace(models=SimpleNamespace(generate_content=flaky_generate))  # type: ignore[assignment]
    fallback = ask("can i apply fertilizer tomorrow?", context={"location": "Galle"})
    assert fallback["provider"] == "gemini", fallback.get("provider_error")
    assert tried[0] == models_for("reasoning")[0] and fallback["model"] == models_for("reasoning")[1], (tried, fallback["model"])
    assert models_for("fast")[0] != models_for("reasoning")[0], "chat should use the fast tier"

    without_model()
    print("MihiMura agent system regression test: PASS")


if __name__ == "__main__":
    run()
