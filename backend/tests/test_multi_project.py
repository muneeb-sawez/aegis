"""AEGIS Multi-Project Isolation Tests (Task 7a).

Verifies:
1. Every node and edge in data/topology.yaml has project_id: demo (seed migration).
2. Pydantic models (Node, Edge, Incident, Outcome) default project_id to 'demo'.
3. Two projects (alpha vs beta) have strict data isolation:
   - Topologies never leak nodes or edges across projects.
   - Callers and blast radius calculations never cross project boundaries.
   - Telemetry alterations in project A never affect project B.
   - Incidents, decisions, and outcomes written to project A are invisible to project B.
   - API endpoints (/graph/topology, /incidents, /chaos/inject, /memory/commit, /predict/analyze)
     strictly isolate project data via project_id query/body parameters.
"""

from pathlib import Path
import pytest
import yaml
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.graph import get_repository
from backend.graph.repository import Edge, Node, Incident, Outcome
from backend.sim.blast_radius import calculate_blast_radius
from backend.sim.risk import PRPayload, assess_change_risk


def test_seed_migration_has_project_id_on_all_nodes_and_edges():
    """Verify data/topology.yaml was properly migrated to include project_id on every node & edge."""
    yaml_path = Path(__file__).resolve().parent.parent.parent / "data" / "topology.yaml"
    assert yaml_path.exists(), f"Seed file {yaml_path} does not exist"

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    assert len(nodes) == 54, f"Expected 54 nodes in seed, got {len(nodes)}"
    assert len(edges) == 142, f"Expected 142 edges in seed, got {len(edges)}"

    # Every node must have project_id == 'demo'
    for n in nodes:
        assert n.get("project_id") == "demo", f"Node {n['id']} missing top-level project_id='demo'"
        assert n.get("properties", {}).get("project_id") == "demo", f"Node {n['id']} properties missing project_id='demo'"

    # Every edge must have project_id == 'demo'
    for e in edges:
        assert e.get("project_id") == "demo", f"Edge {e['source']}->{e['target']} missing top-level project_id='demo'"
        assert e.get("properties", {}).get("project_id") == "demo", f"Edge {e['source']}->{e['target']} properties missing project_id='demo'"


def test_models_default_project_id_to_demo():
    """Verify Pydantic models default project_id to 'demo'."""
    node = Node(id="test-svc", label="Service")
    assert node.project_id == "demo"

    edge = Edge(source="svc-a", target="svc-b", type="CALLS")
    assert edge.project_id == "demo"

    incident = Incident(
        id="inc-9999",
        service_id="paymentservice",
        description="test incident",
        timestamp="2026-10-22T00:00:00Z",
    )
    assert incident.project_id == "demo"

    outcome = Outcome(
        id="out-9999",
        decision_id="dec-9999",
        incident_id="inc-9999",
        service_id="paymentservice",
        fault_type="pool_exhaustion",
        action="scale_pool",
        status="succeeded",
        safety_score=90.0,
        composite_score=90.0,
        timestamp="2026-10-22T00:00:00Z",
    )
    assert outcome.project_id == "demo"


def test_topology_isolation_between_two_projects():
    """Verify modifying or adding nodes in Project Alpha does not affect Project Beta."""
    repo = get_repository()
    repo.reset("project-alpha")
    repo.reset("project-beta")

    # Initial topologies both have 54 nodes and 142 edges
    topo_alpha = repo.get_topology("project-alpha")
    topo_beta = repo.get_topology("project-beta")
    assert len(topo_alpha.nodes) == 54
    assert len(topo_beta.nodes) == 54

    # Add an exclusive node and edge to project-alpha
    if hasattr(repo, "_get_project_graph"):
        g_alpha = repo._get_project_graph("project-alpha")
        g_alpha.add_node("alpha-exclusive-service", label="Service", project_id="project-alpha")
        g_alpha.add_edge("alpha-exclusive-service", "paymentservice", type="CALLS", project_id="project-alpha")

    # Query project-alpha: must include the new node
    alpha_updated = repo.get_topology("project-alpha")
    alpha_node_ids = {n.id for n in alpha_updated.nodes}
    assert "alpha-exclusive-service" in alpha_node_ids
    assert len(alpha_updated.nodes) == 55

    # Query project-beta: must NOT include alpha's exclusive service
    beta_check = repo.get_topology("project-beta")
    beta_node_ids = {n.id for n in beta_check.nodes}
    assert "alpha-exclusive-service" not in beta_node_ids
    assert len(beta_check.nodes) == 54


