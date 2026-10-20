"""AEGIS Pre-Ship Simulation Endpoints (docs/02-CONTRACTS.md §4)."""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.api.schemas import SimulatePRRequest, SimulatePRResponse
from backend.graph import get_repository
from backend.sim.risk import PRPayload, assess_change_risk

router = APIRouter(prefix="/api", tags=["simulation"])

PRS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "prs"


@router.post("/simulate-pr", response_model=SimulatePRResponse)
def simulate_pr(req: SimulatePRRequest) -> SimulatePRResponse:
    """Analyze a proposed PR against graph topology, contract diff, cycle detection,

    and historical incidents to compute evidence-backed risk score.
    """
    repo = get_repository()

    # If schemas are not provided but a known pr_id is specified, load from data/prs/
    target_pr_data = req.model_dump()
    if not req.old_schema and not req.new_schema and req.pr_id:
        lookup_files = {
            "PR-142": "pr_142_breaking.json",
            "PR-010": "pr_safe.json",
            "PR-077": "pr_cyclic.json",
            "PR-055": "pr_moderate.json",
            "PR-021": "pr_leaf.json",
            "PR-001": "pr_gateway.json",
        }
        filename = lookup_files.get(req.pr_id)
        if filename and (PRS_DIR / filename).exists():
            with open(PRS_DIR / filename, "r", encoding="utf-8") as f:
                target_pr_data = json.load(f)

    try:
        pr_payload = PRPayload(
            id=target_pr_data.get("pr_id") or target_pr_data.get("id") or "PR-CUSTOM",
            title=target_pr_data.get("title", "Simulated Change"),
            target_service=target_pr_data.get("target_service", req.target_service),
            author=target_pr_data.get("author", "engineer@company.com"),
            description=target_pr_data.get("description", ""),
            old_schema=target_pr_data.get("old_schema"),
            new_schema=target_pr_data.get("new_schema"),
            proposed_edges=target_pr_data.get("proposed_edges"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PR payload: {e}")

    result = assess_change_risk(pr_payload, repo)

    return SimulatePRResponse(
        pr_id=result.pr_id,
        target_service=result.target_service,
        risk_score=result.risk_score,
        verdict=result.verdict,  # type: ignore
        breakdown=result.breakdown,
        blast_details=result.blast_details,
        contract_diff=result.contract_diff,
        cycle_check=result.cycle_check,
        incident_count_30d=result.incident_count_30d,
        recommendation=result.recommendation,
        explanation=result.explanation,
    )
