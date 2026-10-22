"""Tests for AEGIS unified configuration, Neo4j repository, and fallback behavior."""

import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.graph import get_graph_mode, get_repository
from backend.graph.networkx_repo import NetworkXGraphRepository

client = TestClient(app)


def test_config_defaults_and_validation():
    """Verify settings defaults and that NEO4J_PASSWORD is required when GRAPH_BACKEND=neo4j."""
    from backend.config import Settings

    # Default networkx config works without password
    cfg = Settings(GRAPH_BACKEND="networkx")
    assert cfg.GRAPH_BACKEND == "networkx"
    assert cfg.NEO4J_URI == "bolt://localhost:7687"
    assert cfg.NEO4J_USER == "neo4j"
    assert cfg.NEO4J_PASSWORD is None
    assert cfg.ADMIN_SHARED_SECRET is None
    assert cfg.LLM_PROVIDER == "gemini"
    assert cfg.LLM_MODEL == "gemini/gemini-1.5-flash"
    assert cfg.OLLAMA_BASE_URL == "http://localhost:11434"
    assert cfg.PORT == 8000
    assert cfg.HOST == "0.0.0.0"

    # When GRAPH_BACKEND=neo4j, missing password must raise ValueError
    with pytest.raises(ValueError, match="NEO4J_PASSWORD is required"):
        Settings(GRAPH_BACKEND="neo4j", NEO4J_PASSWORD=None)

    # Valid neo4j config with password
    cfg_neo4j = Settings(GRAPH_BACKEND="neo4j", NEO4J_PASSWORD="secret_password")
    assert cfg_neo4j.NEO4J_PASSWORD == "secret_password"


def test_admin_shared_secret_protection():
    """Verify POST /api/reset is protected when ADMIN_SHARED_SECRET is set."""
    from backend.config import settings

    original_secret = settings.ADMIN_SHARED_SECRET
    try:
        settings.ADMIN_SHARED_SECRET = "super_admin_token_123"

        # Request without header must be 401 Unauthorized
        resp_no_header = client.post("/api/reset")
        assert resp_no_header.status_code == 401

        # Request with incorrect header must be 401
        resp_wrong = client.post("/api/reset", headers={"X-Admin-Secret": "wrong_token"})
        assert resp_wrong.status_code == 401

        # Request with correct header must succeed
        resp_valid = client.post("/api/reset", headers={"X-Admin-Secret": "super_admin_token_123"})
        assert resp_valid.status_code == 200
    finally:
        settings.ADMIN_SHARED_SECRET = original_secret


def test_unreachable_neo4j_fallback_to_ephemeral():
    """Verify fallback to NetworkX and ephemeral health mode when Neo4j is unreachable."""
    from backend.config import settings

    original_backend = settings.GRAPH_BACKEND
    original_uri = settings.NEO4J_URI
    original_pwd = settings.NEO4J_PASSWORD

    try:
        # Point to unreachable port
        settings.GRAPH_BACKEND = "neo4j"
        settings.NEO4J_URI = "bolt://127.0.0.1:59999"
        settings.NEO4J_PASSWORD = "test_password"

        # Force refresh of repository singleton
        repo = get_repository(force_refresh=True)

        # Must fall back to NetworkX
        assert isinstance(repo, NetworkXGraphRepository)

        # GET /health must report mode: ephemeral
        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        data = health_resp.json()
        assert data["mode"] == "ephemeral"
    finally:
        settings.GRAPH_BACKEND = original_backend
        settings.NEO4J_URI = original_uri
        settings.NEO4J_PASSWORD = original_pwd
        get_repository(force_refresh=True)
