"""AEGIS GitHub Authentication & User Login Token Store.

Manages GitHub user profiles, project-to-GitHub connections,
and cryptographically secure user login tokens (aegis_usr_*).
"""

from __future__ import annotations

import json
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field

GITHUB_AUTH_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "github_auth.json"


class GitHubUserProfile(BaseModel):
    """Normalized GitHub user profile."""
    username: str = Field(..., description="GitHub login handle, e.g. 'muneeb-sawez'")
    github_id: str = Field(..., description="Numeric or string GitHub account ID")
    name: str = Field("", description="Full display name")
    email: Optional[str] = Field(None, description="Primary email address")
    avatar_url: Optional[str] = Field(None, description="GitHub avatar image URL")
    html_url: Optional[str] = Field(None, description="Public GitHub profile link")
    public_repos: int = Field(0, description="Public repository count")


class UserSession(BaseModel):
    """Authenticated user session with issued login token."""
    login_token: str = Field(..., description="Active login token, e.g. 'aegis_usr_...'")
    user: GitHubUserProfile
    connected_projects: list[str] = Field(default_factory=list, description="Project IDs connected to this account")
    created_at: str
    last_used_at: str
    expires_at: Optional[str] = None
    github_access_token: Optional[str] = Field(None, description="GitHub OAuth or PAT token for API calls")


class ProjectGitHubConnection(BaseModel):
    """Records which GitHub account is linked to an AEGIS project."""
    project_id: str
    github_username: str
    connected_at: str
    user: GitHubUserProfile


class LoginTokenResponse(BaseModel):
    """Returned upon successful GitHub authentication."""
    status: str = "authenticated"
    login_token: str = Field(..., description="Bearer login token generated for this user session")
    token_type: str = "Bearer"
    expires_in_seconds: int = 86400  # 24 hours
    user: GitHubUserProfile
    connected_project_id: Optional[str] = None
    message: str = "GitHub account successfully authenticated. User login token generated."


