from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.db import audit, get_user, now_iso
from app.supabase_client import first, service_client


def _table(name: str):
    return service_client().table(name)


def _one(name: str, **filters: Any) -> dict[str, Any] | None:
    q = _table(name).select("*")
    for key, value in filters.items():
        q = q.eq(key, value)
    return first(q.limit(1).execute().data)


def _many(name: str, **filters: Any) -> list[dict[str, Any]]:
    q = _table(name).select("*")
    for key, value in filters.items():
        q = q.eq(key, value)
    data = q.execute().data or []
    return list(data) if isinstance(data, list) else []


def _sort(data: list[dict[str, Any]], key: str = "created_at", reverse: bool = True) -> list[dict[str, Any]]:
    return sorted(data, key=lambda x: str(x.get(key) or ""), reverse=reverse)


def _owned(table: str, uid: str) -> list[dict[str, Any]]:
    return _sort(_many(table, owner_uid=uid))


def _required(p: dict[str, Any], *keys: str) -> None:
    missing = [k for k in keys if p.get(k) in (None, "", [])]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")


def _require_farm(uid: str, farm_id: str) -> dict[str, Any]:
    farm = _one("farms", id=farm_id, owner_uid=uid)
    if not farm or farm.get("status") == "archived":
        raise PermissionError("Farm not found or not accessible")
    return farm


def _require_project(uid: str, project_id: str) -> dict[str, Any]:
    project = _one("projects", id=project_id, owner_uid=uid)
    if not project:
        raise PermissionError("Project not found or not accessible")
    return project


def profile(uid: str):
    return get_user(uid)


def update_profile(uid: str, p: dict[str, Any]):
    fields = {
        "name",
        "phone",
        "role",
        "language",
        "district",
        "ds_division",
        "gn_division",
        "location_consent",
        "lat",
        "lon",
        "guidance_mode",
        "irrigation",
        "experience",
        "notification_channels",
        "accessibility_json",
        "primary_crops_json",
        "farm_type",
        "onboarding_complete",
    }
    patch: dict[str, Any] = {}
    for f in fields:
        if f not in p:
            continue
        value = p[f]
        if f == "role":
            value = value if value in {"farmer", "manager", "agronomist", "supplier", "analyst"} else "farmer"
        if f in {"location_consent", "onboarding_complete"}:
            value = bool(value)
        patch[f] = value
    if "role" in patch and patch["role"] != (get_user(uid) or {}).get("role"):
        # A new role must be re-verified by an administrator.
        patch["professional_verified"] = False
    if patch:
        _table("profiles").update(patch).eq("id", uid).execute()
        audit(uid, "update_profile", uid, {k: p[k] for k in p if k in fields})
    return profile(uid)


def list_farms(uid: str):
    return _owned("farms", uid)


def create_farm(uid: str, p: dict[str, Any]):
    _required(p, "name")
    fid = f"farm_{uuid4().hex[:8]}"
    payload = {
        "id": fid,
        "owner_uid": uid,
        "name": p["name"],
        "district": p.get("district", "Ampara"),
        "province": p.get("province", "Eastern"),
        "area": float(p.get("area", 0)),
        "water_source": p.get("water_source", ""),
        "soil_type": p.get("soil_type", ""),
        "land_type": p.get("land_type", ""),
        "crop": p.get("crop", ""),
        "lat": p.get("lat"),
        "lon": p.get("lon"),
        "boundary": p.get("boundary"),
        "status": "active",
        "created_at": now_iso(),
    }
    _table("farms").insert(payload).execute()
    audit(uid, "create_farm", fid, p)
    return _one("farms", id=fid)


def update_farm(uid: str, farm_id: str, p: dict[str, Any]):
    _require_farm(uid, farm_id)
    allowed = {k: v for k, v in p.items() if k in {"name", "district", "province", "area", "water_source", "soil_type", "land_type", "crop", "lat", "lon", "status"}}
    if "boundary" in p:
        allowed["boundary"] = p["boundary"]
    if allowed:
        _table("farms").update(allowed).eq("id", farm_id).eq("owner_uid", uid).execute()
        audit(uid, "update_farm", farm_id, {k: v for k, v in p.items() if k != "boundary"} | ({"boundary_points": len(p.get("boundary") or [])} if "boundary" in p else {}))
    return _one("farms", id=farm_id, owner_uid=uid)


