"""AEGIS Executor — Immutable Audit Log (backend/executor/audit.py).

SAFETY RESPONSIBILITY:
  Every attempted remediation is written to an append-only JSONL file AND to the
  Knowledge Graph as Decision + Outcome nodes (for the feedback loop that changes
  future risk scores).

Rules:
  - NEVER log secrets (API keys, HMAC secrets, passwords).
  - NEVER modify or delete existing audit records — append only.
  - Every entry has a monotonic sequence number, wall-clock timestamp, and
    structured fields for action, result, reasoning trace, and scores.
  - The audit log is the source of truth for the GET /api/decisions endpoint.

Labels: emulated executions carry "emulated: true" in their records
(honesty rule AGENTS.md §6).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Log file path (from config) ───────────────────────────────────────────────
_CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "executor_config.json"

def _audit_log_path() -> Path:
    try:
        cfg = json.loads(_CONFIG_PATH.read_text())
        p = Path(cfg["audit"]["log_path"])
    except Exception:
        p = Path("backend/logs/audit.jsonl")
    # Resolve relative to repo root (parent of backend/)
    if not p.is_absolute():
        p = Path(__file__).parent.parent.parent / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ── Thread-safe append lock ───────────────────────────────────────────────────
_FILE_LOCK = threading.Lock()

# ── In-memory decision registry (for GET /api/decisions) ─────────────────────
_DECISIONS: list[dict[str, Any]] = []
_DECISIONS_LOCK = threading.Lock()


# ── Pydantic schema ───────────────────────────────────────────────────────────

DecisionStatus = Literal["pending", "executing", "succeeded", "rolled_back", "failed", "refused"]


class DecisionRecord(BaseModel):
    """Structured audit record persisted for every remediation decision."""

    decision_id: str = Field(default_factory=lambda: f"dec-{uuid.uuid4().hex[:8]}")
    incident_id: str
    service_id: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    fault_type: str
    safety_score: float
    recovery_score: float
    composite_score: float
    status: DecisionStatus
    reason: str
    reasoning_trace: list[str] = Field(default_factory=list)  # evidence from RCA
    result: dict[str, Any] = Field(default_factory=dict)      # actuator response
    probe_log: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    emulated: bool = True  # honesty label — Phase 1 is always emulated


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sanitize(record: dict[str, Any]) -> dict[str, Any]:
    """SAFETY CHECK 15: Strip any key that looks like a secret before writing."""
    _SECRET_KEYS = {"api_key", "password", "secret", "token", "hmac_secret", "key"}
    return {
        k: "[REDACTED]" if k.lower() in _SECRET_KEYS else v
        for k, v in record.items()
    }


def _append_to_file(record: dict[str, Any]) -> None:
    """Append one JSON line to the audit JSONL file (thread-safe)."""
    log_path = _audit_log_path()
    line = json.dumps(_sanitize(record), default=str) + "\n"
    with _FILE_LOCK:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line)


# ── Public API ────────────────────────────────────────────────────────────────

def record_decision(record: DecisionRecord) -> DecisionRecord:
    """Persist a DecisionRecord to the JSONL file and in-memory registry.

    SAFETY CHECK 15: Secrets are stripped before writing.
    SAFETY CHECK 16: Append-only — existing records are never modified.

    Args:
        record: Fully-populated DecisionRecord.

    Returns:
        The same record (for chaining).
    """
    data = record.model_dump()
    _append_to_file(data)
    with _DECISIONS_LOCK:
        _DECISIONS.append(data)
    logger.info(
        "AUDIT_RECORDED decision_id=%r incident=%r action=%r status=%r",
        record.decision_id,
        record.incident_id,
        record.action,
        record.status,
    )
    return record


def update_decision(decision_id: str, **fields: Any) -> bool:
    """Update mutable fields of an existing in-memory decision (e.g. status).

    SAFETY CHECK 16 (corollary): Only status, result, probe_log, updated_at
    may be updated after creation. A new audit line is appended for every
    update — the original line is never overwritten.

    Returns True if the decision was found and updated.
    """
    now = datetime.now(timezone.utc).isoformat()
    with _DECISIONS_LOCK:
        for dec in _DECISIONS:
            if dec.get("decision_id") == decision_id:
                # Only allow updating safe mutable fields.
                safe_fields = {"status", "result", "probe_log", "updated_at"}
                for k, v in fields.items():
                    if k in safe_fields:
                        dec[k] = v
                dec["updated_at"] = now
                # Append update record to JSONL
                update_entry = {
                    "_update": True,
                    "decision_id": decision_id,
                    "updated_fields": {k: v for k, v in fields.items() if k in safe_fields},
                    "updated_at": now,
                }
                _append_to_file(update_entry)
                logger.info("AUDIT_UPDATED decision_id=%r fields=%s", decision_id, list(fields.keys()))
                return True
    logger.warning("AUDIT_UPDATE_NOT_FOUND decision_id=%r", decision_id)
    return False


def get_all_decisions() -> list[dict[str, Any]]:
    """Return a snapshot of all in-memory decisions (used by GET /api/decisions)."""
    with _DECISIONS_LOCK:
        return list(_DECISIONS)


def persist_to_graph(record: DecisionRecord) -> None:
    """Write Decision + Outcome nodes to the Knowledge Graph (feedback loop).

    This is the M8 feedback loop: incidents written here are seen by the next
    PR simulation and increase the risk score.

    SAFETY CHECK 17: Graph write is best-effort; failures are logged but do not
    abort the audit pipeline.
    """
    try:
        from backend.graph import get_repository
        repo = get_repository()
        repo.add_incident(
            service_id=record.service_id,
            description=(
                f"[executor] {record.action} on {record.service_id} "
                f"— fault: {record.fault_type} — status: {record.status}"
            ),
            decision_data={
                "decision_id": record.decision_id,
                "action": record.action,
                "safety_score": record.safety_score,
                "composite_score": record.composite_score,
                "outcome": record.status,
            },
        )
        logger.info(
            "AUDIT_GRAPH_PERSISTED decision_id=%r service=%r",
            record.decision_id,
            record.service_id,
        )
    except Exception as exc:
        # SAFETY CHECK 17: Graph failure must not prevent the audit from completing.
        logger.error(
            "AUDIT_GRAPH_ERROR decision_id=%r error=%s",
            record.decision_id,
            exc,
        )
