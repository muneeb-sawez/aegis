"""AEGIS Executor — Execution Orchestrator (backend/executor/orchestrator.py).

Coordinates the full remediation pipeline in the correct order:
  1. Validate against allowlist (gate 1)
  2. Score for safety (gate 2)
  3. Snapshot pre-fix state
  4. Based on EXECUTION_MODE:
       approve → create pending Decision, return immediately.
       auto    → proceed to step 5.
  5. Apply fix via actuator
  6. Health-check within verification window
  7. If unhealthy → rollback; if healthy → succeed
  8. Persist audit record and update graph

EXECUTION_MODE env var:
  approve (default) — Decision is created in 'pending' state; POST /api/actuator/approve
                      must be called to execute it.
  auto              — Skip approval; execute immediately (only when env says so).

SAFETY CHECKS summary (see individual modules for details):
  1  allowlist gate        (allowlist.py)
  2  allowlist gate        (allowlist.py)
  3  allowlist gate        (allowlist.py)
  4  scoring table missing (scoring.py)
  5  safety threshold 75   (scoring.py)
  6  per-service lock      (actuator.py)
  7  HMAC signature        (actuator.py)
  8  pre-fix snapshot      (actuator.py)
  9  signature in emulation(actuator.py)
 10  network failure       (actuator.py)
 11  fail-closed probe     (health.py)
 12  deadline enforced     (health.py)
 13  rollback error struct (rollback.py)
 14  snapshot validation   (rollback.py)
 15  secret scrubbing      (audit.py)
 16  append-only audit     (audit.py)
 17  graph-write best-effort(audit.py)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from backend.executor.allowlist import validate_proposal, AllowlistViolation
from backend.executor.scoring import compute_score
from backend.executor.actuator import take_snapshot, apply_fix
from backend.executor.health import check_health, VERIFICATION_WINDOW_SEC
from backend.executor.rollback import rollback
from backend.executor.audit import DecisionRecord, record_decision, update_decision, persist_to_graph

logger = logging.getLogger(__name__)


def _execution_mode() -> str:
    """Read EXECUTION_MODE env var. Defaults to 'approve' (safe default)."""
    mode = os.environ.get("EXECUTION_MODE", "approve").lower()
    # SAFETY CHECK 18: Reject unknown modes; fall back to 'approve'.
    if mode not in ("approve", "auto"):
        logger.warning(
            "EXECUTION_MODE=%r unknown; defaulting to 'approve' for safety.", mode
        )
        mode = "approve"
    return mode


async def run_remediation(
    incident_id: str,
    service_id: str,
    action: str,
    params: dict[str, Any],
    fault_type: str,
    reason: str,
    reasoning_trace: list[str],
    baseline_latency_ms: float = 100.0,
    *,
    override_mode: str | None = None,
) -> DecisionRecord:
    """Run the full guarded remediation pipeline.

    This is the single entry point the API routes call.

    Args:
        incident_id: Incident that triggered this remediation.
        service_id: Target node ID.
        action: Proposed action string.
        params: Action-specific parameters.
        fault_type: RCA fault classification.
        reason: Short rationale from RCA agent.
        reasoning_trace: Full chain of thought from RCA (for audit).
        baseline_latency_ms: Pre-incident latency baseline for health check.
        override_mode: If set, overrides EXECUTION_MODE env var (tests only).

    Returns:
        DecisionRecord with final status.
    """
    mode = override_mode if override_mode is not None else _execution_mode()

    # ── GATE 1 & 2 & 3: Allowlist validation ─────────────────────────────────
    try:
        proposal = validate_proposal(
            action=action,
            target=service_id,
            params=params,
            reason=reason,
            fault_type=fault_type,
        )
    except AllowlistViolation as exc:
        refused_record = DecisionRecord(
            incident_id=incident_id,
            service_id=service_id,
            action=action,
            params=params,
            fault_type=fault_type,
            safety_score=0.0,
            recovery_score=0.0,
            composite_score=0.0,
            status="refused",
            reason=str(exc),
            reasoning_trace=reasoning_trace,
        )
        record_decision(refused_record)
        logger.warning("ORCHESTRATOR_REFUSED incident=%r reason=%s", incident_id, exc)
        return refused_record

    # ── GATE 4 & 5: Safety scoring ────────────────────────────────────────────
    scoring = compute_score(action=proposal.action, fault_type=proposal.fault_type)
    if not scoring.eligible:
        refused_record = DecisionRecord(
            incident_id=incident_id,
            service_id=service_id,
            action=action,
            params=params,
            fault_type=fault_type,
            safety_score=scoring.safety_score,
            recovery_score=scoring.recovery_score,
            composite_score=scoring.composite_score,
            status="refused",
            reason=scoring.refusal_reason,
            reasoning_trace=reasoning_trace,
        )
        record_decision(refused_record)
        logger.warning("ORCHESTRATOR_SCORE_REFUSED incident=%r reason=%s", incident_id, scoring.refusal_reason)
        return refused_record

    # ── Create Decision record ────────────────────────────────────────────────
    status: str = "pending" if mode == "approve" else "executing"
    dec = DecisionRecord(
        incident_id=incident_id,
        service_id=service_id,
        action=proposal.action,
        params=proposal.params,
        fault_type=proposal.fault_type,
        safety_score=scoring.safety_score,
        recovery_score=scoring.recovery_score,
        composite_score=scoring.composite_score,
        status=status,  # type: ignore[arg-type]
        reason=reason,
        reasoning_trace=reasoning_trace,
    )
    record_decision(dec)

    if mode == "approve":
        logger.info(
            "ORCHESTRATOR_PENDING decision_id=%r — waiting for human approval.",
            dec.decision_id,
        )
        return dec

    # ── mode == 'auto': Execute immediately ───────────────────────────────────
    return await _execute_decision(dec, baseline_latency_ms)


async def approve_and_execute(decision_id: str, baseline_latency_ms: float = 100.0) -> DecisionRecord | None:
    """Execute a pending Decision (called by POST /api/actuator/approve).

    Returns None if decision_id is not found or is not in 'pending' state.
    """
    from backend.executor.audit import get_all_decisions

    all_dec = get_all_decisions()
    match = next((d for d in all_dec if d.get("decision_id") == decision_id), None)
    if match is None or match.get("status") != "pending":
        logger.warning(
            "APPROVE_NOT_FOUND_OR_NOT_PENDING decision_id=%r status=%r",
            decision_id,
            match.get("status") if match else "missing",
        )
        return None

    dec = DecisionRecord(**match)
    update_decision(decision_id, status="executing")
    return await _execute_decision(dec, baseline_latency_ms)


async def _execute_decision(dec: DecisionRecord, baseline_latency_ms: float) -> DecisionRecord:
    """Internal: apply the fix, health-check, roll back if needed."""

    # ── SAFETY CHECK 8: Snapshot pre-fix state ────────────────────────────────
    snapshot = take_snapshot(
        service_id=dec.service_id,
        pool_size=dec.params.get("pool_size", 0),
        config_version=dec.params.get("config_version", "unknown"),
    )

    # ── Apply fix (GATES 6, 7, 9, 10) ────────────────────────────────────────
    fix_result = await apply_fix(
        service_id=dec.service_id,
        action=dec.action,
        params=dec.params,
        snapshot=snapshot,
    )

    # SAFETY CHECK 10a: If actuator returned 'rejected' or 'unreachable', fail.
    if fix_result.get("status") in ("rejected", "unreachable"):
        update_decision(dec.decision_id, status="failed", result=fix_result)
        persist_to_graph(dec)
        logger.error(
            "ORCHESTRATOR_FIX_FAILED decision_id=%r status=%r",
            dec.decision_id,
            fix_result.get("status"),
        )
        # Return updated record
        dec = DecisionRecord(**{**dec.model_dump(), "status": "failed", "result": fix_result})
        return dec

    # ── Health check (GATES 11, 12) ───────────────────────────────────────────
    is_healthy, probe_log = await check_health(
        service_id=dec.service_id,
        baseline_latency_ms=baseline_latency_ms,
        verification_window_sec=VERIFICATION_WINDOW_SEC,
    )

    if is_healthy:
        # ── Happy path: succeeded ─────────────────────────────────────────────
        update_decision(dec.decision_id, status="succeeded", result=fix_result, probe_log=probe_log)
        final = DecisionRecord(**{**dec.model_dump(), "status": "succeeded", "result": fix_result, "probe_log": probe_log})
        persist_to_graph(final)
        logger.info("ORCHESTRATOR_SUCCEEDED decision_id=%r", dec.decision_id)
        return final
    else:
        # ── Rollback path (GATES 13, 14) ─────────────────────────────────────
        rb_result = rollback(service_id=dec.service_id, snapshot=snapshot)
        update_decision(
            dec.decision_id,
            status="rolled_back",
            result={"fix_result": fix_result, "rollback_result": rb_result},
            probe_log=probe_log,
        )
        final = DecisionRecord(**{
            **dec.model_dump(),
            "status": "rolled_back",
            "result": {"fix_result": fix_result, "rollback_result": rb_result},
            "probe_log": probe_log,
        })
        persist_to_graph(final)
        logger.warning("ORCHESTRATOR_ROLLED_BACK decision_id=%r", dec.decision_id)
        return final
