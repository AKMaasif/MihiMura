from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.agents.prompts import tts_prompt, voice_system_prompt
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

    # The authoritative agricultural reasoning stays behind consult_mihimura (/ask-ai).
    instruction = voice_system_prompt(name, safe_language)

    return {
        "token": token,
        "expires_at": _iso(expires),
        "new_session_expires_at": _iso(new_session_expires),
        "model": settings.GEMINI_LIVE_MODEL,
        "voice": settings.GEMINI_LIVE_VOICE,
        "language": safe_language,
        "system_instruction": instruction,
    }


# ---------------------------------------------------------------------------
# Reference-style voice output: existing /ask-ai result -> Gemini TTS audio
# This path does not depend on Gemini Live model availability.
# ---------------------------------------------------------------------------
import base64
import io
import wave

TTS_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _find_audio_content(value: Any) -> dict[str, Any] | None:
    """Find the first inline audio block returned by the Interactions REST API."""
    if isinstance(value, dict):
        if value.get("type") == "audio" and value.get("data"):
            return value
        # SDK-style response shapes are also tolerated for easier future migration.
        output_audio = value.get("output_audio")
        if isinstance(output_audio, dict) and output_audio.get("data"):
            return output_audio
        for child in value.values():
            found = _find_audio_content(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_audio_content(child)
            if found:
                return found
    return None


def _pcm_to_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(max(1, channels))
        wf.setsampwidth(2)  # Gemini TTS PCM is 16-bit.
        wf.setframerate(sample_rate or 24000)
        wf.writeframes(pcm)
    return out.getvalue()


def synthesize_voice(text: str, language: str = "English") -> tuple[bytes, str]:
    """Generate speech for an already-grounded MihiMura answer.

    Uses the Gemini TTS model through the Interactions REST API. This intentionally
    does not use the Gemini Live API, so it works even when the API key does not
    expose a Live model in models.list.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("Gemini is not configured on the backend")

    clean_text = (text or "").strip()
    if not clean_text:
        raise RuntimeError("No text was provided for speech synthesis")

    safe_language = language if language in {"English", "Sinhala", "Tamil"} else "English"
    prompt = tts_prompt(safe_language, clean_text)

    payload = {
        "model": settings.GEMINI_TTS_MODEL,
        "input": prompt,
        "response_format": {"type": "audio"},
        "generation_config": {
            "speech_config": [
                {"voice": settings.GEMINI_TTS_VOICE}
            ]
        },
    }

    last_detail = ""
    for attempt in range(2):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    TTS_INTERACTIONS_URL,
                    headers={
                        "x-goog-api-key": settings.GEMINI_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            last_detail = str(exc)
            if attempt == 0:
                continue
            raise RuntimeError(f"Could not reach Gemini TTS service: {exc}") from exc

        if not response.is_success:
            last_detail = response.text[:1200]
            if attempt == 0 and response.status_code >= 500:
                continue
            raise RuntimeError(f"Gemini TTS request failed ({response.status_code}): {last_detail}")

        data = response.json()
        audio = _find_audio_content(data)
        if not audio or not audio.get("data"):
            last_detail = str(data)[:1200]
            if attempt == 0:
                continue
            raise RuntimeError(f"Gemini TTS returned no audio data: {last_detail}")

        try:
            raw = base64.b64decode(audio["data"])
        except Exception as exc:
            raise RuntimeError("Gemini TTS returned invalid base64 audio") from exc

        mime = str(audio.get("mime_type") or audio.get("mimeType") or "audio/l16")
        sample_rate = int(audio.get("sample_rate") or audio.get("sampleRate") or 24000)
        channels = int(audio.get("channels") or 1)

        if mime == "audio/wav" and raw[:4] == b"RIFF":
            return raw, "audio/wav"

        # The TTS examples commonly expose 24 kHz 16-bit mono PCM. Wrap it so
        # browsers can play the response directly through an <audio> element.
        return _pcm_to_wav(raw, sample_rate=sample_rate, channels=channels), "audio/wav"

    raise RuntimeError(f"Gemini TTS failed: {last_detail or 'unknown error'}")
