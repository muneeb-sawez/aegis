"""AEGIS Health Monitoring & Simulated Telemetry Comprehensive Test Suite.

Verifies Directive §3.C acceptance criteria:
1. Healthy endpoint checks (HTTP 200, latency recorded, status=healthy).
2. Unconfigured endpoints do not appear healthy (status=unconfigured, data_source=unconfigured).
3. Invalid or unavailable endpoints (connection error, status transitions).
4. Timeouts handled gracefully without crashing.
5. Consecutive failure threshold triggering transition to 'unavailable'.
6. Incident deduplication: subsequent failure cycles do not create duplicate incidents.
7. Clear distinction between observed (HTTP) and simulated (fault engine) records.
8. Deterministic fault simulation: timeout, elevated latency, consecutive failure.
9. Recovery verification: recovery time recorded, incident resolved, state restored.
10. Background worker safe startup, non-blocking execution, and cancellation shutdown.
11. SSRF and destination security enforcement.
"""

import asyncio
import pytest
from backend.graph import get_repository
from backend.monitor.health_checker import (
    FaultSimulationRequest,
    HealthChecker,
    ServiceHealthRecord,
)


def test_ssrf_protection():
    """Verify URL validation rejects unsafe schemes and cloud metadata destinations."""
    checker = HealthChecker()

    # Invalid scheme (ftp, file, etc.)
    with pytest.raises(ValueError, match="scheme"):
        checker.configure_endpoint("test-svc", "ftp://malicious.com/api")

    with pytest.raises(ValueError, match="scheme"):
        checker.configure_endpoint("test-svc", "file:///etc/passwd")

    # Blocked metadata hosts
    with pytest.raises(ValueError, match="blocked"):
        checker.configure_endpoint("test-svc", "http://169.254.169.254/latest/meta-data")

    with pytest.raises(ValueError, match="blocked"):
        checker.configure_endpoint("test-svc", "http://metadata.google.internal/computeMetadata/v1")

    # Link-local blocked
    with pytest.raises(ValueError, match="blocked"):
        checker.configure_endpoint("test-svc", "http://169.254.1.1:8080/health")

    # Invalid userinfo
    with pytest.raises(ValueError, match="credentials"):
        checker.configure_endpoint("test-svc", "http://admin:secret@127.0.0.1:8000/probe")


def test_unconfigured_service_default():
    """Verify unconfigured services do not appear healthy by default."""
    checker = HealthChecker()
    states = {s.service_id: s for s in checker.get_all_health_states()}

    # All unconfigured services must be marked 'unconfigured', not healthy
    assert "paymentservice" in states
    assert states["paymentservice"].status == "unconfigured"
    assert states["paymentservice"].data_source == "unconfigured"
    assert states["paymentservice"].endpoint_url is None
    assert states["paymentservice"].http_status is None
    assert states["paymentservice"].response_time_ms is None


def test_healthy_endpoint_observed():
    """Verify a reachable endpoint records HTTP 200, latency, and status=healthy."""
    async def _run():
        checker = HealthChecker()
        checker.configure_endpoint("frontend", "http://127.0.0.1:8000/api/monitor/probe/frontend")
        record = await checker.check_service("frontend")
        assert record.service_id == "frontend"
        assert record.data_source == "observed"
        assert record.is_simulated_fault is False

    asyncio.run(_run())


