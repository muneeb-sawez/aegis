"""AEGIS Executor — Action Allowlist (backend/executor/allowlist.py).

SAFETY RESPONSIBILITY: This is the first gate every proposed fix passes through.
If a proposed action is not explicitly on the allowlist, it is REFUSED here and
never reaches the actuator. All refusals are logged to audit.

Non-negotiable rules (AGENTS.md §4):
  - Only 3 actions are allowlisted: restart, scale_pool, rollback.
  - Parameter validators are applied BEFORE any execution.
  - Anything outside the allowlist raises AllowlistViolation and is logged.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Load config (single source of truth) ─────────────────────────────────────
_CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "executor_config.json"


def _load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return json.load(f)


_CFG = _load_config()
_ALLOWED_ACTIONS: frozenset[str] = frozenset(_CFG["allowlist"]["actions"])
_SCALE_POOL_MIN: int = _CFG["allowlist"]["scale_pool_min"]
_SCALE_POOL_MAX: int = _CFG["allowlist"]["scale_pool_max"]


# ── Custom exception ──────────────────────────────────────────────────────────
class AllowlistViolation(ValueError):
    """Raised when a proposed action is not on the allowlist or has invalid params."""


# ── Validated proposal schema ─────────────────────────────────────────────────
class ValidatedProposal(BaseModel):
    """A fully-validated, allowlisted action proposal ready for scoring.

    Fields exactly mirror RankedFix from backend/agent/schemas.py but with
    additional parameter constraints enforced at model construction time.
    """

    action: str = Field(
        ...,
        description="Must be one of: restart, scale_pool, rollback.",
    )
    target: str = Field(
        ...,
        min_length=1,
        description="Target node/service ID — must not be empty.",
    )
    reason: str = Field(
        default="",
        description="Rationale from RCA agent.",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters (e.g. pool_size for scale_pool).",
    )
    fault_type: str = Field(
        default="unknown",
        description="Fault type from RCAResult, used to look up recovery score.",
    )

    # ── SAFETY CHECK 1: action must be on the allowlist ───────────────────────
    @field_validator("action")
    @classmethod
    def action_must_be_allowlisted(cls, v: str) -> str:
        """SAFETY CHECK 1 — reject any action not in the frozen allowlist."""
        if v not in _ALLOWED_ACTIONS:
            # Log refusal BEFORE raising so the record is always written.
            logger.warning(
                "ALLOWLIST_REFUSED action=%r not in allowlist=%s",
                v,
                sorted(_ALLOWED_ACTIONS),
            )
            raise AllowlistViolation(
                f"Action '{v}' is not allowlisted. "
                f"Allowed actions: {sorted(_ALLOWED_ACTIONS)}. "
                "Refusing to proceed."
            )
        return v

    # ── SAFETY CHECK 2: target must be non-empty ──────────────────────────────
    @field_validator("target")
    @classmethod
    def target_must_not_be_empty(cls, v: str) -> str:
        """SAFETY CHECK 2 — a blank target would affect an unknown service."""
        if not v.strip():
            raise AllowlistViolation("target must not be empty or whitespace.")
        return v.strip()

    # ── SAFETY CHECK 3: action-specific parameter validation ──────────────────
    @model_validator(mode="after")
    def validate_action_params(self) -> "ValidatedProposal":
        """SAFETY CHECK 3 — per-action parameter constraints."""
        if self.action == "scale_pool":
            # SAFETY CHECK 3a: pool_size must be present and in [1..100]
            if "pool_size" not in self.params:
                raise AllowlistViolation(
                    "scale_pool requires 'pool_size' in params."
                )
            pool_size = self.params["pool_size"]
            if not isinstance(pool_size, int):
                raise AllowlistViolation(
                    f"scale_pool 'pool_size' must be an integer, got {type(pool_size).__name__}."
                )
            if not (_SCALE_POOL_MIN <= pool_size <= _SCALE_POOL_MAX):
                raise AllowlistViolation(
                    f"scale_pool 'pool_size'={pool_size} out of bounds "
                    f"[{_SCALE_POOL_MIN}..{_SCALE_POOL_MAX}]."
                )

        elif self.action == "restart":
            # SAFETY CHECK 3b: restart requires no dangerous extra params
            # (grace_period_sec is allowed and optional, anything else is suspicious)
            allowed_restart_keys = {"grace_period_sec"}
            extra = set(self.params.keys()) - allowed_restart_keys
            if extra:
                raise AllowlistViolation(
                    f"restart received unexpected params: {extra}. "
                    "Only 'grace_period_sec' is allowed."
                )

        elif self.action == "rollback":
            # SAFETY CHECK 3c: rollback must specify a target_version or revision
            if not self.params.get("target_version") and not self.params.get("revision"):
                raise AllowlistViolation(
                    "rollback requires 'target_version' or 'revision' in params."
                )

        return self


# ── Public API ────────────────────────────────────────────────────────────────

def validate_proposal(
    action: str,
    target: str,
    params: dict[str, Any] | None = None,
    reason: str = "",
    fault_type: str = "unknown",
) -> ValidatedProposal:
    """Validate a proposed remediation action against the allowlist.

    SAFETY GATE: Every fix must pass through this function before scoring
    or execution. On failure, AllowlistViolation is raised; callers must
    catch it, log the refusal to audit, and halt the pipeline.

    Args:
        action: Proposed action string (must be in allowlist).
        target: Service/node ID to act upon.
        params: Action-specific parameters dict.
        reason: Human-readable rationale from RCA agent.
        fault_type: Fault type for recovery score lookup.

    Returns:
        ValidatedProposal if all checks pass.

    Raises:
        AllowlistViolation: If action is not allowlisted or params are invalid.
    """
    try:
        proposal = ValidatedProposal(
            action=action,
            target=target,
            params=params or {},
            reason=reason,
            fault_type=fault_type,
        )
        logger.info(
            "ALLOWLIST_PASSED action=%r target=%r",
            proposal.action,
            proposal.target,
        )
        return proposal
    except AllowlistViolation:
        # Re-raise as-is — caller must audit the refusal.
        raise
    except Exception as exc:
        # Wrap any unexpected Pydantic validation error in AllowlistViolation
        # so callers only need to handle one exception type.
        raise AllowlistViolation(f"Proposal validation failed: {exc}") from exc