def test_telemetry_isolation_between_two_projects():
    """Verify altering telemetry in Project Alpha leaves Project Beta completely untouched."""
    repo = get_repository()
    repo.reset("tenant-1")
    repo.reset("tenant-2")

    # Update telemetry in tenant-1
    repo.set_telemetry("paymentservice", {"p99_ms": 7777.0, "status": "degraded"}, project_id="tenant-1")

    # Verify tenant-1 sees degraded telemetry
    sub_1 = repo.neighbors("paymentservice", hops=1, project_id="tenant-1")
    t1_node = next(n for n in sub_1.nodes if n.id == "paymentservice")
    assert t1_node.properties.get("p99_ms") == 7777.0
    assert t1_node.properties.get("status") == "degraded"

    # Verify tenant-2 sees unaffected baseline telemetry
    sub_2 = repo.neighbors("paymentservice", hops=1, project_id="tenant-2")
    t2_node = next(n for n in sub_2.nodes if n.id == "paymentservice")
    assert t2_node.properties.get("p99_ms") != 7777.0
    assert t2_node.properties.get("status") != "degraded"


def test_callers_and_blast_radius_isolation():
    """Verify callers and blast radius never traverse edges from another project."""
    repo = get_repository()
    repo.reset("proj-a")
    repo.reset("proj-b")

    if hasattr(repo, "_get_project_graph"):
        # Add custom caller in proj-a
        g_a = repo._get_project_graph("proj-a")
        g_a.add_node("tenant-a-order-service", label="Service", project_id="proj-a")
        g_a.add_edge("tenant-a-order-service", "checkoutservice", type="CALLS", project_id="proj-a")

    callers_a = repo.callers("checkoutservice", depth=2, project_id="proj-a")
    caller_ids_a = {c.node for c in callers_a}
    assert "tenant-a-order-service" in caller_ids_a

    callers_b = repo.callers("checkoutservice", depth=2, project_id="proj-b")
    caller_ids_b = {c.node for c in callers_b}
    assert "tenant-a-order-service" not in caller_ids_b

    # Blast radius isolation
    score_a, callers_a, _ = calculate_blast_radius("checkoutservice", repo=repo, project_id="proj-a")
    score_b, callers_b, _ = calculate_blast_radius("checkoutservice", repo=repo, project_id="proj-b")
    affected_a = {c.node for c in callers_a}
    affected_b = {c.node for c in callers_b}
    assert "tenant-a-order-service" in affected_a
    assert "tenant-a-order-service" not in affected_b


def test_incidents_and_outcomes_isolation():
    """Verify incidents and outcomes recorded in Project A are completely invisible to Project B."""
    repo = get_repository()
    repo.reset("project-x")
    repo.reset("project-y")

    # Add incident in project-x
    inc_x = repo.add_incident(
        service_id="paymentservice",
        description="Database connection leak in project-x",
        decision_data={"action": "scale_pool", "safety_score": 92.0, "outcome": "success"},
        project_id="project-x",
    )

    # Add outcome in project-x
    out_x = repo.add_outcome(
        decision_id=inc_x.decision_id or "dec-0001",
        incident_id=inc_x.id,
        service_id="paymentservice",
        fault_type="pool_exhaustion",
        action="scale_pool",
        status="succeeded",
        safety_score=92.0,
        composite_score=91.5,
        project_id="project-x",
    )

    # Project-x queries return the created incident and outcome
    x_incidents = repo.incidents(node="paymentservice", project_id="project-x")
    assert any(i.id == inc_x.id for i in x_incidents)
    x_outcomes = repo.get_outcomes(project_id="project-x")
    assert any(o.id == out_x.id for o in x_outcomes)

    # Project-y queries return zero incidents and zero outcomes
    y_incidents = repo.incidents(node="paymentservice", project_id="project-y")
    assert len(y_incidents) == 0, f"Expected 0 incidents in project-y, found {len(y_incidents)}"
    y_outcomes = repo.get_outcomes(project_id="project-y")
    assert len(y_outcomes) == 0, f"Expected 0 outcomes in project-y, found {len(y_outcomes)}"


