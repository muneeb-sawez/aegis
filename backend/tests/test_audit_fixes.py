"""Regression tests for the 8 core audit defects across PREDICT, MONITOR, and Ingestion."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.graph import get_repository
from backend.ingestion.models import IngestionRequest
from backend.ingestion.service import ingest_repository_or_manifest
from backend.monitor.health_checker import HealthChecker


def test_audit_callers_traverses_depends_on_edges():
    """Verify callers() traverses DEPENDS_ON and CONNECTS_TO edges in addition to CALLS."""
    repo = get_repository()
    repo.reset()

    # Create services with DEPENDS_ON relationship: order_worker -> db_broker
    if hasattr(repo, "_graph"):
        repo._graph.add_node("order_worker", label="Service")
        repo._graph.add_node("db_broker", label="Service")
        repo._graph.add_edge("order_worker", "db_broker", type="DEPENDS_ON")

    callers = repo.callers("db_broker", depth=2)
    caller_ids = {c.node for c in callers}
    assert "order_worker" in caller_ids, f"Expected order_worker in callers of db_broker, got {caller_ids}"


@pytest.mark.anyio
async def test_audit_github_ingestion_rejects_nonexistent_repo_without_fallback():
    """Verify GitHub ingestion does NOT silently fall back to sample topology for unknown repos."""
    req = IngestionRequest(repo_url="nonexistent-user-xyz123/nonexistent-repo-987abc")
    with pytest.raises(Exception) as exc_info:
        await ingest_repository_or_manifest(req)

    err = str(exc_info.value)
    assert "No recognized Docker Compose" in err or "Failed to fetch" in err or "HTTP" in err


def test_audit_monitoring_initial_status_is_pending():
    """Verify unprobed/unmonitored services default to 'pending', not 'healthy'."""
    checker = HealthChecker()
    checker.configure_endpoint("custom_svc", "http://127.0.0.1:8000/api/monitor/probe/custom_svc")
    records = checker.get_all_health_states()
    custom_record = next((r for r in records if r.service_id == "custom_svc"), None)
    assert custom_record is not None
    assert custom_record.status == "pending", f"Expected initial status 'pending', got '{custom_record.status}'"


def test_audit_monitoring_probe_and_fault_endpoints():
    """Verify /api/monitor/probe/{service_id} and /api/monitor/fault work accurately."""
    client = TestClient(app)

    # 1. Probe individual service endpoint
    resp = client.get("/api/monitor/probe/paymentservice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_id"] == "paymentservice"
    assert data["status"] == "ok"

    # 2. Inject fault through API
    fault_resp = client.post("/api/monitor/fault", json={
        "service_id": "paymentservice",
        "fault_type": "timeout",
        "consecutive_failures": 3,
        "latency_ms": 3500.0,
    })
    assert fault_resp.status_code == 200
    fault_data = fault_resp.json()
    assert fault_data["service_id"] == "paymentservice"
    assert fault_data["is_simulated_fault"] is True
    assert fault_data["status"] == "unhealthy"

    # 3. Clear fault
    clear_resp = client.post("/api/monitor/fault", json={
        "service_id": "paymentservice",
        "fault_type": "clear",
        "consecutive_failures": 0,
        "latency_ms": 0.0,
    })
    assert clear_resp.status_code == 200
