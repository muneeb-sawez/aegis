"""Tests for AEGIS GitHub Webhook Ingestion, HMAC Verification & Idempotency.

Verifies:
1. POST /webhooks/github rejects missing or invalid X-Hub-Signature-256 with 401.
2. Valid HMAC-SHA256 signature verified with hmac.compare_digest returns 200 quickly.
3. Webhook deliveries are idempotent: redelivery with same X-GitHub-Delivery returns 200 duplicate status.
4. Scans ONLY changed files from PR/push payloads, ignoring docs and unrelated files.
5. Handles ping, push, and pull_request events.
"""

import json
import uuid
import pytest
import httpx
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.config import settings
from backend.webhooks.processor import extract_changed_files, map_files_to_services, process_github_event
from backend.webhooks.store import get_delivery_store
from backend.webhooks.verify import compute_github_signature

client = TestClient(app)
WEBHOOK_SECRET = settings.GITHUB_WEBHOOK_SECRET


def test_webhook_bad_signature_401():
    """Verify webhook rejects requests with missing or invalid X-Hub-Signature-256."""
    payload = {"zen": "Keep it logically awesome."}
    raw_body = json.dumps(payload).encode("utf-8")

    # 1. Missing signature header
    resp = client.post(
        "/webhooks/github",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-GitHub-Event": "ping"},
    )
    assert resp.status_code == 401
    assert "Invalid or missing X-Hub-Signature-256" in resp.json()["detail"]

    # 2. Forged signature
    resp = client.post(
        "/webhooks/github",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
        },
    )
    assert resp.status_code == 401
    assert "Invalid or missing X-Hub-Signature-256" in resp.json()["detail"]

    # 3. Signature for different payload (tampered body)
    wrong_sig = compute_github_signature(b'{"different": "body"}', WEBHOOK_SECRET)
    resp = client.post(
        "/webhooks/github",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": wrong_sig,
        },
    )
    assert resp.status_code == 401


def test_webhook_valid_ping_200_quick():
    """Verify valid signature returns 200 quickly."""
    delivery_id = f"del-{uuid.uuid4().hex[:12]}"
    payload = {"zen": "Non-blocking graph resilience.", "hook_id": 12345}
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_github_signature(raw_body, WEBHOOK_SECRET)

    resp = client.post(
        "/webhooks/github",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": delivery_id,
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["delivery_id"] == delivery_id
    assert data["redelivery"] is False


def test_webhook_idempotency_and_redelivery():
    """Verify sending the same X-GitHub-Delivery twice returns 200 duplicate status without duplicate work."""
    delivery_id = f"del-{uuid.uuid4().hex[:12]}"
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 142,
            "title": "Update payment schema",
            "changed_files_list": ["services/paymentservice/proto/payment.proto"],
        },
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_github_signature(raw_body, WEBHOOK_SECRET)
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": delivery_id,
        "X-Hub-Signature-256": sig,
    }

    # First delivery: accepted
    resp1 = client.post("/webhooks/github", content=raw_body, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "accepted"
    assert data1["redelivery"] is False

    # Second delivery (GitHub redelivery with same GUID): idempotent skip
    resp2 = client.post("/webhooks/github", content=raw_body, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "duplicate"
    assert data2["redelivery"] is True
    assert "idempotent skip" in data2["message"]


def test_scan_only_changed_files_extraction():
    """Verify only changed files are extracted and non-functional docs are filtered out."""
    # 1. Pull request with mixed changes
    pr_payload = {
        "action": "synchronize",
        "pull_request": {
            "number": 55,
            "title": "Multi-file commit",
            "changed_files_list": [
                "README.md",
                "docs/architecture.png",
                "services/paymentservice/handler.py",
                "services/checkoutservice/client.go",
                "notes.txt",
            ],
        },
    }

    changed = extract_changed_files(pr_payload, "pull_request")
    assert len(changed) == 5
    assert "services/paymentservice/handler.py" in changed

    known = {"paymentservice", "checkoutservice", "frontend"}
    mapped = map_files_to_services(changed, known)

    # Docs and images must be filtered out
    assert "README.md" not in str(mapped)
    assert "docs/architecture.png" not in str(mapped)
    assert "notes.txt" not in str(mapped)

    # Functional code must be mapped to specific services
    assert "paymentservice" in mapped
    assert "checkoutservice" in mapped
    assert mapped["paymentservice"] == ["services/paymentservice/handler.py"]
    assert mapped["checkoutservice"] == ["services/checkoutservice/client.go"]


@pytest.mark.asyncio
async def test_processor_idempotent_writes():
    """Verify background processor assesses risk and performs idempotent graph writes."""
    delivery_id = f"proc-del-{uuid.uuid4().hex[:8]}"
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 142,
            "title": "PR 142 Breaking Change",
            "changed_files_list": ["services/paymentservice/payment.proto"],
        },
        "repository": {"full_name": "company/microservices"},
    }

    result1 = await process_github_event("pull_request", payload, delivery_id=delivery_id, project_id="demo")
    assert result1["status"] == "completed"
    assert result1["pr_id"] == "PR-142"
    assert result1["target_service"] == "paymentservice"
    assert result1["risk_score"] > 0
    assert result1["changed_files"] == ["services/paymentservice/payment.proto"]

    # Re-running the processor for the same event produces identical idempotent outcome
    result2 = await process_github_event("pull_request", payload, delivery_id=delivery_id, project_id="demo")
    assert result2["risk_score"] == result1["risk_score"]
    assert result2["idempotent_key"] == result1["idempotent_key"]


