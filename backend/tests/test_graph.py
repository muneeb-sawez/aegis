"""AEGIS Graph Layer Tests (M1 & M2).

Verifies:
1. Schema & topology constraints: exactly 54 nodes, 142 edges.
2. CALLS edge direction: caller -> callee.
3. Upstream caller traversal: backward BFS along CALLS with 0.75 attenuation.
4. Idempotent loading and reset.
5. Incident additions and queries.
"""

import pytest
from backend.graph.networkx_repo import NetworkXGraphRepository
from backend.graph.seed import generate_topology_data, validate_topology


def test_topology_validation_and_counts():
    """Verify that seed generation produces exactly 54 nodes and 142 edges."""
    data = generate_topology_data()
    valid, msg = validate_topology(data)
    assert valid is True, msg
    assert len(data["nodes"]) == 54
    assert len(data["edges"]) == 142


def test_graph_repository_initialization():
    """Verify repository loads topology and matches contracts."""
    repo = NetworkXGraphRepository()
    topo = repo.get_topology()
    assert len(topo.nodes) == 54
    assert len(topo.edges) == 142

    # Check node categories
    services = [n for n in topo.nodes if n.label == "Service"]
    databases = [n for n in topo.nodes if n.label == "Database"]
    pods = [n for n in topo.nodes if n.label == "Pod"]
    endpoints = [n for n in topo.nodes if n.label == "APIEndpoint"]

    assert len(services) == 8
    assert len(databases) == 6
    assert len(pods) == 16
    assert len(endpoints) == 24


def test_edge_direction_and_callers():
    """Critical Rule: CALLS points caller -> callee.

    repo.callers() must walk BACKWARDS to find upstream callers.
    """
    repo = NetworkXGraphRepository()

    # paymentservice is called by checkoutservice and orderservice directly (hop 1)
    # and called by frontend indirectly (hop 2 via checkoutservice)
    callers = repo.callers("paymentservice", depth=3)
    caller_nodes = {c.node for c in callers}

    assert "checkoutservice" in caller_nodes
    assert "orderservice" in caller_nodes
    assert "frontend" in caller_nodes

    # Check hop attenuation: hop 1 = 1.0, hop 2 = 0.75
    chk_caller = next(c for c in callers if c.node == "checkoutservice")
    assert chk_caller.hops == 1
    assert chk_caller.impact_weight == 1.0

    fe_caller = next(c for c in callers if c.node == "frontend")
    assert fe_caller.hops == 2
    assert fe_caller.impact_weight == 0.75

    # frontend has no upstream callers
    fe_callers = repo.callers("frontend", depth=3)
    service_callers = [c for c in fe_callers if not c.node.startswith("frontend-pod")]
    assert len(service_callers) == 0


def test_neighbors_subgraph():
    """Verify k-hop neighborhood retrieval."""
    repo = NetworkXGraphRepository()
    subgraph = repo.neighbors("paymentservice", hops=1)
    sub_node_ids = {n.id for n in subgraph.nodes}

    assert "paymentservice" in sub_node_ids
    assert "postgres-payment" in sub_node_ids
    assert "checkoutservice" in sub_node_ids


def test_incident_addition_and_reset():
    """Verify incident write-back and clean reset."""
    repo = NetworkXGraphRepository()
    assert len(repo.incidents("paymentservice")) == 0

    inc = repo.add_incident(
        service_id="paymentservice",
        description="DB connection pool exhaustion during load spike",
        decision_data={"action": "scale_pool", "safety_score": 95},
    )
    assert inc.service_id == "paymentservice"
    assert len(repo.incidents("paymentservice")) == 1

    # Reset must restore baseline
    repo.reset()
    assert len(repo.incidents("paymentservice")) == 0
    topo = repo.get_topology()
    assert len(topo.nodes) == 54
    assert len(topo.edges) == 142
