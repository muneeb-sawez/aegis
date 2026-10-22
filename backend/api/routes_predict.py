"""AEGIS PREDICT Change-Risk Analysis API Endpoints (Directive §3.A)."""

from typing import Any, Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.graph import get_repository
from backend.sim.risk import PRPayload, RiskAssessmentResult, assess_change_risk

router = APIRouter(prefix="/api/predict", tags=["predict"])


class ChangeAnalysisRequest(BaseModel):
    service_id: str
    change_type: Literal["api_breaking", "additive_safe", "dependency_add", "dependency_cycle", "custom"] = "api_breaking"
    change_title: str = "Proposed Software Change"
    description: str = ""
    project_id: str = "demo"
    new_dependency_target: Optional[str] = None
    removed_fields: list[str] = Field(default_factory=list)
    added_fields: list[str] = Field(default_factory=list)


@router.get("/services")
def list_predict_services(project_id: str = "demo") -> list[dict[str, Any]]:
    """Return list of candidate microservices available for risk analysis in the active graph."""
    repo = get_repository()
    topo = repo.get_topology(project_id=project_id)
    services = [
        {
            "id": n.id,
            "label": n.label,
            "name": n.properties.get("name", n.id),
            "tier": n.properties.get("tier", "core"),
        }
        for n in topo.nodes
        if n.label == "Service"
    ]
    # If no nodes labeled Service specifically, return all nodes
    if not services:
        services = [{"id": n.id, "label": n.label, "name": n.id, "tier": "general"} for n in topo.nodes]
    return services


@router.post("/analyze", response_model=RiskAssessmentResult)
def analyze_change(req: ChangeAnalysisRequest) -> RiskAssessmentResult:
    """Analyze a proposed software change and calculate evidence-backed risk.

    Follows: Select service -> Specify change -> Analyze graph impact -> Calculate risk -> Display results.
    """
    repo = get_repository()
    topo = repo.get_topology(project_id=req.project_id)

    node_ids = {n.id for n in topo.nodes}

    if req.service_id not in node_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{req.service_id}' does not exist in active graph topology.",
        )

    if req.new_dependency_target and req.new_dependency_target not in node_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Dependency target '{req.new_dependency_target}' does not exist in active graph topology.",
        )

    # Construct schema diff based on change_type
    old_schema: dict[str, Any] = {"properties": {"id": {"type": "string"}, "status": {"type": "string"}}, "required": ["id", "status"]}
    new_schema: dict[str, Any] = {"properties": {"id": {"type": "string"}, "status": {"type": "string"}}, "required": ["id", "status"]}
    proposed_edges: list[dict[str, Any]] = []

    if req.change_type == "api_breaking":
        # Simulate removing required fields
        old_schema["properties"]["transaction_id"] = {"type": "string"}
        old_schema["required"].append("transaction_id")
        # new_schema does not include transaction_id -> breaking contract

    elif req.change_type == "additive_safe":
        # Adds backwards-compatible optional field
        new_schema["properties"]["discount_code"] = {"type": "string"}

    elif req.change_type == "dependency_add":
        if not req.new_dependency_target:
            raise HTTPException(
                status_code=400,
                detail="'new_dependency_target' is required when proposing a 'dependency_add' change.",
            )
        proposed_edges.append({
            "source": req.service_id,
            "target": req.new_dependency_target,
            "type": "CALLS",
        })

    elif req.change_type == "dependency_cycle":
        # Target an existing caller to introduce a cycle
        callers = repo.callers(req.service_id, depth=2)
        if callers:
            cycle_target = callers[0].node
        else:
            # If no callers (e.g. frontend), find an outgoing edge target
            nbrs = repo.neighbors(req.service_id, hops=1)
            out_targets = [
                e.target for e in nbrs.edges
                if e.source == req.service_id and e.type in ("CALLS", "DEPENDS_ON") and e.target != req.service_id
            ]
            cycle_target = out_targets[0] if out_targets else "frontend"

        # Proposed edge is from cycle_target into req.service_id or vice versa to close cycle
        proposed_edges.append({
            "source": req.service_id,
            "target": cycle_target,
            "type": "CALLS",
        })

    elif req.change_type == "custom":
        if req.removed_fields:
            for f in req.removed_fields:
                old_schema["properties"][f] = {"type": "string"}
                old_schema["required"].append(f)
        if req.added_fields:
            for f in req.added_fields:
                new_schema["properties"][f] = {"type": "string"}
        if req.new_dependency_target:
            proposed_edges.append({
                "source": req.service_id,
                "target": req.new_dependency_target,
                "type": "CALLS",
            })

    payload = PRPayload(
        id=f"CHANGE-{req.service_id.upper()}",
        title=req.change_title,
        target_service=req.service_id,
        project_id=req.project_id,
        description=req.description,
        old_schema=old_schema,
        new_schema=new_schema,
        proposed_edges=proposed_edges,
    )

    return assess_change_risk(payload, repo, project_id=req.project_id)


