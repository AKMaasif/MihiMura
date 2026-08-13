from __future__ import annotations

from typing import Any

from app.services.platform import get_project_context


def load_farmer_context(uid: str, supplied: dict[str, Any]) -> dict[str, Any]:
    """Resolve authorized farm context without overwriting explicit conversation facts.

    Context precedence is enforced before this function by the conversation service:
    current message > conversation memory > owned project > profile defaults.
    This function only verifies any selected project and fills fields that remain missing.
    """
    trusted = dict(supplied)
    project_id = str(supplied.get("project_id") or "").strip()
    project = get_project_context(uid, project_id) if project_id else None
    if project:
        for key, value in project.items():
            if trusted.get(key) in (None, "", []):
                trusted[key] = value
        trusted.setdefault("context_scope", "owned-project")
    elif project_id:
        trusted["context_scope"] = "unverified-project"
        trusted.pop("project_id", None)
        trusted.pop("farm_id", None)
    else:
        trusted.setdefault("context_scope", "general")
    trusted.setdefault("language", "English")
    trusted.setdefault("location", trusted.get("district") or "Sri Lanka")
    trusted.setdefault("crop", "")
    trusted.setdefault("stage", "")
    return trusted
