from __future__ import annotations
import json
from typing import Any
from uuid import uuid4
from app.db import audit, execute, rows, row, now_iso, get_user


def _owned(table: str, uid: str) -> list[dict[str, Any]]:
    return rows(f"SELECT * FROM {table} WHERE owner_uid=? ORDER BY created_at DESC", (uid,))

def _require_farm(uid:str,farm_id:str):
    farm=row("SELECT * FROM farms WHERE id=? AND owner_uid=? AND status!='archived'",(farm_id,uid))
    if not farm: raise PermissionError("Farm not found or not accessible")
    return farm

def _require_project(uid:str,project_id:str):
    project=row("SELECT * FROM projects WHERE id=? AND owner_uid=?",(project_id,uid))
    if not project: raise PermissionError("Project not found or not accessible")
    return project

def profile(uid: str): return row("SELECT * FROM users WHERE uid=?", (uid,)) or {}

def update_profile(uid: str, p: dict[str, Any]):
    fields=["name","phone","role","language","district","ds_division","gn_division","location_consent","lat","lon","guidance_mode","irrigation","experience","notification_channels","accessibility_json","primary_crops_json","farm_type","onboarding_complete"]
    values=[]; sets=[]
    for f in fields:
        if f in p:
            sets.append(f"{f}=?"); val=p[f]
            if f == "role":
                # Public onboarding may request a professional workspace, but cannot self-promote to admin.
                val = val if val in {"farmer","manager","agronomist","supplier","analyst"} else "farmer"
            if f in {"accessibility_json","primary_crops_json"} and not isinstance(val,str): val=json.dumps(val)
            if f in {"location_consent","onboarding_complete"}: val=1 if val else 0
            values.append(val)
    if sets: execute(f"UPDATE users SET {','.join(sets)} WHERE uid=?", (*values,uid)); audit(uid,"update_profile",uid,{k:p[k] for k in p if k in fields})
    return profile(uid)

def list_farms(uid: str): return rows("SELECT * FROM farms WHERE owner_uid=? ORDER BY created_at DESC",(uid,))

def create_farm(uid: str,p:dict[str,Any]):
    fid=f"farm_{uuid4().hex[:8]}"; execute("INSERT INTO farms VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(fid,uid,p["name"],p.get("district","Ampara"),p.get("province","Eastern"),float(p.get("area",0)),p.get("water_source",""),p.get("soil_type",""),p.get("land_type",""),p.get("crop",""),p.get("lat"),p.get("lon"),json.dumps(p.get("boundary")) if p.get("boundary") else None,"active",now_iso())); audit(uid,"create_farm",fid,p); return row("SELECT * FROM farms WHERE id=?",(fid,))


def update_farm(uid:str,farm_id:str,p:dict[str,Any]):
    _require_farm(uid,farm_id)
    allowed={k:v for k,v in p.items() if k in {"name","district","province","area","water_source","soil_type","land_type","crop","lat","lon","status"}}
    if "boundary" in p: allowed["boundary_json"]=json.dumps(p["boundary"]) if p["boundary"] else None
    if allowed:
        execute("UPDATE farms SET "+",".join(f"{k}=?" for k in allowed)+" WHERE id=? AND owner_uid=?",(*allowed.values(),farm_id,uid))
        audit(uid,"update_farm",farm_id,{k:v for k,v in p.items() if k != "boundary"}|({"boundary_points":len(p.get("boundary") or [])} if "boundary" in p else {}))
    return row("SELECT * FROM farms WHERE id=? AND owner_uid=?",(farm_id,uid))

def list_projects(uid: str): return rows("SELECT p.*,f.name farm_name,f.district,f.province,f.area,f.lat,f.lon FROM projects p JOIN farms f ON f.id=p.farm_id WHERE p.owner_uid=? ORDER BY p.created_at DESC",(uid,))

def create_project(uid:str,p:dict[str,Any]):
    _require_farm(uid,p["farm_id"])
    pid=f"proj_{uuid4().hex[:8]}"; execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(pid,p["farm_id"],uid,p["crop"],p.get("variety",""),p.get("purpose",""),p.get("season",""),p.get("stage","Planning"),p.get("start_date",""),p.get("actual_start_date",""),p.get("target_harvest",""),p.get("irrigation_mode",""),p.get("seed_source",""),int(p.get("health_score",80)),int(p.get("risk_score",30)),float(p.get("budget",0)),p.get("status","active"),p.get("notes",""),now_iso())); audit(uid,"create_project",pid,p); return row("SELECT * FROM projects WHERE id=?",(pid,))

