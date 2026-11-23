"""Demo requests require explicit opt-in and cannot use shared admin endpoints."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.core import auth
from app.main import app


def run():
    actor = {"uid": auth.DEMO_UID, "provider": "demo", "role": "admin", "professional_verified": True}
    with patch.object(auth.settings, "DEMO_MODE", True), patch.object(auth, "ensure_user", return_value=actor):
        with TestClient(app) as client:
            assert client.get("/api/v1/admin/users").status_code == 401
            assert client.get("/api/v1/admin/users", headers={"X-Demo-User": "other"}).status_code == 401
            for path in ("admin/users", "knowledge/ingestion-jobs", "evaluation/cases"):
                result = client.get(f"/api/v1/{path}", headers={"X-Demo-User": auth.DEMO_UID})
                assert result.status_code == 403, (path, result.status_code)


if __name__ == "__main__":
    run()
    print("Explicit demo identity and shared administrative permissions: PASS")
