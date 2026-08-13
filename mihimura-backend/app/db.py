from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.supabase_client import first, service_client

DEMO_UID = "00000000-0000-0000-0000-000000000001"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_profile(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    out = dict(record)
    # Keep the old frontend contract while using Supabase UUIDs internally.
    out["uid"] = str(out.get("id") or out.get("uid") or "")
    return out


def get_user(uid: str) -> dict[str, Any]:
    result = service_client().table("profiles").select("*").eq("id", uid).limit(1).execute()
    return _clean_profile(first(result.data))


def ensure_user(
    uid: str,
    email: str = "",
    name: str = "Farmer",
    provider: str = "supabase",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Validate real IDs early so malformed demo headers cannot create rows.
    UUID(str(uid))
    existing = get_user(uid)
    if existing:
        patch: dict[str, Any] = {}
        if email and not existing.get("email"):
            patch["email"] = email
        if name and (not existing.get("name") or existing.get("name") == "Farmer"):
            patch["name"] = name
        if provider and not existing.get("provider"):
            patch["provider"] = provider
        if patch:
            service_client().table("profiles").update(patch).eq("id", uid).execute()
        return get_user(uid)

    meta = metadata or {}
    payload = {
        "id": uid,
        "email": email,
        "name": name or meta.get("full_name") or meta.get("name") or "Farmer",
        "provider": provider,
        "role": "farmer",
        "language": "English",
        "district": "Ampara" if provider == "demo" else None,
        "onboarding_complete": provider == "demo",
        "professional_verified": False,
        "status": "active",
    }
    service_client().table("profiles").upsert(payload).execute()
    return get_user(uid)


def audit(actor: str, action: str, entity: str, details: dict[str, Any]) -> None:
    service_client().table("audit_events").insert(
        {
            "actor": actor,
            "action": action,
            "entity": entity,
            "details": details,
            "created_at": now_iso(),
        }
    ).execute()
