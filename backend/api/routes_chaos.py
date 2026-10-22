"""AEGIS Chaos & Fault Injection Endpoints (docs/02-CONTRACTS.md §4)."""

from fastapi import APIRouter, Depends
from backend.api.schemas import InjectFaultRequest, InjectFaultResponse
from backend.auth.dependencies import require_api_key
from backend.auth.store import ProjectRecord
from backend.graph import get_repository

router = APIRouter(prefix="/api/chaos", tags=["chaos"])


@router.post("/inject", response_model=InjectFaultResponse)
def inject_fault(
    req: InjectFaultRequest,
    _auth: ProjectRecord = Depends(require_api_key),
) -> InjectFaultResponse:
    """Inject an emulated operational fault into the topology.

    Phase 1 faults: pool_exhaustion, pod_crash, cpu_saturation, latency_spike.
    Updates in-memory telemetry on the target service and its infrastructure.
    """
    repo = get_repository()
    target_svc = req.target_service or "paymentservice"

    altered_nodes: list[str] = []
    telemetry_applied: dict[str, dict] = {}

    if req.fault_id == "pool_exhaustion":
        # Payment service latency degrades; Postgres connection pool exhausts
        target_db = "postgres-payment" if target_svc == "paymentservice" else f"postgres-{target_svc}"

        svc_telemetry = {
            "p99_ms": 3400.0,
            "error_rate": 0.42,
            "status": "degraded",
            "active_alert": "DatabaseConnectionPoolExhausted",
        }
        db_telemetry = {
            "connections": 100,
            "pool_size": 100,
            "status": "exhausted",
            "p99_ms": 1250.0,
        }

        repo.set_telemetry(target_svc, svc_telemetry, project_id=req.project_id)
        repo.set_telemetry(target_db, db_telemetry, project_id=req.project_id)

        altered_nodes = [target_svc, target_db]
        telemetry_applied = {target_svc: svc_telemetry, target_db: db_telemetry}
        msg = f"Injected pool exhaustion on {target_svc} and {target_db}: connections=100/100, p99=3400ms, error_rate=42%."

    elif req.fault_id in ("pod_crash", "crash"):
        pod_target = f"{target_svc}-pod-1"
        pod_telemetry = {
            "status": "CrashLoopBackOff",
            "cpu_pct": 0.0,
            "restart_count": 5,
        }
        svc_telemetry = {
            "status": "degraded",
            "error_rate": 0.25,
            "p99_ms": 1800.0,
        }
        repo.set_telemetry(pod_target, pod_telemetry, project_id=req.project_id)
        repo.set_telemetry(target_svc, svc_telemetry, project_id=req.project_id)
        altered_nodes = [pod_target, target_svc]
        telemetry_applied = {pod_target: pod_telemetry, target_svc: svc_telemetry}
        msg = f"Injected pod crash on {pod_target}: status=CrashLoopBackOff."

    elif req.fault_id == "cpu_saturation":
        svc_telemetry = {
            "cpu_pct": 99.8,
            "p99_ms": 2800.0,
            "error_rate": 0.22,
            "status": "cpu_throttled",
            "active_alert": "CPUThrottlingHigh",
        }
        repo.set_telemetry(target_svc, svc_telemetry, project_id=req.project_id)
        altered_nodes = [target_svc]
        telemetry_applied = {target_svc: svc_telemetry}
        msg = f"Injected CPU saturation on {target_svc}: cpu=99.8%, p99=2800ms."

    elif req.fault_id == "timeout":
        svc_telemetry = {
            "p99_ms": 5000.0,
            "error_rate": 0.65,
            "status": "timeout",
            "active_alert": "DownstreamRPCTimeout",
        }
        repo.set_telemetry(target_svc, svc_telemetry, project_id=req.project_id)
        altered_nodes = [target_svc]
        telemetry_applied = {target_svc: svc_telemetry}
        msg = f"Injected downstream timeout on {target_svc}: p99=5000ms, error_rate=65%."

    else:
        # Default latency spike / slow
        svc_telemetry = {
            "p99_ms": 2200.0,
            "error_rate": 0.15,
            "status": "elevated_latency",
        }
        repo.set_telemetry(target_svc, svc_telemetry, project_id=req.project_id)
        altered_nodes = [target_svc]
        telemetry_applied = {target_svc: svc_telemetry}
        msg = f"Injected latency spike on {target_svc}: p99=2200ms."

    return InjectFaultResponse(
        fault_id=req.fault_id,
        target_service=target_svc,
        status="active",
        message=msg,
        altered_nodes=altered_nodes,
        applied_telemetry=telemetry_applied,
    )
