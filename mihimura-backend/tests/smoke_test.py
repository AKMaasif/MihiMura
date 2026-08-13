"""Configured Supabase integration smoke test for the v6 multilingual production-oriented agent.

Prerequisites:
1. Run the Supabase migration.
2. Configure mihimura-backend/.env with Supabase keys.
3. Keep DEMO_MODE=true for this local smoke test.

Run from mihimura-backend:
    python tests/smoke_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def run() -> None:
    if not settings.supabase_configured:
        raise SystemExit("Configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running the integration smoke test.")

    with TestClient(app) as client:
        headers = {"X-Demo-User": "00000000-0000-0000-0000-000000000001"}

        def expect(method: str, path: str, status: int = 200, **kwargs):
            response = getattr(client, method)(path, headers=headers, **kwargs)
            assert response.status_code == status, f"{method.upper()} {path}: {response.status_code} {response.text}"
            return response

        health = client.get("/api/v1/health")
        assert health.status_code == 200, health.text
        assert health.json()["supabase_configured"] is True

        farms = expect("get", "/api/v1/farms").json()
        projects = expect("get", "/api/v1/projects").json()
        tasks = expect("get", "/api/v1/tasks").json()
        assert farms and projects and tasks, "Run the Supabase migration demo seed first"

        # Complete report request: crop + location + area are enough to proceed.
        first = expect(
            "post",
            "/api/v1/ask-ai",
            json={
                "question": "i want to plant padddy in polannaruwa areaa. initial land about 1 accr and i need whole report",
                "context": {"language": "English"},
                "mode": "auto",
            },
        ).json()
        cid = first["conversation_id"]
        assert cid
        facts = first["conversation_memory"]["known_facts"]
        assert facts["crop"] == "Paddy"
        assert facts["location"] == "Polonnaruwa"
        assert facts["area_value"] == 1.0
        assert first["detected_mode"] == "full_report"
        assert first["response_type"] == "report_ready"
        assert first.get("report"), "Full Report should auto-generate once blocking facts are known"

        # A report follow-up should reuse memory and must not open an unnecessary form
        # or regenerate another PDF.
        follow = expect(
            "post",
            "/api/v1/ask-ai",
            json={"question": "now list what are the details you need", "context": {}, "conversation_id": cid, "mode": "auto"},
        ).json()
        follow_facts = follow["conversation_memory"]["known_facts"]
        assert follow_facts["location"] == "Polonnaruwa"
        assert follow_facts["crop"] == "Paddy"
        assert follow_facts["area_value"] == 1.0
        assert follow["response_type"] == "answer"
        assert follow.get("auto_generate_report") is False
        assert not follow.get("clarification_fields")

        # Wrong-mode request should pause and recommend the correct workflow.
        switch = expect(
            "post",
            "/api/v1/ask-ai",
            json={
                "question": "Will heavy rain affect fertilizer application tomorrow?",
                "context": {},
                "conversation_id": cid,
                "mode": "simple_chat",
            },
        ).json()
        assert switch["response_type"] == "mode_switch"
        assert switch["suggested_mode"] == "decision_support"

        # A genuinely missing blocking field still produces a minimal clarification.
        missing = expect(
            "post",
            "/api/v1/ask-ai",
            json={
                "question": "Create a complete paddy cultivation report for Polonnaruwa",
                "context": {},
                "mode": "full_report",
            },
        ).json()
        missing_cid = missing["conversation_id"]
        assert missing["response_type"] == "clarification"
        keys = {x["key"] for x in missing.get("clarification_fields", [])}
        assert "area_value" in keys

        completed = expect(
            "post",
            "/api/v1/ask-ai",
            json={
                "question": "",
                "context": {},
                "conversation_id": missing_cid,
                "clarification_answers": {"area_value": 1, "area_unit": "acre"},
                "mode": "full_report",
            },
        ).json()
        assert completed["conversation_memory"]["known_facts"]["area_value"] == 1.0
        assert completed["response_type"] == "report_ready"
        assert completed.get("report")

        history = expect("get", f"/api/v1/conversations/{cid}/messages").json()
        assert len(history) >= 4

        expect("get", "/api/v1/agent-runs")
        expect("get", "/api/v1/reports")
        print("MihiMura v6 Supabase integration smoke test: PASS")


if __name__ == "__main__":
    run()
