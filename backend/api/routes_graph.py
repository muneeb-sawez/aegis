"""AEGIS Graph & Topology Endpoints (docs/02-CONTRACTS.md §4)."""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from backend.api.schemas import ResetResponse, TopologyResponse
from backend.config import settings
from backend.graph import get_repository
from backend.graph.repository import Incident


router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph/topology", response_model=TopologyResponse)
def get_graph_topology() -> TopologyResponse:
    """Return nodes, edges, and telemetry properties for the visualization canvas."""
    repo = get_repository()
    topo = repo.get_topology()
    return TopologyResponse(
        nodes=topo.nodes,
        edges=topo.edges,
        total_nodes=len(topo.nodes),
        total_edges=len(topo.edges),
    )


@router.post("/reset", response_model=ResetResponse)
def reset_to_baseline(
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret"),
) -> ResetResponse:
    """Restore demo baseline in one click (clears incidents, decisions, fault metrics)."""
    if settings.ADMIN_SHARED_SECRET:
        if not x_admin_secret or x_admin_secret != settings.ADMIN_SHARED_SECRET:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: invalid or missing X-Admin-Secret header",
            )
    repo = get_repository()
    repo.reset()
    from backend.monitor.health_checker import get_health_checker
    get_health_checker().reset()
    topo = repo.get_topology()
    return ResetResponse(
        status="ok",
        message="Topology and telemetry successfully reset to clean demo baseline (54 nodes, 142 edges).",
        node_count=len(topo.nodes),
        edge_count=len(topo.edges),
    )



@router.get("/incidents", response_model=list[Incident])
def get_incidents(service_id: str | None = None, days: int = 30) -> list[Incident]:
    """Return historical incidents from GraphRepository."""
    repo = get_repository()
    return repo.incidents(service_id or "", days=days)

