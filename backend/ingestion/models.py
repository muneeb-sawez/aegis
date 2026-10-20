"""AEGIS Repository Ingestion Models (docs/02-CONTRACTS.md & Directive §3.B)."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class IngestedNode(BaseModel):
    id: str
    label: Literal["Service", "Database", "ExternalService", "APIEndpoint", "Pod"]
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance: Literal["manifest", "inferred", "manual"] = "manifest"


class IngestedEdge(BaseModel):
    source: str
    target: str
    type: Literal["CALLS", "DEPENDS_ON", "EXPOSES", "INSTANCE_OF"] = "DEPENDS_ON"
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance: Literal["manifest", "inferred", "manual"] = "manifest"


class ExternalServiceRegistration(BaseModel):
    name: str
    category: str = "Payment Gateway"
    endpoint_url: Optional[str] = None
    health_url: Optional[str] = None
    dependent_service_id: str
    description: str = ""


class IngestionRequest(BaseModel):
    repo_url: Optional[str] = None  # e.g. "https://github.com/GoogleCloudPlatform/microservices-demo" or "owner/repo"
    compose_yaml_content: Optional[str] = None  # direct YAML text input
    branch: str = "main"
    mode: Literal["replace", "merge"] = "replace"


class IngestionResult(BaseModel):
    status: Literal["success", "partial", "error"]
    message: str
    source: str
    nodes_added: int
    nodes_updated: int
    edges_added: int
    total_graph_nodes: int
    total_graph_edges: int
    services_discovered: list[str] = Field(default_factory=list)
