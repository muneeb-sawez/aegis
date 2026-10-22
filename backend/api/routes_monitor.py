import asyncio
from datetime import datetime, timezone
import json
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
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


@router.get("/events")
async def monitor_events_sse(request: Request, max_events: Optional[int] = None):
    """Server-Sent Events (SSE) stream emitting {type: 'probe'|'anomaly'|'recovered', ts, payload}."""
    checker = get_health_checker()
    queue = checker.subscribe_events()

    async def event_generator():
        emitted_count = 0
        try:
            # Emit initial probe events for all currently known services
            for rec in checker.get_all_health_states():
                init_event = {
                    "type": "probe",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "service_id": rec.service_id,
                        "status": rec.status,
                        "http_status": rec.http_status,
                        "latency_ms": rec.response_time_ms,
                        "baseline_latency_ms": rec.baseline_latency_ms,
                        "consecutive_failures": rec.consecutive_failures,
                        "error_rate": rec.error_rate,
                        "ok": rec.status == "healthy",
                        "rolling_latencies": rec.rolling_latencies,
                    },
                }
                yield f"data: {json.dumps(init_event)}\n\n"
                await asyncio.sleep(0)
                emitted_count += 1
                if max_events is not None and emitted_count >= max_events:
                    return

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    await asyncio.sleep(0)
                    emitted_count += 1
                    if max_events is not None and emitted_count >= max_events:
                        return
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    await asyncio.sleep(0)
        finally:
            checker.unsubscribe_events(queue)


    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.post("/unconfigure")
def unconfigure_service_endpoint(service_id: str) -> dict[str, Any]:
    """Remove a service's monitored endpoint, reverting it to unconfigured."""
    checker = get_health_checker()
    checker.unconfigure_endpoint(service_id)
    return {"status": "ok", "service_id": service_id, "endpoint_url": None}


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

