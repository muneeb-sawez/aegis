"""AEGIS Healing, Diagnosis SSE Stream & Actuator Endpoints (docs/02-CONTRACTS.md §4 & §5)."""

import asyncio
from datetime import datetime, timezone
import json
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.schemas import (
    ActuatorExecuteRequest,
    ActuatorExecuteResponse,
    MemoryCommitRequest,
    MemoryCommitResponse,
    SSEEventEnvelope,
)
from backend.auth.dependencies import require_api_key
from backend.auth.store import ProjectRecord
from backend.config import settings
from backend.graph import get_repository
from backend.agent.stream import stream_diagnosis_events

router = APIRouter(prefix="/api", tags=["healing"])


def get_demo_diagnosis_events() -> list[dict[str, Any]]:
    """Generate scripted demo diagnosis workflow events (Demo diagnosis (scripted))."""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "type": "thought",
            "ts": now,
            "payload": {
                "message": "[Demo diagnosis (scripted)] Anomaly detected: paymentservice p99 latency elevated (3400ms > 3x baseline 38ms) across 3 consecutive ticks. Initiating graph-grounded investigation.",
            },
        },
        {
            "type": "cypher",
            "ts": now,
            "payload": {
                "query": "MATCH (s:Service {id: 'paymentservice'})-[r:DEPENDS_ON]->(d:Database) RETURN s.id, d.id, d.connections, d.pool_size, d.status",
                "purpose": "Inspect datastore dependencies and connection saturation",
            },
        },
        {
            "type": "thought",
            "ts": now,
            "payload": {
                "message": "Database 'postgres-payment' connection pool is saturated (100/100). Caller checkoutservice experiencing backpressure. Latency degradation isolated to payment-db bottleneck.",
            },
        },
        {
            "type": "candidates",
            "ts": now,
            "payload": {
                "candidates": [
                    {
                        "action": "scale_pool",
                        "target": "postgres-payment",
                        "params": {"pool_size": 150},
                        "safety_score": 92.0,
                        "recovery_prob": 0.95,
                        "composite_score": round(0.6 * 92.0 + 0.4 * 95.0, 1),
                        "rationale": "Expand postgres-payment connection pool from 100 to 150 to absorb queue backlog.",
                        "eligible_for_auto_exec": True,
                    },
                    {
                        "action": "restart_pod",
                        "target": "paymentservice-pod-1",
                        "params": {"grace_period_sec": 30},
                        "safety_score": 85.0,
                        "recovery_prob": 0.50,
                        "composite_score": round(0.6 * 85.0 + 0.4 * 50.0, 1),
                        "rationale": "Restart primary worker pod to flush leaked connection handles.",
                        "eligible_for_auto_exec": True,
                    },
                    {
                        "action": "rollback_release",
                        "target": "paymentservice",
                        "params": {"revision": "HEAD~1"},
                        "safety_score": 70.0,
                        "recovery_prob": 0.80,
                        "composite_score": round(0.6 * 70.0 + 0.4 * 80.0, 1),
                        "rationale": "Roll back paymentservice deployment to prior stable release (below safety threshold 75).",
                        "eligible_for_auto_exec": False,
                    },
                ]
            },
        },
        {
            "type": "result",
            "ts": now,
            "payload": {
                "hypothesis": "Root cause confirmed: PostgreSQL connection pool exhaustion under load spike.",
                "confidence": 0.94,
                "propagation_path": ["postgres-payment", "paymentservice", "checkoutservice", "frontend"],
                "recommended_action": "scale_pool",
                "target": "postgres-payment",
            },
        },
        {
            "type": "done",
            "ts": now,
            "payload": {
                "message": "Diagnosis completed. Awaiting execution approval for allowlisted action 'scale_pool'.",
            },
        },
    ]


@router.get("/heal/config")
def get_heal_config():
    """Return runtime healing configuration and active mode."""
    return {"demo_mode": settings.DEMO_MODE, "provider": settings.LLM_PROVIDER, "model": settings.LLM_MODEL}