def list_tasks(uid:str): return rows("SELECT t.*,p.crop,f.name farm_name FROM tasks t JOIN projects p ON p.id=t.project_id JOIN farms f ON f.id=p.farm_id WHERE t.owner_uid=? ORDER BY t.due_at",(uid,))

def create_task(uid:str,p:dict[str,Any]):
    _require_project(uid,p["project_id"])
    tid=f"task_{uuid4().hex[:8]}"; execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(tid,p["project_id"],uid,p["title"],p.get("task_type","General"),p["due_at"],p.get("priority","medium"),p.get("weather_dependency",""),"pending",p.get("instructions",""),p.get("materials",""),p.get("assigned_to","Self"),"",p.get("schedule_reason",""),now_iso())); audit(uid,"create_task",tid,p); return row("SELECT * FROM tasks WHERE id=?",(tid,))

def update_task(uid:str,tid:str,p:dict[str,Any]):
    task=row("SELECT * FROM tasks WHERE id=? AND owner_uid=?",(tid,uid))
    if not task: raise PermissionError("Task not found or not accessible")
    allowed={k:v for k,v in p.items() if k in {"status","due_at","assigned_to","completion_note","schedule_reason"}}
    if allowed: execute("UPDATE tasks SET "+",".join(f"{k}=?" for k in allowed)+" WHERE id=? AND owner_uid=?",(*allowed.values(),tid,uid)); audit(uid,"update_task",tid,allowed)
    return row("SELECT * FROM tasks WHERE id=? AND owner_uid=?",(tid,uid))

def list_observations(uid:str): return _owned("observations",uid)

def create_observation(uid:str,p:dict[str,Any]):
    _require_project(uid,p["project_id"])
    oid=f"obs_{uuid4().hex[:8]}"; execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(oid,p["project_id"],uid,now_iso(),p.get("type","field-note"),p["note"],p.get("growth_stage",""),p.get("rainfall",""),p.get("irrigation",""),int(p.get("pest_count",0)),p.get("symptoms",""),p.get("action_taken",""))); audit(uid,"create_observation",oid,p); return row("SELECT * FROM observations WHERE id=?",(oid,))

def list_expenses(uid:str): return _owned("expenses",uid)

def create_expense(uid:str,p:dict[str,Any]):
    _require_project(uid,p["project_id"])
    eid=f"exp_{uuid4().hex[:8]}"; execute("INSERT INTO expenses VALUES (?,?,?,?,?,?,?)",(eid,p["project_id"],uid,now_iso(),p.get("category","Other"),float(p["amount"]),p.get("note",""))); audit(uid,"create_expense",eid,p); return row("SELECT * FROM expenses WHERE id=?",(eid,))

def list_harvests(uid:str): return rows("SELECT * FROM harvests WHERE owner_uid=? ORDER BY harvest_date DESC",(uid,))

def create_harvest(uid:str,p:dict[str,Any]):
    _require_project(uid,p["project_id"])
    hid=f"harv_{uuid4().hex[:8]}"; execute("INSERT INTO harvests VALUES (?,?,?,?,?,?,?,?,?)",(hid,p["project_id"],uid,p.get("harvest_date",now_iso()[:10]),float(p.get("yield_value",0)),p.get("yield_unit","kg"),p.get("quality",""),float(p.get("revenue",0)),p.get("note",""))); audit(uid,"record_harvest",hid,p); return row("SELECT * FROM harvests WHERE id=?",(hid,))

