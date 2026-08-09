from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings


LIVE_TOKEN_URL = "https://generativelanguage.googleapis.com/v1beta/auth_tokens"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def create_voice_session_token(user: dict[str, Any], language: str = "English") -> dict[str, Any]:
    """Create a short-lived Gemini Live API token.

    The long-lived GEMINI_API_KEY never leaves FastAPI. The browser receives only
    the ephemeral token and connects directly to Gemini Live for low-latency audio.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("Gemini is not configured on the backend")

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=30)
    new_session_expires = now + timedelta(minutes=1)

    payload = {
        "uses": 1,
        "expireTime": _iso(expires),
        "newSessionExpireTime": _iso(new_session_expires),
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                LIVE_TOKEN_URL,
                headers={
                    "x-goog-api-key": settings.GEMINI_API_KEY,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Could not reach Gemini Live token service: {exc}") from exc

    if not response.is_success:
        detail = response.text[:1000]
        raise RuntimeError(f"Gemini Live token request failed ({response.status_code}): {detail}")

    data = response.json()
    token = data.get("name")
    if not token:
        raise RuntimeError("Gemini Live token response did not contain a token")

    safe_language = language if language in {"English", "Sinhala", "Tamil"} else "English"
    name = user.get("name") or "Farmer"

    # Keep this prompt short and voice-oriented. The authoritative agricultural
    # reasoning remains behind the consult_mihimura tool (/ask-ai).
    instruction = f"""
You are MihiMura Voice, the real-time voice companion of a Sri Lankan agriculture decision-support platform.
The current user is {name}. The selected application language is {safe_language}.

VOICE AND CONVERSATION STYLE
- Use {safe_language} by default. If the farmer clearly switches language, follow naturally.
- Speak with a mature, energetic, calm adult delivery. Use natural Sri Lankan conversational phrasing.
- In Sinhala and Tamil, prefer simple spoken language used by Sri Lankan farmers; common agricultural English words may be code-switched naturally when useful.
- Keep normal answers concise: usually 2 to 5 short spoken sentences.
- Do not sound like a newsreader and do not read JSON, field names, URLs, or internal agent traces aloud.
- After every answer, stop and listen. Ask at most one follow-up question when more evidence is genuinely needed.

GROUNDING AND SAFETY
- For ANY farm-specific, crop, weather, climate, irrigation, fertilizer, pesticide, disease, task, field-operation, or recommendation question, you MUST call consult_mihimura before answering.
- Treat consult_mihimura as the authoritative decision-support result. Summarize its result faithfully in speech.
- Never invent chemical/fertilizer doses, official alerts, diagnoses, stock, measurements, or certainty.
- If the tool reports uncertainty, a confirmation requirement, or expert escalation, say that clearly.
- Do not execute consequential farm actions directly in this voice session. Explain the proposed action and direct the farmer to the confirmation control when needed.
- You support agricultural decisions; you do not impersonate a certified agronomist.

CONVERSATIONAL LOOP
1. Listen until the farmer finishes speaking.
2. For agriculture/farm decisions, call consult_mihimura with the farmer's complete question.
3. Wait for the tool response.
4. Speak the result naturally in the selected language.
5. Listen for the next question and preserve conversational context.
""".strip()

    return {
        "token": token,
        "expires_at": _iso(expires),
        "new_session_expires_at": _iso(new_session_expires),
        "model": settings.GEMINI_LIVE_MODEL,
        "voice": settings.GEMINI_LIVE_VOICE,
        "language": safe_language,
        "system_instruction": instruction,
    }
