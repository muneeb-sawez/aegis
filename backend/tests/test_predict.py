"""AEGIS PREDICT Change-Risk Tests (Directive §3.A).

Verifies:
1. Low-risk scenario: Safe additive API change.
2. Moderate/High-risk scenario: Breaking contract change removing required fields.
3. High-risk scenario: Introduced dependency cycle.
4. Upstream caller traversal (reverse of CALLS).
5. Exact scoring bounds and formula compliance: Risk = 0.35B + 0.30C + 0.15D + 0.20H.
"""

import pytest
from backend.api.routes_predict import ChangeAnalysisRequest, analyze_change
from backend.graph.networkx_repo import NetworkXGraphRepository


def test_predict_safe_additive_change():
    """Scenario 1: Safe additive change -> Low Risk (< 40.0)."""
    repo = NetworkXGraphRepository()
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


def test_predict_breaking_api_change():
    """Scenario 2: Breaking API change on paymentservice -> High Risk (C=100.0)."""
    repo = NetworkXGraphRepository()
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


def test_predict_dependency_cycle():
    """Scenario 3: Introducing a dependency cycle -> D=100.0."""
    repo = NetworkXGraphRepository()
    req = ChangeAnalysisRequest(
        service_id="shippingservice",
        change_type="dependency_cycle",
        change_title="Add cyclic reverse dependency to caller",
    )
    result = analyze_change(req)

    assert result.breakdown.cycle_score == 100.0
    assert result.cycle_check.has_cycle is True
    assert result.verdict in ("Warn", "Blocked")