def list_projects(uid: str):
    projects = _many("projects", owner_uid=uid)
    farms = {f["id"]: f for f in _many("farms", owner_uid=uid)}
    out = []
    for project in projects:
        farm = farms.get(project.get("farm_id"), {})
        out.append({
            **project,
            "farm_name": farm.get("name"),
            "district": farm.get("district"),
            "province": farm.get("province"),
            "area": farm.get("area"),
            "lat": farm.get("lat"),
            "lon": farm.get("lon"),
        })
    return _sort(out)


def get_project_context(uid: str, project_id: str) -> dict[str, Any] | None:
    project = _one("projects", id=project_id, owner_uid=uid)
    if not project:
        return None
    farm = _one("farms", id=project["farm_id"], owner_uid=uid) or {}
    return {
        "project_id": project.get("id"),
        "crop": project.get("crop"),
        "variety": project.get("variety"),
        "stage": project.get("stage"),
        "season": project.get("season"),
        "irrigation_mode": project.get("irrigation_mode"),
        "health_score": project.get("health_score"),
        "risk_score": project.get("risk_score"),
        "farm_id": farm.get("id"),
        "farm_name": farm.get("name"),
        "district": farm.get("district"),
        "province": farm.get("province"),
        "area": farm.get("area"),
        "water_source": farm.get("water_source"),
        "soil_type": farm.get("soil_type"),
        "lat": farm.get("lat"),
        "lon": farm.get("lon"),
    }


def create_project(uid: str, p: dict[str, Any]):
    _required(p, "farm_id", "crop")
    _require_farm(uid, p["farm_id"])
    pid = f"proj_{uuid4().hex[:8]}"
    payload = {
        "id": pid,
        "farm_id": p["farm_id"],
        "owner_uid": uid,
        "crop": p["crop"],
        "variety": p.get("variety", ""),
        "purpose": p.get("purpose", ""),
        "season": p.get("season", ""),
        "stage": p.get("stage", "Planning"),
        "start_date": p.get("start_date") or None,
        "actual_start_date": p.get("actual_start_date") or None,
        "target_harvest": p.get("target_harvest") or None,
        "irrigation_mode": p.get("irrigation_mode", ""),
        "seed_source": p.get("seed_source", ""),
        "health_score": int(p.get("health_score", 80)),
        "risk_score": int(p.get("risk_score", 30)),
        "budget": float(p.get("budget", 0)),
        "status": p.get("status", "active"),
        "notes": p.get("notes", ""),
        "created_at": now_iso(),
    }
    _table("projects").insert(payload).execute()
    audit(uid, "create_project", pid, p)
    return _one("projects", id=pid)


def list_tasks(uid: str):
    tasks = _many("tasks", owner_uid=uid)
    projects = {p["id"]: p for p in _many("projects", owner_uid=uid)}
    farms = {f["id"]: f for f in _many("farms", owner_uid=uid)}
    out = []
    for task in tasks:
        project = projects.get(task.get("project_id"), {})
        farm = farms.get(project.get("farm_id"), {})
        out.append({**task, "crop": project.get("crop"), "farm_name": farm.get("name")})
    return sorted(out, key=lambda x: str(x.get("due_at") or ""))


def create_task(uid: str, p: dict[str, Any]):
    _required(p, "project_id", "title", "due_at")
    _require_project(uid, p["project_id"])
    tid = f"task_{uuid4().hex[:8]}"
    payload = {
        "id": tid,
        "project_id": p["project_id"],
        "owner_uid": uid,
        "title": p["title"],
        "task_type": p.get("task_type", "General"),
        "due_at": p["due_at"],
        "priority": p.get("priority", "medium"),
        "weather_dependency": p.get("weather_dependency", ""),
        "status": "pending",
        "instructions": p.get("instructions", ""),
        "materials": p.get("materials", ""),
        "assigned_to": p.get("assigned_to", "Self"),
        "completion_note": "",
        "schedule_reason": p.get("schedule_reason", ""),
        "created_at": now_iso(),
    }
    _table("tasks").insert(payload).execute()
    audit(uid, "create_task", tid, p)
    return _one("tasks", id=tid)


