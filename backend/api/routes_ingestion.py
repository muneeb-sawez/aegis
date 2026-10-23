"""AEGIS Ingestion API Endpoints (Directive §3.B)."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from backend.auth.dependencies import require_api_key
from backend.auth.store import ProjectRecord
from backend.ingestion.models import (
    ExternalServiceRegistration,
    GitHubRepoImportRequest,
    IngestionRequest,
    IngestionResult,
)
from backend.ingestion.service import (
    import_github_repository_to_project,
    ingest_repository_or_manifest,
    register_external_service,
)

router = APIRouter(prefix="/api", tags=["ingestion"])


@router.post("/projects/{project_id}/import-github", response_model=IngestionResult)
async def import_github_repo_for_project(
    project_id: str,
    req: GitHubRepoImportRequest,
    _auth: ProjectRecord = Depends(require_api_key),
) -> IngestionResult:
    """Import a GitHub repository manifest, build graph topology, and bind to project."""
    target_pid = project_id or req.project_id or _auth.project_id
    try:
        return await import_github_repository_to_project(
            req=req,
            project_id=target_pid,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub repository import failed: {e}")


@router.post("/ingest/import-github", response_model=IngestionResult)
async def import_github_repo_direct(
    req: GitHubRepoImportRequest,
    _auth: ProjectRecord = Depends(require_api_key),
) -> IngestionResult:
    """Direct import endpoint for GitHub repository manifest and graph generation."""
    target_pid = req.project_id or _auth.project_id or "demo"
    try:
        return await import_github_repository_to_project(
            req=req,
            project_id=target_pid,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub repository import failed: {e}")


@router.post("/ingest/repository", response_model=IngestionResult)
async def ingest_repository(
    req: IngestionRequest,
    _auth: ProjectRecord = Depends(require_api_key),
) -> IngestionResult:
    """Ingest a GitHub repository or raw Docker Compose manifest to build or update the graph."""
    try:
        return await ingest_repository_or_manifest(req)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@router.post("/graph/external-service")
def add_external_service(
    reg: ExternalServiceRegistration,
    _auth: ProjectRecord = Depends(require_api_key),
) -> dict[str, Any]:
    """Manually register an external cloud vendor or API and link to a dependent service."""
    try:
        return register_external_service(reg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to register external service: {e}")


@router.get("/ingest/sample-repos")
def get_sample_repositories() -> list[dict[str, Any]]:
    """Return catalog of pre-bundled test repositories for demonstration and test execution."""
    from backend.ingestion.sample_repos import SAMPLE_REPOSITORIES

    return [
        {
            "slug": s["slug"],
            "name": s["name"],
            "description": s["description"],
            "services_count": s["services_count"],
            "primary_language": s["primary_language"],
            "yaml_preview": s["yaml"][:300] + "...",
        }
        for s in SAMPLE_REPOSITORIES.values()
    ]

