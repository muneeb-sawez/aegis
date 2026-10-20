"""AEGIS Health Monitoring & Telemetry API Endpoints (Directive §3.C)."""

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.monitor.health_checker import (
    FaultSimulationRequest,
    HealthChecker,
    ServiceHealthRecord,
    get_health_checker,
)

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


class ConfigureEndpointRequest(BaseModel):
    service_id: str
    endpoint_url: str


@router.get("/status", response_model=list[ServiceHealthRecord])
def get_monitor_status() -> list[ServiceHealthRecord]:
    """Return current monitored health records across all services."""
    checker = get_health_checker()
    return checker.get_all_health_states()


@router.post("/check-now", response_model=list[ServiceHealthRecord])
async def trigger_health_check() -> list[ServiceHealthRecord]:
    """Trigger an immediate asynchronous health check cycle across all services."""
    checker = get_health_checker()
    return await checker.check_all_services()


@router.post("/fault", response_model=ServiceHealthRecord)
def simulate_fault(req: FaultSimulationRequest) -> ServiceHealthRecord:
    """Inject or clear a simulated fault (timeout, elevated latency, consecutive failure)."""
    checker = get_health_checker()
    return checker.set_fault(req)


@router.post("/configure")
def configure_service_endpoint(req: ConfigureEndpointRequest) -> dict[str, Any]:
    """Configure or update the monitored health endpoint for a service."""
    checker = get_health_checker()
    try:
        checker.configure_endpoint(req.service_id, req.endpoint_url)
        return {"status": "ok", "service_id": req.service_id, "endpoint_url": req.endpoint_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/probe/{service_id}")
def probe_service_endpoint(service_id: str) -> dict[str, Any]:
    """Target probe endpoint for individual service health inspection."""
    from datetime import datetime, timezone

    return {
        "service_id": service_id,
        "status": "ok",
        "app_health": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reachability": "connected",
    }