def update_task(uid: str, tid: str, p: dict[str, Any]):
    if not _one("tasks", id=tid, owner_uid=uid):
        raise PermissionError("Task not found or not accessible")
    allowed = {k: v for k, v in p.items() if k in {"status", "due_at", "assigned_to", "completion_note", "schedule_reason"}}
    if allowed:
        _table("tasks").update(allowed).eq("id", tid).eq("owner_uid", uid).execute()
        audit(uid, "update_task", tid, allowed)
    return _one("tasks", id=tid, owner_uid=uid)


def list_observations(uid: str):
    return _owned("observations", uid)


def create_observation(uid: str, p: dict[str, Any]):
    _required(p, "project_id", "note")
    _require_project(uid, p["project_id"])
    oid = f"obs_{uuid4().hex[:8]}"
    payload = {
        "id": oid,
        "project_id": p["project_id"],
        "owner_uid": uid,
        "created_at": now_iso(),
        "type": p.get("type", "field-note"),
        "note": p["note"],
        "growth_stage": p.get("growth_stage", ""),
        "rainfall": p.get("rainfall", ""),
        "irrigation": p.get("irrigation", ""),
        "pest_count": int(p.get("pest_count", 0)),
        "symptoms": p.get("symptoms", ""),
        "action_taken": p.get("action_taken", ""),
    }
    _table("observations").insert(payload).execute()
    audit(uid, "create_observation", oid, p)
    return _one("observations", id=oid)


def list_expenses(uid: str):
    return _owned("expenses", uid)


def create_expense(uid: str, p: dict[str, Any]):
    _required(p, "project_id", "amount")
    _require_project(uid, p["project_id"])
    eid = f"exp_{uuid4().hex[:8]}"
    payload = {"id": eid, "project_id": p["project_id"], "owner_uid": uid, "created_at": now_iso(), "category": p.get("category", "Other"), "amount": float(p["amount"]), "note": p.get("note", "")}
    _table("expenses").insert(payload).execute()
    audit(uid, "create_expense", eid, p)
    return _one("expenses", id=eid)


def list_harvests(uid: str):
    return _sort(_many("harvests", owner_uid=uid), key="harvest_date")


def create_harvest(uid: str, p: dict[str, Any]):
    _required(p, "project_id")
    _require_project(uid, p["project_id"])
    hid = f"harv_{uuid4().hex[:8]}"
    payload = {
        "id": hid,
        "project_id": p["project_id"],
        "owner_uid": uid,
        "harvest_date": p.get("harvest_date", now_iso()[:10]),
        "yield_value": float(p.get("yield_value", 0)),
        "yield_unit": p.get("yield_unit", "kg"),
        "quality": p.get("quality", ""),
        "revenue": float(p.get("revenue", 0)),
        "note": p.get("note", ""),
        "created_at": now_iso(),
    }
    _table("harvests").insert(payload).execute()
    audit(uid, "record_harvest", hid, p)
    return _one("harvests", id=hid)


def list_orders(uid: str):
    return _owned("orders", uid)


MAX_ORDER_QUANTITY = 1000


