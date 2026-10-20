"""AEGIS PREDICT Change-Risk Analysis API Endpoints (Directive §3.A)."""

from typing import Any, Literal, Optional
from fastapi import APIRouter
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


@router.post("/analyze", response_model=RiskAssessmentResult)
def analyze_change(req: ChangeAnalysisRequest) -> RiskAssessmentResult:
    """Analyze a proposed software change and calculate evidence-backed risk.

    Follows: Select service -> Specify change -> Analyze graph impact -> Calculate risk -> Display results.
    """
    repo = get_repository()

    # Construct schema diff based on change_type
    old_schema: dict[str, Any] = {"properties": {"id": {"type": "string"}}, "required": ["id"]}
    new_schema: dict[str, Any] = {"properties": {"id": {"type": "string"}}, "required": ["id"]}
    proposed_edges: list[dict[str, Any]] = []

    if req.change_type == "api_breaking":
        # Simulate removing required fields
        old_schema["properties"]["transaction_id"] = {"type": "string"}
        old_schema["properties"]["status"] = {"type": "string"}
        old_schema["required"].extend(["transaction_id", "status"])
        # New schema removes transaction_id
        new_schema["properties"]["status"] = {"type": "string"}
        new_schema["required"].append("status")

    elif req.change_type == "additive_safe":
        # Adds optional field
        new_schema["properties"]["discount_code"] = {"type": "string"}

    elif req.change_type == "dependency_add":
        if req.new_dependency_target:
            proposed_edges.append({
                "source": req.service_id,
                "target": req.new_dependency_target,
                "type": "CALLS",
            })

    elif req.change_type == "dependency_cycle":
        # Target an existing caller to introduce a cycle
        callers = repo.callers(req.service_id, depth=1)
        cycle_target = callers[0].node if callers else "frontend"
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
