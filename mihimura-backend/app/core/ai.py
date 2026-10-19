"""Shared Gemini client (``None`` when no API key or SDK is available)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Upper bound for a single model call so a stuck request cannot hang an API worker.
REQUEST_TIMEOUT_MS = 90_000

try:
    from google import genai
except ImportError:  # SDK not installed: agents use their deterministic fallbacks
    genai = None

client: Any | None = None
if genai is not None and settings.GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options={"timeout": REQUEST_TIMEOUT_MS})
    except TypeError:
        # Older SDKs without http_options support.
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as exc:
        logger.error("Gemini init failed: %s", exc)


def get_gemini_client() -> Any | None:
    return client
