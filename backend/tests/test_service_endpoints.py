"""Tests for AEGIS Per-Project Service Endpoint Registration, SSRF Defense, and Secret Encryption.

Verifies:
1. Endpoints can be registered per project (name, health_url, optional admin_url + secret).
2. Every URL is validated through the SSRF check (rejects metadata IPs, link-local, bad schemes, credentials).
3. Secrets are read from env or encrypted store.
4. Secrets are NEVER returned in any API response or public model.
5. Mutating routes require a valid per-project API key (401 otherwise).
6. Multi-tenant endpoint isolation between projects.
"""

import json
import os
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.auth.store import DEFAULT_DEMO_API_KEY, get_project_store
from backend.security.endpoints import ENDPOINTS_FILE_PATH, get_endpoint_registry
from backend.security.ssrf import validate_url_ssrf

client = TestClient(app)
DEMO_HEADERS = {"X-API-Key": DEFAULT_DEMO_API_KEY, "X-Project-ID": "demo"}


def test_ssrf_validator_comprehensive():
    """Verify SSRF validation directly against all attack vectors."""
    # Invalid schemes
    with pytest.raises(ValueError, match="scheme"):
        validate_url_ssrf("ftp://example.com/health")

    with pytest.raises(ValueError, match="scheme"):
        validate_url_ssrf("file:///etc/shadow")

    with pytest.raises(ValueError, match="scheme"):
        validate_url_ssrf("gopher://127.0.0.1:70/test")

    # Embedded credentials
    with pytest.raises(ValueError, match="credentials"):
        validate_url_ssrf("http://admin:supersecret@127.0.0.1:8080/health")

    # Cloud metadata IPs & aliases
    with pytest.raises(ValueError, match="blocked"):
        validate_url_ssrf("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(ValueError, match="blocked"):
        validate_url_ssrf("http://metadata.google.internal/computeMetadata/v1")

    with pytest.raises(ValueError, match="blocked"):
        validate_url_ssrf("http://metadata/computeMetadata/v1")

    with pytest.raises(ValueError, match="blocked"):
        validate_url_ssrf("http://100.100.100.200/latest/meta-data/")

    with pytest.raises(ValueError, match="blocked"):
        validate_url_ssrf("http://169.254.170.2/v2/metadata")

    # Link-local IPs
    with pytest.raises(ValueError, match="blocked"):
        validate_url_ssrf("http://169.254.10.20:8000/probe")

    # Safe URLs
    assert validate_url_ssrf("http://127.0.0.1:8000/api/monitor/probe/paymentservice") == "http://127.0.0.1:8000/api/monitor/probe/paymentservice"
    assert validate_url_ssrf("https://api.github.com/health") == "https://api.github.com/health"
    assert validate_url_ssrf("http://paymentservice:8080/health") == "http://paymentservice:8080/health"


def test_register_endpoint_ssrf_rejection():
    """Verify API rejects any registration where health_url or admin_url violates SSRF."""
    # 1. SSRF in health_url
    resp = client.post(
        "/api/endpoints",
        headers=DEMO_HEADERS,
        json={
            "name": "malicious-service",
            "health_url": "http://169.254.169.254/latest/meta-data",
            "admin_url": "http://127.0.0.1:8080/admin",
        },
    )
    assert resp.status_code == 400
    assert "SSRF" in resp.json()["detail"] or "blocked" in resp.json()["detail"]

    # 2. SSRF in admin_url
    resp = client.post(
        "/api/endpoints",
        headers=DEMO_HEADERS,
        json={
            "name": "malicious-service-2",
            "health_url": "http://127.0.0.1:8080/health",
            "admin_url": "http://metadata.google.internal/computeMetadata/v1",
        },
    )
    assert resp.status_code == 400
    assert "SSRF" in resp.json()["detail"] or "blocked" in resp.json()["detail"]

    # 3. Bad scheme in health_url
    resp = client.post(
        "/api/endpoints",
        headers=DEMO_HEADERS,
        json={
            "name": "malicious-service-3",
            "health_url": "ftp://fileserver/health",
        },
    )
    assert resp.status_code == 400
    assert "scheme" in resp.json()["detail"]


def test_register_endpoint_secrets_encrypted_and_never_returned():
    """Verify secrets are encrypted in storage and NEVER returned in API responses."""
    svc_name = f"test-vault-{uuid.uuid4().hex[:6]}"
    raw_secret = "super-secret-hmac-key-9999"

    # Register endpoint with secret
    resp = client.post(
        "/api/endpoints",
        headers=DEMO_HEADERS,
        json={
            "name": svc_name,
            "health_url": "http://127.0.0.1:8000/health",
            "admin_url": "http://127.0.0.1:8000/admin/fix",
            "secret": raw_secret,
            "project_id": "demo",
        },
    )
    assert resp.status_code == 201
    created_data = resp.json()

    # CRITICAL: Assert secret is NOT in API response
    assert "secret" not in created_data
    assert raw_secret not in str(created_data)
    assert created_data["has_secret"] is True
    assert created_data["secret_source"] == "encrypted_store"

    # Check raw disk storage: Secret MUST be encrypted, NOT plaintext
    with open(ENDPOINTS_FILE_PATH, "r", encoding="utf-8") as f:
        disk_content = f.read()
    assert raw_secret not in disk_content
    assert "enc:v1:" in disk_content

    # Query GET /api/endpoints: Secret MUST NOT be present
    list_resp = client.get("/api/endpoints?project_id=demo")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert raw_secret not in str(list_data)
    found = next((s for s in list_data if s["name"] == svc_name), None)
    assert found is not None
    assert "secret" not in found
    assert found["has_secret"] is True

    # Query single endpoint GET /api/endpoints/{service_name}
    single_resp = client.get(f"/api/endpoints/{svc_name}?project_id=demo")
    assert single_resp.status_code == 200
    single_data = single_resp.json()
    assert "secret" not in single_data
    assert raw_secret not in str(single_data)


def test_secret_resolution_env_and_encrypted_store(monkeypatch):
    """Verify secret resolution reads from env var first, falling back to encrypted store."""
    registry = get_endpoint_registry()
    svc_name = f"secret-res-{uuid.uuid4().hex[:6]}"
    stored_secret = "stored-in-encrypted-file"

    registry.register_endpoint(
        name=svc_name,
        health_url="http://127.0.0.1:8000/health",
        secret=stored_secret,
        project_id="demo",
    )

    # 1. Fallback to encrypted store when no env var set
    resolved = registry.get_secret("demo", svc_name)
    assert resolved == stored_secret

    # 2. Override via environment variable
    env_secret = "env-override-secret-xyz"
    clean_svc = svc_name.upper().replace("-", "_")
    monkeypatch.setenv(f"SERVICE_SECRET_{clean_svc}", env_secret)

    resolved_env = registry.get_secret("demo", svc_name)
    assert resolved_env == env_secret

    # Public API reflects secret_source = "env"
    ep = registry.get_endpoint("demo", svc_name)
    assert ep.secret_source == "env"


def test_mutating_endpoints_require_api_key_401():
    """Verify registering or deleting endpoints without API key returns 401."""
    # Registration without key -> 401
    resp = client.post(
        "/api/endpoints",
        json={
            "name": "no-key-svc",
            "health_url": "http://127.0.0.1:8000/health",
        },
    )
    assert resp.status_code == 401

    # Deletion without key -> 401
    resp = client.delete("/api/endpoints/paymentservice")
    assert resp.status_code == 401


def test_per_project_endpoint_isolation():
    """Verify endpoints registered in Project A are completely isolated from Project B."""
    store = get_project_store()
    tenant_a = f"tenant-a-{uuid.uuid4().hex[:6]}"
    tenant_b = f"tenant-b-{uuid.uuid4().hex[:6]}"

    _, key_a = store.create_project(tenant_a, "Tenant A")
    _, key_b = store.create_project(tenant_b, "Tenant B")

    headers_a = {"X-API-Key": key_a, "X-Project-ID": tenant_a}
    headers_b = {"X-API-Key": key_b, "X-Project-ID": tenant_b}

    # Register endpoint for Tenant A
    resp_a = client.post(
        f"/api/projects/{tenant_a}/endpoints",
        headers=headers_a,
        json={
            "name": "orderservice",
            "health_url": "http://127.0.0.1:9001/health",
            "secret": "orders-secret-a",
            "project_id": tenant_a,
        },
    )
    assert resp_a.status_code == 201

    # Tenant B lists endpoints -> orderservice MUST NOT appear in Tenant B
    resp_b_list = client.get(f"/api/projects/{tenant_b}/endpoints")
    assert resp_b_list.status_code == 200
    b_names = [e["name"] for e in resp_b_list.json()]
    assert "orderservice" not in b_names

    # Tenant B cannot delete Tenant A's endpoint
    cross_del = client.delete(
        f"/api/endpoints/orderservice?project_id={tenant_a}",
        headers=headers_b,
    )
    assert cross_del.status_code == 401
