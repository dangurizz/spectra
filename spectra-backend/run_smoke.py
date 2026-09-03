"""End-to-end smoke test against a live Supabase project.

Requires .env with SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY.
The spots table must already be seeded.

    poetry run python run_smoke.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")


def _fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        _fail(
            "Missing "
            + ", ".join(missing)
            + ". Copy .env.example to .env and paste keys from "
            "Supabase → Settings → API, then run schema.sql and "
            "`poetry run python -m database.seed_spots`."
        )

    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)

    health = client.get("/health")
    if health.status_code != 200 or health.json() != {"status": "ok"}:
        _fail(f"/health returned {health.status_code} {health.text}")
    print("OK  GET /health")

    email = os.getenv("SMOKE_TEST_EMAIL", "spectra-smoke@example.com")
    password = os.getenv("SMOKE_TEST_PASSWORD", "spectra-smoke-test-password")

    login = client.post("/auth/login", json={"email": email, "password": password})
    if login.status_code != 200:
        signup = client.post("/auth/signup", json={"email": email, "password": password})
        if signup.status_code != 200:
            _fail(f"signup failed: {signup.status_code} {signup.text}")
        token = signup.json().get("access_token")
        if not token:
            _fail(
                "signup succeeded but returned no access_token. "
                "Disable 'Confirm email' in Supabase → Authentication → Providers → Email."
            )
        print("OK  POST /auth/signup")
    else:
        token = login.json()["access_token"]
        print("OK  POST /auth/login")

    headers = {"Authorization": f"Bearer {token}"}

    spots = client.get("/spots", headers=headers)
    if spots.status_code != 200:
        _fail(f"/spots failed: {spots.status_code} {spots.text}")
    spot_list = spots.json()
    if not spot_list:
        _fail("No spots returned. Run `poetry run python -m database.seed_spots`.")
    spot_id = spot_list[0]["id"]
    print(f"OK  GET /spots ({len(spot_list)} spots)")

    start = datetime.now(timezone.utc) - timedelta(hours=2)
    end = start + timedelta(hours=1)
    created = client.post(
        "/sessions",
        headers=headers,
        json={
            "spot_id": spot_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "rating": 4,
            "notes": "smoke test",
        },
    )
    if created.status_code != 201:
        _fail(f"create session failed: {created.status_code} {created.text}")
    session = created.json()
    session_id = session["id"]
    conditions = session.get("conditions") or {}
    filled = [k for k, v in conditions.items() if v is not None]
    print(f"OK  POST /sessions ({session_id}) conditions={filled or 'none'}")

    listed = client.get("/sessions", headers=headers)
    if listed.status_code != 200:
        _fail(f"list sessions failed: {listed.status_code} {listed.text}")
    if not any(row["id"] == session_id for row in listed.json()):
        _fail("created session not in GET /sessions")
    print("OK  GET /sessions")

    stats = client.get("/stats", headers=headers)
    if stats.status_code != 200:
        _fail(f"/stats failed: {stats.status_code} {stats.text}")
    if stats.json()["total_sessions"] < 1:
        _fail("stats total_sessions < 1 after create")
    print(f"OK  GET /stats {stats.json()}")

    deleted = client.delete(f"/sessions/{session_id}", headers=headers)
    if deleted.status_code != 204:
        _fail(f"delete session failed: {deleted.status_code} {deleted.text}")
    print("OK  DELETE /sessions/{id}")
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
