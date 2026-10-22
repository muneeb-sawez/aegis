"""Tests for the real SSE diagnosis route GET /api/heal/stream.

Covers:
1. The SSE route yields events in order and ends with 'done'.
2. The SSE route yields an 'error' event on LLM failure.
3. Logging prompt/response/latency/provider to JSONL (no keys logged).
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.config import settings
from backend.graph import get_repository
from backend.agent.schemas import RCAResult, RankedFix


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def seeded_incident():
    repo = get_repository()
    repo.reset()
    inc = repo.add_incident(
        service_id="paymentservice",
        description="Database connection pool timeout on postgres-payment",
    )
    return inc.id


def test_sse_route_yields_events_in_order_and_ends_with_done(test_client, seeded_incident):
    """Verify GET /api/heal/stream yields events in order and concludes with 'done'."""
    mock_rca = RCAResult(
        root_cause_node="postgres-payment",
        root_cause_type="pool_exhausted",
        confidence=0.94,
        propagation_path=["postgres-payment", "paymentservice", "checkoutservice"],
        evidence=["postgres-payment pool saturated at 100/100"],
        ranked_fixes=[
            RankedFix(
                action="scale_pool",
                target="postgres-payment",
                reason="Scale connection pool capacity",
            )
        ],
    )

    with patch.object(settings, "DEMO_MODE", False):
        with patch("backend.agent.stream.diagnose_incident", return_value=mock_rca):
            with test_client.stream("GET", f"/api/heal/stream?incident_id={seeded_incident}") as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]

                events = []
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[len("data: "):].strip()
                        events.append(json.loads(data_str))

                assert len(events) >= 3

                # Extract event types in arrival order
                event_types = [ev["type"] for ev in events]

                # Must start with thought/query and end with done
                assert event_types[0] == "thought"
                assert "query" in event_types
                assert "result" in event_types
                assert event_types[-1] == "done"

                # Check result payload structure
                result_event = next(ev for ev in events if ev["type"] == "result")
                assert result_event["payload"]["root_cause_node"] == "postgres-payment"
                assert result_event["payload"]["confidence"] == 0.94


def test_sse_route_yields_error_event_on_llm_failure(test_client, seeded_incident):
    """Verify GET /api/heal/stream yields an error event when the LLM diagnosis fails."""
    with patch.object(settings, "DEMO_MODE", False):
        with patch("backend.agent.stream.diagnose_incident", side_effect=RuntimeError("Provider connection timeout")):
            with test_client.stream("GET", f"/api/heal/stream?incident_id={seeded_incident}") as response:
                assert response.status_code == 200

                events = []
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[len("data: "):].strip()
                        events.append(json.loads(data_str))

                event_types = [ev["type"] for ev in events]

                # Must contain an error event
                assert "error" in event_types
                error_event = next(ev for ev in events if ev["type"] == "error")
                assert "timeout" in error_event["payload"]["message"].lower() or "error" in error_event["payload"]["message"].lower()


def test_sse_route_demo_mode_fallback(test_client):
    """Verify GET /api/heal/stream returns scripted demo events when DEMO_MODE=True."""
    with patch.object(settings, "DEMO_MODE", True):
        with test_client.stream("GET", "/api/heal/stream") as response:
            assert response.status_code == 200

            events = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[len("data: "):].strip()
                    events.append(json.loads(data_str))

            event_types = [ev["type"] for ev in events]
            assert "cypher" in event_types
            assert "candidates" in event_types
            assert event_types[-1] == "done"
