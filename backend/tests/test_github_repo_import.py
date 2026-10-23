"""Tests for GitHub Repository Discovery and Automatic Graph Import."""

import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.auth.store import get_project_store

client = TestClient(app)


def test_list_github_repositories():
    """Verify GET /api/auth/github/repos returns repository list."""
    resp = client.get("/api/auth/github/repos")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Check structure
    first_repo = data[0]
    assert "full_name" in first_repo
    assert "default_branch" in first_repo
    assert "html_url" in first_repo


def test_import_github_repository_builds_graph_and_binds_project():
    """Verify POST /api/projects/{pid}/import-github creates nodes/edges and binds repo."""
    store = get_project_store()
    test_pid = "demo"
    test_key = "aegis-demo-api-key"

    resp = client.post(
        f"/api/projects/{test_pid}/import-github",
        headers={"X-Project-ID": test_pid, "X-API-Key": test_key},
        json={
            "repo_full_name": "shop-sphere/ecommerce-core",
            "branch": "main",
            "mode": "replace",
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "success"
    assert result["nodes_added"] > 0
    assert result["edges_added"] > 0
    assert "paymentservice" in result["services_discovered"]

    # Verify project record was bound to this repo
    record = store.get_project(test_pid)
    assert record is not None
    assert record.repo_full_name == "shop-sphere/ecommerce-core"
    assert record.repo_branch == "main"

    # Verify get_project_by_repo lookup works
    found = store.get_project_by_repo("shop-sphere/ecommerce-core")
    assert found is not None
    assert found.project_id == test_pid


def test_import_online_git_link_builds_graph():
    """Verify importing with a full online Git URL (https://github.com/owner/repo.git)."""
    store = get_project_store()
    test_pid = "demo"
    test_key = "aegis-demo-api-key"

    resp = client.post(
        f"/api/projects/{test_pid}/import-github",
        headers={"X-Project-ID": test_pid, "X-API-Key": test_key},
        json={
            "repo_full_name": "https://github.com/GoogleCloudPlatform/microservices-demo.git",
            "branch": "main",
            "mode": "replace",
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "success"
    assert result["nodes_added"] > 0
    assert result["edges_added"] > 0

    # Verify project record was bound to the normalized repo name
    record = store.get_project(test_pid)
    assert record is not None
    assert record.repo_full_name == "GoogleCloudPlatform/microservices-demo"

