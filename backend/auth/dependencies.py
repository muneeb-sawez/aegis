"""FastAPI Authentication Dependencies for Per-Project API Keys.

Enforces valid API key verification on all mutating routes.
Validates raw key against SHA-256 hash stored in data/projects.json.
Returns 401 Unauthorized if missing, invalid, or mismatched project tenant.
"""

from __future__ import annotations

import hmac
from typing import Optional
from fastapi import Header, HTTPException, Query, Request

from backend.auth.store import ProjectRecord, get_project_store
from backend.config import settings


def extract_raw_api_key(
    x_api_key: Optional[str] = None,
    authorization: Optional[str] = None,
    api_key_query: Optional[str] = None,
) -> Optional[str]:
    """Extract raw API key from headers or query parameters."""
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()

    if authorization and authorization.strip():
        val = authorization.strip()
        if val.lower().startswith("bearer "):
            return val[7:].strip()
        return val

    if api_key_query and api_key_query.strip():
        return api_key_query.strip()

    return None


async def require_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID"),
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret"),
    api_key: Optional[str] = Query(None, alias="api_key"),
) -> ProjectRecord:
    """Dependency that enforces per-project API key authentication.

    Raises:
        HTTPException(401): If key is missing, invalid, or mismatched to target project.
    """
    target_project = (
        x_project_id
        or request.path_params.get("project_id")
        or request.query_params.get("project_id")
    )

    # 1. Check if admin secret matches (e.g. for reset endpoint with ADMIN_SHARED_SECRET)
    if settings.ADMIN_SHARED_SECRET and x_admin_secret:
        if hmac.compare_digest(x_admin_secret.strip(), settings.ADMIN_SHARED_SECRET.strip()):
            return ProjectRecord(
                project_id=target_project or "demo",
                name="Admin Master",
                description="Authenticated via Admin Shared Secret",
                key_hash="",
                created_at="system",
            )

    # 2. Extract raw API key
    raw_key = extract_raw_api_key(
        x_api_key=x_api_key,
        authorization=authorization,
        api_key_query=api_key,
    )

    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Per-project API key required for mutating routes (provide via 'X-API-Key' header, 'Authorization: Bearer <key>', or '?api_key=')",
        )

    # 3. Determine target project_id if explicitly specified
    if not target_project and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        try:
            body_bytes = await request.body()
            if body_bytes:
                import json
                body_json = json.loads(body_bytes)
                if isinstance(body_json, dict) and "project_id" in body_json and body_json["project_id"]:
                    target_project = str(body_json["project_id"])
        except Exception:
            pass

    # 4. Validate against persistent store (SHA-256 hash comparison)
    store = get_project_store()
    project = store.validate_key(raw_key, project_id=target_project)

    # 4b. Support GitHub User Login Token (aegis_usr_*)
    if not project and raw_key.startswith("aegis_usr_"):
        from backend.auth.github_store import get_github_auth_store
        gh_store = get_github_auth_store()
        session = gh_store.get_session_by_token(raw_key)
        if session:
            effective_project = target_project or "demo"
            if not target_project or effective_project in session.connected_projects or effective_project == "demo":
                return ProjectRecord(
                    project_id=effective_project,
                    name=f"GitHub: {session.user.name or session.user.username}",
                    description=f"Authenticated via GitHub login token for @{session.user.username}",
                    key_hash="",
                    created_at=session.created_at,
                )

    if not project:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid API key or project access denied",
        )

    return project
