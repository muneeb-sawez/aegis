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
    project_id: str = "demo"
    properties: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    source: str
    target: str
    type: str  # CALLS, DEPENDS_ON, EXPOSES, INSTANCE_OF, OCCURRED_IN, RESOLVED_BY, RESULTED_IN
    project_id: str = "demo"
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
    project_id: str = "demo"
    resolved: bool = True
    decision_id: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)


class Outcome(BaseModel):
    """Structured result of a remediation Decision (RESULTED_IN edge target)."""

    id: str
    decision_id: str
    incident_id: str
    service_id: str
    fault_type: str
    action: str
    status: str          # succeeded | rolled_back | failed | refused
    safety_score: float
    composite_score: float
    timestamp: str
    project_id: str = "demo"
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphRepository(ABC):
    """Abstract interface for all AEGIS graph operations."""

    @abstractmethod
    def get_topology(self, project_id: str = "demo") -> Topology:
        """Return the complete active topology: nodes, edges, and telemetry properties."""
        pass

    @abstractmethod
    def neighbors(self, node: str, hops: int = 1, project_id: str = "demo") -> Subgraph:
        """Return the immediate k-hop neighborhood (both directions) for node."""
        pass

    @abstractmethod
    def callers(self, node: str, depth: int = 3, project_id: str = "demo") -> list[Caller]:
        """Return upstream callers of node, walking BACKWARDS along CALLS edges.

        Rule: CALLS is always caller -> callee. Callers are predecessors.
        """
        pass

    @abstractmethod
    def incidents(self, node: str = "", days: int = 30, project_id: str = "demo") -> list[Incident]:
        """Return historical incidents associated with node within the last `days` days.

        If node is empty, returns all incidents within the last `days` days.
        """
        pass

    @abstractmethod
    def set_telemetry(self, node: str, fields: dict[str, Any], project_id: str = "demo") -> None:
        """Update telemetry/metric properties on a given node."""
        pass

    @abstractmethod
    def add_incident(
        self,
        service_id: str,
        description: str,
        decision_data: Optional[dict[str, Any]] = None,
        project_id: str = "demo",
    ) -> Incident:
        """Create an Incident node, Decision node, and link them via OCCURRED_IN and RESOLVED_BY."""
        pass

    @abstractmethod
    def reset(self, project_id: str = "demo") -> None:
        """Restore graph to the clean demo baseline topology."""
        pass

    @abstractmethod
    def add_outcome(
        self,
        decision_id: str,
        incident_id: str,
        service_id: str,
        fault_type: str,
        action: str,
        status: str,
        safety_score: float,
        composite_score: float,
        project_id: str = "demo",
    ) -> "Outcome":
        """Create an Outcome node and link it via Decision-[:RESULTED_IN]->Outcome.

        Called by feedback/writer.py after every terminal decision status.
        """
        pass

    @abstractmethod
    def get_outcomes(
        self,
        fault_type: str = "",
        action: str = "",
        days: int = 90,
        project_id: str = "demo",
    ) -> list["Outcome"]:
        """Return Outcome nodes optionally filtered by fault_type and/or action.

        Used by scoring.py to compute success-rate table when >= 3 samples exist.
        """
        pass

    @abstractmethod
    def get_all_incidents_with_descriptions(self, days: int = 90, project_id: str = "demo") -> list[dict[str, Any]]:
        """Return all incidents as dicts with at least 'id', 'service_id', 'description'.

        Used by the similarity engine in feedback/similarity.py.
        """
        pass

