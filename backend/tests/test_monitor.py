"""AEGIS Health Monitoring & Simulated Telemetry Tests (Directive §3.C).

Verifies:
1. Endpoint URL validation and SSRF defense.
2. Simulated fault injection (timeout, latency, consecutive failure).
3. Consecutive failure threshold triggering an Incident in the graph.
4. Fault clearing and health recovery.
"""

import pytest
from backend.graph import get_repository
from backend.monitor.health_checker import FaultSimulationRequest, HealthChecker


def test_ssrf_protection():
    checker = HealthChecker()

    # Invalid scheme
    with pytest.raises(ValueError, match="scheme"):
        checker.configure_endpoint("test-svc", "ftp://malicious.com/api")

    # Blocked metadata host
    with pytest.raises(ValueError, match="blocked"):
        checker.configure_endpoint("test-svc", "http://169.254.169.254/latest/meta-data")


def test_simulated_fault_and_alert_generation():
    repo = get_repository()
    checker = HealthChecker(failure_threshold=3)

    # Initial state is healthy
    checker.configure_endpoint("paymentservice", "http://127.0.0.1:8000/")

    # Inject simulated timeout
    req = FaultSimulationRequest(
        service_id="paymentservice",
        fault_type="timeout",
        consecutive_failures=3,
    )
    record = checker.set_fault(req)

    assert record.is_simulated_fault is True
    assert record.status == "unhealthy"
    assert record.http_status == 504
    assert record.consecutive_failures == 3
    assert record.alert_active is True
    assert record.active_incident_id is not None

    # Verify incident was recorded in Knowledge Graph
    incidents = repo.incidents("paymentservice")
    assert len(incidents) >= 1
    assert "health monitor alert" in incidents[0].description


def test_fault_clearing_and_recovery():
    checker = HealthChecker(failure_threshold=3)

    # Inject fault
    req = FaultSimulationRequest(
        service_id="paymentservice",
        fault_type="elevated_latency",
        latency_ms=3200.0,
    )
    record = checker.set_fault(req)
    assert record.status == "degraded"
    assert record.response_time_ms == 3200.0

    # Clear fault
    req_clear = FaultSimulationRequest(service_id="paymentservice", fault_type="clear")
    record_recovered = checker.set_fault(req_clear)
    assert record_recovered.is_simulated_fault is False
    assert record_recovered.status == "healthy"
    assert record_recovered.alert_active is False
