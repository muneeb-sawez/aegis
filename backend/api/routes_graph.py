"""AEGIS Graph & Topology Endpoints (docs/02-CONTRACTS.md §4)."""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from backend.api.schemas import ResetResponse, TopologyResponse
from backend.auth.dependencies import require_api_key
from backend.auth.store import ProjectRecord
from backend.config import settings
from backend.graph import get_repository
from backend.graph.repository import Incident


router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph/topology", response_model=TopologyResponse)
def get_graph_topology(project_id: str = "demo") -> TopologyResponse:
    """Return nodes, edges, and telemetry properties for the visualization canvas."""
    repo = get_repository()
    topo = repo.get_topology(project_id=project_id)
    return TopologyResponse(
        nodes=topo.nodes,
        edges=topo.edges,
        total_nodes=len(topo.nodes),
        total_edges=len(topo.edges),
    )


@router.post("/reset", response_model=ResetResponse)
def reset_to_baseline(
    project_id: str = "demo",
    _auth: ProjectRecord = Depends(require_api_key),
) -> ResetResponse:
    """Restore demo baseline in one click (clears incidents, decisions, fault metrics)."""
    repo = get_repository()
    repo.reset(project_id=project_id)
    from backend.monitor.health_checker import get_health_checker
    get_health_checker().reset()
    topo = repo.get_topology(project_id=project_id)
    return ResetResponse(
        status="ok",
        message=f"Topology and telemetry for project '{project_id}' successfully reset to clean demo baseline (54 nodes, 142 edges).",
        node_count=len(topo.nodes),
        edge_count=len(topo.edges),
        project_id=project_id,
    )


@router.get("/incidents", response_model=list[Incident])
def get_incidents(service_id: str | None = None, days: int = 30, project_id: str = "demo") -> list[Incident]:
    """Return historical incidents from GraphRepository for project_id."""
    repo = get_repository()
    return repo.incidents(service_id or "", days=days, project_id=project_id)


