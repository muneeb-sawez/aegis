"""AEGIS Project Management & API Key Management Endpoints.

Allows creating new projects, provisioning per-project API keys (hashed in storage),
and querying project metadata and topology statistics.
"""

from __future__ import annotations

import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.auth.store import (
    ProjectCreationResponse,
    ProjectPublic,
    get_project_store,
)
from backend.graph import get_repository

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    project_id: str = Field(..., description="Unique alphanumeric identifier (e.g. 'checkout-prod')")
    name: str = Field(..., description="Human-readable project title")
    description: Optional[str] = Field("", description="Optional project description")
    seed_baseline: bool = Field(True, description="Whether to seed the 54-node baseline graph")


@router.get("", response_model=list[ProjectPublic])
def list_projects() -> list[ProjectPublic]:
    """List all registered projects, their key security status, and graph size."""
    store = get_project_store()
    repo = get_repository()
    all_projects = store.load_all()

    results: list[ProjectPublic] = []
    for pid, p in all_projects.items():
        topo = repo.get_topology(project_id=pid)
        results.append(
            ProjectPublic(
                project_id=p.project_id,
                name=p.name,
                description=p.description,
                created_at=p.created_at,
                key_status="SHA-256 Hashed",
                node_count=len(topo.nodes),
                edge_count=len(topo.edges),
                repo_full_name=p.repo_full_name,
                repo_branch=p.repo_branch,
                manifest_path=p.manifest_path,
            )
        )
    return results


@router.post("", response_model=ProjectCreationResponse, status_code=201)
def create_project(req: CreateProjectRequest) -> ProjectCreationResponse:
    """Create a new project tenant and generate a secure API key.

    The plaintext API key is returned ONLY once in this response.
    The key is stored on disk strictly as a SHA-256 cryptographic hash.
    """
    clean_id = req.project_id.strip().lower()
    if not clean_id:
        raise HTTPException(status_code=400, detail="project_id cannot be empty")

    if not re.match(r"^[a-z0-9-_]+$", clean_id):
        raise HTTPException(
            status_code=400,
            detail="project_id must only contain lowercase alphanumeric characters, hyphens, and underscores",
        )

    store = get_project_store()
    if store.get_project(clean_id):
        raise HTTPException(status_code=409, detail=f"Project '{clean_id}' already exists")

    try:
        record, raw_key = store.create_project(
            project_id=clean_id,
            name=req.name.strip() or clean_id,
            description=req.description or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Initialize graph topology for the new project if requested
    if req.seed_baseline:
        repo = get_repository()
        repo.reset(project_id=clean_id)

    return ProjectCreationResponse(
        project_id=record.project_id,
        name=record.name,
        description=record.description,
        api_key=raw_key,
        created_at=record.created_at,
        message="Project registered successfully. Please copy and store your API key securely. It cannot be recovered once this modal closes.",
    )


@router.get("/{project_id}", response_model=ProjectPublic)
def get_project_details(project_id: str) -> ProjectPublic:
    """Retrieve metadata and topology metrics for a single project."""
    store = get_project_store()
    record = store.get_project(project_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    repo = get_repository()
    topo = repo.get_topology(project_id=project_id)
    return ProjectPublic(
        project_id=record.project_id,
        name=record.name,
        description=record.description,
        created_at=record.created_at,
        key_status="SHA-256 Hashed",
        node_count=len(topo.nodes),
        edge_count=len(topo.edges),
        repo_full_name=record.repo_full_name,
        repo_branch=record.repo_branch,
        manifest_path=record.manifest_path,
    )


class IntegrateGitHubProjectRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL or slug (e.g. 'https://github.com/spring-petclinic/spring-petclinic-microservices')")
    project_id: Optional[str] = Field(None, description="Optional custom project ID/slug. Defaults to repository name.")
    name: Optional[str] = Field(None, description="Optional human-readable project title")
    branch: Optional[str] = Field("main", description="Target Git branch")
    mode: Optional[str] = Field("replace", description="Graph ingestion mode: 'replace' or 'merge'")


class IntegrateGitHubProjectResponse(BaseModel):
    project_id: str
    name: str
    description: str
    repo_full_name: str
    repo_branch: str
    nodes_added: int
    edges_added: int
    total_nodes: int
    total_edges: int
    services_discovered: list[str]
    message: str
    api_key: Optional[str] = None


@router.post("/integrate-github", response_model=IntegrateGitHubProjectResponse, status_code=201)
async def integrate_github_project(req: IntegrateGitHubProjectRequest) -> IntegrateGitHubProjectResponse:
    """Seamlessly integrate a project directly via its GitHub repository link.
    
    1. Parses repository slug/URL.
    2. Auto-provisions the project tenant in storage if not already registered.
    3. Fetches and parses microservice manifests from GitHub.
    4. Builds and populates the isolated architecture knowledge graph.
    5. Returns project summary and topology metrics.
    """
    from backend.ingestion.github_fetcher import parse_github_repo_url
    from backend.ingestion.models import GitHubRepoImportRequest
    from backend.ingestion.service import import_github_repository_to_project

    raw_url = req.repo_url.strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="Repository URL cannot be empty")

    try:
        owner, repo_name = parse_github_repo_url(raw_url)
        normalized_slug = f"{owner}/{repo_name}"
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Derive clean project_id slug
    if req.project_id and req.project_id.strip():
        clean_pid = req.project_id.strip().lower()
    else:
        clean_pid = repo_name.lower().replace(".", "-").replace("_", "-")

    clean_pid = re.sub(r"[^a-z0-9-_]", "", clean_pid) or "github-project"

    store = get_project_store()
    existing = store.get_project(clean_pid)
    raw_key = None

    if not existing:
        proj_name = req.name.strip() if req.name else repo_name.replace("-", " ").replace("_", " ").title()
        record, raw_key = store.create_project(
            project_id=clean_pid,
            name=proj_name,
            description=f"Integrated from GitHub repository '{normalized_slug}'.",
        )
    else:
        record = existing

    # Import GitHub manifest and build graph topology
    import_req = GitHubRepoImportRequest(
        repo_full_name=normalized_slug,
        branch=req.branch or "main",
        mode=req.mode or "replace",
        project_id=clean_pid,
    )

    try:
        ingest_result = await import_github_repository_to_project(
            req=import_req,
            project_id=clean_pid,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest GitHub repository: {e}")

    repo = get_repository()
    topo = repo.get_topology(project_id=clean_pid)

    return IntegrateGitHubProjectResponse(
        project_id=clean_pid,
        name=record.name,
        description=record.description,
        repo_full_name=normalized_slug,
        repo_branch=req.branch or "main",
        nodes_added=ingest_result.nodes_added,
        edges_added=ingest_result.edges_added,
        total_nodes=len(topo.nodes),
        total_edges=len(topo.edges),
        services_discovered=ingest_result.services_discovered,
        message=f"Repository '{normalized_slug}' successfully integrated into project '{clean_pid}'. Knowledge graph mapped with {len(topo.nodes)} services and {len(topo.edges)} dependencies.",
        api_key=raw_key,
    )