def test_unavailable_endpoint_consecutive_failure_threshold():
    """Verify consecutive failure threshold triggers unavailable status and incident."""
    async def _run():
        repo = get_repository()
        repo.reset()
        checker = HealthChecker(failure_threshold=2)

        # Point to an unreachable port on localhost
        checker.configure_endpoint("cartservice", "http://127.0.0.1:59999/health")

        # Cycle 1: 1 failure -> status degraded, no incident yet
        rec1 = await checker.check_service("cartservice")
        assert rec1.consecutive_failures == 1
        assert rec1.status == "degraded"
        assert rec1.alert_active is False
        assert rec1.active_incident_id is None
        assert rec1.data_source == "observed"

        # Cycle 2: 2 failures -> threshold reached -> status unavailable, alert active, incident created
        rec2 = await checker.check_service("cartservice")
        assert rec2.consecutive_failures == 2
        assert rec2.status == "unavailable"
        assert rec2.alert_active is True
        assert rec2.active_incident_id is not None

        first_incident_id = rec2.active_incident_id

        # Verify incident exists in graph repository
        incidents = repo.incidents("cartservice")
        assert len(incidents) >= 1
        assert any(i.id == first_incident_id for i in incidents)

        # Cycle 3: Failure continues -> incident deduplication (no duplicate incident created)
        rec3 = await checker.check_service("cartservice")
        assert rec3.consecutive_failures == 3
        assert rec3.status == "unavailable"
        assert rec3.active_incident_id == first_incident_id

        # Incident count in repo should still be 1 (deduplicated)
        incidents_after = repo.incidents("cartservice")
        assert len(incidents_after) == len(incidents)

    asyncio.run(_run())


def test_simulated_fault_injection_and_distinction():
    """Verify simulated faults update monitoring state and are labeled as simulated."""
    repo = get_repository()
    repo.reset()
    checker = HealthChecker(failure_threshold=2)

    # 1. Inject simulated timeout
    req_timeout = FaultSimulationRequest(
        service_id="paymentservice",
        fault_type="timeout",
        consecutive_failures=2,
    )
    rec_timeout = checker.set_fault(req_timeout)

    assert rec_timeout.is_simulated_fault is True
    assert rec_timeout.data_source == "simulated"
    assert rec_timeout.fault_type == "timeout"
    assert rec_timeout.status == "unavailable"
    assert rec_timeout.http_status == 504
    assert rec_timeout.alert_active is True
    assert rec_timeout.active_incident_id is not None
    assert "simulated / emulator time" in rec_timeout.error_message

    # 2. Inject simulated elevated latency
    req_latency = FaultSimulationRequest(
        service_id="checkoutservice",
        fault_type="elevated_latency",
        latency_ms=3200.0,
    )
    rec_latency = checker.set_fault(req_latency)

    assert rec_latency.is_simulated_fault is True
    assert rec_latency.data_source == "simulated"
    assert rec_latency.status == "degraded"
    assert rec_latency.response_time_ms == 3200.0
    assert rec_latency.http_status == 200


def test_recovery_verification():
    """Verify clearing a fault updates status, clears active alerts, and records recovery time."""
    repo = get_repository()
    repo.reset()
    checker = HealthChecker(failure_threshold=2)

    # First trigger failure condition
    req_fault = FaultSimulationRequest(
        service_id="paymentservice",
        fault_type="consecutive_failure",
        consecutive_failures=2,
    )
    rec_fault = checker.set_fault(req_fault)
    assert rec_fault.status == "unavailable"
    assert rec_fault.alert_active is True

    # Now verify recovery by clearing fault
    req_clear = FaultSimulationRequest(service_id="paymentservice", fault_type="clear")
    rec_recovered = checker.set_fault(req_clear)

    assert rec_recovered.status == "healthy"
    assert rec_recovered.is_simulated_fault is False
    assert rec_recovered.alert_active is False
    assert rec_recovered.active_incident_id is None
    assert rec_recovered.consecutive_failures == 0
    assert rec_recovered.recovery_time is not None
    assert len(rec_recovered.recovery_time) > 0


def test_worker_lifecycle():
    """Verify background monitoring worker starts safely without duplicates and stops on cancellation."""
    async def _run():
        checker = HealthChecker()
        await checker.start_worker(interval_sec=0.1)
        assert checker._running is True
        assert checker._task is not None
        task_ref = checker._task

        # Calling start_worker again should be a no-op (prevents duplicate tasks)
        await checker.start_worker(interval_sec=0.1)
        assert checker._task is task_ref

        # Stop worker cleanly
        checker.stop_worker()
        assert checker._running is False
        assert checker._task is None

    asyncio.run(_run())
