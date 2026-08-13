from __future__ import annotations
import json
from typing import Any
from app.core.ai import get_gemini_client
from app.core.config import settings


def demo_diagnosis(crop_hint: str, symptoms: str = "", image_count: int = 1) -> dict[str, Any]:
    return {
        "crop": crop_hint if crop_hint and crop_hint != "Auto-detect" else "Chilli",
        "crop_confidence": 0.92,
        "quality": "acceptable",
        "image_count": image_count,
        "observed_symptoms": [x.strip() for x in symptoms.split(',') if x.strip()][:6] or ["localized yellowing", "small irregular lesions"],
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
        "disclaimer": "A phone image alone cannot confirm many crop diseases.",
        "provider": "demo",
    }


def analyze_crop_images(images: list[tuple[bytes, str]], crop_hint: str = "", symptoms: str = "") -> dict[str, Any]:
    if not images:
        return demo_diagnosis(crop_hint, symptoms, 0)
    client = get_gemini_client()
    if client is None:
        return demo_diagnosis(crop_hint, symptoms, len(images))
    try:
        from google.genai import types
        prompt = f"""You are MihiMura Crop Vision, a cautious agricultural decision-support agent.
You have {len(images)} guided farmer images. Treat them as complementary evidence, not as laboratory confirmation.
Return valid JSON only with these keys:
- crop: string
- crop_confidence: number 0-1
- quality: string
- image_count: integer
- observed_symptoms: array of strings
- differential: array of 2-4 objects {{condition, confidence 0-1, evidence}}
- root_causes: array of strings
- urgency: string
- safe_steps: array of low-risk actions
- treatment_options: array prioritizing cultural/biological/observation options before chemical options
- expert_review: boolean
- additional_evidence_needed: array of strings
- disclaimer: string

Critical rules:
1. Never claim certainty from images alone.
2. Never provide a pesticide or fertilizer dose/rate.
3. Do not recommend a commercial product from an image.
4. If evidence is weak, conflicting, blurred, or a serious condition is plausible, set expert_review=true.
5. Explicitly describe supporting and conflicting evidence in the differential.
6. Preserve safety and recommend official crop protocols / expert review where appropriate.

Crop hint: {crop_hint or 'unknown'}
Farmer symptom/context notes: {symptoms or 'not provided'}
"""
        parts: list[Any] = []
        for data, mime in images:
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))
        parts.append(prompt)
        response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=parts)
        text = (response.text or '').strip()
        if text.startswith('```'):
            text = text.strip('`')
            text = text[4:].strip() if text.startswith('json') else text
        result = json.loads(text)
        result['provider'] = 'gemini'
        result.setdefault('image_count', len(images))
        return result
    except Exception as exc:
        result = demo_diagnosis(crop_hint, symptoms, len(images))
        result['provider'] = 'demo-fallback'
        result['provider_error'] = str(exc)
        return result


def analyze_crop_image(image_bytes: bytes, mime_type: str, crop_hint: str = "", symptoms: str = "") -> dict[str, Any]:
    """Backward-compatible single-image wrapper."""
    return analyze_crop_images([(image_bytes, mime_type)], crop_hint, symptoms)