def list_orders(uid:str):
    data=_owned("orders",uid)
    for x in data: x["items"]=json.loads(x.pop("items_json"))
    return data

def create_order(uid:str,p:dict[str,Any]):
    _require_project(uid,p["project_id"])
    oid=f"ord_{uuid4().hex[:8]}"; items=p.get("items",[]); total=sum(float(i.get("price",0))*int(i.get("quantity",1)) for i in items); execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",(oid,uid,p["project_id"],now_iso(),total,"confirmed",json.dumps(items),p.get("delivery_address",""),p.get("payment_method","Cash on delivery"),p.get("delivery_method","Standard"),1)); audit(uid,"confirmed_order",oid,{"total":total,"items":items}); return next(x for x in list_orders(uid) if x["id"]==oid)

def list_expert_cases(uid:str): return _owned("expert_cases",uid)

def create_expert_case(uid:str,p:dict[str,Any]):
    _require_project(uid,p["project_id"])
    cid=f"case_{uuid4().hex[:8]}"; execute("INSERT INTO expert_cases VALUES (?,?,?,?,?,?,?,?,?,?,?)",(cid,uid,p["project_id"],now_iso(),p.get("urgency","medium"),p["reason"],"open",p.get("evidence",""),p.get("preferred_language","English"),p.get("availability",""),"")); audit(uid,"expert_escalation",cid,p); return row("SELECT * FROM expert_cases WHERE id=?",(cid,))


def update_expert_case_for_actor(actor:dict[str,Any],case_id:str,p:dict[str,Any]):
    allowed={k:v for k,v in p.items() if k in {"status","expert_decision","availability"}}
    privileged = actor.get("provider")=="demo" or (actor.get("role") in {"agronomist","expert","admin"} and bool(actor.get("professional_verified")))
    target = row("SELECT * FROM expert_cases WHERE id=?",(case_id,)) if privileged else row("SELECT * FROM expert_cases WHERE id=? AND owner_uid=?",(case_id,actor["uid"]))
    if not target: return None
    if allowed:
        execute("UPDATE expert_cases SET "+",".join(f"{k}=?" for k in allowed)+" WHERE id=?",(*allowed.values(),case_id))
        audit(actor["uid"],"expert_case_update",case_id,allowed|{"privileged_review":privileged})
    return row("SELECT * FROM expert_cases WHERE id=?",(case_id,))

def list_notifications(uid:str): return _owned("notifications",uid)

def create_notification(uid:str,p:dict[str,Any]):
    nid=f"note_{uuid4().hex[:8]}"
    execute("INSERT INTO notifications(id,owner_uid,created_at,scheduled_at,channel,title,body,status,acknowledged) VALUES (?,?,?,?,?,?,?,?,?)",(nid,uid,now_iso(),p.get("scheduled_at") or now_iso(),p.get("channel","in-app"),p["title"],p["body"],p.get("status","scheduled"),0))
    audit(uid,"schedule_notification",nid,{"channel":p.get("channel","in-app"),"scheduled_at":p.get("scheduled_at")})
    return row("SELECT * FROM notifications WHERE id=?",(nid,))

def update_notification(uid: str, nid: str, p: dict[str, Any]):
    note = row(
        "SELECT * FROM notifications WHERE id=? AND owner_uid=?",
        (nid, uid)
    )

    if not note:
        raise PermissionError(
            "Notification not found or not accessible"
        )

    allowed = {}

    if "acknowledged" in p:
        allowed["acknowledged"] = (
            1 if p.get("acknowledged") else 0
        )

    if (
        "status" in p
        and p.get("status")
        in {"scheduled", "sent", "failed", "cancelled"}
    ):
        allowed["status"] = p.get("status")

    if allowed:
        execute(
            "UPDATE notifications SET "
            + ",".join(f"{k}=?" for k in allowed)
            + " WHERE id=? AND owner_uid=?",
            (*allowed.values(), nid, uid)
        )

        audit(
            uid,
            "update_notification",
            nid,
            allowed
        )

    return row(
        "SELECT * FROM notifications "
        "WHERE id=? AND owner_uid=?",
        (nid, uid)
    )


