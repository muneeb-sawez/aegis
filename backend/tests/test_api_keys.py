"""Tests for AEGIS Per-Project API Keys & Authentication.

Verifies:
1. API keys are hashed with SHA-256 in storage; raw keys are NEVER written to disk.
2. Mutating routes return 401 when no API key is provided.
3. Mutating routes return 401 when an invalid API key is provided.
4. Mutating routes return 200 when a valid API key is provided.
5. Cross-tenant isolation: Project A's key cannot mutate Project B (returns 401).
6. POST /api/projects returns the one-time raw API key and correctly registers the hashed key.
7. Read-only endpoints do not require API keys.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.auth.store import (
    DEFAULT_DEMO_API_KEY,
    PROJECTS_DATA_PATH,
    get_project_store,
    hash_api_key,
)

client = TestClient(app)


def test_keys_hashed_in_storage():
    """Verify data/projects.json only stores SHA-256 hashes, not plaintext keys."""
    store = get_project_store()
    projects = store.load_all()

    assert "demo" in projects
    demo_rec = projects["demo"]

    # Verify hash is a 64-char hex SHA-256 string
    assert len(demo_rec.key_hash) == 64
    assert demo_rec.key_hash == hash_api_key(DEFAULT_DEMO_API_KEY)

    # Read raw JSON file directly from disk and assert DEFAULT_DEMO_API_KEY is not in raw text
    with open(PROJECTS_DATA_PATH, "r", encoding="utf-8") as f:
        raw_content = f.read()
    assert DEFAULT_DEMO_API_KEY not in raw_content
    assert "aegis-demo-api-key" not in raw_content


def test_mutating_routes_require_api_key_401():
    """Verify mutating routes return 401 when called without API key."""
    # 1. /api/reset
    resp = client.post("/api/reset")
    assert resp.status_code == 401
    assert "API key required" in resp.json()["detail"]

    # 2. /api/chaos/inject
    resp = client.post("/api/chaos/inject", json={"fault_id": "pool_exhaustion"})
    assert resp.status_code == 401

    # 3. /api/actuator/execute
    resp = client.post(
        "/api/actuator/execute",
        json={
            "incident_id": "inc-01",
            "service_id": "paymentservice",
            "action": "restart_pod",
            "params": {},
        },
    )
    assert resp.status_code == 401

    # 4. /api/memory/commit
    resp = client.post(
        "/api/memory/commit",
        json={
            "service_id": "paymentservice",
            "incident_description": "Test incident",
            "action_taken": "restart_pod",
            "outcome": "success",
        },
    )
    assert resp.status_code == 401

    # 5. /api/monitor/fault
    resp = client.post("/api/monitor/fault", json={"service_id": "frontend", "fault_type": "timeout"})
    assert resp.status_code == 401


def test_mutating_routes_reject_invalid_key_401():
    """Verify mutating routes return 401 when called with invalid API key."""
    headers = {"X-API-Key": "invalid_bogus_key_12345"}

    resp = client.post("/api/reset", headers=headers)
    assert resp.status_code == 401
    assert "Invalid API key" in resp.json()["detail"]

    resp = client.post(
        "/api/chaos/inject",
        headers=headers,
        json={"fault_id": "pool_exhaustion"},
    )
    assert resp.status_code == 401


def test_mutating_routes_accept_valid_key_200():
    """Verify mutating routes succeed when called with the valid project API key."""
    headers = {"X-API-Key": DEFAULT_DEMO_API_KEY}

    # /api/reset
    resp = client.post("/api/reset", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["node_count"] == 54

    # /api/chaos/inject
    resp = client.post(
        "/api/chaos/inject",
        headers=headers,
        json={"fault_id": "pool_exhaustion", "target_service": "paymentservice"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] in ("active", "injected")


def test_create_project_and_per_project_isolation():
    """Verify creating a new project yields one-time key and enforces tenant boundaries."""
    import uuid
    new_pid = f"sec-{uuid.uuid4().hex[:8]}"
    create_payload = {
        "project_id": new_pid,
        "name": "Team Security",
        "description": "Security testing tenant",
        "seed_baseline": True,
    }

    # Create project
    create_resp = client.post("/api/projects", json=create_payload)
    assert create_resp.status_code == 201
    create_data = create_resp.json()

    assert create_data["project_id"] == new_pid
    assert "api_key" in create_data
    new_key = create_data["api_key"]
    assert new_key.startswith("aegis_key_")

    # Verify key is hashed in storage, not plaintext
    with open(PROJECTS_DATA_PATH, "r", encoding="utf-8") as f:
        file_content = f.read()
    assert new_key not in file_content

    # Mutating with new project's key on new project succeeds
    tenant_headers = {"X-API-Key": new_key, "X-Project-ID": new_pid}
    resp = client.post(
        f"/api/chaos/inject?project_id={new_pid}",
        headers=tenant_headers,
        json={"fault_id": "cpu_saturation", "target_service": "frontend", "project_id": new_pid},
    )
    assert resp.status_code == 200

    # Cross-tenant violation: new project's key CANNOT mutate the demo project
    cross_resp = client.post(
        "/api/chaos/inject?project_id=demo",
        headers={"X-API-Key": new_key},
        json={"fault_id": "cpu_saturation", "target_service": "frontend", "project_id": "demo"},
    )
    assert cross_resp.status_code == 401


def test_readonly_routes_do_not_require_api_key():
    """Verify read-only endpoints remain accessible without API keys."""
    # Topology
    resp = client.get("/api/graph/topology")
    assert resp.status_code == 200
    assert "nodes" in resp.json()

    # Incidents
    resp = client.get("/api/incidents")
    assert resp.status_code == 200

    # Decisions
    resp = client.get("/api/decisions")
    assert resp.status_code == 200

    # List projects
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert any(p["project_id"] == "demo" for p in resp.json())
