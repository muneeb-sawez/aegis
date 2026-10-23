"""Tests for AEGIS Graph AI Copilot & Memory (Topology Screen Assistant)."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.graph import get_repository
from backend.graph.mutator import get_graph_mutator
from backend.agent.chat_memory import get_chat_memory

client = TestClient(app)


def test_graph_mutator_operations():
    mutator = get_graph_mutator()
    pid = "test_copilot_mutations"

    # Add node
    node = mutator.add_node(pid, "user-service", "Service", {"technology": "Go", "port": 8080})
    assert node.id == "user-service"
    assert node.properties["technology"] == "Go"

    # Update node
    updated = mutator.update_node(pid, "user-service", properties={"port": 9090})
    assert updated.properties["port"] == 9090

    # Add edge
    edge = mutator.add_edge(pid, "user-service", "user-db", "DEPENDS_ON")
    assert edge.source == "user-service"
    assert edge.target == "user-db"
    assert edge.type == "DEPENDS_ON"

    # Rewire edge
    reconnected = mutator.update_edge(pid, "user-service", "user-db", new_target="cluster-db")
    assert reconnected.target == "cluster-db"

    # Delete edge
    deleted_edge = mutator.delete_edge(pid, "user-service", "cluster-db")
    assert deleted_edge is True

    # Delete node
    deleted_node = mutator.delete_node(pid, "user-service")
    assert deleted_node is True


def test_chat_memory_and_anaphora():
    mem = get_chat_memory()
    pid = "mem_test_project"
    sid = "session_1"

    mem.clear(pid, sid)
    mem.add_user_message(pid, sid, "Create a cache node named session-cache")
    mem.record_node_creation(pid, sid, "session-cache", "Database", {"technology": "Redis"})

    entities = mem.get_session_entities(pid, sid)
    assert entities["last_referenced_node"] == "session-cache"
    assert len(entities["created_nodes"]) == 1
    assert entities["created_nodes"][0]["id"] == "session-cache"

    history = mem.get_history(pid, sid)
    assert len(history) == 1
    assert history[0].role == "user"


def test_copilot_api_explanation():
    resp = client.post(
        "/api/graph/chat",
        json={
            "project_id": "demo",
            "session_id": "test_sess",
            "message": "Explain what microservices are present in this repo",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 20
    assert data["total_nodes"] > 0
    assert "nodes" in data


def test_copilot_api_node_creation_and_memory():
    sid = "sess_create_and_connect"

    # 1. Ask copilot to create a node
    resp1 = client.post(
        "/api/graph/chat",
        json={
            "project_id": "demo",
            "session_id": sid,
            "message": "Add a new service called telemetry-collector with Python",
        },
    )
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert any(a.get("action") == "CREATE_NODE" or a.get("action_type") == "CREATE_NODE" for a in (d1["executed_actions"] + d1["actions"]))

    # 2. Check history endpoint
    h_resp = client.get(f"/api/graph/chat/history?project_id=demo&session_id={sid}")
    assert h_resp.status_code == 200
    h_data = h_resp.json()
    assert h_data["entities"]["last_referenced_node"] == "telemetry-collector"

    # 3. Follow up using anaphora ("connect it to paymentservice")
    resp2 = client.post(
        "/api/graph/chat",
        json={
            "project_id": "demo",
            "session_id": sid,
            "message": "Connect paymentservice to it",
        },
    )
    assert resp2.status_code == 200
    d2 = resp2.json()
    # Check that paymentservice -> telemetry-collector was created
    created_edges = [
        e for e in d2["edges"]
        if e.get("source") == "paymentservice" and e.get("target") == "telemetry-collector"
    ]
    assert len(created_edges) >= 1
