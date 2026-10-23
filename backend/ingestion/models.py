"""AEGIS Repository Ingestion Models (docs/02-CONTRACTS.md & Directive §3.B)."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class IngestedNode(BaseModel):
    id: str
    label: Literal["Service", "Database", "ExternalService", "APIEndpoint", "Pod"]
    project_id: str = "demo"
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance: Literal["manifest", "inferred", "manual"] = "manifest"


class IngestedEdge(BaseModel):
    source: str
    target: str
    type: Literal["CALLS", "DEPENDS_ON", "EXPOSES", "INSTANCE_OF"] = "DEPENDS_ON"
    project_id: str = "demo"
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance: Literal["manifest", "inferred", "manual"] = "manifest"


class ExternalServiceRegistration(BaseModel):
    name: str
    category: str = "Payment Gateway"
    endpoint_url: Optional[str] = None
    health_url: Optional[str] = None
    dependent_service_id: str
    description: str = ""
    project_id: str = "demo"


class IngestionRequest(BaseModel):
    repo_url: Optional[str] = None  # e.g. "https://github.com/GoogleCloudPlatform/microservices-demo" or "owner/repo"
    repository_url: Optional[str] = None  # alias for repo_url
    compose_yaml_content: Optional[str] = None  # direct YAML text input
    branch: str = "main"
    mode: Literal["replace", "merge"] = "replace"
    project_id: str = "demo"
    github_token: Optional[str] = None


class GitHubRepoImportRequest(BaseModel):
    repo_full_name: str = Field(..., description="GitHub 'owner/repo' (e.g. 'GoogleCloudPlatform/microservices-demo')")
    branch: str = Field("main", description="Branch to scan for manifest files")
    mode: Literal["replace", "merge"] = Field("replace", description="Graph update mode")
    project_id: Optional[str] = Field(None, description="Target project ID (defaults to active project)")
    github_token: Optional[str] = Field(None, description="Optional GitHub access token override")


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
    project_id: str = "demo"
