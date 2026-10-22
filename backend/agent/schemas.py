"""AEGIS Agent Schemas (Pydantic v2).

Defines the structured output contracts for graph-grounded root cause analysis (RCA)
and guarded fix action proposals.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

# Only 3 actions allowlisted for actuator proposal
AllowlistedAction = Literal["restart", "scale_pool", "rollback"]


class RankedFix(BaseModel):
    """Guarded fix action recommendation proposed by the diagnosis agent."""

    action: AllowlistedAction = Field(
        ...,
        description="Allowlisted remediation action: 'restart', 'scale_pool', or 'rollback'.",
    )
    target: str = Field(
        ...,
        description="Target node/service ID in the topology graph to execute upon.",
    )
    reason: str = Field(
        ...,
        description="Justification and rationale derived strictly from graph evidence.",
    )


class RCAResult(BaseModel):
    """Root Cause Analysis diagnosis output structure."""

    root_cause_node: str = Field(
        ...,
        description="Graph node ID identified as the primary failure root cause.",
    )
    root_cause_type: str = Field(
        ...,
        description="Categorical failure classification (e.g. pool_exhaustion, deadlock, cpu_spike).",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Diagnosis confidence score strictly bounded between 0.0 and 1.0.",
    )
    propagation_path: list[str] = Field(
        default_factory=list,
        description="Ordered sequence of node IDs showing blast radius propagation.",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Concrete telemetry and graph facts supporting this diagnosis.",
    )
    ranked_fixes: list[RankedFix] = Field(
        default_factory=list,
        description="Ranked list of allowlisted candidate remediation actions.",
    )
