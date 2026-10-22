"""AEGIS Feedback Writer (backend/feedback/writer.py) — M8 Learning Loop.

GOAL: After every terminal Decision, persist structured Outcome nodes to the
Knowledge Graph so future risk scores and recovery probabilities automatically
reflect real remediation history.

Graph relationships written:
  Incident -[:RESOLVED_BY]-> Decision -[:RESULTED_IN]-> Outcome
  Outcome  -[:OCCURRED_IN]-> Service

Rules:
  - Only writes Outcomes for terminal statuses: succeeded, rolled_back, failed, refused.
  - Best-effort: failures are logged but never abort the audit pipeline.
  - Labels emulated outcomes (Phase 1 honesty rule AGENTS.md §6).
  - Reads/writes through GraphRepository ONLY — no raw graph access.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Terminal statuses that deserve an Outcome node (pending/executing are not terminal)
TERMINAL_STATUSES = {"succeeded", "rolled_back", "failed", "refused"}


def write_outcome(
    decision_id: str,
    incident_id: str,
    service_id: str,
    fault_type: str,
    action: str,
    status: str,
    safety_score: float,
    composite_score: float,
    project_id: str = "demo",
    repo=None,
) -> dict[str, Any] | None:
    """Persist an Outcome node and RESULTED_IN edge to the Knowledge Graph.

    Called by audit.persist_to_graph() after every terminal decision.

    Args:
        decision_id: The executor Decision ID.
        incident_id: The triggering Incident ID.
        service_id: The service that was targeted.
        fault_type: RCA fault classification (pool_exhaustion, pod_crash, …).
        action: The action that was attempted (restart, scale_pool, rollback).
        status: Terminal decision status — must be in TERMINAL_STATUSES.
        safety_score: The computed safety score for this action.
        composite_score: The 0.6×Safety + 0.4×Recovery composite score.
        project_id: Project scope (default 'demo').
        repo: GraphRepository instance (defaults to get_repository()).

    Returns:
        The serialised Outcome dict, or None if the write failed or status is non-terminal.
    """
    # Only write for terminal statuses
    if status not in TERMINAL_STATUSES:
        logger.debug(
            "WRITER_SKIP_NON_TERMINAL decision_id=%r status=%r",
            decision_id,
            status,
        )
        return None

    try:
        if repo is None:
            from backend.graph import get_repository
            repo = get_repository()

        outcome = repo.add_outcome(
            decision_id=decision_id,
            incident_id=incident_id,
            service_id=service_id,
            fault_type=fault_type,
            action=action,
            status=status,
            safety_score=safety_score,
            composite_score=composite_score,
            project_id=project_id,
        )

        logger.info(
            "FEEDBACK_WRITTEN outcome_id=%r decision=%r fault=%r action=%r status=%r project=%r",
            outcome.id,
            decision_id,
            fault_type,
            action,
            status,
            project_id,
        )
        return outcome.model_dump()

    except Exception as exc:
        # Best-effort: never crash the audit pipeline
        logger.error(
            "FEEDBACK_WRITE_ERROR decision_id=%r error=%s",
            decision_id,
            exc,
        )
        return None


def compute_success_rate_table(
    fault_type: str,
    action: str,
    repo=None,
    min_samples: int = 3,
    days: int = 90,
    project_id: str = "demo",
) -> dict[str, Any]:
    """Compute empirical success rate for (fault_type, action) from past Outcomes.

    Returns a dict:
      {
        "rate": float,          # 0.0..1.0 — fraction of 'succeeded' outcomes
        "sample_count": int,    # total outcomes for this (fault_type, action)
        "reliable": bool,       # True when sample_count >= min_samples
      }

    If fewer than min_samples outcomes exist, reliable=False and the caller
    should fall back to the static lookup table in executor_config.json.
    """
    try:
        if repo is None:
            from backend.graph import get_repository
            repo = get_repository()

        outcomes = repo.get_outcomes(fault_type=fault_type, action=action, days=days, project_id=project_id)

        total = len(outcomes)

        if total == 0:
            return {"rate": 0.0, "sample_count": 0, "reliable": False}

        successes = sum(1 for o in outcomes if o.status == "succeeded")
        rate = successes / total

        reliable = total >= min_samples
        logger.debug(
            "SUCCESS_RATE fault=%r action=%r rate=%.2f samples=%d reliable=%s",
            fault_type,
            action,
            rate,
            total,
            reliable,
        )
        return {"rate": rate, "sample_count": total, "reliable": reliable}

    except Exception as exc:
        logger.error("SUCCESS_RATE_ERROR fault=%r action=%r error=%s", fault_type, action, exc)
        return {"rate": 0.0, "sample_count": 0, "reliable": False}