def _priced_items(raw_items: Any) -> list[dict[str, Any]]:
    """Rebuild order lines from the catalog so the client cannot set prices."""
    catalog = {item["id"]: item for item in PRODUCTS}
    items: list[dict[str, Any]] = []
    for raw in raw_items or []:
        product = catalog.get(str((raw or {}).get("id") or ""))
        if not product:
            raise ValueError("Order contains an unknown product")
        try:
            quantity = int((raw or {}).get("quantity", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("Order quantity must be a whole number") from exc
        if not 1 <= quantity <= MAX_ORDER_QUANTITY:
            raise ValueError(f"Order quantity must be between 1 and {MAX_ORDER_QUANTITY}")
        items.append({
            "id": product["id"],
            "name": product["name"],
            "supplier": product["supplier"],
            "pack": product["pack"],
            "price": product["price"],
            "quantity": quantity,
        })
    if not items:
        raise ValueError("Order must contain at least one item")
    return items


def create_order(uid: str, p: dict[str, Any]):
    _required(p, "project_id")
    _require_project(uid, p["project_id"])
    oid = f"ord_{uuid4().hex[:8]}"
    items = _priced_items(p.get("items"))
    total = sum(float(i["price"]) * i["quantity"] for i in items)
    payload = {
        "id": oid,
        "owner_uid": uid,
        "project_id": p["project_id"],
        "created_at": now_iso(),
        "total": total,
        "status": "confirmed",
        "items": items,
        "delivery_address": p.get("delivery_address", ""),
        "payment_method": p.get("payment_method", "Cash on delivery"),
        "delivery_method": p.get("delivery_method", "Standard"),
        "consent": True,
    }
    _table("orders").insert(payload).execute()
    audit(uid, "confirmed_order", oid, {"total": total, "items": items})
    return _one("orders", id=oid)


def list_expert_cases(uid: str):
    return _owned("expert_cases", uid)


def create_expert_case(uid: str, p: dict[str, Any]):
    _required(p, "project_id", "reason")
    _require_project(uid, p["project_id"])
    cid = f"case_{uuid4().hex[:8]}"
    payload = {
        "id": cid,
        "owner_uid": uid,
        "project_id": p["project_id"],
        "created_at": now_iso(),
        "urgency": p.get("urgency", "medium"),
        "reason": p["reason"],
        "status": "open",
        "evidence": p.get("evidence", ""),
        "preferred_language": p.get("preferred_language", "English"),
        "availability": p.get("availability", ""),
        "expert_decision": "",
    }
    _table("expert_cases").insert(payload).execute()
    audit(uid, "expert_escalation", cid, p)
    return _one("expert_cases", id=cid)


def _privileged(actor: dict[str, Any], roles: set[str]) -> bool:
    if actor.get("provider") == "demo":
        return bool(settings.DEMO_PRIVILEGED)
    return actor.get("role") in roles and bool(actor.get("professional_verified"))


OWNER_CASE_STATUSES = {"open", "closed", "cancelled"}


def update_expert_case_for_actor(actor: dict[str, Any], case_id: str, p: dict[str, Any]):
    privileged = _privileged(actor, {"agronomist", "expert", "admin"})
    if privileged:
        allowed = {k: v for k, v in p.items() if k in {"status", "expert_decision", "availability"}}
    else:
        allowed = {k: v for k, v in p.items() if k == "availability"}
        if p.get("status") in OWNER_CASE_STATUSES:
            allowed["status"] = p["status"]
    target = _one("expert_cases", id=case_id) if privileged else _one("expert_cases", id=case_id, owner_uid=actor["uid"])
    if not target:
        return None
    if allowed:
        _table("expert_cases").update(allowed).eq("id", case_id).execute()
        audit(actor["uid"], "expert_case_update", case_id, allowed | {"privileged_review": privileged})
    return _one("expert_cases", id=case_id)


def list_notifications(uid: str):
    return _owned("notifications", uid)


def create_notification(uid: str, p: dict[str, Any]):
    _required(p, "title", "body")
    nid = f"note_{uuid4().hex[:8]}"
    payload = {
        "id": nid,
        "owner_uid": uid,
        "created_at": now_iso(),
        "scheduled_at": p.get("scheduled_at") or now_iso(),
        "channel": p.get("channel", "in-app"),
        "title": p["title"],
        "body": p["body"],
        "status": p.get("status", "scheduled"),
        "acknowledged": False,
    }
    _table("notifications").insert(payload).execute()
    audit(uid, "schedule_notification", nid, {"channel": payload["channel"], "scheduled_at": payload["scheduled_at"]})
    return _one("notifications", id=nid)


def update_notification(uid: str, nid: str, p: dict[str, Any]):
    if not _one("notifications", id=nid, owner_uid=uid):
        raise PermissionError("Notification not found or not accessible")
    allowed: dict[str, Any] = {}
    if "acknowledged" in p:
        allowed["acknowledged"] = bool(p.get("acknowledged"))
    if p.get("status") in {"scheduled", "sent", "failed", "cancelled"}:
        allowed["status"] = p.get("status")
    if allowed:
        _table("notifications").update(allowed).eq("id", nid).eq("owner_uid", uid).execute()
        audit(uid, "update_notification", nid, allowed)
    return _one("notifications", id=nid, owner_uid=uid)


def list_community_reports(min_count: int = 3):
    rows = [x for x in _many("community_reports") if x.get("anonymized")]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in rows:
        grouped[(item.get("district") or "Unknown", item.get("crop") or "", item.get("report_type") or "symptom")].append(item)
    clusters: list[dict[str, Any]] = []
    for i, ((district, crop, report_type), items) in enumerate(grouped.items()):
        if len(items) < min_count:
            continue
        latest = max(str(x.get("created_at") or "") for x in items)
        severity = "high" if any(x.get("severity") in {"high", "emergency"} for x in items) else "watch"
        clusters.append({
            "id": f"cluster_{i}_{district}_{crop}_{report_type}",
            "district": district,
            "crop": crop,
            "report_type": report_type,
            "report_count": len(items),
            "severity": severity,
            "created_at": latest,
            "note": f"{len(items)} anonymized reports crossed the publication threshold; field verification is recommended before treatment.",
        })
    return _sort(clusters)


def create_community_report(uid: str, p: dict[str, Any]):
    rid = f"comm_{uuid4().hex[:8]}"
    payload = {
        "id": rid,
        "owner_uid": uid,
        "created_at": now_iso(),
        "district": p.get("district", "Ampara"),
        "crop": p.get("crop", ""),
        "report_type": p.get("report_type", "symptom"),
        "severity": p.get("severity", "watch"),
        "note": p.get("note", ""),
        "lat": p.get("lat"),
        "lon": p.get("lon"),
        "anonymized": True,
    }
    _table("community_reports").insert(payload).execute()
    audit(uid, "community_report", rid, {"district": payload["district"], "type": payload["report_type"]})
    return {"id": rid, "status": "queued-for-privacy-threshold"}


def save_device_token(uid: str, token: str, platform: str = "web"):
    # Kept as a generic device/subscription registry; it no longer implies legacy push-provider coupling.
    existing = first(_table("device_tokens").select("*").eq("token", token).limit(1).execute().data)
    payload = {"id": (existing or {}).get("id") or f"device_{uuid4().hex[:8]}", "owner_uid": uid, "token": token, "platform": platform, "created_at": now_iso()}
    _table("device_tokens").upsert(payload).execute()
    audit(uid, "register_device_token", payload["id"], {"platform": platform})
    return {"id": payload["id"], "registered": True, "platform": platform}


def list_device_tokens(uid: str):
    return [{k: x.get(k) for k in ("id", "platform", "created_at")} for x in _owned("device_tokens", uid)]


def audit_log(uid: str | None = None, limit: int = 100):
    data = _many("audit_events", **({"actor": uid} if uid else {}))
    return _sort(data)[:limit]


def request_account_deletion(uid: str):
    stamp = now_iso()
    _table("profiles").update({"status": "deletion_requested", "deletion_requested_at": stamp}).eq("id", uid).execute()
    audit(uid, "account_deletion_requested", uid, {"requested_at": stamp})
    return {
        "status": "deletion_requested",
        "requested_at": stamp,
        "message": "Account deletion is queued. An administrator can complete deletion from Supabase Auth after retention checks.",
    }


def list_expert_cases_for_actor(actor: dict[str, Any]):
    if _privileged(actor, {"agronomist", "expert", "admin"}):
        cases = _many("expert_cases")
        profiles = {p["id"]: p for p in _many("profiles")}
        rank = {"emergency": 0, "high": 1, "medium": 2, "low": 3}
        out = []
        for case in cases:
            farmer = profiles.get(case.get("owner_uid"), {})
            out.append({**case, "farmer_name": farmer.get("name"), "farmer_district": farmer.get("district")})
        return sorted(out, key=lambda x: (rank.get(str(x.get("urgency")), 4), str(x.get("created_at") or "")))
    return list_expert_cases(actor["uid"])


def audit_log_for_actor(actor: dict[str, Any], limit: int = 100):
    if _privileged(actor, {"admin"}):
        return audit_log(None, limit)
    return audit_log(actor["uid"], limit)


def record_agent_run(uid: str, request_text: str, result: dict[str, Any], context: dict[str, Any], conversation_id: str | None = None, message_id: str | None = None):
    rid = f"run_{uuid4().hex[:10]}"
    payload = {
        "id": rid,
        "owner_uid": uid,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "created_at": now_iso(),
        "request": request_text,
        "tools": result.get("agent_trace", []),
        "evidence": result.get("sources", []),
        "provider": result.get("provider", "policy"),
        "model": str(result.get("model", context.get("model", ""))),
        "policy_decision": "confirmation-required" if result.get("confirmation_required") else "advisory",
        "latency_ms": int(result.get("latency_ms", 0)),
        "output": {k: v for k, v in result.items() if k not in {"agent_trace", "sources"}},
    }
    _table("agent_runs").insert(payload).execute()
    return rid


def list_agent_runs_for_actor(actor: dict[str, Any], limit: int = 100):
    data = _many("agent_runs") if _privileged(actor, {"admin"}) else _many("agent_runs", owner_uid=actor["uid"])
    return _sort(data)[:limit]


def list_users_for_admin(actor: dict[str, Any]):
    if not _privileged(actor, {"admin"}):
        return []
    users = _many("profiles")
    return _sort([
        {
            "uid": str(u.get("id")),
            "email": u.get("email"),
            "name": u.get("name"),
            "role": u.get("role"),
            "language": u.get("language"),
            "district": u.get("district"),
            "provider": u.get("provider"),
            "onboarding_complete": u.get("onboarding_complete"),
            "professional_verified": u.get("professional_verified"),
            "status": u.get("status"),
            "created_at": u.get("created_at"),
        }
        for u in users
    ])


def set_professional_verification(actor: dict[str, Any], uid: str, verified: bool):
    if not _privileged(actor, {"admin"}):
        raise PermissionError("Administrator verification required")
    target = get_user(uid)
    if not target:
        return None
    if target.get("role") not in {"agronomist", "supplier", "analyst", "admin"}:
        return target
    _table("profiles").update({"professional_verified": bool(verified)}).eq("id", uid).execute()
    audit(actor["uid"], "professional_verification", uid, {"verified": verified, "role": target.get("role")})
    return get_user(uid)


def set_user_status(actor: dict[str, Any], uid: str, status: str):
    if not _privileged(actor, {"admin"}):
        raise PermissionError("Administrator access required")
    if uid == actor.get("uid"):
        raise PermissionError("Use a separate administrator account to suspend your own account")
    if status not in {"active", "suspended"}:
        raise ValueError("Status must be active or suspended")
    target = get_user(uid)
    if not target:
        return None
    if target.get("provider") == "demo":
        raise PermissionError("The fixed demo identity cannot be suspended")
    _table("profiles").update({"status": status, "updated_at": now_iso()}).eq("id", uid).execute()
    audit(actor["uid"], "user_status_changed", uid, {"status": status})
    return get_user(uid)


PRODUCTS = [
    {"id": "p1", "name": "Certified Paddy Seed – Bg 352", "category": "Seed", "specification": "Certified seed class", "price": 4200, "pack": "20 kg", "supplier": "Eastern Farmer Cooperative", "verified": True, "stock": 42, "distance": "7 km", "compatibility": "Paddy", "safety": "Verify season, seed class and storage condition.", "why": "Matches demo paddy variety; recommendation remains agronomy-first."},
    {"id": "p2", "name": "Yellow Sticky Traps", "category": "Monitoring", "specification": "Non-chemical monitoring aid", "price": 850, "pack": "20 traps", "supplier": "BioField Lanka", "verified": True, "stock": 76, "distance": "16 km", "compatibility": "Chilli", "safety": "Monitoring aid only; does not confirm pest species.", "why": "Low-risk scouting support for flying pest pressure."},
    {"id": "p3", "name": "Field Soil Moisture Meter", "category": "Equipment", "specification": "Portable capacitive meter", "price": 6900, "pack": "1 unit", "supplier": "FarmTech Ampara", "verified": True, "stock": 9, "distance": "22 km", "compatibility": "All crops", "safety": "Calibrate for field soil before decisions.", "why": "Supports verification of water-budget estimates."},
    {"id": "p4", "name": "Protective Field Kit", "category": "Safety", "specification": "Gloves, eye protection, washable apron", "price": 3250, "pack": "1 kit", "supplier": "AgriSafe Cooperative", "verified": True, "stock": 33, "distance": "9 km", "compatibility": "Field operations", "safety": "Use according to task and product label requirements.", "why": "Supports safer field work when protective equipment is required."},
]

SUPPLIERS = [
    {"id": "s1", "name": "Eastern Farmer Cooperative", "district": "Ampara", "verified": True, "rating": 4.8, "delivery": "Same/next day"},
    {"id": "s2", "name": "BioField Lanka", "district": "Batticaloa", "verified": True, "rating": 4.6, "delivery": "1–2 days"},
    {"id": "s3", "name": "FarmTech Ampara", "district": "Ampara", "verified": True, "rating": 4.7, "delivery": "Same day pickup"},
]