def test_api_routes_project_isolation():
    """Verify API endpoints enforce multi-tenancy and project isolation."""
    from backend.auth.store import get_project_store, hash_api_key
    from backend.executor.audit import record_decision, DecisionRecord

    store = get_project_store()
    all_projects = store.load_all()
    if "api-tenant-1" not in all_projects:
        _, key1 = store.create_project("api-tenant-1", "API Tenant 1")
    else:
        key1 = "key-tenant-1"
        all_projects["api-tenant-1"].key_hash = hash_api_key(key1)
        store.save_all(all_projects)

    all_projects = store.load_all()
    if "api-tenant-2" not in all_projects:
        _, key2 = store.create_project("api-tenant-2", "API Tenant 2")
    else:
        key2 = "key-tenant-2"
        all_projects["api-tenant-2"].key_hash = hash_api_key(key2)
        store.save_all(all_projects)

    client = TestClient(app)
    t1_headers = {"X-API-Key": key1, "X-Project-ID": "api-tenant-1"}
    t2_headers = {"X-API-Key": key2, "X-Project-ID": "api-tenant-2"}

    # Reset both test projects
    client.post("/api/reset?project_id=api-tenant-1", headers=t1_headers)
    client.post("/api/reset?project_id=api-tenant-2", headers=t2_headers)

    # 1. Inject fault in api-tenant-1 only
    resp = client.post(
        "/api/chaos/inject",
        headers=t1_headers,
        json={
            "fault_id": "pool_exhaustion",
            "target_service": "paymentservice",
            "project_id": "api-tenant-1",
        },
    )
    assert resp.status_code == 200

    # 2. Verify api-tenant-1 topology has degraded telemetry
    t1_resp = client.get("/api/graph/topology?project_id=api-tenant-1")
    assert t1_resp.status_code == 200
    t1_data = t1_resp.json()
    t1_payment = next(n for n in t1_data["nodes"] if n["id"] == "paymentservice")
    assert t1_payment["properties"].get("status") == "degraded"

    # 3. Verify api-tenant-2 topology is clean and unaffected
    t2_resp = client.get("/api/graph/topology?project_id=api-tenant-2")
    assert t2_resp.status_code == 200
    t2_data = t2_resp.json()
    t2_payment = next(n for n in t2_data["nodes"] if n["id"] == "paymentservice")
    assert t2_payment["properties"].get("status") != "degraded"

    # 4. Execute a proposal for api-tenant-1 to restore healthy telemetry
    exec_resp = client.post(
        "/api/actuator/execute",
        headers=t1_headers,
        json={
            "action": "scale_pool",
            "target": "paymentservice",
            "params": {"pool_size": 150},
            "project_id": "api-tenant-1",
        },
    )
    assert exec_resp.status_code == 200

    # Record decision record for api-tenant-1
    record_decision(DecisionRecord(
        incident_id="inc-api-01",
        service_id="paymentservice",
        action="scale_pool",
        fault_type="pool_exhaustion",
        safety_score=92.0,
        recovery_score=95.0,
        composite_score=93.2,
        project_id="api-tenant-1",
        status="succeeded",
        reason="Scale pool remediation applied successfully",
    ))

    # 5. Commit incident to api-tenant-1 only
    commit_resp = client.post(
        "/api/memory/commit",
        headers=t1_headers,
        json={
            "service_id": "paymentservice",
            "incident_description": "Connection pool exhausted under heavy flash sale load",
            "action_taken": "scale_pool",
            "safety_score": 92.0,
            "outcome": "succeeded",
            "project_id": "api-tenant-1",
        },
    )
    assert commit_resp.status_code == 200

    # 6. Check incidents API: api-tenant-1 has 1 incident; api-tenant-2 has 0
    inc_t1 = client.get("/api/incidents?project_id=api-tenant-1")
    assert inc_t1.status_code == 200
    assert len(inc_t1.json()) == 1

    inc_t2 = client.get("/api/incidents?project_id=api-tenant-2")
    assert inc_t2.status_code == 200
    assert len(inc_t2.json()) == 0

    # 7. Check decisions API: api-tenant-1 has >= 1 decision; api-tenant-2 has 0
    dec_t1 = client.get("/api/decisions?project_id=api-tenant-1")
    assert dec_t1.status_code == 200
    assert len(dec_t1.json()) >= 1

    dec_t2 = client.get("/api/decisions?project_id=api-tenant-2")
    assert dec_t2.status_code == 200
    assert len(dec_t2.json()) == 0


def test_predict_risk_isolation_between_two_projects():
    """Verify risk scores calculated for the same PR reflect project-specific incidents."""
    repo = get_repository()
    repo.reset("risk-tenant-clean")
    repo.reset("risk-tenant-with-incident")

    # Add incident in risk-tenant-with-incident only
    repo.add_incident(
        service_id="paymentservice",
        description="Past pool exhaustion",
        decision_data={"action": "scale_pool", "safety_score": 90, "outcome": "success"},
        project_id="risk-tenant-with-incident",
    )

    pr = PRPayload(
        id="pr-142",
        title="Breaking change to payment endpoint",
        target_service="paymentservice",
        endpoints_added=[],
        endpoints_modified=["POST /charge"],
        endpoints_removed=[],
        dependencies_added=[],
        dependencies_removed=[],
    )

    res_clean = assess_change_risk(pr, repo=repo, project_id="risk-tenant-clean")
    res_incident = assess_change_risk(pr, repo=repo, project_id="risk-tenant-with-incident")

    # Risk score in the project with an incident must be higher due to H term (+25 to H => +5 to score)
    assert res_incident.risk_score > res_clean.risk_score
    assert res_incident.breakdown.history_score == 25.0
    assert res_clean.breakdown.history_score == 0.0
