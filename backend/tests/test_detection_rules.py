"""Unit and integration tests for AEGIS deterministic detection rules, de-duplication, and SSE events."""

import asyncio
import json
import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from backend.api.main import app
from backend.config import settings
from backend.graph import get_repository
from backend.monitor.health_checker import (
    HealthChecker,
    ProbeResult,
    get_health_checker,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_monitor():
    """Ensure clean monitor and graph state before each test."""
    repo = get_repository()
    repo.reset()
    checker = get_health_checker()
    checker.reset()
    yield
    checker.stop_worker()
    checker.reset()


def test_rule_baseline_latency_computation():
    """Rule: baseline latency is computed as median of first healthy window."""
    checker = HealthChecker()
    service_id = "test-service"

    # Ingest healthy latencies: [40, 50, 60, 45, 55] (baseline_window = 5)
    latencies = [40.0, 50.0, 60.0, 45.0, 55.0]
    for lat in latencies:
        checker.record_probe(
            service_id=service_id,
            status="healthy",
            http_code=200,
            latency_ms=lat,
            ok=True,
        )

    baseline = checker.get_baseline_latency(service_id)
    assert baseline is not None
    # Median of [40, 45, 50, 55, 60] is 50.0
    assert baseline == 50.0


def test_rule_latency_multiplier_anomaly():
    """Rule: anomaly when latency > multiplier x baseline for N probes."""
    checker = HealthChecker()
    service_id = "latency-service"

    # Establish baseline = 50ms with 5 healthy probes
    for _ in range(5):
        checker.record_probe(service_id, "healthy", 200, 50.0, ok=True)
    assert checker.get_baseline_latency(service_id) == 50.0

    # Probe 1 elevated: 160ms (> 3x50 = 150ms). 1 probe not enough if N=2
    checker.record_probe(service_id, "degraded", 200, 160.0, ok=True)
    anomaly1 = checker.evaluate_anomaly(service_id)
    if settings.CONSECUTIVE_FAILURES > 1:
        assert anomaly1 is None or anomaly1.get("trigger") != "latency_multiplier"

    # Probe 2 elevated: 170ms (> 150ms) -> triggers latency_multiplier
    checker.record_probe(service_id, "degraded", 200, 170.0, ok=True)
    anomaly2 = checker.evaluate_anomaly(service_id)
    assert anomaly2 is not None
    assert anomaly2["trigger"] == "latency_multiplier"
    assert anomaly2["status"] == "degraded"


def test_rule_consecutive_failures_anomaly():
    """Rule: anomaly when consecutive failures >= threshold."""
    checker = HealthChecker()
    service_id = "fail-service"

    # Failure 1
    checker.record_probe(service_id, "degraded", 500, 20.0, ok=False, error="HTTP 500")
    assert checker.evaluate_anomaly(service_id) is None

    # Failure 2 (reaches CONSECUTIVE_FAILURES = 2)
    checker.record_probe(service_id, "unavailable", 500, 25.0, ok=False, error="HTTP 500")
    anomaly = checker.evaluate_anomaly(service_id)
    assert anomaly is not None
    assert anomaly["trigger"] == "consecutive_failures"
    assert anomaly["status"] == "unavailable"


def test_rule_error_rate_threshold_anomaly():
    """Rule: anomaly when error rate in rolling window exceeds threshold."""
    checker = HealthChecker()
    service_id = "err-rate-service"

    # 1 ok, 3 failures -> 3/4 = 75% error rate (> 50% threshold)
    checker.record_probe(service_id, "healthy", 200, 30.0, ok=True)
    checker.record_probe(service_id, "degraded", 503, 30.0, ok=False, error="503")
    checker.record_probe(service_id, "degraded", 503, 30.0, ok=False, error="503")
    checker.record_probe(service_id, "degraded", 503, 30.0, ok=False, error="503")

    anomaly = checker.evaluate_anomaly(service_id)
    assert anomaly is not None
    # Trigger is either consecutive_failures or error_rate
    assert anomaly["trigger"] in ("error_rate", "consecutive_failures")


@pytest.mark.anyio
async def test_episode_deduplication_and_cooldown():
    """Rule: emit ONE anomaly event and create ONE Incident node per episode; cooldown prevents repeated incidents."""
    repo = get_repository()
    repo.reset()
    checker = HealthChecker()
    service_id = "dedup-service"

    emitted_events: list[dict] = []
    q = checker.subscribe_events()

    async def collect_events():
        while True:
            try:
                ev = await asyncio.wait_for(q.get(), timeout=0.1)
                emitted_events.append(ev)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                break

    # 1. Trigger consecutive failure episode
    await checker.process_probe_outcome(
        service_id=service_id,
        status="degraded",
        http_code=500,
        latency_ms=20.0,
        ok=False,
        error="Fail 1",
    )
    await checker.process_probe_outcome(
        service_id=service_id,
        status="unavailable",
        http_code=500,
        latency_ms=20.0,
        ok=False,
        error="Fail 2",
    )

    # Allow event queue to collect
    task = asyncio.create_task(collect_events())
    await asyncio.sleep(0.05)
    task.cancel()

    # Verify Incident created once
    incidents = repo.incidents(service_id)
    assert len(incidents) == 1
    incident_id = incidents[0].id

    # Verify ONE anomaly event
    anomaly_events = [e for e in emitted_events if e["type"] == "anomaly"]
    assert len(anomaly_events) == 1
    assert anomaly_events[0]["payload"]["service_id"] == service_id
    assert anomaly_events[0]["payload"]["incident_id"] == incident_id

    # 2. Subsequent failures in the SAME episode must NOT create new incidents or anomaly events
    emitted_events.clear()
    for _ in range(3):
        await checker.process_probe_outcome(
            service_id=service_id,
            status="unavailable",
            http_code=500,
            latency_ms=20.0,
            ok=False,
            error="Continued Fail",
        )

    task = asyncio.create_task(collect_events())
    await asyncio.sleep(0.05)
    task.cancel()

    # Still only 1 incident and 0 new anomaly events
    assert len(repo.incidents(service_id)) == 1
    assert len([e for e in emitted_events if e["type"] == "anomaly"]) == 0

    # 3. Recovery ends episode and emits ONE recovered event
    emitted_events.clear()
    await checker.process_probe_outcome(
        service_id=service_id,
        status="healthy",
        http_code=200,
        latency_ms=30.0,
        ok=True,
    )

    task = asyncio.create_task(collect_events())
    await asyncio.sleep(0.05)
    task.cancel()

    recovered_events = [e for e in emitted_events if e["type"] == "recovered"]
    assert len(recovered_events) == 1
    assert recovered_events[0]["payload"]["service_id"] == service_id

    # 4. Immediate re-failure within cooldown does NOT create a new incident
    emitted_events.clear()
    await checker.process_probe_outcome(
        service_id=service_id,
        status="unavailable",
        http_code=500,
        latency_ms=20.0,
        ok=False,
        error="Rapid Flap",
    )
    await checker.process_probe_outcome(
        service_id=service_id,
        status="unavailable",
        http_code=500,
        latency_ms=20.0,
        ok=False,
        error="Rapid Flap 2",
    )

    # Within COOLDOWN_SECONDS, no duplicate incident is added
    assert len(repo.incidents(service_id)) == 1

    checker.unsubscribe_events(q)


@pytest.mark.anyio
async def test_integration_fake_endpoint_flips_to_failing():
    """Integration test using a fake endpoint that flips to failing: exactly one anomaly event and one Incident."""
    repo = get_repository()
    repo.reset()
    checker = HealthChecker()

    # Create a small fake FastAPI endpoint in-memory
    fake_app = FastAPI()
    endpoint_state = {"healthy": True}

    @fake_app.get("/test/health")
    def fake_health():
        if endpoint_state["healthy"]:
            return {"status": "ok"}
        raise HTTPException(status_code=500, detail="Fake service failure")

    # Wire custom transport for testing
    transport = ASGITransport(app=fake_app)
    custom_client = AsyncClient(transport=transport, base_url="http://fake-test")
    checker.set_custom_http_client(custom_client)
    checker.configure_endpoint("paymentservice", "http://fake-test/test/health")

    q = checker.subscribe_events()
    emitted_events: list[dict] = []

    async def collect_events():
        while True:
            try:
                ev = await asyncio.wait_for(q.get(), timeout=0.05)
                emitted_events.append(ev)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                break

    # 1. Establish healthy baseline (5 probes)
    for _ in range(5):
        await checker.check_service("paymentservice")

    assert checker.get_baseline_latency("paymentservice") is not None
    assert checker.get_health_state("paymentservice").status == "healthy"

    # 2. Flip endpoint to failing
    endpoint_state["healthy"] = False

    # Probe 1: degraded
    await checker.check_service("paymentservice")
    assert checker.get_health_state("paymentservice").status == "degraded"
    assert len(repo.incidents("paymentservice")) == 0

    # Probe 2: reaches threshold -> triggers anomaly & incident
    await checker.check_service("paymentservice")
    assert checker.get_health_state("paymentservice").status in ("unavailable", "degraded")
    assert len(repo.incidents("paymentservice")) == 1

    # Probe 3 & 4: still failing -> deduplication ensures no duplicate incidents
    await checker.check_service("paymentservice")
    await checker.check_service("paymentservice")
    assert len(repo.incidents("paymentservice")) == 1

    # Drain events
    task = asyncio.create_task(collect_events())
    await asyncio.sleep(0.05)
    task.cancel()

    # Exactly ONE anomaly event emitted across the entire episode
    anomalies = [e for e in emitted_events if e["type"] == "anomaly"]
    assert len(anomalies) == 1
    assert anomalies[0]["payload"]["service_id"] == "paymentservice"

    # 3. Flip back to healthy -> verified recovery
    endpoint_state["healthy"] = True
    emitted_events.clear()

    await checker.check_service("paymentservice")
    assert checker.get_health_state("paymentservice").status == "healthy"

    task = asyncio.create_task(collect_events())
    await asyncio.sleep(0.05)
    task.cancel()

    recovered = [e for e in emitted_events if e["type"] == "recovered"]
    assert len(recovered) == 1
    assert recovered[0]["payload"]["service_id"] == "paymentservice"

    checker.unsubscribe_events(q)


def test_monitor_sse_events_endpoint():
    """Verify GET /api/monitor/events emits valid SSE messages in expected format."""
    resp = client.get("/api/monitor/events?max_events=1")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert "data:" in resp.text
    assert '"type":' in resp.text
    assert '"payload":' in resp.text



