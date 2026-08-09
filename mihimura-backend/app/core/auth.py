from __future__ import annotations
from functools import lru_cache
from typing import Any
from fastapi import Header, HTTPException
from app.core.config import settings
from app.db import ensure_user, get_user

@lru_cache(maxsize=1)
def _firebase_auth():
    path = settings.firebase_credentials_path
    if not path or not path.exists():
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials, auth
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(str(path)))
        return auth
    except Exception:
        return None


def get_current_user(authorization: str | None = Header(default=None), x_demo_user: str | None = Header(default=None)) -> dict[str, Any]:
    auth_lib = _firebase_auth()
    if authorization and authorization.lower().startswith("bearer ") and auth_lib:
        token = authorization.split(" ", 1)[1]
        try:
            decoded = auth_lib.verify_id_token(token)
            uid = decoded["uid"]
            ensure_user(uid=uid, email=decoded.get("email", ""), name=decoded.get("name", "Farmer"), provider="firebase")
            return get_user(uid)
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Invalid authentication token: {exc}") from exc

    if settings.DEMO_MODE:
        uid = x_demo_user or "demo_farmer_001"
        ensure_user(uid=uid, email="demo@mihimura.lk", name="Demo Farmer", provider="demo")
        return get_user(uid)
    raise HTTPException(status_code=401, detail="Authentication required")
