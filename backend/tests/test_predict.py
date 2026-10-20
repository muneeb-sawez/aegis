"""AEGIS PREDICT Change-Risk & Impact Analysis Tests (Directive §3.A).

Verifies:
1. Low-risk scenario: Safe additive API change (< 40.0, Approved).
2. Moderate/High-risk scenario: Breaking contract change removing required fields.
3. High-risk scenario: Introduced dependency cycle (D=100.0, Blocked/Warn).
4. Outbound dependency addition (dependency_add) expanding architecture.
5. Upstream caller traversal (CALLS, DEPENDS_ON) and attenuation.
6. Isolated service impact analysis (B=0.0, callers=[]).
7. Transitive traversal and cycle safety (no infinite recursion).
8. Missing incident history: clean zero-history baseline documentation.
9. Invalid inputs & error handling: HTTP 404 for unknown services, HTTP 400 for missing dependency target.
10. Formula bounds and exact arithmetic: Risk = 0.35B + 0.30C + 0.15D + 0.20H bounded in [0.0, 100.0].
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.routes_predict import ChangeAnalysisRequest, analyze_change
from backend.graph import get_repository
from backend.graph.networkx_repo import NetworkXGraphRepository
from backend.sim.risk import PRPayload, assess_change_risk


def test_predict_safe_additive_change():
    """Scenario 1: Safe additive change -> Low Risk (< 40.0, Approved)."""
    req = ChangeAnalysisRequest(
        service_id="cartservice",
        change_type="additive_safe",
        change_title="Add optional coupon discount",
    )
    result = analyze_change(req)

    assert result.breakdown.contract_score == 0.0
    assert result.breakdown.cycle_score == 0.0
    assert result.risk_score < 40.0
    assert result.verdict == "Approved"
    assert any("clean baseline" in exp for exp in result.explanation)


def test_predict_breaking_api_change():
    """Scenario 2: Breaking API change on paymentservice -> High Contract Severity (C=100.0)."""
    req = ChangeAnalysisRequest(
        service_id="paymentservice",
        change_type="api_breaking",
        change_title="Remove transaction_id field from charge response",
    )
    result = analyze_change(req)

    assert result.breakdown.contract_score == 100.0
    assert result.contract_diff.is_breaking is True
    # Upstream callers must include checkoutservice, orderservice, frontend
    callers = [c["node"] for c in result.blast_details]
    assert "checkoutservice" in callers
    assert "orderservice" in callers
    assert "frontend" in callers
    assert result.risk_score >= 40.0
    assert result.verdict in ("Warn", "Blocked")


def test_predict_dependency_cycle():
    """Scenario 3: Introducing a dependency cycle -> D=100.0, acyclic penalty enforced."""
    req = ChangeAnalysisRequest(
        service_id="shippingservice",
        change_type="dependency_cycle",
        change_title="Add cyclic reverse dependency to caller",
    )
    result = analyze_change(req)

    assert result.breakdown.cycle_score == 100.0
    assert result.cycle_check.has_cycle is True
    assert result.verdict in ("Warn", "Blocked")


def test_predict_dependency_add():
    """Scenario 4: Valid architectural dependency addition."""
    req = ChangeAnalysisRequest(
        service_id="cartservice",
        change_type="dependency_add",
        new_dependency_target="emailservice",
        change_title="Send email notification on cart abandon",
    )
    result = analyze_change(req)

    assert result.breakdown.cycle_score == 0.0
    assert result.breakdown.contract_score == 0.0
    # Formula check
    expected = round(0.35 * result.breakdown.blast_score + 0.20 * result.breakdown.history_score, 1)
    assert abs(result.risk_score - expected) <= 0.1


def test_predict_formula_boundary_and_weights():
    """Verify exact formula bounds: 0.35B + 0.30C + 0.15D + 0.20H in [0.0, 100.0]."""
    repo = get_repository()
    # Baseline PR with zero changes
    payload = PRPayload(
        id="CHANGE-TEST",
        title="Zero Change Test",
        target_service="paymentservice",
        old_schema={"properties": {"x": {"type": "string"}}},
        new_schema={"properties": {"x": {"type": "string"}}},
    )
    res = assess_change_risk(payload, repo)
    assert 0.0 <= res.risk_score <= 100.0
    assert res.breakdown.weights["W_B"] == 0.35
    assert res.breakdown.weights["W_C"] == 0.30
    assert res.breakdown.weights["W_D"] == 0.15
    assert res.breakdown.weights["W_H"] == 0.20

    # Classification boundaries check
    if res.risk_score < 40.0:
        assert res.verdict == "Approved"
    elif res.risk_score < 70.0:
        assert res.verdict == "Warn"
    else:
        assert res.verdict == "Blocked"


def test_predict_isolated_service():
    """Verify that an isolated service in the graph has B=0.0 and callers=[]."""
    repo = get_repository()
    # Register an isolated service
    if hasattr(repo, "_graph"):
        repo._graph.add_node("isolated-svc", label="Service")

    req = ChangeAnalysisRequest(
        service_id="isolated-svc",
        change_type="additive_safe",
        change_title="Change to isolated service",
    )
    result = analyze_change(req)

    assert result.breakdown.blast_score == 0.0
    assert len(result.blast_details) == 0
    assert result.risk_score < 40.0
    assert result.verdict == "Approved"


def test_predict_transitive_multi_hop_and_cycle_traversal():
    """Verify multi-hop backward traversal and cycle termination without infinite loops."""
    repo = get_repository()
    if hasattr(repo, "_graph"):
        # Create cycle: loop1 -> loop2 -> loop3 -> loop1
        repo._graph.add_node("loop1", label="Service")
        repo._graph.add_node("loop2", label="Service")
        repo._graph.add_node("loop3", label="Service")
        repo._graph.add_edge("loop1", "loop2", type="CALLS")
        repo._graph.add_edge("loop2", "loop3", type="CALLS")
        repo._graph.add_edge("loop3", "loop1", type="CALLS")

    # callers() on loop3 must terminate and return loop2 (hop 1) and loop1 (hop 2)
    callers = repo.callers("loop3", depth=3)
    caller_ids = {c.node for c in callers}
    assert "loop2" in caller_ids
    assert "loop1" in caller_ids


def test_predict_incident_history_impact():
    """Verify that adding an incident increases H term by 25.0 points (+5.0 total)."""
    repo = get_repository()
    req = ChangeAnalysisRequest(
        service_id="paymentservice",
        change_type="api_breaking",
    )
    res_before = analyze_change(req)

    # Add incident
    repo.add_incident(
        service_id="paymentservice",
        description="Outage on payment gateway under load",
        decision_data={"cause": "pool_exhaustion"},
    )

    res_after = analyze_change(req)
    assert res_after.breakdown.history_score == res_before.breakdown.history_score + 25.0
    # +25.0 H * 0.20 weight = +5.0 points in composite risk score
    assert round(res_after.risk_score - res_before.risk_score, 1) == 5.0
    assert any("+25.0 penalty" in exp for exp in res_after.explanation)


def test_predict_invalid_service_id_error():
    """Verify HTTP 404 is raised when an unknown service is analyzed."""
    req = ChangeAnalysisRequest(
        service_id="nonexistent-ghost-service",
        change_type="api_breaking",
    )
    with pytest.raises(HTTPException) as exc_info:
        analyze_change(req)
    assert exc_info.value.status_code == 404
    assert "does not exist in active graph" in exc_info.value.detail


def test_predict_missing_dependency_target_error():
    """Verify HTTP 400 is raised when dependency_add has no new_dependency_target."""
    req = ChangeAnalysisRequest(
        service_id="paymentservice",
        change_type="dependency_add",
        new_dependency_target=None,
    )
    with pytest.raises(HTTPException) as exc_info:
        analyze_change(req)
    assert exc_info.value.status_code == 400
    assert "required when proposing a 'dependency_add'" in exc_info.value.detail


def test_predict_services_api_endpoint():
    """Verify GET /api/predict/services returns active services in graph."""
    client = TestClient(app)
    resp = client.get("/api/predict/services")
    assert resp.status_code == 200
    services = resp.json()
    assert isinstance(services, list)
    service_ids = {s["id"] for s in services}
    assert "paymentservice" in service_ids
    assert "frontend" in service_ids
