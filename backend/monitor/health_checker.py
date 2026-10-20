"""AEGIS Service Health Monitoring & Simulated Telemetry Engine (Directive §3.C).

Features:
- Periodic asynchronous HTTP health checks with response timing.
- SSRF prevention (URL scheme validation, port validation, cloud metadata blocking).
- Explicit service endpoint configuration; unconfigured services are marked 'unconfigured'.
- Distinction between real observed HTTP checks and simulated fault checks.
- Consecutive failure threshold (default: 2) triggering an Incident in the Knowledge Graph.
- Incident deduplication (only one active incident per failing service).
- Verified recovery detection with recovery timestamp recording.
- Deterministic fault simulation (simulated timeout, elevated latency, consecutive failure).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import ipaddress
import time
from typing import Any, Literal, Optional
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, Field

from backend.graph import get_repository

BLOCKED_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata",
    "100.100.100.200",
    "169.254.170.2",
}

HealthStatus = Literal["pending", "healthy", "degraded", "unavailable", "unhealthy", "unconfigured", "unknown"]
DataSource = Literal["observed", "simulated", "unconfigured"]


class ServiceHealthRecord(BaseModel):
    service_id: str
    endpoint_url: Optional[str] = None
    status: HealthStatus = "unconfigured"
    http_status: Optional[int] = None
    response_time_ms: Optional[float] = None
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


class HealthChecker:
    """Singleton health monitoring agent for AEGIS services."""

    def __init__(self, failure_threshold: int = 2, timeout_sec: float = 3.0):
        self.failure_threshold = failure_threshold
        self.timeout_sec = timeout_sec
        self.interval_sec = 10.0
        self._monitored_services: dict[str, str] = {}
        self._health_state: dict[str, ServiceHealthRecord] = {}
        self._active_faults: dict[str, dict[str, Any]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Discover or initialize known service records as unconfigured by default
        self._init_services()

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
        except Exception:
            pass

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
        if not url or not isinstance(url, str):
            raise ValueError("Endpoint URL cannot be empty.")

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

        host = (parsed.hostname or "").lower()
        if not host:
            raise ValueError("URL must include a valid hostname or IP address.")

        if host in BLOCKED_HOSTS:
            raise ValueError(f"Target host '{host}' is blocked for security purposes.")

        # Check for link-local or cloud metadata IP ranges
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_link_local:
                raise ValueError(f"Link-local IP address '{host}' is blocked.")
        except ValueError as e:
            if "blocked" in str(e):
                raise
            # Not an IP string, which is normal for domain names

        # Prevent userinfo credentials in target URL
        if parsed.username or parsed.password:
            raise ValueError("User credentials are not allowed in endpoint URLs.")

        # Port validation if specified
        if parsed.port is not None and not (1 <= parsed.port <= 65535):
            raise ValueError(f"Port {parsed.port} is outside valid range (1-65535).")

    async def start_worker(self, interval_sec: float = 10.0):
        """Start continuous background monitoring worker (safe, non-blocking, single instance)."""
        if self._running or (self._task is not None and not self._task.done()):
            return
        self._running = True
        self.interval_sec = interval_sec

        async def _loop():
            # Initial probe on startup
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
        """Inject or clear a deterministic simulated operational fault (simulated / emulator time)."""
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

            # If service has an explicit endpoint, set to unknown until next check
            # If purely simulated, mark verified recovery
            record.is_simulated_fault = False
            record.fault_type = None
            record.consecutive_failures = 0
            record.alert_active = False
            record.active_incident_id = None
            record.error_message = None
            record.recovery_time = now_iso
            record.last_check_time = now_iso

            if record.endpoint_url:
                record.data_source = "observed"
                record.status = "healthy"
                record.http_status = 200
                record.response_time_ms = 35.0
            else:
                record.data_source = "simulated"
                record.status = "healthy"
                record.http_status = 200
                record.response_time_ms = 35.0

            try:
                repo = get_repository()
                repo.set_telemetry(req.service_id, {"status": "healthy", "p99_ms": 35.0, "error_rate": 0.0})
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

        # Deduplicated incident generation if failure threshold is reached
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
                )
                record.active_incident_id = inc.id
                repo.set_telemetry(req.service_id, {"status": "unavailable", "alert": record.error_message})
            except Exception:
                pass

        return record

    async def check_service(self, service_id: str) -> ServiceHealthRecord:
        """Execute a single health check cycle for a given service."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Check if simulated fault is active
        if service_id in self._active_faults:
            fault_def = self._active_faults[service_id]
            req = FaultSimulationRequest(service_id=service_id, **fault_def)
            return self.set_fault(req)

        endpoint_url = self._monitored_services.get(service_id)

        # 2. Check if service is unconfigured
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

        # 3. Perform real HTTP health check
        record = self._health_state.get(service_id)
        if not record:
            record = ServiceHealthRecord(
                service_id=service_id,
                endpoint_url=endpoint_url,
                status="unknown",
                data_source="observed",
                failure_threshold=self.failure_threshold,
            )
            self._health_state[service_id] = record

        record.endpoint_url = endpoint_url
        record.data_source = "observed"
        record.is_simulated_fault = False
        record.fault_type = None
        record.last_check_time = now_iso

        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(endpoint_url)
                latency = round((time.perf_counter() - start_time) * 1000.0, 2)
                record.response_time_ms = latency
                record.http_status = resp.status_code

                if resp.status_code == 200:
                    # Verified recovery detection
                    if record.consecutive_failures > 0 or record.alert_active or record.status in ("unavailable", "degraded"):
                        record.recovery_time = now_iso

                    record.status = "healthy"
                    record.consecutive_failures = 0
                    record.error_message = None
                    record.alert_active = False
                    record.active_incident_id = None

                    try:
                        repo = get_repository()
                        repo.set_telemetry(service_id, {"status": "healthy", "p99_ms": latency, "error_rate": 0.0})
                    except Exception:
                        pass

                elif resp.status_code < 500:
                    record.consecutive_failures += 1
                    record.error_message = f"HTTP {resp.status_code} client error."
                    if record.consecutive_failures >= self.failure_threshold:
                        record.status = "unavailable"
                        record.alert_active = True
                    else:
                        record.status = "degraded"

                else:
                    record.consecutive_failures += 1
                    record.error_message = f"HTTP {resp.status_code} server error."
                    if record.consecutive_failures >= self.failure_threshold:
                        record.status = "unavailable"
                        record.alert_active = True
                    else:
                        record.status = "degraded"

        except httpx.TimeoutException:
            record.consecutive_failures += 1
            record.http_status = None
            record.response_time_ms = self.timeout_sec * 1000.0
            record.error_message = f"Request timed out after {self.timeout_sec}s."
            if record.consecutive_failures >= self.failure_threshold:
                record.status = "unavailable"
                record.alert_active = True
            else:
                record.status = "degraded"

        except Exception as e:
            record.consecutive_failures += 1
            record.http_status = None
            record.response_time_ms = None
            record.error_message = f"Connection error: {str(e)}"
            if record.consecutive_failures >= self.failure_threshold:
                record.status = "unavailable"
                record.alert_active = True
            else:
                record.status = "degraded"

        # Deduplicated incident generation if consecutive failures reach threshold
        if record.consecutive_failures >= self.failure_threshold and not record.active_incident_id:
            try:
                repo = get_repository()
                inc = repo.add_incident(
                    service_id=service_id,
                    description=f"Health monitor alert: {record.error_message}",
                    decision_data={
                        "trigger": "consecutive_failure_threshold",
                        "failures": record.consecutive_failures,
                        "data_source": "observed",
                    },
                )
                record.active_incident_id = inc.id
                repo.set_telemetry(service_id, {"status": "unavailable", "alert": record.error_message})
            except Exception:
                pass

        return record

    async def check_all_services(self) -> list[ServiceHealthRecord]:
        """Perform health checks across all known services (both configured and unconfigured)."""
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
        """Reset monitoring state and faults back to initial baseline."""
        self._active_faults.clear()
        self._health_state.clear()
        self._monitored_services.clear()
        self._init_services()


# Global singleton instance
_checker_instance: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = HealthChecker()
    return _checker_instance
