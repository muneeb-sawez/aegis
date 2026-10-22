"""AEGIS GitHub Authentication & User Login Token Test Suite."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.auth.github_store import get_github_auth_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_github_auth_store(tmp_path, monkeypatch):
    """Ensure clean isolated store for testing."""
    test_file = tmp_path / "test_github_auth.json"
    store = get_github_auth_store()
    monkeypatch.setattr(store, "file_path", test_file)
    store._sessions.clear()
    store._connections.clear()
    store._init_defaults()
    yield


def test_get_github_oauth_url():
    """Verify GitHub OAuth URL generation endpoint."""
    resp = client.get("/api/auth/github/url?project_id=demo")
    assert resp.status_code == 200
    data = resp.json()
    assert "authorize_url" in data
    assert "github.com/login/oauth/authorize" in data["authorize_url"]
    assert "project_id" in data
    assert data["project_id"] == "demo"


def test_github_auth_demo_generates_login_token():
    """Verify authenticating with GitHub issues a secure user login token and connects project."""
    payload = {
        "project_id": "demo",
        "demo_login": True,
        "demo_username": "octocat-engineer",
    }
    resp = client.post("/api/auth/github/authenticate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "authenticated"
    assert "login_token" in data
    token = data["login_token"]
    assert token.startswith("aegis_usr_")
    assert data["token_type"] == "Bearer"
    assert data["user"]["username"] == "octocat-engineer"
    assert data["connected_project_id"] == "demo"

    # Verify querying /me with issued login token
    me_resp = client.get(
        "/api/auth/github/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["login_token"] == token
    assert me_data["user"]["username"] == "octocat-engineer"
    assert "demo" in me_data["connected_projects"]


def test_github_auth_me_unauthorized_cases():
    """Verify /me rejects missing or invalid tokens."""
    # Missing token
    resp1 = client.get("/api/auth/github/me")
    assert resp1.status_code == 401

    # Invalid token
    resp2 = client.get(
        "/api/auth/github/me",
        headers={"Authorization": "Bearer aegis_usr_invalid_token_999"},
    )
    assert resp2.status_code == 401


def test_project_connection_status_and_disconnect():
    """Verify querying connection status and disconnecting a project."""
    # Authenticate to link project
    auth_resp = client.post(
        "/api/auth/github/authenticate",
        json={"project_id": "test-fleet", "demo_login": True, "demo_username": "dev-lead"},
    )
    assert auth_resp.status_code == 200
    token = auth_resp.json()["login_token"]

    # Check status
    status_resp = client.get("/api/auth/github/status?project_id=test-fleet")
    assert status_resp.status_code == 200
    assert status_resp.json()["is_connected"] is True
    assert status_resp.json()["connection"]["github_username"] == "dev-lead"

    # Connect another project with the same login token
    conn_resp = client.post(
        "/api/auth/github/connect",
        json={"project_id": "second-fleet"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conn_resp.status_code == 200
    assert conn_resp.json()["project_id"] == "second-fleet"

    # Disconnect first project
    disc_resp = client.post(
        "/api/auth/github/disconnect",
        json={"project_id": "test-fleet"},
    )
    assert disc_resp.status_code == 200
    assert disc_resp.json()["disconnected"] is True

    # Verify status is now disconnected
    status_after = client.get("/api/auth/github/status?project_id=test-fleet")
    assert status_after.json()["is_connected"] is False


def test_require_api_key_accepts_github_login_token():
    """Verify generated GitHub login token can authenticate protected mutating API routes."""
    # Authenticate to get a user login token
    auth_resp = client.post(
        "/api/auth/github/authenticate",
        json={"project_id": "demo", "demo_login": True, "demo_username": "sre-commander"},
    )
    token = auth_resp.json()["login_token"]

    # Call protected endpoint /api/monitor/check-now using Bearer <login_token>
    probe_resp = client.post(
        "/api/monitor/check-now",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should be 200 OK (not 401 Unauthorized)
    assert probe_resp.status_code == 200
    results = probe_resp.json()
    assert isinstance(results, list)
    assert len(results) > 0


def test_authenticate_invalid_params():
    """Verify endpoint rejects requests with no code, no token, and demo_login=false."""
    resp = client.post("/api/auth/github/authenticate", json={"project_id": "demo", "demo_login": False})
    assert resp.status_code == 400