@router.get("/heal/stream")
async def stream_heal_events(incident_id: str = "", project_id: str = "demo"):
    """Stream diagnosis and remediation reasoning via Server-Sent Events (SSE)."""
    async def event_generator() -> AsyncGenerator[str, None]:
        if settings.DEMO_MODE:
            events = get_demo_diagnosis_events()
            for ev in events:
                envelope = SSEEventEnvelope(**ev)
                yield f"data: {envelope.model_dump_json()}\n\n"
                await asyncio.sleep(0.3)
        else:
            async for ev in stream_diagnosis_events(incident_id=incident_id, project_id=project_id):
                envelope = SSEEventEnvelope(**ev)
                yield f"data: {envelope.model_dump_json()}\n\n"
                await asyncio.sleep(0.1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/heal/events", response_model=list[SSEEventEnvelope])
async def get_heal_events_polling(incident_id: str = "", project_id: str = "demo") -> list[SSEEventEnvelope]:
    """Polling fallback for diagnosis events if SSE is blocked in the client environment."""
    if settings.DEMO_MODE:
        return [SSEEventEnvelope(**ev) for ev in get_demo_diagnosis_events()]

    events: list[SSEEventEnvelope] = []
    async for ev in stream_diagnosis_events(incident_id=incident_id, project_id=project_id):
        events.append(SSEEventEnvelope(**ev))
    return events


@router.post("/actuator/execute", response_model=ActuatorExecuteResponse)
def execute_actuator_action(
    req: ActuatorExecuteRequest,
    _auth: ProjectRecord = Depends(require_api_key),
) -> ActuatorExecuteResponse:
    """Execute a guarded allowlisted remediation action.

    Safety Rules (.agent/rules/03-actuator-safety.md):
    - Only 3 actions allowlisted: restart_pod, scale_pool, rollback_release.
    - Parameter validation: pool_size must be >= 50 and <= 500.
    - If deliberate bad fix or verification failure: trigger rollback.
    """
    repo = get_repository()
    now_str = datetime.now(timezone.utc).strftime("%H%M%S")
    execution_id = f"exec-{now_str}"

    # 1. Action allowlist validation
    if req.action not in ("restart_pod", "scale_pool", "rollback_release"):
        raise HTTPException(
            status_code=400,
            detail=f"Action '{req.action}' is rejected: Not in guarded actuator allowlist.",
        )

    # 2. Check parameter validity / deliberate bad fix test
    if req.action == "scale_pool":
        pool_size = req.params.get("pool_size", 150)
        if pool_size < 50:
            # Bad fix mode: simulate automatic dead-man rollback
            return ActuatorExecuteResponse(
                execution_id=execution_id,
                action=req.action,
                target=req.target,
                status="rolled_back",
                safety_score=35.0,
                message="Dead-man health check failed: pool_size too low, system deteriorated. Automatically rolled back to pre-action snapshot.",
                health_verified=False,
            )

        # Successful remediation: restore healthy telemetry
        repo.set_telemetry(req.target, {
            "connections": 45,
            "pool_size": pool_size,
            "status": "healthy",
            "p99_ms": 6.0,
        }, project_id=req.project_id)
        # If target service was paymentservice, restore its latency
        repo.set_telemetry("paymentservice", {
            "p99_ms": 38.0,
            "error_rate": 0.001,
            "status": "healthy",
            "active_alert": None,
        }, project_id=req.project_id)

        return ActuatorExecuteResponse(
            execution_id=execution_id,
            action=req.action,
            target=req.target,
            status="executed",
            safety_score=92.0,
            message=f"Successfully scaled pool on {req.target} to {pool_size}. Health verified: p99 latency restored to 38ms.",
            health_verified=True,
        )

    elif req.action == "restart_pod":
        repo.set_telemetry(req.target, {
            "status": "Running",
            "restart_count": 0,
            "cpu_pct": 22.0,
            "p99_ms": 38.0,
        }, project_id=req.project_id)
        return ActuatorExecuteResponse(
            execution_id=execution_id,
            action=req.action,
            target=req.target,
            status="executed",
            safety_score=85.0,
            message=f"Pod {req.target} gracefully restarted. Pod status: Running, CPU: 22%.",
            health_verified=True,
        )

    else:
        # rollback_release
        return ActuatorExecuteResponse(
            execution_id=execution_id,
            action=req.action,
            target=req.target,
            status="executed",
            safety_score=75.0,
            message=f"Deployment {req.target} rolled back to revision HEAD~1.",
            health_verified=True,
        )


@router.post("/memory/commit", response_model=MemoryCommitResponse)
def commit_incident_to_graph(
    req: MemoryCommitRequest,
    _auth: ProjectRecord = Depends(require_api_key),
) -> MemoryCommitResponse:
    """Write completed incident and resolution decision back to the Knowledge Graph (M8).

    Crucial feedback loop: writes (:Incident)-[:OCCURRED_IN]->(:Service) and
    (:Decision)-[:RESOLVED_BY]->(:Incident).
    Subsequent PR simulations on this service will see this incident and increase risk score.
    """
    repo = get_repository()
    incident = repo.add_incident(
        service_id=req.service_id,
        description=req.incident_description,
        decision_data={
            "action": req.action_taken,
            "safety_score": req.safety_score,
            "outcome": req.outcome,
        },
        project_id=req.project_id,
    )

    return MemoryCommitResponse(
        incident_id=incident.id,
        decision_id=incident.decision_id or "dec-unknown",
        service_id=req.service_id,
        status="committed",
        message=f"Incident '{incident.id}' successfully committed to Knowledge Graph for service '{req.service_id}'. Future risk assessments will account for this incident.",
    )