class GitHubAuthStore:
    """Thread-safe persistent store for GitHub user sessions and project connections."""

    _instance: Optional["GitHubAuthStore"] = None
    _lock = threading.Lock()

    def __init__(self, file_path: Path = GITHUB_AUTH_DATA_PATH) -> None:
        self.file_path = file_path
        self._mutex = threading.Lock()
        self._sessions: dict[str, UserSession] = {}  # token -> session
        self._connections: dict[str, ProjectGitHubConnection] = {}  # project_id -> connection
        self._load()

    def _load(self) -> None:
        """Load sessions and connections from disk."""
        if not self.file_path.exists():
            self._init_defaults()
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            raw_sessions = data.get("sessions", {})
            self._sessions = {
                token: UserSession(**item) for token, item in raw_sessions.items()
            }

            raw_conns = data.get("project_connections", {})
            self._connections = {
                pid: ProjectGitHubConnection(**item) for pid, item in raw_conns.items()
            }
        except Exception:
            self._init_defaults()

    def _init_defaults(self) -> None:
        """Seed default demo connection if no storage exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        demo_user = GitHubUserProfile(
            username="muneeb-sawez",
            github_id="10001",
            name="Muneeb Sawez",
            email="muneeb@example.com",
            avatar_url="https://github.com/muneeb-sawez.png",
            html_url="https://github.com/muneeb-sawez",
            public_repos=12,
        )
        demo_token = "aegis_usr_demo_login_token_88776655"
        now_iso = datetime.now(timezone.utc).isoformat()
        
        demo_session = UserSession(
            login_token=demo_token,
            user=demo_user,
            connected_projects=["demo"],
            created_at=now_iso,
            last_used_at=now_iso,
        )
        self._sessions = {demo_token: demo_session}
        self._connections = {
            "demo": ProjectGitHubConnection(
                project_id="demo",
                github_username=demo_user.username,
                connected_at=now_iso,
                user=demo_user,
            )
        }
        self._save()

    def _save(self) -> None:
        """Serialize data to disk atomically."""
        data = {
            "sessions": {token: s.model_dump() for token, s in self._sessions.items()},
            "project_connections": {pid: c.model_dump() for pid, c in self._connections.items()},
        }
        tmp_path = self.file_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(self.file_path)

    def create_or_update_session(
        self,
        user: GitHubUserProfile,
        project_id: Optional[str] = None,
        github_access_token: Optional[str] = None,
    ) -> LoginTokenResponse:
        """Create or refresh a user session, issue a login token, and link to project."""
        with self._mutex:
            # Check if user already has an active session
            existing_token: Optional[str] = None
            for token, session in self._sessions.items():
                if session.user.username.lower() == user.username.lower():
                    existing_token = token
                    break

            now_iso = datetime.now(timezone.utc).isoformat()
            if existing_token:
                token = existing_token
                session = self._sessions[token]
                session.user = user
                session.last_used_at = now_iso
                if github_access_token:
                    session.github_access_token = github_access_token
                if project_id and project_id not in session.connected_projects:
                    session.connected_projects.append(project_id)
            else:
                token = f"aegis_usr_{secrets.token_hex(20)}"
                connected = [project_id] if project_id else []
                session = UserSession(
                    login_token=token,
                    user=user,
                    connected_projects=connected,
                    created_at=now_iso,
                    last_used_at=now_iso,
                    github_access_token=github_access_token,
                )
                self._sessions[token] = session

            # Connect project if provided
            if project_id:
                self._connections[project_id] = ProjectGitHubConnection(
                    project_id=project_id,
                    github_username=user.username,
                    connected_at=now_iso,
                    user=user,
                )

            self._save()

            return LoginTokenResponse(
                status="authenticated",
                login_token=token,
                token_type="Bearer",
                expires_in_seconds=86400,
                user=user,
                connected_project_id=project_id,
                message=f"GitHub account '@{user.username}' authenticated. Login token issued successfully.",
            )

    def get_session_by_token(self, token: str) -> Optional[UserSession]:
        """Validate and return session for a raw login token."""
        clean_token = token.strip()
        with self._mutex:
            session = self._sessions.get(clean_token)
            if session:
                session.last_used_at = datetime.now(timezone.utc).isoformat()
                self._save()
            return session

    def get_project_connection(self, project_id: str) -> Optional[ProjectGitHubConnection]:
        """Retrieve GitHub connection for a specific project."""
        with self._mutex:
            return self._connections.get(project_id)

    def connect_project(self, project_id: str, user: GitHubUserProfile) -> ProjectGitHubConnection:
        """Explicitly connect a project to a GitHub user profile."""
        with self._mutex:
            now_iso = datetime.now(timezone.utc).isoformat()
            conn = ProjectGitHubConnection(
                project_id=project_id,
                github_username=user.username,
                connected_at=now_iso,
                user=user,
            )
            self._connections[project_id] = conn
            
            # Update user session connected projects list
            for session in self._sessions.values():
                if session.user.username.lower() == user.username.lower():
                    if project_id not in session.connected_projects:
                        session.connected_projects.append(project_id)

            self._save()
            return conn

    def disconnect_project(self, project_id: str) -> bool:
        """Disconnect GitHub connection from a project."""
        with self._mutex:
            if project_id in self._connections:
                conn = self._connections.pop(project_id)
                # Remove from user sessions
                for session in self._sessions.values():
                    if session.user.username.lower() == conn.github_username.lower():
                        if project_id in session.connected_projects:
                            session.connected_projects.remove(project_id)
                self._save()
                return True
            return False

    def list_all_connections(self) -> dict[str, ProjectGitHubConnection]:
        """List all active project-github connections."""
        with self._mutex:
            return dict(self._connections)


def get_github_auth_store() -> GitHubAuthStore:
    """Return singleton instance of GitHubAuthStore."""
    if GitHubAuthStore._instance is None:
        with GitHubAuthStore._lock:
            if GitHubAuthStore._instance is None:
                GitHubAuthStore._instance = GitHubAuthStore()
    return GitHubAuthStore._instance
