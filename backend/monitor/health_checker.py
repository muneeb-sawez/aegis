"""AEGIS Service Health Monitoring & Simulated Telemetry Engine (Directive §3.C).

Features:
- Periodic asynchronous HTTP health checks with response timing.
- SSRF prevention (URL scheme validation, cloud metadata blocking).
- Consecutive failure threshold & automatic incident/alert emission.
- Recovery detection when endpoints return to healthy state.
- Deterministic fault simulation (simulated timeout, latency, consecutive errors).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Literal, Optional
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, Field

from backend.graph import get_repository

BLOCKED_HOSTS = {"169.254.169.254", "metadata.google.internal", "metadata"}


class ServiceHealthRecord(BaseModel):
    service_id: str
    endpoint_url: str
    status: Literal["healthy", "degraded", "unhealthy", "unreachable"] = "healthy"
    http_status: Optional[int] = None
    response_time_ms: float = 0.0
    last_check_time: str = ""
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    is_simulated_fault: bool = False
    fault_type: Optional[str] = None
    alert_active: bool = False
    active_incident_id: Optional[str] = None


class FaultSimulationRequest(BaseModel):
    service_id: str
    fault_type: Literal["timeout", "elevated_latency", "consecutive_failure", "clear"]
    consecutive_failures: int = 3
    latency_ms: float = 3500.0


class HealthChecker:
    """Singleton health monitoring agent for AEGIS services."""

    def __init__(self, failure_threshold: int = 3, timeout_sec: float = 3.0):
        self.failure_threshold = failure_threshold
        self.timeout_sec = timeout_sec
        self._monitored_services: dict[str, str] = {}
        self._health_state: dict[str, ServiceHealthRecord] = {}
        self._active_faults: dict[str, dict[str, Any]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Register default service endpoints
        self._init_defaults()

    def _init_defaults(self):
        # Configure endpoints for core services
        defaults = {
            "frontend": "http://127.0.0.1:8000/",
            "checkoutservice": "http://127.0.0.1:8000/api/graph/topology",
            "paymentservice": "http://127.0.0.1:8000/api/graph/topology",
            "orderservice": "http://127.0.0.1:8000/",
            "cartservice": "http://127.0.0.1:8000/",
            "recommendationservice": "http://127.0.0.1:8000/",
            "shippingservice": "http://127.0.0.1:8000/",
            "emailservice": "http://127.0.0.1:8000/",
        }
        for sid, url in defaults.items():
            self.configure_endpoint(sid, url)

    def configure_endpoint(self, service_id: str, endpoint_url: str):
        """Register or update a service's monitored health check endpoint."""
        self._validate_url(endpoint_url)
        self._monitored_services[service_id] = endpoint_url
        if service_id not in self._health_state:
            self._health_state[service_id] = ServiceHealthRecord(
                service_id=service_id,
                endpoint_url=endpoint_url,
                status="healthy",
                last_check_time=datetime.now(timezone.utc).isoformat(),
            )
        else:
            self._health_state[service_id].endpoint_url = endpoint_url

    def _validate_url(self, url: str):
        """Validate URL to prevent SSRF and unsafe requests."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")
        host = (parsed.hostname or "").lower()
        if host in BLOCKED_HOSTS:
            raise ValueError(f"Target host '{host}' is blocked for security purposes.")

    def set_fault(self, req: FaultSimulationRequest) -> ServiceHealthRecord:
        """Inject or clear a deterministic simulated operational fault."""
        if req.fault_type == "clear":
            self._active_faults.pop(req.service_id, None)
            record = self._health_state.get(req.service_id)
            if record:
                record.is_simulated_fault = False
                record.fault_type = None
                record.consecutive_failures = 0
                record.status = "healthy"
                record.alert_active = False
                record.error_message = None
            return record or ServiceHealthRecord(
                service_id=req.service_id,
                endpoint_url=self._monitored_services.get(req.service_id, ""),
            )

        # Apply fault
        self._active_faults[req.service_id] = {
            "fault_type": req.fault_type,
            "consecutive_failures": req.consecutive_failures,
            "latency_ms": req.latency_ms,
        }

        # Update monitored state immediately
        record = self._health_state.get(req.service_id)
        if not record:
            record = ServiceHealthRecord(
                service_id=req.service_id,
                endpoint_url=self._monitored_services.get(req.service_id, ""),
            )
            self._health_state[req.service_id] = record

        record.is_simulated_fault = True
        record.fault_type = req.fault_type
        record.last_check_time = datetime.now(timezone.utc).isoformat()

        if req.fault_type == "timeout":
            record.status = "unhealthy"
            record.http_status = 504
            record.response_time_ms = self.timeout_sec * 1000.0
            record.consecutive_failures = req.consecutive_failures
            record.error_message = f"Simulated connection timeout after {self.timeout_sec}s."
            record.alert_active = True
        elif req.fault_type == "elevated_latency":
            record.status = "degraded"
            record.http_status = 200
            record.response_time_ms = req.latency_ms
            record.consecutive_failures = 1
            record.error_message = f"Elevated latency observed ({req.latency_ms}ms > baseline)."
        elif req.fault_type == "consecutive_failure":
            record.status = "unhealthy"
            record.http_status = 500
            record.consecutive_failures = req.consecutive_failures
            record.error_message = f"Repeated connection failures ({req.consecutive_failures} consecutive errors)."
            record.alert_active = True

        # Trigger automatic incident in Knowledge Graph if threshold reached
        if record.consecutive_failures >= self.failure_threshold and not record.active_incident_id:
            repo = get_repository()
            inc = repo.add_incident(
                service_id=req.service_id,
                description=f"Automated health monitor alert: {record.error_message}",
                decision_data={"trigger": "health_threshold", "failures": record.consecutive_failures},
            )
            record.active_incident_id = inc.id

        return record

    async def check_service(self, service_id: str) -> ServiceHealthRecord:
        """Execute a single health check cycle for a given service."""
        # 1. Check if simulated fault is active
        if service_id in self._active_faults:
            fault_def = self._active_faults[service_id]
            req = FaultSimulationRequest(service_id=service_id, **fault_def)
            return self.set_fault(req)

        endpoint_url = self._monitored_services.get(service_id)
        if not endpoint_url:
            return ServiceHealthRecord(
                service_id=service_id,
                endpoint_url="",
                status="unreachable",
                error_message="No endpoint configured.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        record = self._health_state.get(service_id)
        if not record:
            record = ServiceHealthRecord(service_id=service_id, endpoint_url=endpoint_url)
            self._health_state[service_id] = record

        record.last_check_time = now_iso
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(endpoint_url)
                latency = round((time.perf_counter() - start_time) * 1000.0, 2)

                record.response_time_ms = latency
                record.http_status = resp.status_code

                if resp.status_code == 200:
                    # Success recovery
                    record.status = "healthy"
                    record.consecutive_failures = 0
                    record.error_message = None
                    record.alert_active = False
                    record.is_simulated_fault = False
                elif resp.status_code < 500:
                    record.status = "degraded"
                    record.consecutive_failures += 1
                    record.error_message = f"HTTP {resp.status_code} client error."
                else:
                    record.status = "unhealthy"
                    record.consecutive_failures += 1
                    record.error_message = f"HTTP {resp.status_code} internal server error."

        except httpx.TimeoutException:
            record.status = "unhealthy"
            record.consecutive_failures += 1
            record.response_time_ms = self.timeout_sec * 1000.0
            record.error_message = f"Request timed out after {self.timeout_sec}s."
        except Exception as e:
            record.status = "unreachable"
            record.consecutive_failures += 1
            record.error_message = str(e)

        # Trigger automatic incident in Knowledge Graph if threshold reached
        if record.consecutive_failures >= self.failure_threshold and not record.alert_active:
            record.alert_active = True
            repo = get_repository()
            inc = repo.add_incident(
                service_id=service_id,
                description=f"Automated health monitor alert: {record.error_message}",
                decision_data={"trigger": "consecutive_failure_threshold", "failures": record.consecutive_failures},
            )
            record.active_incident_id = inc.id

        return record

    async def check_all_services(self) -> list[ServiceHealthRecord]:
        """Perform health checks across all registered services."""
        tasks = [self.check_service(sid) for sid in list(self._monitored_services.keys())]
        return await asyncio.gather(*tasks)

    def get_all_health_states(self) -> list[ServiceHealthRecord]:
        """Return the current cached health records for all services."""
        return list(self._health_state.values())


# Global singleton instance
_checker_instance: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = HealthChecker()
    return _checker_instance
