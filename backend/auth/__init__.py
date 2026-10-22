"""AEGIS Authentication & Per-Project API Key Package."""

from backend.auth.store import (
    DEFAULT_DEMO_API_KEY,
    ProjectCreationResponse,
    ProjectPublic,
    ProjectRecord,
    ProjectStore,
    get_project_store,
    hash_api_key,
)
from backend.auth.github_store import (
    GitHubUserProfile,
    LoginTokenResponse,
    ProjectGitHubConnection,
    UserSession,
    get_github_auth_store,
)

__all__ = [
    "DEFAULT_DEMO_API_KEY",
    "ProjectCreationResponse",
    "ProjectPublic",
    "ProjectRecord",
    "ProjectStore",
    "get_project_store",
    "hash_api_key",
    "GitHubUserProfile",
    "LoginTokenResponse",
    "ProjectGitHubConnection",
    "UserSession",
    "get_github_auth_store",
]