def test_push_event_changed_files_and_api_alias():
    """Verify push event extracts commits diff and works on /api/webhooks/github alias."""
    delivery_id = f"del-push-{uuid.uuid4().hex[:8]}"
    push_payload = {
        "ref": "refs/heads/main",
        "commits": [
            {
                "id": "c1",
                "added": ["services/frontend/server.js"],
                "modified": ["services/paymentservice/db.py"],
                "removed": [],
            },
            {
                "id": "c2",
                "added": [],
                "modified": ["docs/index.md"],
                "removed": ["old_script.sh"],
            },
        ],
    }
    raw_body = json.dumps(push_payload).encode("utf-8")
    sig = compute_github_signature(raw_body, WEBHOOK_SECRET)

    resp = client.post(
        "/api/webhooks/github",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": delivery_id,
            "X-Hub-Signature-256": sig,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
    assert resp.json()["event"] == "push"


@pytest.mark.asyncio
async def test_pull_request_opened_and_synchronize_comments(monkeypatch):
    """Verify PR opened posts a new comment, and PR synchronize patches the existing one."""
    monkeypatch.setattr("backend.config.settings.GITHUB_TOKEN", "ghp_mock_token_for_tests")

    comments_store = []
    call_log = []

    def mock_github_api(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        call_log.append((request.method, url))

        # 1. GET PR comments
        if request.method == "GET" and "/issues/142/comments" in url:
            return httpx.Response(200, json=comments_store)

        # 2. POST comment
        if request.method == "POST" and "/issues/142/comments" in url:
            data = json.loads(request.content.decode("utf-8"))
            new_id = 55001 + len(comments_store)
            comment_obj = {"id": new_id, "body": data["body"], "html_url": f"https://github.com/aegis/repo/pull/142#c{new_id}"}
            comments_store.append(comment_obj)
            return httpx.Response(201, json=comment_obj)

        # 3. PATCH comment
        if request.method == "PATCH" and "/issues/comments/" in url:
            data = json.loads(request.content.decode("utf-8"))
            cid = int(url.split("/issues/comments/")[-1])
            for c in comments_store:
                if c["id"] == cid:
                    c["body"] = data["body"]
                    return httpx.Response(200, json=c)
            return httpx.Response(404)

        return httpx.Response(404)

    client_mock = httpx.AsyncClient(transport=httpx.MockTransport(mock_github_api))

    try:
        # A. Pull Request Opened: Post initial comment
        pr_opened_payload = {
            "action": "opened",
            "pull_request": {
                "number": 142,
                "title": "Add breaking field removal",
                "changed_files_list": ["services/paymentservice/payment.proto"],
            },
            "repository": {
                "name": "boutique-app",
                "full_name": "GoogleCloudPlatform/boutique-app",
                "owner": {"login": "GoogleCloudPlatform"},
            },
        }

        res_opened = await process_github_event(
            event_type="pull_request",
            payload=pr_opened_payload,
            delivery_id="del-pr-open-001",
            project_id="demo",
            github_client=client_mock,
        )

        assert res_opened["status"] == "completed"
        assert res_opened["pr_id"] == "PR-142"
        assert "comment" in res_opened
        assert res_opened["comment"]["action"] == "posted"
        assert res_opened["comment"]["comment_id"] == 55001
        assert len(comments_store) == 1
        assert "<!-- aegis-risk-report -->" in comments_store[0]["body"]

        # B. Pull Request Synchronize (new commit on same PR): Update existing comment instead of duplicate!
        pr_sync_payload = {
            "action": "synchronize",
            "pull_request": {
                "number": 142,
                "title": "Add breaking field removal (v2)",
                "changed_files_list": ["services/paymentservice/payment.proto"],
            },
            "repository": {
                "name": "boutique-app",
                "full_name": "GoogleCloudPlatform/boutique-app",
                "owner": {"login": "GoogleCloudPlatform"},
            },
        }

        res_sync = await process_github_event(
            event_type="pull_request",
            payload=pr_sync_payload,
            delivery_id="del-pr-sync-002",
            project_id="demo",
            github_client=client_mock,
        )

        assert res_sync["status"] == "completed"
        assert "comment" in res_sync
        assert res_sync["comment"]["action"] == "patched"
        assert res_sync["comment"]["comment_id"] == 55001
        # Crucial check: still only 1 comment in store (no duplicates created!)
        assert len(comments_store) == 1

        # Verify no second POST was issued
        post_calls = [c for c in call_log if c[0] == "POST"]
        patch_calls = [c for c in call_log if c[0] == "PATCH"]
        assert len(post_calls) == 1
        assert len(patch_calls) == 1
    finally:
        await client_mock.aclose()

