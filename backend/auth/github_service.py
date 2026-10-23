"""AEGIS GitHub OAuth & Profile Service.

Handles interactions with GitHub's OAuth2 endpoints and user profile REST API.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Optional
import httpx

from backend.auth.github_store import GitHubUserProfile
from backend.config import settings

logger = logging.getLogger("aegis.auth.github")

GITHUB_API_BASE = "https://api.github.com"
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"


class GitHubAuthError(ValueError):
    """Raised when GitHub authentication or profile retrieval fails."""


async def fetch_github_user_profile(access_token: str) -> GitHubUserProfile:
    """Fetch authenticated user profile directly from GitHub REST API."""
    clean_token = access_token.strip()
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AEGIS-Autonomous-System/1.0",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{GITHUB_API_BASE}/user", headers=headers)
        if resp.status_code == 401:
            raise GitHubAuthError("Invalid GitHub access token or unauthorized credentials.")
        if resp.status_code != 200:
            raise GitHubAuthError(f"GitHub API returned error HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        
        # Optionally fetch primary email if private
        email = data.get("email")
        if not email:
            try:
                emails_resp = await client.get(f"{GITHUB_API_BASE}/user/emails", headers=headers)
                if emails_resp.status_code == 200:
                    for em in emails_resp.json():
                        if em.get("primary"):
                            email = em.get("email")
                            break
            except Exception as e:
                logger.debug("Failed to fetch private email from GitHub: %s", e)

        return GitHubUserProfile(
            username=data.get("login", "unknown"),
            github_id=str(data.get("id", "0")),
            name=data.get("name") or data.get("login") or "GitHub User",
            email=email,
            avatar_url=data.get("avatar_url"),
            html_url=data.get("html_url"),
            public_repos=data.get("public_repos", 0),
        )


async def exchange_github_oauth_code(code: str) -> str:
    """Exchange OAuth authorization code for GitHub access token."""
    client_id = settings.GITHUB_CLIENT_ID
    client_secret = settings.GITHUB_CLIENT_SECRET

    if not client_id or not client_secret:
        raise GitHubAuthError("GitHub OAuth client credentials (GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET) are not configured.")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code.strip(),
    }
    if settings.GITHUB_REDIRECT_URI:
        payload["redirect_uri"] = settings.GITHUB_REDIRECT_URI

    headers = {
        "Accept": "application/json",
        "User-Agent": "AEGIS-Autonomous-System/1.0",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(GITHUB_OAUTH_TOKEN_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            raise GitHubAuthError(f"GitHub OAuth token exchange failed with HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        error = data.get("error")
        if error:
            desc = data.get("error_description", error)
            raise GitHubAuthError(f"GitHub OAuth error: {desc}")

        access_token = data.get("access_token")
        if not access_token:
            raise GitHubAuthError("GitHub OAuth response did not contain an access_token.")

        return access_token


def build_github_oauth_url(project_id: str, state: Optional[str] = None) -> str:
    """Construct the browser redirect URL to initiate GitHub OAuth flow."""
    client_id = settings.GITHUB_CLIENT_ID or "placeholder_client_id"
    redirect_uri = settings.GITHUB_REDIRECT_URI or "http://localhost:5173/"
    
    state_payload = state or f"project:{project_id}"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user,user:email,repo",
        "state": state_payload,
    }
    return f"{GITHUB_OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def create_mock_github_user(
    username: str = "muneeb-sawez",
    name: str = "Muneeb Sawez",
    email: str = "muneeb@example.com",
) -> GitHubUserProfile:
    """Create a verified mock profile for offline demonstration and unit testing."""
    return GitHubUserProfile(
        username=username.strip(),
        github_id="998877",
        name=name.strip(),
        email=email.strip(),
        avatar_url=f"https://github.com/{username.strip()}.png",
        html_url=f"https://github.com/{username.strip()}",
        public_repos=15,
    )


DEMO_SAMPLE_REPOSITORIES = [
    {
        "id": 101,
        "name": "microservices-demo",
        "full_name": "GoogleCloudPlatform/microservices-demo",
        "owner": "GoogleCloudPlatform",
        "private": False,
        "html_url": "https://github.com/GoogleCloudPlatform/microservices-demo",
        "description": "Online Boutique: 11-tier cloud-native microservices architecture demo application.",
        "default_branch": "main",
        "updated_at": "2026-10-22T18:30:00Z",
    },
    {
        "id": 102,
        "name": "ecommerce-core",
        "full_name": "shop-sphere/ecommerce-core",
        "owner": "shop-sphere",
        "private": False,
        "html_url": "https://github.com/shop-sphere/ecommerce-core",
        "description": "Enterprise cloud-native e-commerce topology with 11 microservices and external payment gateway.",
        "default_branch": "main",
        "updated_at": "2026-10-21T12:00:00Z",
    },
    {
        "id": 103,
        "name": "ledger-core",
        "full_name": "fintech-nexus/ledger-core",
        "owner": "fintech-nexus",
        "private": True,
        "html_url": "https://github.com/fintech-nexus/ledger-core",
        "description": "High-throughput financial ledger, transaction router, fraud detection, and PostgreSQL audit vault.",
        "default_branch": "main",
        "updated_at": "2026-10-20T09:15:00Z",
    },
    {
        "id": 104,
        "name": "aegis",
        "full_name": "muneeb-sawez/aegis",
        "owner": "muneeb-sawez",
        "private": False,
        "html_url": "https://github.com/muneeb-sawez/aegis",
        "description": "Autonomous Engineering Graph & Intelligence System for distributed microservice architectures.",
        "default_branch": "main",
        "updated_at": "2026-10-22T21:00:00Z",
    },
]


async def fetch_user_repositories(
    access_token: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Fetch repositories from GitHub or return curated demo catalog if offline/demo."""
    token = access_token or settings.GITHUB_TOKEN

    if not token or settings.DEMO_MODE or token.startswith("aegis_mock_") or token.startswith("demo_"):
        return DEMO_SAMPLE_REPOSITORIES

    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AEGIS-Autonomous-System/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/user/repos?sort=updated&per_page=100&affiliation=owner,collaborator,organization_member",
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for r in data:
                    results.append({
                        "id": r.get("id"),
                        "name": r.get("name"),
                        "full_name": r.get("full_name"),
                        "owner": r.get("owner", {}).get("login", "") if isinstance(r.get("owner"), dict) else "",
                        "private": bool(r.get("private")),
                        "html_url": r.get("html_url", ""),
                        "description": r.get("description") or "",
                        "default_branch": r.get("default_branch", "main"),
                        "updated_at": r.get("updated_at", ""),
                    })
                return results
            else:
                logger.warning("GitHub user repos returned status %d. Falling back to demo catalog.", resp.status_code)
                return DEMO_SAMPLE_REPOSITORIES
    except Exception as e:
        logger.warning("Failed to fetch repositories from GitHub (%s). Falling back to demo catalog.", e)
        return DEMO_SAMPLE_REPOSITORIES
