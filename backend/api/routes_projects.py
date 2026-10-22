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
    )
