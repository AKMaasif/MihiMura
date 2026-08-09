from __future__ import annotations
from app.core.auth import _firebase_auth

def send_push(token: str, title: str, body: str, data: dict[str,str] | None=None) -> dict:
    if not token: return {"sent":False,"reason":"missing-token"}
    if _firebase_auth() is None: return {"sent":False,"reason":"firebase-admin-not-configured"}
    try:
        from firebase_admin import messaging
        msg=messaging.Message(notification=messaging.Notification(title=title,body=body),data=data or {},token=token)
        return {"sent":True,"message_id":messaging.send(msg)}
    except Exception as exc:
        return {"sent":False,"reason":str(exc)}
