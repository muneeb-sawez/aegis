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
    new_dependency_target: Optional[str] = None
    removed_fields: list[str] = Field(default_factory=list)
    added_fields: list[str] = Field(default_factory=list)


@router.get("/services")
def list_predict_services() -> list[dict[str, Any]]:
    """Return list of candidate microservices available for risk analysis in the active graph."""
    repo = get_repository()
    topo = repo.get_topology()
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
    topo = repo.get_topology()
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
        description=req.description,
        old_schema=old_schema,
        new_schema=new_schema,
        proposed_edges=proposed_edges,
    )

    return assess_change_risk(payload, repo)
