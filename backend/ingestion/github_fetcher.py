"""AEGIS GitHub Repository Fetcher (Directive §3.B).

Fetches manifest files via GitHub REST API without requiring git clone.
Uses optional GITHUB_TOKEN for authenticated quota.
"""

from __future__ import annotations

import base64
import os
import re
from typing import Optional
import httpx

CANDIDATE_COMPOSE_FILES = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yaml",
    "compose.yml",
]


def parse_github_repo_url(url_or_slug: str) -> tuple[str, str]:
    """Extract (owner, repo) from URL or slug like 'GoogleCloudPlatform/microservices-demo'."""
    clean = url_or_slug.strip().rstrip("/")
    if "github.com/" in clean:
        parts = clean.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1].replace(".git", "")
    elif "/" in clean:
        parts = clean.split("/")
        if len(parts) == 2:
            return parts[0], parts[1].replace(".git", "")

    raise ValueError(f"Invalid GitHub repository identifier: '{url_or_slug}'. Expected 'owner/repo' or 'https://github.com/owner/repo'.")


async def fetch_file_content_from_github(
    owner: str,
    repo: str,
    filepath: str,
    branch: str = "main",
    token: Optional[str] = None,
) -> Optional[str]:
    """Fetch raw or base64 file content from GitHub REST API."""
    api_token = token or os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AEGIS-Ingestion-Agent/1.0",
    }
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}?ref={branch}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "content" in data:
                raw_bytes = base64.b64decode(data["content"])
                return raw_bytes.decode("utf-8", errors="replace")
        elif resp.status_code == 404 and branch == "main":
            # Retry with master branch if main was not found
            url_master = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}?ref=master"
            resp_m = await client.get(url_master, headers=headers)
            if resp_m.status_code == 200:
                data = resp_m.json()
                if isinstance(data, dict) and "content" in data:
                    raw_bytes = base64.b64decode(data["content"])
                    return raw_bytes.decode("utf-8", errors="replace")

    return None


async def find_and_fetch_compose_manifest(
    owner: str,
    repo: str,
    branch: str = "main",
) -> tuple[str, str]:
    """Search candidate compose files in repo root and return (filename, content)."""
    for candidate in CANDIDATE_COMPOSE_FILES:
        content = await fetch_file_content_from_github(owner, repo, candidate, branch)
        if content:
            return candidate, content

    raise FileNotFoundError(
        f"No recognized Docker Compose manifest found in {owner}/{repo}. "
        f"Checked: {', '.join(CANDIDATE_COMPOSE_FILES)}."
    )
