"""Tests for AEGIS Fallback Resilience.

Verifies:
1. No LLM Key: Automatically and gracefully falls back to deterministic rules engine.
2. Neo4j Down: Automatically falls back to NetworkX in-memory graph repository.
3. Target Unreachable: Actuator safely records failure without hanging or crashing.
"""

import pytest
import os
from unittest.mock import patch

from backend.agent.context import build_context
from backend.agent.rca import diagnose_incident
from backend.agent.schemas import RCAResult
from backend.config import settings
from backend.executor.orchestrator import run_remediation
from backend.graph import get_repository
from backend.graph.networkx_repo import NetworkXGraphRepository


def test_fallback_no_llm_key(monkeypatch):
    """Verify diagnosis falls back cleanly to deterministic rules when no LLM key is configured."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")

    repo = get_repository()
    repo.reset(project_id="demo")

    from backend.api.routes_chaos import inject_fault
    from backend.api.schemas import InjectFaultRequest

    inject_resp = inject_fault(
        InjectFaultRequest(
            fault_id="pool_exhaustion",
            target_service="paymentservice",
            project_id="demo",
        )
    )

    # Add an incident on paymentservice
    inc = repo.add_incident(
        service_id="paymentservice",
        description=inject_resp.message,
        project_id="demo",
    )
    context = build_context(inc.id, repo=repo, project_id="demo")

    # Diagnose incident
    result = diagnose_incident(context)

    # Must return a valid RCAResult instance from fallback rules
    assert isinstance(result, RCAResult)
    assert result.root_cause_node in ("postgres-payment", "paymentservice")
    assert "pool" in result.root_cause_type.lower()
    assert result.confidence > 0.0
    assert len(result.ranked_fixes) > 0


def test_fallback_neo4j_down(monkeypatch):
    """Verify get_repository() gracefully falls back to NetworkX if Neo4j is down or unreachable."""
    monkeypatch.setattr(settings, "GRAPH_BACKEND", "neo4j")
    monkeypatch.setattr(settings, "NEO4J_URI", "bolt://127.0.0.1:9999")  # Unreachable port

    # Force refresh the repository singleton
    repo = get_repository(force_refresh=True)

    # Must fall back to NetworkXGraphRepository
    assert isinstance(repo, NetworkXGraphRepository)

    # Verify standard repository operations still work seamlessly
    topo = repo.get_topology(project_id="demo")
    assert len(topo.nodes) > 0
    assert any(n.id == "paymentservice" for n in topo.nodes)

    # Restore default backend
    monkeypatch.setattr(settings, "GRAPH_BACKEND", "networkx")
    get_repository(force_refresh=True)


@pytest.mark.asyncio
async def test_fallback_target_unreachable(monkeypatch):
    """Verify actuator safely marks status='failed' when target service is unreachable, without hanging."""
    # Point target base URL to unreachable port
    monkeypatch.setenv("ACTUATOR_TARGET_BASE_URL", "http://127.0.0.1:65432")
    monkeypatch.setenv("ACTUATOR_TIMEOUT_SEC", "1.0")

    repo = get_repository()
    repo.reset(project_id="demo")

    inc = repo.add_incident(
        service_id="paymentservice",
        description="Downstream timeout test",
        project_id="demo",
    )

    # Attempt remediation
    dec = await run_remediation(
        incident_id=inc.id,
        service_id="paymentservice",
        action="restart",
        params={},
        fault_type="timeout",
        reason="Test unreachable target fallback",
        reasoning_trace=["Testing network timeout failure mode"],
        project_id="demo",
        override_mode="auto",
    )

    # Must record failed status and structured unreachable result without throwing unhandled exception
    assert dec.status in ("failed", "refused", "rolled_back")
    assert dec.service_id == "paymentservice"
