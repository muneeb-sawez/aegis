"""AEGIS Simulation & Risk Configuration (M4).

Centralizes all weights, thresholds, and parameters.
Docs: docs/04-ALGORITHMS.md & .agent/rules/01-architecture-and-contracts.md.
No magic numbers outside this file!
"""

from pydantic import BaseModel, Field


class RiskConfig(BaseModel):
    # Component weights in Risk = W_B*B + W_C*C + W_D*D + W_H*H
    weight_blast: float = Field(default=0.35, description="Weight for blast radius (B)")
    weight_contract: float = Field(default=0.30, description="Weight for contract breaking severity (C)")
    weight_cycle: float = Field(default=0.15, description="Weight for cycle penalty (D)")
    weight_history: float = Field(default=0.20, description="Weight for incident history factor (H)")

    # Blast radius attenuation
    blast_attenuation: float = Field(default=0.75, description="Attenuation factor per hop (0.75^(hops-1))")
    blast_max_depth: int = Field(default=3, description="Maximum backward traversal depth")
    blast_normalization_cap: float = Field(default=6.0, description="Sum of weighted impact needed for B=100")

    # Gate thresholds
    threshold_approve: float = Field(default=40.0, description="Score below this is Approved")
    threshold_block: float = Field(default=70.0, description="Score at or above this is Blocked")

    # History penalty per incident
    history_penalty_per_incident: float = Field(default=25.0, description="H points per incident in past 30 days")
    history_max_score: float = Field(default=100.0, description="Cap for history factor H")


DEFAULT_CONFIG = RiskConfig()
