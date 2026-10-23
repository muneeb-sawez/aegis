"""AEGIS GitHub Authentication & Project Connection API Routes.

Provides:
- OAuth URL generation: GET /api/auth/github/url
- GitHub Authentication & Login Token generation: POST /api/auth/github/authenticate
- Current User Profile: GET /api/auth/github/me
- Project Connection Status: GET /api/auth/github/status
- Connect / Disconnect Project: POST /api/auth/github/connect, POST /api/auth/github/disconnect
"""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.auth.github_service import (
    GitHubAuthError,
    build_github_oauth_url,
    create_mock_github_user,
    exchange_github_oauth_code,
    fetch_github_user_profile,
    fetch_user_repositories,
)
from backend.auth.github_store import (
    GitHubUserProfile,
    LoginTokenResponse,
    ProjectGitHubConnection,
    UserSession,
    get_github_auth_store,
)
from backend.config import settings

logger = logging.getLogger("aegis.api.github_auth")

router = APIRouter(prefix="/api/auth/github", tags=["github-auth"])


class GitHubRepoSummary(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    private: bool = False
    html_url: str
    description: str = ""
    default_branch: str = "main"
    updated_at: str = ""


class GitHubAuthRequest(BaseModel):
    project_id: str = Field("demo", description="Target project to connect with the authenticated GitHub account")
    code: Optional[str] = Field(None, description="GitHub OAuth authorization code from callback")
    token: Optional[str] = Field(None, description="Direct GitHub Personal Access Token or OAuth access token")
    demo_login: bool = Field(False, description="When True, completes instant verified authentication without external cloud call")
    demo_username: Optional[str] = Field(None, description="Optional custom handle when demo_login is enabled")


class GitHubAuthUrlResponse(BaseModel):
    authorize_url: str
    is_oauth_configured: bool
    client_id_configured: bool
    project_id: str
    redirect_uri: Optional[str]


class ProjectConnectionStatusResponse(BaseModel):
    is_connected: bool
    project_id: str
    connection: Optional[ProjectGitHubConnection] = None


class ConnectProjectRequest(BaseModel):
    project_id: str = Field(..., description="Project ID to connect to the currently authenticated user")


class DisconnectProjectRequest(BaseModel):
    project_id: str = Field(..., description="Project ID to disconnect from GitHub")


def extract_login_token(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_login_token: Optional[str] = Header(None, alias="X-Login-Token"),
    token_query: Optional[str] = Query(None, alias="token"),
) -> Optional[str]:
    """Helper to extract login token from headers or query params."""
    if x_login_token and x_login_token.strip():
        return x_login_token.strip()
    if authorization and authorization.strip():
        val = authorization.strip()
        if val.lower().startswith("bearer "):
            return val[7:].strip()
        return val
    if token_query and token_query.strip():
        return token_query.strip()
    return None


@router.get("/url", response_model=GitHubAuthUrlResponse)
def get_github_auth_url(
    project_id: str = Query("demo", description="Project ID to connect after authentication"),
    state: Optional[str] = Query(None, description="Optional OAuth state nonce"),
) -> GitHubAuthUrlResponse:
    """Return the GitHub OAuth2 authorization URL and configuration status."""
    is_configured = bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET)
    auth_url = build_github_oauth_url(project_id=project_id, state=state)

    return GitHubAuthUrlResponse(
        authorize_url=auth_url,
        is_oauth_configured=is_configured,
        client_id_configured=bool(settings.GITHUB_CLIENT_ID),
        project_id=project_id,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
    )


