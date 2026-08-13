from __future__ import annotations

from typing import Any
from fastapi import Header, HTTPException

from app.core.config import settings
from app.db import DEMO_UID, ensure_user, get_user
from app.supabase_client import service_client, supabase_configured


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _provider(user: Any) -> str:
    app_meta = _value(user, "app_metadata", {}) or {}
    if isinstance(app_meta, dict):
        return str(app_meta.get("provider") or "supabase")
    return "supabase"


def get_current_user(
    authorization: str | None = Header(default=None),
    x_demo_user: str | None = Header(default=None),
) -> dict[str, Any]:
    if authorization and authorization.lower().startswith("bearer "):
        if not supabase_configured():
            raise HTTPException(status_code=503, detail="Supabase authentication is not configured on the backend")
        token = authorization.split(" ", 1)[1].strip()
        try:
            response = service_client().auth.get_user(token)
            user = _value(response, "user")
            if not user:
                raise ValueError("Supabase returned no authenticated user")
            uid = str(_value(user, "id"))
            email = str(_value(user, "email", "") or "")
            metadata = _value(user, "user_metadata", {}) or {}
            name = "Farmer"
            if isinstance(metadata, dict):
                name = str(metadata.get("full_name") or metadata.get("name") or name)
            ensure_user(uid=uid, email=email, name=name, provider=_provider(user), metadata=metadata)
            profile = get_user(uid)
            if profile.get("status") in {"suspended", "deleted"}:
                raise HTTPException(status_code=403, detail="This MihiMura account is not active")
            return profile
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Invalid or expired Supabase session: {exc}") from exc

    if settings.DEMO_MODE:
        # Demo access is deliberately a single fixed identity. Never accept an
        # arbitrary UUID from a browser header as an impersonation mechanism.
        uid = DEMO_UID
        try:
            return ensure_user(uid=uid, email="demo@mihimura.lk", name="Demo Farmer", provider="demo")
        except Exception as exc:
            if not supabase_configured():
                raise HTTPException(status_code=503, detail="Configure Supabase before using demo access") from exc
            raise

    raise HTTPException(status_code=401, detail="Authentication required")
