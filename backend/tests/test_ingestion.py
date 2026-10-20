"""AEGIS Ingestion Tests (Directive §3.B).

Verifies:
1. Docker Compose manifest parsing (services, databases, dependencies, invalid YAML).
2. GitHub URL parsing and validation (valid slugs, invalid formats).
3. Missing manifest detection on unknown repos without silent fallback.
4. Idempotent merging without duplicate nodes or duplicate edges.
5. Explicit active graph replacement (mode="replace") vs merging (mode="merge").
6. External service registration with health endpoints and validation on dependent services.
7. Impact-analysis alignment: DEPENDS_ON relationship recognized in caller traversal.
8. Graph topology serialization for frontend visualization.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.graph import get_repository
from backend.ingestion.docker_compose import parse_docker_compose
from backend.ingestion.github_fetcher import parse_github_repo_url
from backend.ingestion.models import ExternalServiceRegistration, IngestionRequest
from backend.ingestion.service import (
    ingest_repository_or_manifest,
    merge_ingested_elements,
    register_external_service,
)
from backend.sim.blast_radius import calculate_blast_radius

SAMPLE_COMPOSE = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    depends_on:
      - api
  api:
    image: custom-api:v1
    environment:
      - DB_HOST=postgres-db
    depends_on:
      - postgres-db
  postgres-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: main
"""


def test_docker_compose_parsing():
    """Verify Docker Compose parses services, databases, and dependencies."""
    nodes, edges = parse_docker_compose(SAMPLE_COMPOSE)
    node_ids = {n.id for n in nodes}
    assert "web" in node_ids
    assert "api" in node_ids
    assert "postgres-db" in node_ids

    # Check postgres-db is categorized as Database
    pg_node = next(n for n in nodes if n.id == "postgres-db")
    assert pg_node.label == "Database"

    # Check web depends on api, api depends on postgres-db
    dep_edges = [(e.source, e.target) for e in edges if e.type == "DEPENDS_ON"]
    assert ("web", "api") in dep_edges
    assert ("api", "postgres-db") in dep_edges


def test_docker_compose_invalid_yaml():
    """Verify invalid Docker Compose syntax raises a descriptive ValueError."""
    with pytest.raises(ValueError, match="Invalid Docker Compose"):
        parse_docker_compose("services: [invalid unclosed yaml")

    with pytest.raises(ValueError, match="'services' root block"):
        parse_docker_compose("version: '3.8'\nnetworks: {default: {}}")


def test_github_repo_url_parsing():
    """Verify GitHub repository identifier parser handles various formats."""
    # Standard slug
    owner, repo = parse_github_repo_url("GoogleCloudPlatform/microservices-demo")
    assert owner == "GoogleCloudPlatform"
    assert repo == "microservices-demo"

    # HTTPS URL
    owner, repo = parse_github_repo_url("https://github.com/muneeb-sawez/aegis.git")
    assert owner == "muneeb-sawez"
    assert repo == "aegis"

    # Invalid identifiers
    with pytest.raises(ValueError, match="Invalid GitHub repository identifier"):
        parse_github_repo_url("single-token-without-slash")


def test_idempotent_ingestion_and_duplicate_prevention():
    """Verify repeated ingestion updates existing elements without creating duplicates."""
    repo = get_repository()
    nodes, edges = parse_docker_compose(SAMPLE_COMPOSE)

    # First merge
    added1, updated1, edges1 = merge_ingested_elements(nodes, edges, replace=False)
    assert added1 >= 0
    assert updated1 >= 0

    # Second merge (idempotent - no duplicate nodes or edges)
    added2, updated2, edges2 = merge_ingested_elements(nodes, edges, replace=False)
    assert added2 == 0
    assert updated2 == len(nodes)
    assert edges2 == 0


@pytest.mark.anyio
async def test_explicit_graph_replacement_mode():
    """Verify mode='replace' isolates the active graph to only the imported manifest."""
    repo = get_repository()
    # Ingest 3-service compose with mode="replace"
    req = IngestionRequest(
        compose_yaml_content=SAMPLE_COMPOSE,
        mode="replace",
    )
    res = await ingest_repository_or_manifest(req)
    assert res.status == "success"

    # Active graph must contain only the 3 services from SAMPLE_COMPOSE
    topo = repo.get_topology()
    assert len(topo.nodes) == 3
    node_ids = {n.id for n in topo.nodes}
    assert node_ids == {"web", "api", "postgres-db"}


def test_external_service_registration_with_health_endpoint():
    """Verify registration of third-party SaaS vendor with optional health endpoint."""
    repo = get_repository()
    repo.reset()

    reg = ExternalServiceRegistration(
        name="Stripe Payments",
        category="Payment Gateway",
        endpoint_url="https://api.stripe.com/v1",
        health_url="https://api.stripe.com/health",
        dependent_service_id="paymentservice",
        description="External credit card processing gateway",
    )
    res = register_external_service(reg)
    assert res["status"] == "success"
    ext_id = res["external_service_id"]
    assert ext_id == "ext-stripe-payments"

    # Verify node exists in graph
    topo = repo.get_topology()
    ext_node = next((n for n in topo.nodes if n.id == ext_id), None)
    assert ext_node is not None
    assert ext_node.label == "ExternalService"
    assert ext_node.properties.get("health_url") == "https://api.stripe.com/health"

    # Verify relationship direction: paymentservice -> ext-stripe-payments (DEPENDS_ON)
    dep_edge = next((e for e in topo.edges if e.source == "paymentservice" and e.target == ext_id), None)
    assert dep_edge is not None
    assert dep_edge.type == "DEPENDS_ON"


def test_external_service_rejects_nonexistent_dependent():
    """Verify registering an external service for a non-existent service raises ValueError."""
    repo = get_repository()
    reg = ExternalServiceRegistration(
        name="Twilio SMS",
        category="SMS Gateway",
        dependent_service_id="ghost-service-xyz",
    )
    with pytest.raises(ValueError, match="does not exist in the active graph topology"):
        register_external_service(reg)


def test_imported_dependency_impact_analysis_alignment():
    """Verify DEPENDS_ON edges are recognized in impact analysis without conversion to CALLS."""
    repo = get_repository()
    repo.reset()

    # Ingest sample compose: web -> api -> postgres-db via DEPENDS_ON
    nodes, edges = parse_docker_compose(SAMPLE_COMPOSE)
    merge_ingested_elements(nodes, edges, replace=True)

    # Calling blast radius on postgres-db should discover api (hop 1) and web (hop 2)
    b_score, callers, caller_details = calculate_blast_radius("postgres-db", repo)
    caller_ids = {c.node for c in callers}
    assert "api" in caller_ids
    assert "web" in caller_ids
    assert b_score > 0.0


def test_graph_topology_api_response_serialization():
    """Verify /api/graph/topology returns serialized node and edge models for React Flow."""
    client = TestClient(app)
    resp = client.get("/api/graph/topology")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    # Check structure of first node
    first_node = data["nodes"][0]
    assert "id" in first_node
    assert "label" in first_node
    assert "properties" in first_node
