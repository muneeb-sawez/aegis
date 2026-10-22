"""AEGIS Graph Package (M1).

Provides the factory method get_repository() to retrieve either
Neo4jGraphRepository or NetworkXGraphRepository according to GRAPH_BACKEND.
"""

from __future__ import annotations

import logging
from typing import Optional

from backend.config import settings
from backend.graph.networkx_repo import NetworkXGraphRepository
from backend.graph.repository import GraphRepository

logger = logging.getLogger("aegis.graph")

_instance: Optional[GraphRepository] = None
_mode: str = "ephemeral"


def get_graph_mode() -> str:
    """Return the active storage mode: 'persistent' or 'ephemeral'."""
    global _instance
    if _instance is None:
        get_repository()
    return _mode


def get_repository(force_refresh: bool = False) -> GraphRepository:
    """Return the singleton instance of the configured GraphRepository."""
    global _instance, _mode
    if _instance is not None and not force_refresh:
        return _instance

    backend = settings.GRAPH_BACKEND.lower()
    if backend == "neo4j":
        try:
            from backend.graph.neo4j_repo import Neo4jGraphRepository
            repo = Neo4jGraphRepository()
            repo.verify_connectivity()
            # Seed only if graph is empty
            if repo.is_empty():
                logger.info("Neo4j database is empty. Seeding from topology.yaml...")
                repo.reset()
            _instance = repo
            _mode = "persistent"
            return _instance
        except Exception as e:
            # Fall back to NetworkX with warning
            logger.warning(f"Failed to connect to Neo4j ({e}). Falling back to NetworkX.")
            print(f"[AEGIS WARNING] Failed to connect to Neo4j ({e}). Falling back to NetworkX.")
            _instance = NetworkXGraphRepository()
            _mode = "ephemeral"
            return _instance
    else:
        _instance = NetworkXGraphRepository()
        _mode = "ephemeral"
        return _instance

