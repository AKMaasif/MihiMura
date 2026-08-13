from __future__ import annotations


def send_push(token: str, title: str, body: str, data: dict[str, str] | None = None) -> dict:
    """Remote push transport placeholder for browser-independent delivery.

    MihiMura currently uses persisted in-app notifications plus the browser Notification API.
    Add a standards-based Web Push provider here later without coupling notification delivery to authentication.
    """
    if not token:
        return {"sent": False, "reason": "missing-subscription"}
    return {
        "sent": False,
        "reason": "remote-web-push-not-configured",
        "title": title,
        "body": body,
        "data": data or {},
    }