@router.post("/authenticate", response_model=LoginTokenResponse)
async def authenticate_github(req: GitHubAuthRequest) -> LoginTokenResponse:
    """Authenticate with GitHub, connect to the project, and generate a user login token."""
    store = get_github_auth_store()
    user_profile: Optional[GitHubUserProfile] = None

    effective_github_token: Optional[str] = None

    # 1. Demo / Offline Flow
    if req.demo_login or (not req.code and not req.token and settings.DEMO_MODE):
        username = req.demo_username or "muneeb-sawez"
        user_profile = create_mock_github_user(
            username=username,
            name="Muneeb Sawez",
            email=f"{username}@users.noreply.github.com",
        )
        effective_github_token = "demo_login_token"
    # 2. OAuth Code Exchange Flow
    elif req.code:
        try:
            github_token = await exchange_github_oauth_code(req.code)
            effective_github_token = github_token
            user_profile = await fetch_github_user_profile(github_token)
        except GitHubAuthError as exc:
            logger.warning("GitHub OAuth code exchange failed: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            logger.error("Unexpected error during GitHub OAuth exchange: %s", exc)
            raise HTTPException(status_code=502, detail=f"GitHub OAuth gateway communication error: {exc}")
    # 3. Direct Access Token Flow
    elif req.token:
        try:
            effective_github_token = req.token.strip()
            user_profile = await fetch_github_user_profile(req.token)
        except GitHubAuthError as exc:
            logger.warning("GitHub token authentication failed: %s", exc)
            raise HTTPException(status_code=401, detail=str(exc))
        except Exception as exc:
            logger.error("Unexpected error during GitHub profile retrieval: %s", exc)
            raise HTTPException(status_code=502, detail=f"Failed to communicate with GitHub API: {exc}")
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide an OAuth authorization 'code', a direct GitHub 'token', or set 'demo_login': true.",
        )

    # 4. Issue Login Token & Link to Project
    login_resp = store.create_or_update_session(
        user=user_profile,
        project_id=req.project_id,
        github_access_token=effective_github_token,
    )
    return login_resp


@router.get("/repos", response_model=list[GitHubRepoSummary])
async def list_github_repositories(
    token: Optional[str] = Depends(extract_login_token),
) -> list[GitHubRepoSummary]:
    """List GitHub repositories accessible to the current user or demo catalog."""
    store = get_github_auth_store()
    gh_token: Optional[str] = None
    if token:
        session = store.get_session_by_token(token)
        if session and session.github_access_token:
            gh_token = session.github_access_token

    repos_raw = await fetch_user_repositories(access_token=gh_token)
    return [GitHubRepoSummary(**r) for r in repos_raw]


@router.get("/me", response_model=UserSession)
def get_current_user_profile(
    token: Optional[str] = Depends(extract_login_token),
) -> UserSession:
    """Retrieve active GitHub user session and connected projects using login token."""
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing user login token. Provide 'Authorization: Bearer <token>' or 'X-Login-Token' header.",
        )

    store = get_github_auth_store()
    session = store.get_session_by_token(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid, expired, or revoked login token.")

    return session


@router.get("/status", response_model=ProjectConnectionStatusResponse)
def get_project_connection_status(
    project_id: str = Query("demo", description="Project ID to check GitHub connection status for"),
) -> ProjectConnectionStatusResponse:
    """Check whether a project is currently connected to an authenticated GitHub account."""
    store = get_github_auth_store()
    conn = store.get_project_connection(project_id)
    return ProjectConnectionStatusResponse(
        is_connected=conn is not None,
        project_id=project_id,
        connection=conn,
    )


@router.post("/connect", response_model=ProjectGitHubConnection)
def connect_project_to_active_user(
    req: ConnectProjectRequest,
    token: Optional[str] = Depends(extract_login_token),
) -> ProjectGitHubConnection:
    """Connect an existing project to the authenticated GitHub user."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required to connect project to GitHub.")

    store = get_github_auth_store()
    session = store.get_session_by_token(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid login token.")

    conn = store.connect_project(project_id=req.project_id, user=session.user)
    return conn


@router.post("/disconnect")
def disconnect_project_from_github(
    req: DisconnectProjectRequest,
) -> dict[str, Any]:
    """Disconnect a project from its linked GitHub account."""
    store = get_github_auth_store()
    removed = store.disconnect_project(req.project_id)
    return {
        "project_id": req.project_id,
        "disconnected": removed,
        "message": f"Project '{req.project_id}' disconnected from GitHub." if removed else f"Project '{req.project_id}' was not connected.",
    }