def list_community_reports(min_count:int=3):
    # Regional publication endpoint: never returns individual reporter identity, exact coordinates or farm boundaries.
    clusters=rows("""SELECT district,crop,report_type,COUNT(*) report_count,MAX(created_at) latest_report,
        CASE WHEN SUM(CASE WHEN severity IN ('high','emergency') THEN 1 ELSE 0 END)>0 THEN 'high' ELSE 'watch' END severity
        FROM community_reports WHERE anonymized=1 GROUP BY district,crop,report_type HAVING COUNT(*)>=?
        ORDER BY report_count DESC, latest_report DESC""",(min_count,))
    for i,x in enumerate(clusters):
        x["id"]=f"cluster_{i}_{x['district']}_{x['crop']}_{x['report_type']}"
        x["created_at"]=x.pop("latest_report")
        x["note"]=f"{x['report_count']} anonymized reports crossed the publication threshold; field verification is recommended before treatment."
    return clusters

def create_community_report(uid:str,p:dict[str,Any]):
    rid=f"comm_{uuid4().hex[:8]}"; execute("INSERT INTO community_reports VALUES (?,?,?,?,?,?,?,?,?,?,?)",(rid,uid,now_iso(),p.get("district","Ampara"),p.get("crop",""),p.get("report_type","symptom"),p.get("severity","watch"),p.get("note",""),p.get("lat"),p.get("lon"),1)); audit(uid,"community_report",rid,{"district":p.get("district"),"type":p.get("report_type")}); return {"id":rid,"status":"queued-for-privacy-threshold"}

def save_device_token(uid:str, token:str, platform:str="web"):
    did=f"device_{uuid4().hex[:8]}"
    execute("INSERT OR REPLACE INTO device_tokens VALUES (?,?,?,?,?)",(did,uid,token,platform,now_iso()))
    audit(uid,"register_device_token",did,{"platform":platform})
    return {"id":did,"registered":True,"platform":platform}

def list_device_tokens(uid:str): return rows("SELECT id,platform,created_at FROM device_tokens WHERE owner_uid=? ORDER BY created_at DESC",(uid,))

def audit_log(uid:str|None=None,limit:int=100):
    data=rows("SELECT * FROM audit_events "+("WHERE actor=? " if uid else "")+"ORDER BY id DESC LIMIT ?",((uid,limit) if uid else (limit,)))
    for x in data: x["details"]=json.loads(x.pop("details_json"))
    return data


def request_account_deletion(uid:str):
    stamp=now_iso()
    execute("UPDATE users SET status='deletion_requested', deletion_requested_at=? WHERE uid=?",(stamp,uid))
    audit(uid,"account_deletion_requested",uid,{"requested_at":stamp})
    return {"status":"deletion_requested","requested_at":stamp,"message":"Account deletion is queued. Production deployments should verify identity, respect legal retention requirements, remove application data, and delete the identity-provider account."}

def list_expert_cases_for_actor(actor:dict[str,Any]):
    if actor.get("provider")=="demo" or (actor.get("role") in {"agronomist","expert","admin"} and bool(actor.get("professional_verified"))):
        return rows("SELECT e.*,u.name farmer_name,u.district farmer_district FROM expert_cases e LEFT JOIN users u ON u.uid=e.owner_uid ORDER BY CASE e.urgency WHEN 'emergency' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, e.created_at DESC")
    return list_expert_cases(actor["uid"])

def audit_log_for_actor(actor:dict[str,Any],limit:int=100):
    if actor.get("provider")=="demo" or (actor.get("role")=="admin" and bool(actor.get("professional_verified"))): return audit_log(None,limit)
    return audit_log(actor["uid"],limit)

