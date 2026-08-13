import logging
from typing import Any
from app.core.config import settings
logger=logging.getLogger(__name__); client:Any|None=None
try:
    from google import genai
except ImportError:
    genai=None
if genai is not None and settings.GEMINI_API_KEY:
    try: client=genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as exc: logger.error('Gemini init failed: %s',exc)
def get_gemini_client()->Any|None: return client
