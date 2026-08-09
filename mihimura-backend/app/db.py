from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from app.core.config import settings

DB_PATH = Path(settings.DATABASE_PATH)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]

def row(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connection() as conn:
        r = conn.execute(query, params).fetchone()
        return dict(r) if r else None

def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    with connection() as conn:
        conn.execute(query, params)

def audit(actor: str, action: str, entity: str, details: dict[str, Any]) -> None:
    execute("INSERT INTO audit_events(created_at,actor,action,entity,details_json) VALUES (?,?,?,?,?)", (now_iso(), actor, action, entity, json.dumps(details)))

def ensure_user(uid: str, email: str = "", name: str = "Farmer", provider: str = "demo") -> None:
    execute("INSERT OR IGNORE INTO users(uid,email,name,role,language,district,provider,onboarding_complete,created_at) VALUES (?,?,?,?,?,?,?,?,?)", (uid,email,name,"farmer","English","Ampara",provider,0,now_iso()))

def get_user(uid: str) -> dict[str, Any]:
    return row("SELECT * FROM users WHERE uid=?", (uid,)) or {}

def init_db() -> None:
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          uid TEXT PRIMARY KEY, email TEXT, name TEXT, phone TEXT, role TEXT NOT NULL DEFAULT 'farmer', language TEXT NOT NULL DEFAULT 'English',
          district TEXT, ds_division TEXT, gn_division TEXT, provider TEXT, onboarding_complete INTEGER NOT NULL DEFAULT 0,
          location_consent INTEGER NOT NULL DEFAULT 0, lat REAL, lon REAL, guidance_mode TEXT, irrigation TEXT, experience TEXT,
          notification_channels TEXT, accessibility_json TEXT, primary_crops_json TEXT, farm_type TEXT, professional_verified INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active', deletion_requested_at TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS farms (
          id TEXT PRIMARY KEY, owner_uid TEXT NOT NULL, name TEXT NOT NULL, district TEXT NOT NULL, province TEXT NOT NULL,
          area REAL NOT NULL, water_source TEXT, soil_type TEXT, land_type TEXT, crop TEXT, lat REAL, lon REAL,
          boundary_json TEXT, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects (
          id TEXT PRIMARY KEY, farm_id TEXT NOT NULL, owner_uid TEXT NOT NULL, crop TEXT NOT NULL, variety TEXT, purpose TEXT, season TEXT,
          stage TEXT, start_date TEXT, actual_start_date TEXT, target_harvest TEXT, irrigation_mode TEXT, seed_source TEXT,
          health_score INTEGER, risk_score INTEGER, budget REAL, status TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, owner_uid TEXT NOT NULL, title TEXT NOT NULL, task_type TEXT,
          due_at TEXT NOT NULL, priority TEXT NOT NULL, weather_dependency TEXT, status TEXT NOT NULL, instructions TEXT,
          materials TEXT, assigned_to TEXT, completion_note TEXT, schedule_reason TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS observations (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, owner_uid TEXT NOT NULL, created_at TEXT NOT NULL, type TEXT NOT NULL,
          note TEXT NOT NULL, growth_stage TEXT, rainfall TEXT, irrigation TEXT, pest_count INTEGER DEFAULT 0, symptoms TEXT, action_taken TEXT
        );
        CREATE TABLE IF NOT EXISTS expenses (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, owner_uid TEXT NOT NULL, created_at TEXT NOT NULL, category TEXT, amount REAL, note TEXT
        );
        CREATE TABLE IF NOT EXISTS harvests (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, owner_uid TEXT NOT NULL, harvest_date TEXT, yield_value REAL, yield_unit TEXT, quality TEXT, revenue REAL, note TEXT
        );
        CREATE TABLE IF NOT EXISTS orders (
          id TEXT PRIMARY KEY, owner_uid TEXT NOT NULL, project_id TEXT NOT NULL, created_at TEXT NOT NULL, total REAL NOT NULL,
          status TEXT NOT NULL, items_json TEXT NOT NULL, delivery_address TEXT, payment_method TEXT, delivery_method TEXT, consent INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS expert_cases (
          id TEXT PRIMARY KEY, owner_uid TEXT NOT NULL, project_id TEXT NOT NULL, created_at TEXT NOT NULL, urgency TEXT NOT NULL,
          reason TEXT NOT NULL, status TEXT NOT NULL, evidence TEXT, preferred_language TEXT, availability TEXT, expert_decision TEXT
        );
        CREATE TABLE IF NOT EXISTS notifications (
          id TEXT PRIMARY KEY, owner_uid TEXT NOT NULL, created_at TEXT NOT NULL, scheduled_at TEXT, channel TEXT, title TEXT, body TEXT, status TEXT, acknowledged INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS recommendations (
          id TEXT PRIMARY KEY, owner_uid TEXT NOT NULL, project_id TEXT, created_at TEXT NOT NULL, action TEXT, rationale TEXT,
          confidence REAL, sources_json TEXT, alternatives_json TEXT, safety_json TEXT, expiry TEXT, status TEXT
        );
        CREATE TABLE IF NOT EXISTS community_reports (
          id TEXT PRIMARY KEY, owner_uid TEXT NOT NULL, created_at TEXT NOT NULL, district TEXT, crop TEXT, report_type TEXT,
          severity TEXT, note TEXT, lat REAL, lon REAL, anonymized INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS audit_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, entity TEXT NOT NULL, details_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS device_tokens (
          id TEXT PRIMARY KEY, owner_uid TEXT NOT NULL, token TEXT NOT NULL UNIQUE, platform TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_runs (
          id TEXT PRIMARY KEY, owner_uid TEXT NOT NULL, created_at TEXT NOT NULL, request TEXT, tools_json TEXT, evidence_json TEXT,
          provider TEXT, model TEXT, policy_decision TEXT, latency_ms INTEGER, output_json TEXT
        );
        """)
        # Lightweight SQLite migrations for users who are upgrading an existing demo DB.
        user_columns={r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "primary_crops_json" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN primary_crops_json TEXT")
        if "farm_type" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN farm_type TEXT")
        if "professional_verified" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN professional_verified INTEGER NOT NULL DEFAULT 0")
        if "status" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        if "deletion_requested_at" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN deletion_requested_at TEXT")
        notification_columns={r[1] for r in conn.execute("PRAGMA table_info(notifications)").fetchall()}
        if "scheduled_at" not in notification_columns:
            conn.execute("ALTER TABLE notifications ADD COLUMN scheduled_at TEXT")

    ensure_user("demo_farmer_001", "demo@mihimura.lk", "Demo Farmer", "demo")
    if not rows("SELECT * FROM farms"):
        execute("INSERT INTO farms VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
          "farm_ampara_01","demo_farmer_001","Ampara Paddy Block","Ampara","Eastern",42.5,"Irrigation canal","Alluvial clay","Lowland paddy","Paddy",7.291,81.674,
          json.dumps([[81.669,7.286],[81.679,7.286],[81.679,7.296],[81.669,7.296],[81.669,7.286]]),"active",now_iso()))
        execute("INSERT INTO farms VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
          "farm_ampara_02","demo_farmer_001","East Chilli Plot","Ampara","Eastern",15.2,"Tube well","Sandy loam","Upland","Chilli",7.245,81.755,None,"active",now_iso()))
        execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
          "proj_paddy_2026","farm_ampara_01","demo_farmer_001","Paddy","Bg 352","Grain production","Yala","Tillering","2026-07-02","2026-07-02","2026-10-18","Canal","Certified seed",68,62,145000,"active","Demo digital twin",now_iso()))
        execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
          "proj_chilli_2026","farm_ampara_02","demo_farmer_001","Chilli","MI-2","Fresh market","Yala","Flowering","2026-06-18","2026-06-18","2026-10-05","Drip","Certified seed",84,38,98000,"active","Demo chilli project",now_iso()))
        for item in [
          ("task_01","proj_paddy_2026","Inspect western edge for leaf stress","Scouting","2026-08-07T16:30:00+05:30","high","Before next rainfall","Inspect 5 representative locations and attach photos."),
          ("task_02","proj_paddy_2026","Review fertilizer timing","Nutrition","2026-08-08T07:00:00+05:30","high","Delay if heavy-rain probability exceeds safety threshold","Check current forecast and approved protocol before any application."),
          ("task_03","proj_chilli_2026","Potassium nutrition check","Nutrition","2026-08-09T08:00:00+05:30","medium","Avoid during strong rain","Review flowering-stage condition; do not invent rates."),
        ]:
            execute("INSERT INTO tasks(id,project_id,owner_uid,title,task_type,due_at,priority,weather_dependency,status,instructions,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (*item[:2],"demo_farmer_001",*item[2:7],"pending",item[7],now_iso()))

    if not rows("SELECT * FROM community_reports"):
        for i,note in enumerate([
            "Small flying insects seen on chilli leaves",
            "Leaf curling and insect activity in nearby chilli plot",
            "Sticky trap count increased this week",
        ],start=1):
            execute("INSERT INTO community_reports VALUES (?,?,?,?,?,?,?,?,?,?,?)",(f"comm_demo_{i}","demo_farmer_001",now_iso(),"Ampara","Chilli","pest sighting","watch",note,None,None,1))
