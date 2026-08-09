"""MihiMura API smoke test.

Run from mihimura-backend with:
    python tests/smoke_test.py

The test uses DEMO_MODE and a temporary SQLite database path supplied by the
shell/environment when desired. It validates the highest-risk application
contracts: tenant isolation, confirmation-gated commerce, explainable AI,
notification scheduling and multi-image scan intake.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def run() -> None:
    with TestClient(app) as client:
        farmer = {"X-Demo-User": "demo_farmer_001"}
        other = {"X-Demo-User": "smoke_other_user"}

        def expect(method: str, path: str, status: int = 200, headers=None, **kwargs):
            response = getattr(client, method)(path, headers=headers if headers is not None else farmer, **kwargs)
            assert response.status_code == status, f"{method.upper()} {path}: {response.status_code} {response.text}"
            return response

        expect("get", "/api/v1/health", headers={})
        farms = expect("get", "/api/v1/farms").json()
        projects = expect("get", "/api/v1/projects").json()
        tasks = expect("get", "/api/v1/tasks").json()
        assert farms and projects and tasks
        farm_id, project_id, task_id = farms[0]["id"], projects[0]["id"], tasks[0]["id"]

        dashboard = expect("get", "/api/v1/dashboard").json()
        assert len(dashboard["provinces"]) == 9

        order = {
            "project_id": project_id,
            "items": [{"product_id": "bio-neem-001", "name": "Bio Neem", "price": 1500, "quantity": 1}],
            "delivery_address": "Smoke-test address",
            "payment_method": "Cash on delivery",
            "delivery_method": "Standard",
            "confirmed": False,
        }
        expect("post", "/api/v1/orders", 400, json={"data": order})
        order["confirmed"] = True
        expect("post", "/api/v1/orders", json={"data": order})

        ai = expect(
            "post",
            "/api/v1/ask-ai",
            json={"question": "Can I apply fertilizer tomorrow?", "context": {"project_id": project_id}},
        ).json()
        required = {
            "summary", "recommended_action", "why", "confidence", "alternatives",
            "do_not_do", "sources", "confirmation_required", "follow_up", "agent_trace", "run_id",
        }
        assert required.issubset(ai)
        expect("get", "/api/v1/agent-runs")

        image_files = [
            ("images", ("leaf-front.jpg", b"jpeg-placeholder-front", "image/jpeg")),
            ("images", ("leaf-back.jpg", b"jpeg-placeholder-back", "image/jpeg")),
        ]
        scan = expect(
            "post",
            "/api/v1/diagnose-image",
            files=image_files,
            data={"crop_hint": "Chilli", "project_id": project_id, "symptoms": "leaf curl"},
        ).json()
        assert scan["image_count"] == 2

        reminder = expect(
            "post",
            "/api/v1/notifications",
            json={"data": {
                "channel": "in-app",
                "title": "Smoke-test task reminder",
                "body": "Check the field",
                "scheduled_at": "2026-08-08T07:00:00+05:30",
            }},
        ).json()
        assert reminder["scheduled_at"]

        # Tenant isolation: a second user cannot mutate the farmer's records.
        expect("patch", f"/api/v1/farms/{farm_id}", 403, headers=other, json={"data": {"name": "Forbidden"}})
        expect("patch", f"/api/v1/tasks/{task_id}", 403, headers=other, json={"status": "completed"})
        expect(
            "post", "/api/v1/tasks", 403, headers=other,
            json={"data": {"project_id": project_id, "title": "Forbidden", "due_at": "2026-08-08T10:00:00Z"}},
        )

        print("MihiMura backend smoke test: PASS")


if __name__ == "__main__":
    run()
