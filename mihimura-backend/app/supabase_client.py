from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import settings

try:
    from supabase import Client, create_client
except ImportError:  # Allows import/build before dependencies are installed.
    Client = Any  # type: ignore[assignment,misc]
    create_client = None  # type: ignore[assignment]


@lru_cache(maxsize=1)
def service_client() -> Client:
    if not settings.supabase_configured:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    if create_client is None:
        raise RuntimeError("The Python 'supabase' package is not installed.")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)  # type: ignore[arg-type]


def supabase_configured() -> bool:
    return settings.supabase_configured and create_client is not None


def first(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None
