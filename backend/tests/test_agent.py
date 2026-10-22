"""Tests for AEGIS Agent schemas and context builder.

Covers:
1. Schema rejects an action outside the allowlist.
2. Context includes the 2-hop neighbours (callers, callees, datastores).
3. Context stays under the token cap (~3000 tokens, truncating oldest incidents first).
"""

import pytest
from pydantic import ValidationError

from backend.agent.schemas import RCAResult, RankedFix, AllowlistedAction
from backend.agent.context import build_context, count_tokens, MAX_CONTEXT_TOKENS
from backend.graph import get_repository


def test_schema_valid():
    """Verify that a valid RCAResult with allowlisted actions is accepted."""
    rca = RCAResult(
        root_cause_node="paymentservice",
        root_cause_type="pool_exhaustion",
        confidence=0.92,
        propagation_path=["postgres-payment", "paymentservice", "checkoutservice"],
        evidence=[
            "postgres-payment connections at 100/100 limit",
            "paymentservice latency spiked from 38ms to 3400ms",
        ],
        ranked_fixes=[
            RankedFix(
                action="scale_pool",
                target="postgres-payment",
                reason="Increase max_connections pool to clear queue",
            ),
            RankedFix(
                action="restart",
                target="paymentservice",
                reason="Clear hanging client connection sockets",
            ),
            RankedFix(
                action="rollback",
                target="paymentservice",
                reason="Revert breaking pool configuration update",
            ),
        ],
    )
    assert rca.root_cause_node == "paymentservice"
    assert rca.confidence == 0.92
    assert len(rca.ranked_fixes) == 3
    assert rca.ranked_fixes[0].action == "scale_pool"


def test_schema_rejects_action_outside_allowlist():
    """Verify that schema rejects an action outside the allowlist (e.g. restart, scale_pool, rollback)."""
    # 1. Direct RankedFix validation
    with pytest.raises(ValidationError) as excinfo:
        RankedFix(
            action="drop_database",  # Not in allowlist
            target="postgres-payment",
            reason="Illegal dangerous action",
        )
    assert "Input should be 'restart', 'scale_pool' or 'rollback'" in str(excinfo.value) or "action" in str(excinfo.value)

    # 2. Inside RCAResult validation
    with pytest.raises(ValidationError):
        RCAResult(
            root_cause_node="paymentservice",
            root_cause_type="pool_exhaustion",
            confidence=0.8,
            propagation_path=[],
            evidence=[],
            ranked_fixes=[
                {"action": "reboot_host", "target": "paymentservice", "reason": "Disallowed action"}
            ],
        )


def test_schema_rejects_invalid_confidence():
    """Verify that confidence outside 0.0..1.0 raises ValidationError."""
    with pytest.raises(ValidationError):
        RCAResult(
            root_cause_node="paymentservice",
            root_cause_type="pool_exhaustion",
            confidence=1.5,  # > 1.0
            propagation_path=[],
            evidence=[],
            ranked_fixes=[],
        )

    with pytest.raises(ValidationError):
        RCAResult(
            root_cause_node="paymentservice",
            root_cause_type="pool_exhaustion",
            confidence=-0.1,  # < 0.0
            propagation_path=[],
            evidence=[],
            ranked_fixes=[],
        )


def test_context_includes_2hop_neighbours():
    """Verify context includes failing node, 2-hop neighbourhood (callers, callees, datastores), telemetry, and incidents."""
    repo = get_repository()
    repo.reset()

    # Create an active incident on paymentservice
    inc = repo.add_incident(
        service_id="paymentservice",
        description="Database connection pool exhausted on postgres-payment",
        decision_data={"action": "scale_pool", "safety_score": 95},
    )

    ctx = build_context(inc.id, repo=repo)

    # 1. Failing node
    assert ctx["failing_node"] == "paymentservice"

    # 2. 2-hop neighbourhood
    neighbourhood = ctx["neighbourhood_2hop"]
    node_ids = {n["id"] for n in neighbourhood["nodes"]}
    assert "paymentservice" in node_ids
    # 2-hop neighbours must include datastore postgres-payment and callers checkoutservice
    assert "postgres-payment" in node_ids
    assert "checkoutservice" in node_ids

    # Datastores classified in neighbourhood
    assert "postgres-payment" in neighbourhood["datastores"]

    # Callers includes checkoutservice
    assert any("checkoutservice" in c for c in neighbourhood["callers"])

    # Callees of paymentservice includes postgres-payment
    assert "postgres-payment" in neighbourhood["callees"]

    # 3. Telemetry per node
    assert "paymentservice" in ctx["telemetry"]
    assert "postgres-payment" in ctx["telemetry"]
    assert "p99_ms" in ctx["telemetry"]["paymentservice"] or "status" in ctx["telemetry"]["paymentservice"]

    # 4. Open and past incidents
    assert "open_incidents" in ctx
    assert "past_incidents" in ctx


def test_context_stays_under_cap_with_many_incidents():
    """Verify context stays under the token cap (~3000 tokens) by truncating oldest incidents first."""
    repo = get_repository()
    repo.reset()

    # Create an initial failing incident
    main_inc = repo.add_incident(
        service_id="paymentservice",
        description="Initial active pool exhaustion incident",
    )

    # Inject many historical incidents with large text bodies to exceed token cap
    for i in range(25):
        repo.add_incident(
            service_id="paymentservice",
            description=f"Historical incident #{i}: " + ("High latency connection pool deadlock warning. " * 30),
            decision_data={"action": "restart", "run_id": i},
        )

    # Call build_context with default token cap (~3000)
    ctx = build_context(main_inc.id, repo=repo)

    # Must stay within MAX_CONTEXT_TOKENS (~3000)
    assert ctx["token_count"] <= MAX_CONTEXT_TOKENS
    # Must have capped past incidents to at most 5
    assert len(ctx["past_incidents"]) <= 5

    # Test with a very tight cap (e.g., 800 tokens) to verify oldest incident truncation
    tight_cap = 800
    tight_ctx = build_context(main_inc.id, repo=repo, max_tokens=tight_cap)
    assert tight_ctx["token_count"] <= tight_cap

    # If any incidents remain, verify they are newer than the ones truncated
    if len(tight_ctx["past_incidents"]) > 1:
        timestamps = [inc["timestamp"] for inc in tight_ctx["past_incidents"]]
        # Sorted descending (newest first)
        assert timestamps == sorted(timestamps, reverse=True)
