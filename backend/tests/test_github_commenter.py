"""Tests for backend/webhooks/github_commenter.py

Verifies:
- Comment formatting with marker and simulated label
- Token handling and skip when no token is configured
- Detection of existing comments via marker
- Creation of new comment when none exists (POST)
- Idempotent update of existing comment (PATCH) preventing duplicate spam
"""

import json
import pytest
import httpx
from backend.webhooks.github_commenter import (
    AEGIS_COMMENT_MARKER,
    format_risk_comment,
    get_existing_comment_id,
    post_or_update_pr_comment,
)


def test_format_risk_comment_contains_required_sections():
    """Verify comment Markdown includes marker, badge, blast radius, and simulated notice."""
    comment = format_risk_comment(
        pr_number=142,
        target_service="paymentservice",
        risk_score=86.4,
        blast_radius=["checkoutservice", "frontend"],
        breaking_changes=["Field 'account_id' removed in PaymentRequest"],
        project_id="demo",
    )

    assert AEGIS_COMMENT_MARKER in comment
    assert "PR #142" in comment
    assert "CRITICAL RISK" in comment
    assert "86.4 / 100" in comment
    assert "`paymentservice`" in comment
    assert "`checkoutservice`" in comment
    assert "account_id" in comment
    assert "Simulated/emulator measurement" in comment


def test_format_risk_comment_low_risk_no_breaking():
    """Verify formatting when risk is low and no breaking changes are present."""
    comment = format_risk_comment(
        pr_number=77,
        target_service="emailservice",
        risk_score=25.0,
        blast_radius=[],
        breaking_changes=[],
        project_id="proj-beta",
    )

    assert "LOW RISK" in comment
    assert "No breaking changes detected" in comment
    assert "*None (leaf service)*" in comment


@pytest.mark.asyncio
async def test_post_comment_skipped_without_token():
    """Verify commenter skips safely when GITHUB_TOKEN is empty."""
    res = await post_or_update_pr_comment(
        owner="test-org",
        repo="test-repo",
        pr_number=142,
        comment_body="test",
        token="",
    )
    assert res["status"] == "skipped"
    assert res["action"] == "skipped_no_token"


@pytest.mark.asyncio
async def test_post_new_comment_when_none_exists():
    """Verify POST request is made when no existing AEGIS comment is found."""
    posted_payloads = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # 1. GET comments query: return empty list
        if request.method == "GET" and "/issues/142/comments" in url_str:
            return httpx.Response(200, json=[])
        # 2. POST new comment
        if request.method == "POST" and "/issues/142/comments" in url_str:
            data = json.loads(request.content.decode("utf-8"))
            posted_payloads.append(data)
            return httpx.Response(
                201,
                json={"id": 99001, "body": data["body"], "html_url": "https://github.com/test/pull/142#c1"},
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    try:
        res = await post_or_update_pr_comment(
            owner="test-org",
            repo="microservices",
            pr_number=142,
            comment_body="<!-- aegis-risk-report -->\nFirst evaluation",
            token="ghp_test_token_123",
            client=client,
        )

        assert res["status"] == "created"
        assert res["action"] == "posted"
        assert res["comment_id"] == 99001
        assert len(posted_payloads) == 1
        assert "First evaluation" in posted_payloads[0]["body"]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_update_existing_comment_instead_of_duplicate():
    """Verify PATCH request updates existing comment instead of creating a second comment."""
    patched_payloads = []
    existing_comment_id = 88200

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        # 1. GET comments query: return existing comment with marker
        if request.method == "GET" and "/issues/142/comments" in url_str:
            return httpx.Response(
                200,
                json=[
                    {"id": 10001, "body": "LGTM from reviewer"},
                    {"id": existing_comment_id, "body": f"{AEGIS_COMMENT_MARKER}\nOld Risk 80.0"},
                ],
            )
        # 2. PATCH existing comment
        if request.method == "PATCH" and f"/issues/comments/{existing_comment_id}" in url_str:
            data = json.loads(request.content.decode("utf-8"))
            patched_payloads.append(data)
            return httpx.Response(
                200,
                json={"id": existing_comment_id, "body": data["body"], "html_url": "https://github.com/test/pull/142#c2"},
            )
        # Should NOT call POST
        if request.method == "POST":
            return httpx.Response(500, json={"error": "Should not post duplicate comment"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    try:
        new_comment_text = f"{AEGIS_COMMENT_MARKER}\nUpdated Risk 86.4 on synchronize"
        res = await post_or_update_pr_comment(
            owner="test-org",
            repo="microservices",
            pr_number=142,
            comment_body=new_comment_text,
            token="ghp_test_token_123",
            client=client,
        )

        assert res["status"] == "updated"
        assert res["action"] == "patched"
        assert res["comment_id"] == existing_comment_id
        assert len(patched_payloads) == 1
        assert "Updated Risk 86.4 on synchronize" in patched_payloads[0]["body"]
    finally:
        await client.aclose()
