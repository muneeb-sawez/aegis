"""AEGIS Executor — Safety & Recovery Scoring (backend/executor/scoring.py).

SAFETY RESPONSIBILITY: This is the second gate. Even if an action is on the
allowlist, it will be REFUSED here if Safety < 75 (from executor_config.json).

Formula (docs/04-ALGORITHMS.md, executor section):
  Safety   = 100 - (blast_risk + data_loss_risk + overhead_risk)   # per-action table
  Recovery = per-fault-type lookup                                  # from config
  Score    = 0.6 * Safety + 0.4 * Recovery

Execution is blocked when Safety < safety_threshold (default 75).
All weights and tables come from data/executor_config.json — no magic numbers here.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Load config ───────────────────────────────────────────────────────────────
_CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "executor_config.json"


def _load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return json.load(f)


_CFG = _load_config()
_SAFETY_TABLE: dict[str, dict[str, float]] = _CFG["safety_risk_table"]
_RECOVERY_TABLE: dict[str, float] = _CFG["recovery_table"]
_SCORE_CFG: dict[str, float] = _CFG["scoring"]

SAFETY_WEIGHT: float = _SCORE_CFG["safety_weight"]           # 0.6
RECOVERY_WEIGHT: float = _SCORE_CFG["recovery_weight"]       # 0.4
SAFETY_THRESHOLD: float = _SCORE_CFG["safety_threshold"]     # 75.0


# ── Result dataclass ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ScoringResult:
    """Immutable scoring breakdown for a proposed fix."""

    action: str
    fault_type: str
    blast_risk: float
    data_loss_risk: float
    overhead_risk: float
    safety_score: float        # 0..100
    recovery_score: float      # 0..100
    composite_score: float     # 0..100
    eligible: bool             # False if Safety < safety_threshold
    refusal_reason: str        # Non-empty only when eligible=False


# ── Public API ────────────────────────────────────────────────────────────────

def compute_score(action: str, fault_type: str) -> ScoringResult:
    """Compute safety, recovery, and composite scores for a proposed fix.

    SAFETY GATE (second): Returns ScoringResult.eligible=False and a
    refusal_reason when Safety < SAFETY_THRESHOLD. The caller must refuse
    to execute and record the refusal in audit before halting.

    Args:
        action: Allowlisted action string (already validated by allowlist.py).
        fault_type: Fault type from RCAResult for recovery score lookup.

    Returns:
        ScoringResult with all fields populated.
    """
    # ── Fetch per-action risk table ───────────────────────────────────────────
    # SAFETY CHECK 4: If action is somehow not in the table (shouldn't happen
    # after allowlist), refuse conservatively with maximum risk.
    risk_row = _SAFETY_TABLE.get(action)
    if risk_row is None:
        logger.error(
            "SCORING_MISSING_TABLE action=%r — no entry in safety_risk_table; refusing.",
            action,
        )
        return ScoringResult(
            action=action,
            fault_type=fault_type,
            blast_risk=100.0,
            data_loss_risk=100.0,
            overhead_risk=100.0,
            safety_score=0.0,
            recovery_score=0.0,
            composite_score=0.0,
            eligible=False,
            refusal_reason=f"Action '{action}' has no entry in safety_risk_table — refusing conservatively.",
        )

    blast_risk: float = float(risk_row["blast_risk"])
    data_loss_risk: float = float(risk_row["data_loss_risk"])
    overhead_risk: float = float(risk_row["overhead_risk"])

    # Safety = 100 - total risk. Clamped to [0, 100].
    total_risk = blast_risk + data_loss_risk + overhead_risk
    safety_score: float = max(0.0, min(100.0, 100.0 - total_risk))

    # ── SAFETY CHECK 5: Refuse if Safety < threshold ──────────────────────────
    refusal_reason = ""
    eligible = True
    if safety_score < SAFETY_THRESHOLD:
        refusal_reason = (
            f"Safety score {safety_score:.1f} is below threshold {SAFETY_THRESHOLD}. "
            f"Action '{action}' refused (blast={blast_risk}, data_loss={data_loss_risk}, overhead={overhead_risk})."
        )
        eligible = False
        logger.warning("SCORING_REFUSED %s", refusal_reason)

    # ── Recovery score lookup ─────────────────────────────────────────────────
    # Fallback to 'unknown' if fault_type not in table.
    recovery_score: float = float(
        _RECOVERY_TABLE.get(fault_type, _RECOVERY_TABLE.get("unknown", 50.0))
    )

    composite_score: float = SAFETY_WEIGHT * safety_score + RECOVERY_WEIGHT * recovery_score

    result = ScoringResult(
        action=action,
        fault_type=fault_type,
        blast_risk=blast_risk,
        data_loss_risk=data_loss_risk,
        overhead_risk=overhead_risk,
        safety_score=safety_score,
        recovery_score=recovery_score,
        composite_score=composite_score,
        eligible=eligible,
        refusal_reason=refusal_reason,
    )

    logger.info(
        "SCORING action=%r fault=%r safety=%.1f recovery=%.1f composite=%.1f eligible=%s",
        action,
        fault_type,
        safety_score,
        recovery_score,
        composite_score,
        eligible,
    )
    return result
