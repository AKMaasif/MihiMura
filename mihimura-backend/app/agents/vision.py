"""Crop Vision agent: cautious differential diagnosis from 1-4 farmer photos."""

from __future__ import annotations

from typing import Any

from app.agents.contracts import VisionOutput, clamp_confidence
from app.agents.llm import LLMError, LLMUnavailable, generate_structured
from app.agents.prompts import PROMPT_VERSION, VISION_SYSTEM_PROMPT
from app.core.config import settings
from app.services.language import normalize_language

DISCLAIMER = "A phone image alone cannot confirm many crop diseases."


def demo_diagnosis(crop_hint: str, symptoms: str = "", image_count: int = 1) -> dict[str, Any]:
    """Illustrative result used when no model is configured or the model fails."""
    return {
        "crop": crop_hint if crop_hint and crop_hint != "Auto-detect" else "Chilli",
        "crop_confidence": 0.92,
        "quality": "acceptable",
        "image_count": image_count,
        "observed_symptoms": [x.strip() for x in symptoms.split(",") if x.strip()][:6] or ["localized yellowing", "small irregular lesions"],
        "differential": [
            {"condition": "nutrient / water stress", "confidence": 0.63, "evidence": "Yellowing can be compatible but is non-specific."},
            {"condition": "early fungal leaf spot", "confidence": 0.41, "evidence": "Some lesions are compatible; field context and another viewpoint are required."},
        ],
        "root_causes": ["water stress", "nutrient imbalance", "possible pathogen"],
        "urgency": "monitor within 24 hours",
        "safe_steps": ["Photograph the leaf underside", "Inspect 10 nearby plants", "Record recent irrigation and treatments"],
        "treatment_options": ["Improve observation and field hygiene", "Use an approved crop protocol after confirmation"],
        "expert_review": False,
        "additional_evidence_needed": ["leaf underside", "whole-plant view", "recent treatment history"],
        "disclaimer": DISCLAIMER,
        "provider": "demo",
    }


def _sanitize(result: dict[str, Any], image_count: int) -> dict[str, Any]:
    result["crop_confidence"] = clamp_confidence(result.get("crop_confidence"), 0.5)
    differential = sorted(
        ({**d, "confidence": clamp_confidence(d.get("confidence"), 0.0)} for d in result.get("differential") or []),
        key=lambda d: d["confidence"],
        reverse=True,
    )[:4]
    result["differential"] = differential
    # Weak or ambiguous evidence always goes to a human.
    top = differential[0]["confidence"] if differential else 0.0
    second = differential[1]["confidence"] if len(differential) > 1 else 0.0
    if top < 0.5 or (top - second) < 0.1:
        result["expert_review"] = True
    result["image_count"] = image_count
    result["disclaimer"] = result.get("disclaimer") or DISCLAIMER
    return result


def analyze_crop_images(images: list[tuple[bytes, str]], crop_hint: str = "", symptoms: str = "", language: str = "English") -> dict[str, Any]:
    if not images:
        return demo_diagnosis(crop_hint, symptoms, 0)
    payload = {
        "image_count": len(images),
        "crop_hint": crop_hint or "unknown",
        "farmer_notes": symptoms or "not provided",
        "language": normalize_language(language),
    }
    try:
        result = generate_structured(
            system=VISION_SYSTEM_PROMPT,
            payload=payload,
            schema=VisionOutput,
            images=images,
            temperature=0.2,
        )
    except LLMUnavailable:
        return demo_diagnosis(crop_hint, symptoms, len(images))
    except LLMError as exc:
        result = demo_diagnosis(crop_hint, symptoms, len(images))
        result["provider"] = "demo-fallback"
        result["provider_error"] = str(exc)
        return result
    result = _sanitize(result, len(images))
    result.update({"provider": "gemini", "model": settings.GEMINI_MODEL, "prompt_version": PROMPT_VERSION})
    return result


def analyze_crop_image(image_bytes: bytes, mime_type: str, crop_hint: str = "", symptoms: str = "") -> dict[str, Any]:
    """Single-image wrapper kept for older callers."""
    return analyze_crop_images([(image_bytes, mime_type)], crop_hint, symptoms)
