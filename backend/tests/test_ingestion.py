"""AEGIS Ingestion Tests (Directive §3.B).

Verifies:
1. Docker Compose manifest parsing (services, databases, dependencies).
2. Inferred dependencies from environment variables.
3. Idempotent merging without duplicate nodes.
4. Manual external service registration.
"""

import pytest
from backend.graph import get_repository
from backend.ingestion.docker_compose import parse_docker_compose
from backend.ingestion.models import ExternalServiceRegistration
from backend.ingestion.service import merge_ingested_elements, register_external_service

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
    nodes, edges = parse_docker_compose(SAMPLE_COMPOSE)
    node_ids = {n.id for n in nodes}
    assert "web" in node_ids
    assert "api" in node_ids
    assert "postgres-db" in node_ids

    # Check postgres-db is categorized as Database
    pg_node = next(n for n in nodes if n.id == "postgres-db")
    assert pg_node.label == "Database"

    # Check web depends on api
    dep_edges = [(e.source, e.target) for e in edges if e.type == "DEPENDS_ON"]
    assert ("web", "api") in dep_edges
    assert ("api", "postgres-db") in dep_edges


def test_idempotent_ingestion():
    repo = get_repository()
    nodes, edges = parse_docker_compose(SAMPLE_COMPOSE)

    # First merge
    added1, updated1, edges1 = merge_ingested_elements(nodes, edges)
    assert added1 >= 0  # May have been added previously or in clean state
    assert updated1 >= 0

    # Second merge (idempotent - no duplicate nodes or edges)
    added2, updated2, edges2 = merge_ingested_elements(nodes, edges)
    assert added2 == 0
    assert updated2 == len(nodes)
    assert edges2 == 0


def test_external_service_registration():
    repo = get_repository()
    reg = ExternalServiceRegistration(
        name="Stripe Payments",
        category="Payment Gateway",
        endpoint_url="https://api.stripe.com/v1",
        dependent_service_id="paymentservice",
        description="External credit card processing gateway",
    )
    res = register_external_service(reg)
    assert res["status"] == "success"
    ext_id = res["external_service_id"]
    assert ext_id == "ext-stripe-payments"

    # Verify edge exists in graph
    topo = repo.get_topology()
    ext_node = next((n for n in topo.nodes if n.id == ext_id), None)
    assert ext_node is not None
    assert ext_node.label == "ExternalService"

    dep_edge = next((e for e in topo.edges if e.source == "paymentservice" and e.target == ext_id), None)
    assert dep_edge is not None
    assert dep_edge.type == "DEPENDS_ON"


@pytest.mark.anyio
async def test_sample_repos_catalog_and_ingestion():
    from backend.ingestion.models import IngestionRequest
    from backend.ingestion.sample_repos import SAMPLE_REPOSITORIES
    from backend.ingestion.service import ingest_repository_or_manifest

    assert "shop-sphere/ecommerce-core" in SAMPLE_REPOSITORIES
    assert "fintech-nexus/ledger-core" in SAMPLE_REPOSITORIES

    req = IngestionRequest(repo_url="shop-sphere/ecommerce-core")
    result = await ingest_repository_or_manifest(req)
    assert result.status == "success"
    assert "shop-sphere" in result.source
    assert "frontend" in result.services_discovered
    assert "paymentservice" in result.services_discovered