class PRComparisonResponse(BaseModel):
    pr_id: str
    target_service: str
    project_id: str = "demo"
    baseline_score: float
    current_score: float
    delta_score: float
    baseline_history_score: float
    current_history_score: float
    delta_history_score: float
    incident_count: int
    verdict_before: str
    verdict_after: str
    explanation: str


@router.get("/pr-comparison", response_model=PRComparisonResponse)
def get_pr_risk_comparison(pr_id: str = "PR-142", project_id: str = "demo") -> PRComparisonResponse:
    """Return before vs after risk comparison for a pull request (e.g. PR-142).

    Compares:
      - Baseline risk score (calculated on clean topology with 0 incidents, H=0)
      - Current risk score (calculated on active graph with live incidents)
      - The delta and human-readable explanation of how the historical learning term shifted.
    """
    import json
    from pathlib import Path
    from backend.graph.networkx_repo import NetworkXGraphRepository

    prs_dir = Path(__file__).resolve().parent.parent.parent / "data" / "prs"
    lookup = {
        "PR-142": "pr_142_breaking.json",
        "PR-010": "pr_safe.json",
        "PR-077": "pr_cyclic.json",
        "PR-055": "pr_moderate.json",
        "PR-021": "pr_leaf.json",
        "PR-001": "pr_gateway.json",
    }
    filename = lookup.get(pr_id, "pr_142_breaking.json")
    file_path = prs_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"PR file {filename} not found.")

    with open(file_path, "r", encoding="utf-8") as f:
        pr_data = json.load(f)

    payload = PRPayload(
        id=pr_data.get("id", pr_id),
        title=pr_data.get("title", f"Change for {pr_id}"),
        target_service=pr_data.get("target_service", "paymentservice"),
        project_id=project_id,
        author=pr_data.get("author", "engineer@company.com"),
        description=pr_data.get("description", ""),
        old_schema=pr_data.get("old_schema"),
        new_schema=pr_data.get("new_schema"),
        proposed_edges=pr_data.get("proposed_edges"),
    )

    # 1. Baseline assessment (isolated graph with 0 incidents)
    baseline_repo = NetworkXGraphRepository()
    baseline_res = assess_change_risk(payload, baseline_repo, project_id=project_id)

    # 2. Current assessment (active graph repository)
    current_repo = get_repository()
    current_res = assess_change_risk(payload, current_repo, project_id=project_id)

    delta_score = round(current_res.risk_score - baseline_res.risk_score, 1)
    delta_hist = round(current_res.breakdown.history_score - baseline_res.breakdown.history_score, 1)
    incident_count = current_res.incident_count_30d

    if incident_count == 0:
        explanation = (
            f"Baseline risk score for {payload.id} ({payload.target_service}) in project '{project_id}' is {baseline_res.risk_score:.1f} "
            f"(H=0.0). No historical incidents have been recorded in the active Knowledge Graph yet. "
            f"If an incident occurs in {payload.target_service}, each recorded incident adds +25.0 to H "
            f"(weight 0.20), shifting the risk score by +5.0 points to {baseline_res.risk_score + 5.0:.1f}."
        )
    else:
        explanation = (
            f"{payload.id} ({payload.target_service}) risk score in project '{project_id}' increased from {baseline_res.risk_score:.1f} "
            f"to {current_res.risk_score:.1f} ({delta_score:+.1f} pts) because {incident_count} incident(s) "
            f"in {payload.target_service} increased the historical penalty H from {baseline_res.breakdown.history_score:.1f} "
            f"to {current_res.breakdown.history_score:.1f} (0.20 × {delta_hist:.1f} = {delta_score:+.1f})."
        )

    return PRComparisonResponse(
        pr_id=payload.id,
        target_service=payload.target_service,
        project_id=project_id,
        baseline_score=baseline_res.risk_score,
        current_score=current_res.risk_score,
        delta_score=delta_score,
        baseline_history_score=baseline_res.breakdown.history_score,
        current_history_score=current_res.breakdown.history_score,
        delta_history_score=delta_hist,
        incident_count=incident_count,
        verdict_before=baseline_res.verdict,
        verdict_after=current_res.verdict,
        explanation=explanation,
    )


