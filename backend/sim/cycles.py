"""AEGIS Cycle Detection Engine using Tarjan SCC (M4).

Analyzes whether a proposed change introduces dependency cycles.
Docs: docs/04-ALGORITHMS.md §3.
Any strongly connected component of size > 1 => D = 100.0, else 0.0.
"""

from __future__ import annotations

from typing import Any
import networkx as nx

from backend.graph.repository import GraphRepository
from pydantic import BaseModel, Field


class CycleCheckResult(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    has_cycle: bool
    cycles_detected: list[list[str]] = Field(default_factory=list)
    description: str


def detect_cycles(
    repo: GraphRepository,
    proposed_edges: list[dict[str, Any]] | None = None,
) -> CycleCheckResult:
    """Run Tarjan's Strongly Connected Components algorithm on the topology graph

    including any new edges introduced by a PR.
    """
    topo = repo.get_topology()

    # Build a DiGraph for SCC analysis
    G = nx.DiGraph()
    for n in topo.nodes:
        G.add_node(n.id)

    # Add existing CALLS edges
    for e in topo.edges:
        if e.type == "CALLS":
            G.add_edge(e.source, e.target)

    # Add proposed new edges
    if proposed_edges:
        for pe in proposed_edges:
            src = pe.get("source")
            tgt = pe.get("target")
            if src and tgt:
                G.add_edge(src, tgt)

    # Run Tarjan SCC
    sccs = list(nx.strongly_connected_components(G))
    cycles = [list(comp) for comp in sccs if len(comp) > 1]

    has_cycle = len(cycles) > 0
    score = 100.0 if has_cycle else 0.0

    if has_cycle:
        cycle_strs = [" -> ".join(c + [c[0]]) for c in cycles]
        desc = f"Dependency cycle detected via Tarjan SCC: {'; '.join(cycle_strs)}"
    else:
        desc = "No dependency cycles detected in the call graph."

    return CycleCheckResult(
        score=score,
        has_cycle=has_cycle,
        cycles_detected=cycles,
        description=desc,
    )
