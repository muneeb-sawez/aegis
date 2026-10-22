"""AEGIS Service Endpoints Registration & Management Routes.

Per-project service endpoint registration:
- Fields: name, health_url, optional admin_url, optional secret.
- Every URL is strictly verified by the SSRF check before registration (rejects cloud metadata, link-local, dangerous schemes).
- Secrets are encrypted at rest with PBKDF2-HMAC-SHA256 authenticated encryption or read from env.
- Plaintext secrets are NEVER returned by any API route or public schema.
- Mutating routes require a valid per-project API key (401 otherwise).
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.auth.dependencies import require_api_key
from backend.auth.store import ProjectRecord
from backend.security.endpoints import (
    ServiceEndpointPublic,
    get_endpoint_registry,
)
from backend.security.ssrf import validate_url_ssrf

router = APIRouter(prefix="/api", tags=["service-endpoints"])


class RegisterServiceEndpointRequest(BaseModel):
    name: str = Field(..., description="Service identifier (e.g. paymentservice)")
    health_url: str = Field(..., description="SSRF-protected HTTP/HTTPS health probe endpoint")
    admin_url: Optional[str] = Field(None, description="Optional SSRF-protected actuator admin endpoint")
    secret: Optional[str] = Field(None, description="Optional admin HMAC secret (encrypted at rest; never returned)")
    project_id: Optional[str] = Field(None, description="Target project ID (defaults to authenticated project)")


# ── Registration (Mutating Route: Requires API Key & SSRF Check) ───────────────

@router.post("/endpoints", response_model=ServiceEndpointPublic, status_code=201)
def register_service_endpoint(
    req: RegisterServiceEndpointRequest,
    _auth: ProjectRecord = Depends(require_api_key),
) -> ServiceEndpointPublic:
    """Register or update a service endpoint for a project.

    Every URL is run through the SSRF check.
    Secrets are stored encrypted and are NEVER returned in the API response.
    """
    target_pid = req.project_id or _auth.project_id
    if _auth.name != "Admin Master" and req.project_id and req.project_id != _auth.project_id:
        raise HTTPException(
            status_code=401,
            detail=f"Unauthorized: API key does not grant access to project '{req.project_id}'",
        )

    registry = get_endpoint_registry()
    try:
        # validate_url_ssrf is executed inside register_endpoint for both health_url and admin_url
        record = registry.register_endpoint(
            name=req.name,
            health_url=req.health_url,
            admin_url=req.admin_url,
            secret=req.secret,
            project_id=target_pid,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"SSRF / Validation Failed: {e}")

    # Return public view without secret
    pub = registry.get_endpoint(target_pid, record.name)
    if not pub:
        raise HTTPException(status_code=500, detail="Failed to retrieve registered endpoint")
    return pub


@router.post("/projects/{project_id}/endpoints", response_model=ServiceEndpointPublic, status_code=201)
def register_project_service_endpoint(
    project_id: str,
    req: RegisterServiceEndpointRequest,
    _auth: ProjectRecord = Depends(require_api_key),
) -> ServiceEndpointPublic:
    """Register endpoint for a specific project path."""
    req.project_id = project_id
    return register_service_endpoint(req=req, _auth=_auth)


# ── Listing Endpoints (Read-Only: Never Exposes Plaintext Secrets) ─────────────

@router.get("/endpoints", response_model=list[ServiceEndpointPublic])
def list_service_endpoints(project_id: str = Query("demo")) -> list[ServiceEndpointPublic]:
    """List registered service endpoints for a project. Plaintext secrets are never exposed."""
    registry = get_endpoint_registry()
    return registry.list_endpoints(project_id=project_id)


@router.get("/projects/{project_id}/endpoints", response_model=list[ServiceEndpointPublic])
def list_project_endpoints(project_id: str) -> list[ServiceEndpointPublic]:
    """List registered service endpoints for project_id. Plaintext secrets are never exposed."""
    registry = get_endpoint_registry()
    return registry.list_endpoints(project_id=project_id)


@router.get("/endpoints/{service_name}", response_model=ServiceEndpointPublic)
def get_service_endpoint(service_name: str, project_id: str = Query("demo")) -> ServiceEndpointPublic:
    """Retrieve metadata for a single service endpoint. Plaintext secrets are never exposed."""
    registry = get_endpoint_registry()
    ep = registry.get_endpoint(project_id=project_id, name=service_name)
    if not ep:
        raise HTTPException(status_code=404, detail=f"Service endpoint '{service_name}' not found for project '{project_id}'")
    return ep


# ── Deletion (Mutating Route: Requires API Key) ────────────────────────────────

@router.delete("/endpoints/{service_name}")
def delete_service_endpoint(
    service_name: str,
    project_id: Optional[str] = Query(None),
    _auth: ProjectRecord = Depends(require_api_key),
) -> dict[str, str]:
    """Unregister a service endpoint."""
    target_pid = project_id or _auth.project_id
    if _auth.name != "Admin Master" and project_id and project_id != _auth.project_id:
        raise HTTPException(status_code=401, detail="Unauthorized: Cross-tenant endpoint deletion refused")

    registry = get_endpoint_registry()
    success = registry.delete_endpoint(project_id=target_pid, name=service_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Service endpoint '{service_name}' not found")
    return {"status": "ok", "message": f"Endpoint '{service_name}' unregistered from project '{target_pid}'"}
