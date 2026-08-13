from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

SUPPORTED_LANGUAGES = ("English", "Sinhala", "Tamil")


@dataclass(frozen=True)
class LanguageDetection:
    language: str
    confidence: float
    sinhala_chars: int
    tamil_chars: int
    latin_chars: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_language(value: Any, fallback: str = "English") -> str:
    text = str(value or "").strip().lower()
    if text in {"sinhala", "si", "si-lk", "සිංහල"}:
        return "Sinhala"
    if text in {"tamil", "ta", "ta-lk", "தமிழ்"}:
        return "Tamil"
    if text in {"english", "en", "en-lk"}:
        return "English"
    return fallback if fallback in SUPPORTED_LANGUAGES else "English"


def detect_language(text: str, fallback: str = "English") -> LanguageDetection:
    """Detect English/Sinhala/Tamil cheaply and deterministically.

    Sinhala and Tamil use distinct Unicode blocks, so script detection is much more
    reliable for these three languages than asking the LLM on every turn. Mixed-script
    messages are classified by the dominant supported script. Short punctuation/numeric
    messages fall back to the supplied conversation/profile language.
    """
    value = text or ""
    sinhala = sum(1 for ch in value if "\u0d80" <= ch <= "\u0dff")
    tamil = sum(1 for ch in value if "\u0b80" <= ch <= "\u0bff")
    latin = len(re.findall(r"[A-Za-z]", value))
    total = sinhala + tamil + latin

    if total == 0:
        return LanguageDetection(normalize_language(fallback), 0.35, sinhala, tamil, latin)

    # A few native-script characters are enough to make the language highly reliable.
    if sinhala >= tamil and sinhala >= latin and sinhala > 0:
        confidence = min(0.995, 0.72 + (sinhala / max(total, 1)) * 0.27)
        return LanguageDetection("Sinhala", confidence, sinhala, tamil, latin)
    if tamil >= sinhala and tamil >= latin and tamil > 0:
        confidence = min(0.995, 0.72 + (tamil / max(total, 1)) * 0.27)
        return LanguageDetection("Tamil", confidence, sinhala, tamil, latin)

    # If native script is present in a mixed sentence, prefer it when it is not just a
    # one-character fragment. This handles messages such as "weather එක කොහොමද?".
    if sinhala >= 2 and sinhala >= tamil:
        return LanguageDetection("Sinhala", 0.83, sinhala, tamil, latin)
    if tamil >= 2 and tamil > sinhala:
        return LanguageDetection("Tamil", 0.83, sinhala, tamil, latin)

    return LanguageDetection("English", min(0.98, 0.68 + (latin / max(total, 1)) * 0.28), sinhala, tamil, latin)


def language_code(language: str) -> str:
    normalized = normalize_language(language)
    return {"English": "en-LK", "Sinhala": "si-LK", "Tamil": "ta-LK"}[normalized]
