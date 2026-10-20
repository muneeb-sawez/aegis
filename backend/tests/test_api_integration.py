"""AEGIS End-to-End API Integration & Closed-Loop Lifecycle Test.

Tests the complete operational lifecycle across all API endpoints:
1. Topology inspection (54 nodes / 142 edges)
2. Pre-Ship simulation on PR #142 (pre-incident baseline)
3. Chaos fault injection (pool exhaustion)
4. Guarded Actuator execution (testing both bad-fix rollback and valid execution)
5. Incident Memory Commit (feedback write-back to graph)
6. Post-incident Pre-Ship simulation on PR #142 (+5.0 point increase)
7. Reset API restoring clean baseline
"""

from fastapi.testclient import TestClient
import pytest

from backend.api.main import app

client = TestClient(app)


def test_api_root_and_docs():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "AEGIS"
    assert data["phase"] == 1


def test_api_topology():
    response = client.get("/api/graph/topology")
    assert response.status_code == 200
    data = response.json()
    assert data["total_nodes"] == 54
    assert data["total_edges"] == 142
    assert len(data["nodes"]) == 54
    assert len(data["edges"]) == 142


def test_api_closed_loop_lifecycle():
    # 0. Ensure clean baseline
    reset_resp = client.post("/api/reset")
    assert reset_resp.status_code == 200

    # 1. Pre-ship simulation on PR #142 (Fresh baseline)
    sim_pre_resp = client.post(
        "/api/simulate-pr",
        json={"pr_id": "PR-142", "target_service": "paymentservice"},
    )
    assert sim_pre_resp.status_code == 200
    sim_pre = sim_pre_resp.json()
    pre_score = sim_pre["risk_score"]
    assert sim_pre["breakdown"]["contract_score"] == 100.0
    assert sim_pre["breakdown"]["history_score"] == 0.0
    assert sim_pre["incident_count_30d"] == 0

    # 2. Inject pool-exhaustion fault
    fault_resp = client.post(
        "/api/chaos/inject",
        json={"fault_id": "pool_exhaustion", "target_service": "paymentservice"},
    )
    assert fault_resp.status_code == 200
    fault_data = fault_resp.json()
    assert "paymentservice" in fault_data["altered_nodes"]
    assert "postgres-payment" in fault_data["altered_nodes"]

    # 3. Retrieve diagnosis events via polling fallback
    events_resp = client.get("/api/heal/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 5
    types = [ev["type"] for ev in events]
    assert "thought" in types
    assert "cypher" in types
    assert "candidates" in types
    assert "result" in types

    # 4. Actuator: Test deliberate bad fix triggering automatic rollback
    bad_fix_resp = client.post(
        "/api/actuator/execute",
        json={
            "action": "scale_pool",
            "target": "postgres-payment",
            "params": {"pool_size": 20},  # Under minimum threshold
            "rationale": "Attempting dangerously small pool size",
        },
    )
    assert bad_fix_resp.status_code == 200
    bad_fix_data = bad_fix_resp.json()
    assert bad_fix_data["status"] == "rolled_back"
    assert bad_fix_data["health_verified"] is False

    # 5. Actuator: Execute valid allowlisted remediation
    valid_fix_resp = client.post(
        "/api/actuator/execute",
        json={
            "action": "scale_pool",
            "target": "postgres-payment",
            "params": {"pool_size": 150},
            "rationale": "Expanding DB connection pool to 150",
        },
    )
    assert valid_fix_resp.status_code == 200
    valid_fix_data = valid_fix_resp.json()
    assert valid_fix_data["status"] == "executed"
    assert valid_fix_data["health_verified"] is True

    # 6. Memory Commit: Write incident back to Knowledge Graph
    commit_resp = client.post(
        "/api/memory/commit",
        json={
            "service_id": "paymentservice",
            "incident_description": "PostgreSQL connection pool exhausted under spike",
            "action_taken": "scale_pool",
            "outcome": "success",
            "safety_score": 92.0,
        },
    )
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()
    assert commit_data["status"] == "committed"

    # 7. Post-incident Pre-ship simulation on PR #142 (Closed-loop learning test)
    sim_post_resp = client.post(
        "/api/simulate-pr",
        json={"pr_id": "PR-142", "target_service": "paymentservice"},
    )
    assert sim_post_resp.status_code == 200
    sim_post = sim_post_resp.json()
    post_score = sim_post["risk_score"]
    assert sim_post["breakdown"]["history_score"] == 25.0
    assert sim_post["incident_count_30d"] == 1

    # Verify the +5.0 point increase
    delta = round(post_score - pre_score, 1)
    assert delta == 5.0, f"Expected exactly +5.0 risk increase, got {delta} ({pre_score} -> {post_score})"

    # 8. Reset to baseline restores clean initial state
    client.post("/api/reset")
    sim_reset_resp = client.post(
        "/api/simulate-pr",
        json={"pr_id": "PR-142", "target_service": "paymentservice"},
    )
    assert sim_reset_resp.json()["risk_score"] == pre_score
