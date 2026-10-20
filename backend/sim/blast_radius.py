"""AEGIS Blast Radius Engine (M4).

Traverses BACKWARDS along CALLS edges to determine all upstream callers
affected by a proposed service change, applying hop attenuation.
Docs: docs/04-ALGORITHMS.md §1.
"""

from __future__ import annotations

from typing import Any
from backend.graph.repository import Caller, GraphRepository
from backend.sim.config import DEFAULT_CONFIG, RiskConfig


def calculate_blast_radius(
    service_id: str,
    repo: GraphRepository,
    config: RiskConfig = DEFAULT_CONFIG,
) -> tuple[float, list[Caller], list[dict[str, Any]]]:
    """Calculate normalized blast radius score (B in [0, 100]) and list of affected callers.

    Returns:
        (b_score, callers, caller_details)
    """
    callers = repo.callers(service_id, depth=config.blast_max_depth)

    # Sum the attenuated weights
    raw_impact = sum(c.impact_weight for c in callers)

    # Normalize to 0-100 scale using the configured cap
    # E.g. If sum of impact weights >= config.blast_normalization_cap, B = 100.0
    normalized_b = min(100.0, round((raw_impact / config.blast_normalization_cap) * 100.0, 2))

    details = [
        {
            "node": c.node,
            "hops": c.hops,
            "impact_weight": c.impact_weight,
            "severity_halo": "red" if c.impact_weight >= 0.8 else "amber",
        }
        for c in callers
    ]

    return normalized_b, callers, details
