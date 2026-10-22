"""AEGIS Executor API Routes (backend/api/routes_actuator.py).

Routes:
  POST /api/actuator/execute  — Submit an RCA proposal for remediation.
  POST /api/actuator/approve  — Approve a pending Decision (approve mode only).
  GET  /api/decisions         — List all Decision records (audit log).

EXECUTION_MODE env var controls behaviour:
  approve (default) — Returns a pending Decision; requires /approve to run.
  auto              — Executes immediately without human approval.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["executor"])


# ── Request / Response schemas ────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    """Payload for POST /api/actuator/execute."""

    incident_id: str = Field(..., description="Incident that triggered this remediation.")
    service_id: str = Field(..., description="Target service/node ID.")
    action: str = Field(..., description="Proposed allowlisted action.")
    params: dict[str, Any] = Field(default_factory=dict)
    fault_type: str = Field(default="unknown")
    reason: str = Field(default="")
    reasoning_trace: list[str] = Field(default_factory=list)
    baseline_latency_ms: float = Field(default=100.0)


class ApproveRequest(BaseModel):
    """Payload for POST /api/actuator/approve."""

    decision_id: str
    baseline_latency_ms: float = Field(default=100.0)


class DecisionResponse(BaseModel):
    """Summary of a Decision record returned by the API."""

    decision_id: str
    incident_id: str
    service_id: str
    action: str
    params: dict[str, Any]
    fault_type: str
    safety_score: float
    recovery_score: float
    composite_score: float
    status: str
    reason: str
    created_at: str
    updated_at: str
    emulated: bool


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/actuator/execute", response_model=DecisionResponse)
async def execute_proposal(req: ExecuteRequest) -> DecisionResponse:
    """Submit an RCA-proposed fix for execution.

    Pipeline: allowlist → scoring → snapshot → (pending | auto-execute).
    Returns the Decision record with current status.
    """
    from backend.executor.orchestrator import run_remediation

    dec = await run_remediation(
        incident_id=req.incident_id,
        service_id=req.service_id,
        action=req.action,
        params=req.params,
        fault_type=req.fault_type,
        reason=req.reason,
        reasoning_trace=req.reasoning_trace,
        baseline_latency_ms=req.baseline_latency_ms,
    )
    return DecisionResponse(**dec.model_dump())


@router.post("/actuator/approve", response_model=DecisionResponse)
async def approve_decision(req: ApproveRequest) -> DecisionResponse:
    """Approve and execute a pending Decision.

    Only valid when EXECUTION_MODE=approve. Returns 404 if decision_id is not
    found or is not in 'pending' state.
    """
    from backend.executor.orchestrator import approve_and_execute

    dec = await approve_and_execute(
        decision_id=req.decision_id,
        baseline_latency_ms=req.baseline_latency_ms,
    )
    if dec is None:
        raise HTTPException(
            status_code=404,
            detail=f"Decision '{req.decision_id}' not found or not in 'pending' state.",
        )
    return DecisionResponse(**dec.model_dump())


@router.get("/decisions", response_model=list[DecisionResponse])
def list_decisions() -> list[DecisionResponse]:
    """Return all Decision records from the in-memory audit registry."""
    from backend.executor.audit import get_all_decisions

    records = get_all_decisions()
    return [DecisionResponse(**r) for r in records if _is_valid_decision(r)]


def _is_valid_decision(r: dict[str, Any]) -> bool:
    """Filter out update-only records (they have '_update: True')."""
    return not r.get("_update", False)
