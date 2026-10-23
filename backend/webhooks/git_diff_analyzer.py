"""AEGIS Git Diff Ingestion — GitHub PR File Diff Fetcher.

Downloads the live unified patch for every changed file in a GitHub Pull Request
using the GitHub REST API. No assumptions about file type, language, or service.

The raw patch text is fed directly into the Cohere Command A reasoning brain
(backend/agent/pr_reasoner.py) for zero-hardcoded analysis.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("aegis.webhooks.git_diff_analyzer")


class FileDiff(BaseModel):
    """Represents a single changed file's metadata and raw unified diff patch."""

    filename: str
    status: str                   # "added" | "modified" | "removed" | "renamed"
    patch: Optional[str] = None   # Raw unified diff — None for binary or empty files
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    previous_filename: Optional[str] = None   # Set on renames


async def fetch_pr_file_diffs(
    owner: str,
    repo: str,
    pr_number: int,
    token: str,
    client: Optional[httpx.AsyncClient] = None,
) -> list[FileDiff]:
    """Fetch the list of changed files and their raw unified diffs for a GitHub PR.

    Calls:
        GET /repos/{owner}/{repo}/pulls/{pr_number}/files

    Returns:
        List of FileDiff — one per changed file in the PR.
        Binary files, submodule changes, and files without a patch are included
        but have patch=None so the downstream brain can skip them gracefully.

    Notes:
        - GitHub returns at most 3000 files per request; this covers all real PRs.
        - The `patch` field contains the raw unified diff text (the '+' and '-' lines)
          that the LLM reasoning stages consume.
    """
    should_close = client is None
    if should_close:
        client = httpx.AsyncClient(timeout=15.0)

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "AEGIS-Risk-Bot/2.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    try:
        resp = await client.get(url, headers=headers, params={"per_page": 100})
        resp.raise_for_status()
        raw_files: list[dict] = resp.json()

        diffs: list[FileDiff] = []
        for f in raw_files:
            if not isinstance(f, dict):
                continue
            diffs.append(
                FileDiff(
                    filename=f.get("filename", ""),
                    status=f.get("status", "modified"),
                    patch=f.get("patch"),         # None for binary files — LLM skips them
                    additions=f.get("additions", 0),
                    deletions=f.get("deletions", 0),
                    changes=f.get("changes", 0),
                    previous_filename=f.get("previous_filename"),
                )
            )

        logger.info(
            "DIFF_FETCHED repo=%r pr=%d files=%d",
            f"{owner}/{repo}", pr_number, len(diffs),
        )
        return diffs

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "DIFF_FETCH_HTTP_ERROR pr=%d status=%d body=%s",
            pr_number, exc.response.status_code, exc.response.text[:200],
        )
        return []
    except Exception as exc:
        logger.warning("DIFF_FETCH_ERROR pr=%d error=%s", pr_number, exc)
        return []
    finally:
        if should_close:
            await client.aclose()


def resolve_github_token_for_project(
    project_id: str,
    repo_full_name: str,
    fallback_token: Optional[str] = None,
) -> Optional[str]:
    """Find the best GitHub OAuth token for a given project and repository.

    Search order:
    1. `data/github_auth.json` — session tokens connected to this project.
    2. `settings.GITHUB_TOKEN` (fallback PAT from .env).

    This ensures AEGIS uses the authenticated user's token when available
    (higher rate limits, access to private repos) and falls back gracefully.
    """
    import json
    from pathlib import Path

    auth_path = Path(__file__).resolve().parent.parent.parent / "data" / "github_auth.json"
    if auth_path.exists():
        try:
            with open(auth_path, "r", encoding="utf-8") as f:
                auth_data = json.load(f)

            sessions = auth_data.get("sessions", {})
            for session in sessions.values():
                token = session.get("github_access_token")
                connected = session.get("connected_projects", [])
                if token and project_id in connected:
                    return token

            # Also check: any session whose user owns the repo
            for session in sessions.values():
                token = session.get("github_access_token")
                user = session.get("user", {})
                username = user.get("username", "")
                if token and repo_full_name.startswith(username + "/"):
                    return token

        except Exception:
            pass

    return fallback_token
