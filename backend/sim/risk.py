"""AEGIS Change-Risk Prediction Engine (M4).

Computes deterministic, evidence-backed risk score for any proposed pull request:
Risk = W_B*B + W_C*C + W_D*D + W_H*H
Thresholds:
- Score < 40: Approved (Low Risk)
- 40 <= Score < 70: Warn (Requires SRE Review)
- Score >= 70: Blocked (High Risk / Breaking)
Docs: docs/04-ALGORITHMS.md §5 & .agent/rules/05-honesty-real-vs-simulated.md.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from backend.graph.repository import GraphRepository
from backend.sim.blast_radius import calculate_blast_radius
from backend.sim.config import DEFAULT_CONFIG, RiskConfig
from backend.sim.contract_diff import ContractDiffResult, diff_schemas
from backend.sim.cycles import CycleCheckResult, detect_cycles


class PRPayload(BaseModel):
    id: str
    title: str
    target_service: str
    project_id: str = "demo"
    author: str = "engineer@example.com"
    description: str = ""
    old_schema: dict[str, Any] | None = None
    new_schema: dict[str, Any] | None = None
    proposed_edges: list[dict[str, Any]] | None = None


class RiskBreakdown(BaseModel):
    blast_score: float = Field(ge=0.0, le=100.0)
    contract_score: float = Field(ge=0.0, le=100.0)
    cycle_score: float = Field(ge=0.0, le=100.0)
    history_score: float = Field(ge=0.0, le=100.0)
    weights: dict[str, float]


class RiskAssessmentResult(BaseModel):
    pr_id: str
    target_service: str
    project_id: str = "demo"
    risk_score: float = Field(ge=0.0, le=100.0)
    verdict: str  # Approved, Warn, Blocked
    breakdown: RiskBreakdown
    blast_details: list[dict[str, Any]]
    contract_diff: ContractDiffResult
    cycle_check: CycleCheckResult
    incident_count_30d: int
    recommendation: str
    explanation: list[str]


def assess_change_risk(
    pr: PRPayload,
    repo: GraphRepository,
    config: RiskConfig = DEFAULT_CONFIG,
    project_id: str = "demo",
) -> RiskAssessmentResult:
    """Compute the multi-factor change-risk score and merge gate verdict."""
    eff_project_id = project_id if project_id != "demo" else (pr.project_id or "demo")

    # 1. Term B: Blast Radius
    b_score, callers, caller_details = calculate_blast_radius(
        pr.target_service,
        repo,
        config=config,
        project_id=eff_project_id,
    )


    # 2. Term C: Breaking Contract Severity
    contract_res = diff_schemas(pr.old_schema, pr.new_schema)
    c_score = contract_res.score

    # 3. Term D: Cycle Penalty
    cycle_res = detect_cycles(repo, pr.proposed_edges, project_id=eff_project_id)
    d_score = cycle_res.score

    # 4. Term H: Historical Incidents (past 30 days)
    incidents = repo.incidents(pr.target_service, days=30, project_id=eff_project_id)
    inc_count = len(incidents)
    h_score = min(
        config.history_max_score,
        round(inc_count * config.history_penalty_per_incident, 2),
    )


    # 5. Composite Risk Score
    composite_raw = (
        config.weight_blast * b_score
        + config.weight_contract * c_score
        + config.weight_cycle * d_score
        + config.weight_history * h_score
    )
    risk_score = round(min(100.0, max(0.0, composite_raw)), 1)

    # 6. Gate Verdict
    # Hard Gate Rule: If a breaking API contract change is detected (C == 100.0),
    # it must NEVER be marked 'Approved' regardless of weighted score.
    # Breaking contracts require at least SRE review (Blocked or Warn).
    if contract_res.is_breaking:
        # Minimum risk floor of 70.0 (or threshold_block) for breaking API changes
        risk_score = max(risk_score, config.threshold_block)
        verdict = "Blocked"
        recommendation = (
            f"Deployment BLOCKED: Critical API contract breaking change detected in '{pr.target_service}'. "
            "Upstream consumers will experience deserialization/runtime failures without consumer-side coordination."
        )
    elif risk_score >= config.threshold_block:
        verdict = "Blocked"
        recommendation = (
            f"Deployment blocked: Risk score of {risk_score} exceeds safety threshold ({config.threshold_block}). "
            "Requires breaking-change approval and manual mitigation plan."
        )
    elif risk_score >= config.threshold_approve:
        verdict = "Warn"
        recommendation = (
            f"Review recommended: Risk score of {risk_score} indicates moderate blast radius or architectural changes. "
            "Requires peer SRE sign-off before merging."
        )
    else:
        verdict = "Approved"
        recommendation = (
            f"Approved for auto-deploy: Low risk score of {risk_score} (< {config.threshold_approve}). "
            "Safe backwards-compatible changes with minimal upstream impact."
        )

    # 7. Human-readable explanation factors
    explanations: list[str] = []
    explanations.append(
        f"Blast Radius (B={b_score}): Found {len(callers)} upstream callers with total attenuated impact {sum(c.impact_weight for c in callers):.2f}."
    )
    if contract_res.is_breaking:
        explanations.append(
            f"Contract Severity (C={c_score}): Breaking changes detected ({len(contract_res.changes)} breaking alterations)."
        )
    else:
        explanations.append("Contract Severity (C=0.0): No breaking API/schema contract changes detected.")

    if cycle_res.has_cycle:
        explanations.append(f"Cycle Penalty (D={d_score}): {cycle_res.description}")
    else:
        explanations.append("Cycle Penalty (D=0.0): Graph topology remains acyclic.")

    if inc_count == 0:
        explanations.append(
            f"Incident History (H=0.0): No incidents recorded on {pr.target_service} in the past 30 days (clean baseline)."
        )
    else:
        explanations.append(
            f"Incident History (H={h_score}): {inc_count} incident(s) recorded on {pr.target_service} in the past 30 days (+{h_score:.1f} penalty)."
        )

    return RiskAssessmentResult(
        pr_id=pr.id,
        target_service=pr.target_service,
        project_id=eff_project_id,
        risk_score=risk_score,
        verdict=verdict,
        breakdown=RiskBreakdown(
            blast_score=b_score,
            contract_score=c_score,
            cycle_score=d_score,
            history_score=h_score,
            weights={
                "W_B": config.weight_blast,
                "W_C": config.weight_contract,
                "W_D": config.weight_cycle,
                "W_H": config.weight_history,
            },
        ),
        blast_details=caller_details,
        contract_diff=contract_res,
        cycle_check=cycle_res,
        incident_count_30d=inc_count,
        recommendation=recommendation,
        explanation=explanations,
    )
