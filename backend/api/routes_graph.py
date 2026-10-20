"""AEGIS Graph & Topology Endpoints (docs/02-CONTRACTS.md §4)."""

from fastapi import APIRouter
from backend.api.schemas import ResetResponse, TopologyResponse
from backend.graph import get_repository

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
def reset_to_baseline() -> ResetResponse:
    """Restore demo baseline in one click (clears incidents, decisions, fault metrics)."""
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
