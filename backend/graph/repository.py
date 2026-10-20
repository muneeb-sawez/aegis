"""AEGIS Graph Repository Interface (docs/02-CONTRACTS.md §3).

Encapsulates all graph operations. No Cypher or direct graph storage queries
are permitted outside backend/graph/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str
    label: str  # Service, Database, APIEndpoint, Pod, Incident, Decision
    properties: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    source: str
    target: str
    type: str  # CALLS, DEPENDS_ON, EXPOSES, INSTANCE_OF, OCCURRED_IN, RESOLVED_BY
    properties: dict[str, Any] = Field(default_factory=dict)


class Topology(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)


class Subgraph(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)


class Caller(BaseModel):
    node: str
    hops: int
    impact_weight: float = 1.0


class Incident(BaseModel):
    id: str
    service_id: str
    description: str
    timestamp: str
    resolved: bool = True
    decision_id: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphRepository(ABC):
    """Abstract interface for all AEGIS graph operations."""

    @abstractmethod
    def get_topology(self) -> Topology:
        """Return the complete active topology: nodes, edges, and telemetry properties."""
        pass

    @abstractmethod
    def neighbors(self, node: str, hops: int = 1) -> Subgraph:
        """Return the immediate k-hop neighborhood (both directions) for node."""
        pass

    @abstractmethod
    def callers(self, node: str, depth: int = 3) -> list[Caller]:
        """Return upstream callers of node, walking BACKWARDS along CALLS edges.

        Rule: CALLS is always caller -> callee. Callers are predecessors.
        """
        pass

    @abstractmethod
    def incidents(self, node: str, days: int = 30) -> list[Incident]:
        """Return historical incidents associated with node within the last `days` days."""
        pass

    @abstractmethod
    def set_telemetry(self, node: str, fields: dict[str, Any]) -> None:
        """Update telemetry/metric properties on a given node."""
        pass

    @abstractmethod
    def add_incident(
        self,
        service_id: str,
        description: str,
        decision_data: Optional[dict[str, Any]] = None,
    ) -> Incident:
        """Create an Incident node, Decision node, and link them via OCCURRED_IN and RESOLVED_BY."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Restore graph to the clean demo baseline topology."""
        pass