def record_agent_run(uid:str,request_text:str,result:dict[str,Any],context:dict[str,Any]):
    rid=f"run_{uuid4().hex[:10]}"
    trace=result.get("agent_trace",[])
    sources=result.get("sources",[])
    execute("INSERT INTO agent_runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",(rid,uid,now_iso(),request_text,json.dumps(trace),json.dumps(sources),result.get("provider","policy"),str(result.get("model",context.get("model",''))),"confirmation-required" if result.get("confirmation_required") else "advisory",int(result.get("latency_ms",0)),json.dumps({k:v for k,v in result.items() if k not in {"agent_trace","sources"}},default=str)))
    return rid

def list_agent_runs_for_actor(actor:dict[str,Any],limit:int=100):
    if actor.get("provider")=="demo" or (actor.get("role")=="admin" and bool(actor.get("professional_verified"))):
        return rows("SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT ?",(limit,))
    return rows("SELECT * FROM agent_runs WHERE owner_uid=? ORDER BY created_at DESC LIMIT ?",(actor["uid"],limit))

def list_users_for_admin(actor:dict[str,Any]):
    if not (actor.get("provider")=="demo" or (actor.get("role")=="admin" and bool(actor.get("professional_verified")))):
        return []
    return rows("SELECT uid,email,name,role,language,district,provider,onboarding_complete,professional_verified,status,created_at FROM users ORDER BY created_at DESC")

def set_professional_verification(actor:dict[str,Any],uid:str,verified:bool):
    if not (actor.get("provider")=="demo" or (actor.get("role")=="admin" and bool(actor.get("professional_verified")))):
        raise PermissionError("Administrator verification required")
    target=get_user(uid)
    if not target: return None
    if target.get("role") not in {"agronomist","supplier","analyst","admin"}:
        return target
    execute("UPDATE users SET professional_verified=? WHERE uid=?",(1 if verified else 0,uid))
    audit(actor["uid"],"professional_verification",uid,{"verified":verified,"role":target.get("role")})
    return get_user(uid)

PRODUCTS=[
 {"id":"p1","name":"Certified Paddy Seed – Bg 352","category":"Seed","specification":"Certified seed class","price":4200,"pack":"20 kg","supplier":"Eastern Farmer Cooperative","verified":True,"stock":42,"distance":"7 km","compatibility":"Paddy","safety":"Verify season, seed class and storage condition.","why":"Matches demo paddy variety; recommendation remains agronomy-first."},
 {"id":"p2","name":"Yellow Sticky Traps","category":"Monitoring","specification":"Non-chemical monitoring aid","price":850,"pack":"20 traps","supplier":"BioField Lanka","verified":True,"stock":76,"distance":"16 km","compatibility":"Chilli","safety":"Monitoring aid only; does not confirm pest species.","why":"Low-risk scouting support for flying pest pressure."},
 {"id":"p3","name":"Field Soil Moisture Meter","category":"Equipment","specification":"Portable capacitive meter","price":6900,"pack":"1 unit","supplier":"FarmTech Ampara","verified":True,"stock":9,"distance":"22 km","compatibility":"All crops","safety":"Calibrate for field soil before decisions.","why":"Supports verification of water-budget estimates."},
 {"id":"p4","name":"Protective Field Kit","category":"Safety","specification":"Gloves, eye protection, washable apron","price":3250,"pack":"1 kit","supplier":"AgriSafe Cooperative","verified":True,"stock":33,"distance":"9 km","compatibility":"Field operations","safety":"Use according to task and product label requirements.","why":"Supports safer field work when protective equipment is required."}
]
SUPPLIERS=[{"id":"s1","name":"Eastern Farmer Cooperative","district":"Ampara","verified":True,"rating":4.8,"delivery":"Same/next day"},{"id":"s2","name":"BioField Lanka","district":"Batticaloa","verified":True,"rating":4.6,"delivery":"1–2 days"},{"id":"s3","name":"FarmTech Ampara","district":"Ampara","verified":True,"rating":4.7,"delivery":"Same day pickup"}]
