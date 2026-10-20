"""AEGIS Graph Package (M1).

Provides the factory method get_repository() to retrieve either
Neo4jGraphRepository or NetworkXGraphRepository according to GRAPH_BACKEND.
"""

from __future__ import annotations

import os
from backend.graph.networkx_repo import NetworkXGraphRepository
from backend.graph.repository import GraphRepository

_instance: GraphRepository | None = None


def get_repository(force_refresh: bool = False) -> GraphRepository:
    """Return the singleton instance of the configured GraphRepository."""
    global _instance
    if _instance is not None and not force_refresh:
        return _instance

    backend = os.getenv("GRAPH_BACKEND", "networkx").lower()
    if backend == "neo4j":
        try:
            from backend.graph.neo4j_repo import Neo4jGraphRepository
            _instance = Neo4jGraphRepository()
            return _instance
        except Exception as e:
            # Fall back to NetworkX with warning
            print(f"[AEGIS WARNING] Failed to connect to Neo4j ({e}). Falling back to NetworkX.")
            _instance = NetworkXGraphRepository()
            return _instance
    else:
        _instance = NetworkXGraphRepository()
        return _instance
