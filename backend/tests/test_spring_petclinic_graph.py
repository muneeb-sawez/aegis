"""AEGIS Spring Petclinic Java Microservices Graph Verification Suite.

Tests:
1. Direct integration of open source Spring Petclinic via GitHub repo link.
2. Complete graph topology verification (Java / Spring Boot microservices, datastores, infra).
3. Edge direction adherence: CALLS points caller -> callee (api-gateway -> business services).
4. DEPENDS_ON edges to config-server and discovery-server (Eureka).
5. Multi-tenant project isolation (demo 54-node baseline intact, Petclinic in dedicated namespace).
6. Risk calculation and blast radius walking backwards on Java microservices.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.auth.store import DEFAULT_DEMO_API_KEY, get_project_store
from backend.graph import get_repository
from backend.sim.blast_radius import calculate_blast_radius
from backend.sim.cycles import detect_cycles


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Ensure clean baseline and stores before each test."""
    repo = get_repository()
    repo.reset("demo")
    repo.reset("spring-petclinic-microservices")
    repo.reset("spring-petclinic")
    yield


def test_integrate_spring_petclinic_via_github_url():
    """Test integrating Spring Petclinic via direct GitHub URL."""
    client = TestClient(app, headers={"X-API-Key": DEFAULT_DEMO_API_KEY})

    payload = {
        "repo_url": "https://github.com/spring-petclinic/spring-petclinic-microservices",
        "branch": "main",
        "mode": "replace",
    }
    resp = client.post("/api/projects/integrate-github", json=payload)
    assert resp.status_code == 201, f"Failed to integrate: {resp.text}"
    data = resp.json()

    assert data["project_id"] == "spring-petclinic-microservices"
    assert data["repo_full_name"] == "spring-petclinic/spring-petclinic-microservices"
    assert data["total_nodes"] >= 10
    assert data["total_edges"] >= 10
    assert "customers-service" in data["services_discovered"]
    assert "visits-service" in data["services_discovered"]
    assert "vets-service" in data["services_discovered"]
    assert "api-gateway" in data["services_discovered"]


def test_spring_petclinic_java_topology_and_attributes():
    """Verify nodes, labels, Java technology attributes, and database classification."""
    client = TestClient(app, headers={"X-API-Key": DEFAULT_DEMO_API_KEY})

    # Integrate repo
    resp = client.post(
        "/api/projects/integrate-github",
        json={"repo_url": "spring-petclinic/spring-petclinic-microservices"},
    )
    assert resp.status_code == 201
    pid = "spring-petclinic-microservices"

    # Query topology for spring-petclinic-microservices
    topo_resp = client.get(f"/api/graph/topology?project_id={pid}")
    assert topo_resp.status_code == 200
    topo = topo_resp.json()

    node_map = {n["id"]: n for n in topo["nodes"]}

    # 1. Verify Java / Spring Boot Microservices
    expected_java_services = [
        "api-gateway",
        "customers-service",
        "visits-service",
        "vets-service",
        "discovery-server",
        "config-server",
        "admin-server",
    ]
    for s_id in expected_java_services:
        assert s_id in node_map, f"Missing expected Java service '{s_id}' in graph"
        props = node_map[s_id].get("properties", {})
        assert props.get("technology") == "Java / Spring Boot" or "spring" in props.get("image", "").lower(), (
            f"Service {s_id} missing Java / Spring Boot technology metadata: {props}"
        )

    # 2. Verify Datastore services labeled as Database
    expected_db_services = ["mysql-customers", "mysql-visits", "mysql-vets"]
    for db_id in expected_db_services:
        assert db_id in node_map, f"Missing expected database node '{db_id}'"
        assert node_map[db_id]["label"] == "Database", f"Expected Database label for {db_id}, got {node_map[db_id]['label']}"


def test_spring_petclinic_edge_directions_and_calls():
    """Verify caller-callee edge directions strictly follow rule 1: CALLS points caller -> callee."""
    client = TestClient(app, headers={"X-API-Key": DEFAULT_DEMO_API_KEY})

    client.post(
        "/api/projects/integrate-github",
        json={"repo_url": "https://github.com/spring-petclinic/spring-petclinic-microservices"},
    )
    pid = "spring-petclinic-microservices"

    repo = get_repository()
    topo = repo.get_topology(project_id=pid)

    calls_edges = [(e.source, e.target) for e in topo.edges if e.type == "CALLS"]
    depends_edges = [(e.source, e.target) for e in topo.edges if e.type == "DEPENDS_ON"]

    # Rule 1: api-gateway routes to customers-service, visits-service, vets-service
    # Direction: api-gateway (caller) -> customers-service (callee)
    assert ("api-gateway", "customers-service") in calls_edges, "api-gateway must call customers-service"
    assert ("api-gateway", "visits-service") in calls_edges, "api-gateway must call visits-service"
    assert ("api-gateway", "vets-service") in calls_edges, "api-gateway must call vets-service"

    # Microservices must depend on config-server and discovery-server
    assert ("customers-service", "config-server") in depends_edges, "customers-service must depend on config-server"
    assert ("customers-service", "discovery-server") in depends_edges, "customers-service must depend on discovery-server"

    # Verify backwards blast radius: callers of customers-service must include api-gateway
    callers = repo.callers("customers-service", depth=1, project_id=pid)
    caller_ids = {c.node for c in callers}
    assert "api-gateway" in caller_ids, f"api-gateway must be found as caller of customers-service, got: {caller_ids}"


def test_spring_petclinic_project_isolation():
    """Verify that Spring Petclinic topology does not overwrite the demo project baseline."""
    client = TestClient(app, headers={"X-API-Key": DEFAULT_DEMO_API_KEY})

    # Integrate into spring-petclinic
    client.post(
        "/api/projects/integrate-github",
        json={"repo_url": "spring-projects/spring-petclinic", "project_id": "petclinic-isolated"},
    )

    repo = get_repository()

    # Demo project must still have baseline 54 nodes and 142 edges
    demo_topo = repo.get_topology(project_id="demo")
    assert len(demo_topo.nodes) == 54, f"Demo project node count altered: {len(demo_topo.nodes)}"
    assert len(demo_topo.edges) == 142, f"Demo project edge count altered: {len(demo_topo.edges)}"

    # Isolated petclinic project must have its distinct microservices
    petclinic_topo = repo.get_topology(project_id="petclinic-isolated")
    assert len(petclinic_topo.nodes) != 54
    node_ids = {n.id for n in petclinic_topo.nodes}
    assert "customers-service" in node_ids
    assert "checkoutservice" not in node_ids  # Boutique service not in Petclinic


def test_blast_radius_and_cycles_on_spring_petclinic():
    """Verify graph algorithms (cycles, blast radius) execute correctly on the Java Petclinic graph."""
    client = TestClient(app, headers={"X-API-Key": DEFAULT_DEMO_API_KEY})

    client.post(
        "/api/projects/integrate-github",
        json={"repo_url": "spring-petclinic"},
    )
    pid = "spring-petclinic-microservices"

    repo = get_repository()

    # 1. Cycle detection (authentic microservice graph should be acyclic)
    cycle_res = detect_cycles(repo=repo, project_id=pid)
    assert not cycle_res.has_cycle
    assert len(cycle_res.cycles_detected) == 0

    # 2. Blast radius calculation on visits-service
    b_score, callers, details = calculate_blast_radius("visits-service", repo=repo, project_id=pid)
    assert b_score >= 0.0
    caller_ids = {c.node for c in callers}
    assert "api-gateway" in caller_ids, f"api-gateway must be in blast radius callers of visits-service: {caller_ids}"
