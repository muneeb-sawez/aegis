"""AEGIS Service Health Monitoring, Rolling Window Telemetry & Anomaly Engine.

Features:
1. Rolling window per monitored service (latest N probes: status, http code, latency, ok/fail).
2. Deterministic baseline latency computation (median of first healthy window).
3. Config-driven anomaly detection rules:
   - Latency > multiplier x baseline for N consecutive probes.
   - Consecutive failures >= threshold.
   - Error rate in rolling window >= threshold.
4. Episode-based anomaly deduplication and cooldown: exactly ONE incident and ONE anomaly event per episode.
5. Verified recovery detection: emits ONE recovered event upon episode resolution.
6. Real-time SSE event broadcaster ({type: 'probe'|'anomaly'|'recovered', ts, payload}).
7. Asynchronous background polling worker with configurable interval and strict per-probe timeout.
8. SSRF protection and destination security validation.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import ipaddress
import logging
import statistics
import time
from typing import Any, Literal, Optional
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, Field

from backend.config import settings
from backend.graph import get_repository

logger = logging.getLogger("aegis.monitor")

BLOCKED_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata",
    "100.100.100.200",
    "169.254.170.2",
}

HealthStatus = Literal["pending", "healthy", "degraded", "unavailable", "unhealthy", "unconfigured", "unknown"]
DataSource = Literal["observed", "simulated", "unconfigured"]


class ProbeResult(BaseModel):
    timestamp: str
    status: HealthStatus
    http_code: Optional[int] = None
    latency_ms: Optional[float] = None
    ok: bool = True
    error: Optional[str] = None


class ServiceHealthRecord(BaseModel):
    service_id: str
    endpoint_url: Optional[str] = None
    status: HealthStatus = "unconfigured"
    http_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    baseline_latency_ms: Optional[float] = None
    rolling_latencies: list[float] = Field(default_factory=list)
    error_rate: float = 0.0
    last_check_time: str = ""
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    failure_threshold: int = 2
    data_source: DataSource = "unconfigured"
    is_simulated_fault: bool = False
    fault_type: Optional[str] = None
    alert_active: bool = False
    active_incident_id: Optional[str] = None
    recovery_time: Optional[str] = None


class FaultSimulationRequest(BaseModel):
    service_id: str
    fault_type: Literal["timeout", "elevated_latency", "consecutive_failure", "clear"]
    consecutive_failures: int = 2
    latency_ms: float = 3500.0
    project_id: str = "demo"


class EventBroadcaster:
    """Async pub/sub event broadcaster for SSE clients."""

    def __init__(self):
        self._listeners: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=200)
        self._listeners.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._listeners.discard(q)

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        envelope = {
            "type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        dead: set[asyncio.Queue] = set()
        for q in list(self._listeners):
            try:
                q.put_nowait(envelope)
            except asyncio.QueueFull:
                dead.add(q)
        for q in dead:
            self._listeners.discard(q)


class HealthChecker:
    """Singleton health monitoring and anomaly detection agent."""

    def __init__(self, failure_threshold: Optional[int] = None, timeout_sec: Optional[float] = None):
        self.failure_threshold = failure_threshold or settings.CONSECUTIVE_FAILURES
        self.timeout_sec = timeout_sec or settings.MONITOR_TIMEOUT_SEC
        self.interval_sec = settings.MONITOR_INTERVAL_SEC

        self._monitored_services: dict[str, str] = {}
        self._health_state: dict[str, ServiceHealthRecord] = {}
        self._active_faults: dict[str, dict[str, Any]] = {}

        # Rolling window & anomaly tracking
        self._rolling_probes: dict[str, deque[ProbeResult]] = {}
        self._healthy_baseline_samples: dict[str, list[float]] = {}
        self._baseline_latencies: dict[str, float] = {}
        self._active_episodes: dict[str, dict[str, Any]] = {}
        self._last_incident_time: dict[str, float] = {}

        # Background worker & custom client for tests
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._custom_client: Optional[httpx.AsyncClient] = None
        self._broadcaster = EventBroadcaster()

        self._init_services()

    def set_custom_http_client(self, client: Optional[httpx.AsyncClient]) -> None:
        """Allow injecting in-memory AsyncClient for tests."""
        self._custom_client = client

    def subscribe_events(self) -> asyncio.Queue:
        return self._broadcaster.subscribe()

    def unsubscribe_events(self, q: asyncio.Queue) -> None:
        self._broadcaster.unsubscribe(q)

    async def broadcast_event(self, event_type: str, payload: dict[str, Any]) -> None:
        await self._broadcaster.broadcast(event_type, payload)

    def _init_services(self):
        """Initialize known microservices in unconfigured state without fake endpoints."""
        default_services = [
            "frontend",
            "checkoutservice",
            "paymentservice",
            "orderservice",
            "cartservice",
            "recommendationservice",
            "shippingservice",
            "emailservice",
        ]
        try:
            repo = get_repository()
            topo = repo.get_topology()
            for node in topo.nodes:
                if node.label in ("Service", "ExternalService"):
                    if node.id not in default_services:
                        default_services.append(node.id)
        except Exception:
            pass

        for sid in default_services:
            if sid not in self._health_state:
                self._health_state[sid] = ServiceHealthRecord(
                    service_id=sid,
                    endpoint_url=None,
                    status="unconfigured",
                    data_source="unconfigured",
                    failure_threshold=self.failure_threshold,
                    error_message="No health check endpoint configured.",
                )
            if sid not in self._rolling_probes:
                self._rolling_probes[sid] = deque(maxlen=20)
            if sid not in self._healthy_baseline_samples:
                self._healthy_baseline_samples[sid] = []

    def _sync_graph_services(self):
        """Synchronize active services from graph repository."""
        try:
            repo = get_repository()
            topo = repo.get_topology()
            for node in topo.nodes:
                if node.label in ("Service", "ExternalService") and node.id not in self._health_state:
                    self._health_state[node.id] = ServiceHealthRecord(
                        service_id=node.id,
                        endpoint_url=self._monitored_services.get(node.id),
                        status="unconfigured",
                        data_source="unconfigured",
                        failure_threshold=self.failure_threshold,
                        error_message="No health check endpoint configured.",
                    )
                    self._rolling_probes[node.id] = deque(maxlen=20)
                    self._healthy_baseline_samples[node.id] = []
        except Exception:
            pass

    def get_baseline_latency(self, service_id: str) -> Optional[float]:
        return self._baseline_latencies.get(service_id)

    def get_health_state(self, service_id: str) -> Optional[ServiceHealthRecord]:
        return self._health_state.get(service_id)

    def get_error_rate(self, service_id: str) -> float:
        probes = self._rolling_probes.get(service_id)
        if not probes:
            return 0.0
        failures = sum(1 for p in probes if not p.ok)
        return round(failures / len(probes), 4)

    def record_probe(
        self,
        service_id: str,
        status: HealthStatus,
        http_code: Optional[int],
        latency_ms: Optional[float],
        ok: bool,
        error: Optional[str] = None,
    ) -> ProbeResult:
        """Append probe result to rolling window and compute baseline latency if needed."""
        now_iso = datetime.now(timezone.utc).isoformat()
        probe = ProbeResult(
            timestamp=now_iso,
            status=status,
            http_code=http_code,
            latency_ms=latency_ms,
            ok=ok,
            error=error,
        )

        if service_id not in self._rolling_probes:
            self._rolling_probes[service_id] = deque(maxlen=20)
        self._rolling_probes[service_id].append(probe)

        # Baseline latency computation: median of first BASELINE_WINDOW healthy probes
        if ok and latency_ms is not None:
            if service_id not in self._healthy_baseline_samples:
                self._healthy_baseline_samples[service_id] = []

            samples = self._healthy_baseline_samples[service_id]
            if len(samples) < settings.BASELINE_WINDOW:
                samples.append(latency_ms)
                if len(samples) >= settings.BASELINE_WINDOW:
                    median_val = round(float(statistics.median(samples)), 2)
                    self._baseline_latencies[service_id] = median_val
                    try:
                        repo = get_repository()
                        repo.set_telemetry(service_id, {"baseline_p99_ms": median_val})
                    except Exception:
                        pass

        return probe

    def evaluate_anomaly(self, service_id: str) -> Optional[dict[str, Any]]:
        """Evaluate deterministic rules over rolling window and consecutive failures.

        Rules:
        1. Consecutive failures >= CONSECUTIVE_FAILURES threshold -> unavailable
        2. Latency > LATENCY_MULTIPLIER x baseline for N probes -> degraded
        3. Error rate in rolling window >= ERROR_RATE_THRESHOLD -> degraded
        """
        probes = list(self._rolling_probes.get(service_id, []))
        if not probes:
            return None

        latest_probe = probes[-1]

        # Calculate consecutive failures directly from rolling window
        consecutive_fails = 0
        for p in reversed(probes):
            if not p.ok:
                consecutive_fails += 1
            else:
                break

        threshold = self.failure_threshold

        # Rule 1: Consecutive failures
        if consecutive_fails >= threshold:
            return {
                "trigger": "consecutive_failures",
                "status": "unavailable",
                "reason": f"Service outage: {consecutive_fails} consecutive failures (threshold {threshold})",
            }

        # Rule 2: Latency Multiplier
        baseline = self._baseline_latencies.get(service_id)
        n_needed = max(2, min(settings.CONSECUTIVE_FAILURES, settings.BASELINE_WINDOW))

        if baseline is not None and len(probes) >= n_needed:
            cutoff = settings.LATENCY_MULTIPLIER * baseline
            recent_n = probes[-n_needed:]
            if all(p.latency_ms is not None and p.latency_ms > cutoff for p in recent_n):
                latest_lat = recent_n[-1].latency_ms
                return {
                    "trigger": "latency_multiplier",
                    "status": "degraded",
                    "reason": f"Elevated latency: last {n_needed} probes ({latest_lat}ms) exceeded {settings.LATENCY_MULTIPLIER}x baseline ({baseline}ms)",
                }

        # Rule 3: Error Rate Threshold
        if not latest_probe.ok and len(probes) >= min(3, settings.BASELINE_WINDOW):
            err_rate = sum(1 for p in probes if not p.ok) / len(probes)
            if err_rate >= settings.ERROR_RATE_THRESHOLD:
                return {
                    "trigger": "error_rate",
                    "status": "degraded",
                    "reason": f"High error rate: {err_rate:.1%} in rolling window exceeds threshold {settings.ERROR_RATE_THRESHOLD:.1%}",
                }

        return None

    async def process_probe_outcome(
        self,
        service_id: str,
        status: HealthStatus,
        http_code: Optional[int],
        latency_ms: Optional[float],
        ok: bool,
        error: Optional[str] = None,
        data_source: DataSource = "observed",
    ) -> ServiceHealthRecord:
        """Process probe outcome, evaluate rules, manage episodes, and emit events."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.record_probe(service_id, status, http_code, latency_ms, ok, error)

        record = self._health_state.get(service_id)
        if not record:
            record = ServiceHealthRecord(
                service_id=service_id,
                endpoint_url=self._monitored_services.get(service_id),
                failure_threshold=self.failure_threshold,
            )
            self._health_state[service_id] = record

        record.http_status = http_code
        record.response_time_ms = latency_ms
        record.last_check_time = now_iso
        record.data_source = data_source
        record.baseline_latency_ms = self._baseline_latencies.get(service_id)
        record.rolling_latencies = [p.latency_ms for p in self._rolling_probes.get(service_id, []) if p.latency_ms is not None]
        record.error_rate = self.get_error_rate(service_id)

        if ok:
            record.consecutive_failures = 0
            record.error_message = None
            record.status = "healthy"
        else:
            record.consecutive_failures += 1
            record.error_message = error or f"Probe failed (HTTP {http_code})"
            record.status = "degraded"

        # Evaluate detection rules
        anomaly = self.evaluate_anomaly(service_id)

        if anomaly:
            record.status = anomaly["status"]
            is_in_episode = service_id in self._active_episodes
            now_sec = time.time()
            last_incident_time = self._last_incident_time.get(service_id, 0.0)
            cooldown_passed = (now_sec - last_incident_time) >= settings.COOLDOWN_SECONDS

            if not is_in_episode:
                if cooldown_passed:
                    # Start new episode: create ONE Incident node & emit ONE anomaly event
                    incident_id = None
                    try:
                        repo = get_repository()
                        inc = repo.add_incident(
                            service_id=service_id,
                            description=f"Health monitor alert: {anomaly['reason']}",
                            decision_data={
                                "trigger": anomaly["trigger"],
                                "reason": anomaly["reason"],
                                "failures": record.consecutive_failures,
                                "data_source": record.data_source,
                            },
                        )
                        incident_id = inc.id
                        repo.set_telemetry(service_id, {"status": anomaly["status"], "alert": anomaly["reason"]})
                    except Exception as e:
                        logger.error(f"Failed to record incident to graph: {e}")

                    self._active_episodes[service_id] = {
                        "incident_id": incident_id,
                        "trigger": anomaly["trigger"],
                        "reason": anomaly["reason"],
                        "started_at": now_iso,
                    }
                    self._last_incident_time[service_id] = now_sec
                    record.active_incident_id = incident_id
                    record.alert_active = True

                    await self.broadcast_event("anomaly", {
                        "service_id": service_id,
                        "incident_id": incident_id,
                        "trigger": anomaly["trigger"],
                        "reason": anomaly["reason"],
                        "status": anomaly["status"],
                        "latency_ms": record.response_time_ms,
                        "baseline_latency_ms": record.baseline_latency_ms,
                        "consecutive_failures": record.consecutive_failures,
                        "error_rate": record.error_rate,
                    })
                else:
                    logger.info(f"Anomaly detected on {service_id} but suppressed by cooldown ({settings.COOLDOWN_SECONDS}s).")
            else:
                # Already in episode: deduplicated
                record.active_incident_id = self._active_episodes[service_id].get("incident_id")
                record.alert_active = True

        else:
            # Healthy or recovering
            if ok:
                record.status = "healthy"
                if service_id in self._active_episodes:
                    # Verified recovery: end episode & emit ONE recovered event
                    ep = self._active_episodes.pop(service_id)
                    prev_incident = ep.get("incident_id")
                    record.recovery_time = now_iso
                    record.alert_active = False
                    record.active_incident_id = None

                    try:
                        repo = get_repository()
                        repo.set_telemetry(service_id, {"status": "healthy", "p99_ms": latency_ms, "error_rate": 0.0})
                    except Exception:
                        pass

                    await self.broadcast_event("recovered", {
                        "service_id": service_id,
                        "previous_incident_id": prev_incident,
                        "status": "healthy",
                        "recovery_time": now_iso,
                        "latency_ms": latency_ms,
                    })

        # Broadcast probe event for all subscribers
        await self.broadcast_event("probe", {
            "service_id": service_id,
            "status": record.status,
            "http_status": record.http_status,
            "latency_ms": record.response_time_ms,
            "baseline_latency_ms": record.baseline_latency_ms,
            "consecutive_failures": record.consecutive_failures,
            "error_rate": record.error_rate,
            "ok": ok,
            "rolling_latencies": record.rolling_latencies,
        })

        return record

    def configure_endpoint(self, service_id: str, endpoint_url: str):
        """Register or update a service's monitored health check endpoint."""
        self._validate_url(endpoint_url)
        self._monitored_services[service_id] = endpoint_url
        if service_id not in self._health_state:
            self._health_state[service_id] = ServiceHealthRecord(
                service_id=service_id,
                endpoint_url=endpoint_url,
                status="pending",
                data_source="observed",
                failure_threshold=self.failure_threshold,
                last_check_time="",
            )
        else:
            rec = self._health_state[service_id]
            rec.endpoint_url = endpoint_url
            rec.data_source = "observed"
            if rec.status in ("unconfigured", "unknown"):
                rec.status = "pending"
                rec.error_message = None

    def unconfigure_endpoint(self, service_id: str):
        """Remove a service's monitored endpoint."""
        self._monitored_services.pop(service_id, None)
        if service_id in self._health_state:
            rec = self._health_state[service_id]
            rec.endpoint_url = None
            rec.status = "unconfigured"
            rec.data_source = "unconfigured"
            rec.error_message = "No health check endpoint configured."
            rec.http_status = None
            rec.response_time_ms = None
            rec.consecutive_failures = 0
            rec.alert_active = False

    def _validate_url(self, url: str):
        """Validate URL to prevent SSRF and unsafe requests."""
        from backend.security.ssrf import validate_url_ssrf
        validate_url_ssrf(url)

    async def start_worker(self, interval_sec: Optional[float] = None):
        """Start continuous background monitoring worker on configurable interval."""
        if self._running or (self._task is not None and not self._task.done()):
            return
        self._running = True
        self.interval_sec = interval_sec or settings.MONITOR_INTERVAL_SEC

        async def _loop():
            try:
                await self.check_all_services()
            except asyncio.CancelledError:
                return
            except Exception:
                pass

            while self._running:
                try:
                    await asyncio.sleep(self.interval_sec)
                    if not self._running:
                        break
                    await self.check_all_services()
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

        self._task = asyncio.create_task(_loop())

    def stop_worker(self):
        """Stop background health check worker cleanly without blocking."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    def set_fault(self, req: FaultSimulationRequest) -> ServiceHealthRecord:
        """Inject or clear a simulated operational fault (simulated / emulator time)."""
        now_iso = datetime.now(timezone.utc).isoformat()

        if req.fault_type == "clear":
            self._active_faults.pop(req.service_id, None)
            record = self._health_state.get(req.service_id)
            if not record:
                record = ServiceHealthRecord(
                    service_id=req.service_id,
                    endpoint_url=self._monitored_services.get(req.service_id),
                )
                self._health_state[req.service_id] = record

            record.is_simulated_fault = False
            record.fault_type = None
            record.consecutive_failures = 0
            record.alert_active = False
            record.active_incident_id = None
            record.error_message = None
            record.recovery_time = now_iso
            record.last_check_time = now_iso
            record.status = "healthy"
            record.http_status = 200
            record.response_time_ms = 35.0

            try:
                repo = get_repository()
                repo.set_telemetry(req.service_id, {"status": "healthy", "p99_ms": 35.0, "error_rate": 0.0}, project_id=req.project_id)
            except Exception:
                pass

            return record

        # Apply fault
        self._active_faults[req.service_id] = {
            "fault_type": req.fault_type,
            "consecutive_failures": req.consecutive_failures,
            "latency_ms": req.latency_ms,
        }

        record = self._health_state.get(req.service_id)
        if not record:
            record = ServiceHealthRecord(
                service_id=req.service_id,
                endpoint_url=self._monitored_services.get(req.service_id),
            )
            self._health_state[req.service_id] = record

        record.is_simulated_fault = True
        record.data_source = "simulated"
        record.fault_type = req.fault_type
        record.last_check_time = now_iso
        record.failure_threshold = self.failure_threshold

        if req.fault_type == "timeout":
            record.consecutive_failures = req.consecutive_failures
            record.http_status = 504
            record.response_time_ms = self.timeout_sec * 1000.0
            record.error_message = f"Simulated connection timeout after {self.timeout_sec}s (simulated / emulator time)"
            if record.consecutive_failures >= self.failure_threshold:
                record.status = "unavailable"
                record.alert_active = True
            else:
                record.status = "degraded"

        elif req.fault_type == "elevated_latency":
            record.status = "degraded"
            record.http_status = 200
            record.response_time_ms = req.latency_ms
            record.consecutive_failures = 1
            record.error_message = f"Elevated latency observed ({req.latency_ms}ms > baseline, simulated / emulator time)"
            record.alert_active = False

        elif req.fault_type == "consecutive_failure":
            record.consecutive_failures = req.consecutive_failures
            record.http_status = 500
            record.response_time_ms = 45.0
            record.error_message = f"Repeated connection failures ({req.consecutive_failures} errors, simulated / emulator time)"
            if record.consecutive_failures >= self.failure_threshold:
                record.status = "unavailable"
                record.alert_active = True
            else:
                record.status = "degraded"

        if record.consecutive_failures >= self.failure_threshold and not record.active_incident_id:
            try:
                repo = get_repository()
                inc = repo.add_incident(
                    service_id=req.service_id,
                    description=f"Health monitor alert: {record.error_message}",
                    decision_data={
                        "trigger": "consecutive_failure_threshold",
                        "failures": record.consecutive_failures,
                        "data_source": "simulated",
                    },
                    project_id=req.project_id,
                )
                record.active_incident_id = inc.id
                repo.set_telemetry(req.service_id, {"status": "unavailable", "alert": record.error_message}, project_id=req.project_id)
            except Exception:
                pass

        return record

    async def check_service(self, service_id: str) -> ServiceHealthRecord:
        """Execute a single health check cycle with strict timeout shorter than interval."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Simulated fault active
        if service_id in self._active_faults:
            fault_def = self._active_faults[service_id]
            req = FaultSimulationRequest(service_id=service_id, **fault_def)
            return self.set_fault(req)

        endpoint_url = self._monitored_services.get(service_id)

        # 2. Unconfigured service
        if not endpoint_url:
            record = self._health_state.get(service_id)
            if not record:
                record = ServiceHealthRecord(
                    service_id=service_id,
                    endpoint_url=None,
                    status="unconfigured",
                    data_source="unconfigured",
                    failure_threshold=self.failure_threshold,
                    error_message="No health check endpoint configured.",
                )
                self._health_state[service_id] = record
            else:
                record.status = "unconfigured"
                record.data_source = "unconfigured"
                record.endpoint_url = None
                record.http_status = None
                record.response_time_ms = None
                record.consecutive_failures = 0
                record.alert_active = False
                record.error_message = "No health check endpoint configured."
            record.last_check_time = now_iso
            return record

        # 3. Real HTTP health check with timeout < interval
        start_time = time.perf_counter()

        try:
            if self._custom_client is not None:
                call_coro = self._custom_client.get(endpoint_url)
                resp = await asyncio.wait_for(call_coro, timeout=self.timeout_sec)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    resp = await client.get(endpoint_url)

            latency = round((time.perf_counter() - start_time) * 1000.0, 2)

            if resp.status_code == 200:
                return await self.process_probe_outcome(
                    service_id=service_id,
                    status="healthy",
                    http_code=200,
                    latency_ms=latency,
                    ok=True,
                )
            elif resp.status_code < 500:
                return await self.process_probe_outcome(
                    service_id=service_id,
                    status="degraded",
                    http_code=resp.status_code,
                    latency_ms=latency,
                    ok=False,
                    error=f"HTTP {resp.status_code} client error.",
                )
            else:
                return await self.process_probe_outcome(
                    service_id=service_id,
                    status="unavailable",
                    http_code=resp.status_code,
                    latency_ms=latency,
                    ok=False,
                    error=f"HTTP {resp.status_code} server error.",
                )

        except (asyncio.TimeoutError, httpx.TimeoutException):
            timeout_latency = round(self.timeout_sec * 1000.0, 2)
            return await self.process_probe_outcome(
                service_id=service_id,
                status="unavailable",
                http_code=None,
                latency_ms=timeout_latency,
                ok=False,
                error=f"Request timed out after {self.timeout_sec}s.",
            )

        except Exception as e:
            return await self.process_probe_outcome(
                service_id=service_id,
                status="unavailable",
                http_code=None,
                latency_ms=None,
                ok=False,
                error=f"Connection error: {str(e)}",
            )

    async def check_all_services(self) -> list[ServiceHealthRecord]:
        """Perform health checks across all known services."""
        self._sync_graph_services()
        service_ids = list(self._health_state.keys())
        tasks = [self.check_service(sid) for sid in service_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        records: list[ServiceHealthRecord] = []
        for r in results:
            if isinstance(r, ServiceHealthRecord):
                records.append(r)
        return records

    def get_all_health_states(self) -> list[ServiceHealthRecord]:
        """Return the current cached health records across all services."""
        self._sync_graph_services()
        return list(self._health_state.values())

    def reset(self):
        """Reset monitoring state and faults back to clean initial baseline."""
        self._active_faults.clear()
        self._health_state.clear()
        self._monitored_services.clear()
        self._rolling_probes.clear()
        self._healthy_baseline_samples.clear()
        self._baseline_latencies.clear()
        self._active_episodes.clear()
        self._last_incident_time.clear()
        self._custom_client = None
        self._init_services()


# Global singleton instance
_checker_instance: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = HealthChecker()
    return _checker_instance
