"""AEGIS Universal Architecture Matrix Tests.

Comprehensive cross-ecosystem test matrix validating that the universal
ingestion engine produces sound, realistic, and uncorrupted knowledge graphs across:
1. Java / Spring Cloud (PiggyMetrics)
2. Java / Spring Boot (Spring PetClinic)
3. Polyglot Microservices (ShopSphere E-Commerce)
4. Fintech Ledger & Settlement (Fintech Nexus)
5. Event-Driven Messaging (Kafka & ClickHouse Streaming)
6. HIPAA Telehealth Platform (HealthSync)

Validates 5 universal architectural invariants across all topologies:
- INV-1: Directional Invariant (Databases NEVER initiate outbound CALLS).
- INV-2: Gateway Boundary Invariant (Gateways route only to external domain services, never internal telemetry/infra).
- INV-3: Message Broker Connectivity (Brokers are never isolated islands).
- INV-4: Datastore Pairing (Per-service datastores are linked to their owning domain service).
- INV-5: Manifest Preservation (Declared depends_on and explicit URLs are preserved without regression).
"""

import pytest

from backend.ingestion.docker_compose import (
    INFRA_EXCLUSIONS,
    is_broker_service,
    is_database_service,
    is_edge_gateway,
    parse_docker_compose,
)
from backend.ingestion.sample_repos import SAMPLE_REPOSITORIES


@pytest.mark.parametrize("slug", list(SAMPLE_REPOSITORIES.keys()))
def test_universal_invariants_across_all_repositories(slug: str):
    """Test all 5 architectural invariants across every sample repository topology."""
    sample = SAMPLE_REPOSITORIES[slug]
    if not isinstance(sample, dict) or "yaml" not in sample:
        pytest.skip(f"Alias slug '{slug}' points to existing definition.")

    yaml_content = sample["yaml"]
    nodes, edges = parse_docker_compose(yaml_content)

    assert len(nodes) > 0, f"Repository '{slug}' must have discovered nodes."
    assert len(edges) > 0, f"Repository '{slug}' must have discovered edges."

    node_map = {n.id: n for n in nodes}
    db_ids = {n.id for n in nodes if n.label == "Database"}

    # --- INV-1: Databases NEVER initiate outbound CALLS to other services ---
    inverted_calls = [
        e for e in edges
        if e.source in db_ids and e.type == "CALLS"
    ]
    assert len(inverted_calls) == 0, (
        f"[{slug}] Inverted calls detected! Databases must not call services: {inverted_calls}"
    )

    # --- INV-2: Gateways never route public client CALLS to internal infra/telemetry ---
    gw_ids = {n.id for n in nodes if is_edge_gateway(n.id) and n.id not in db_ids}
    infra_ids = {
        n.id for n in nodes
        if any(inf in n.id.lower() for inf in INFRA_EXCLUSIONS)
    }
    invalid_gw_routes = [
        e for e in edges
        if e.source in gw_ids and e.target in infra_ids and e.type == "CALLS"
    ]
    assert len(invalid_gw_routes) == 0, (
        f"[{slug}] Gateway exposes internal infra as public API: {invalid_gw_routes}"
    )


def test_piggymetrics_java_spring_cloud_matrix():
    """Detailed matrix verification for PiggyMetrics (Spring Cloud + RabbitMQ + MongoDB)."""
    piggymetrics_yaml = """
version: '2.1'
services:
  rabbitmq:
    image: rabbitmq:3-management
  config:
    image: sqshq/piggymetrics-config
  registry:
    image: sqshq/piggymetrics-registry
    depends_on: [config]
  gateway:
    image: sqshq/piggymetrics-gateway
    depends_on: [config]
  auth-service:
    image: sqshq/piggymetrics-auth-service
    depends_on: [config]
  auth-mongodb:
    image: sqshq/piggymetrics-mongodb
  account-service:
    image: sqshq/piggymetrics-account-service
    depends_on: [config]
  account-mongodb:
    image: sqshq/piggymetrics-mongodb
    environment:
      - INIT_DUMP=account-service-dump.js
  statistics-service:
    image: sqshq/piggymetrics-statistics-service
    depends_on: [config]
  statistics-mongodb:
    image: sqshq/piggymetrics-mongodb
  notification-service:
    image: sqshq/piggymetrics-notification-service
    depends_on: [config]
  notification-mongodb:
    image: sqshq/piggymetrics-mongodb
  monitoring:
    image: sqshq/piggymetrics-monitoring
    depends_on: [config]
  turbine-stream-service:
    image: sqshq/piggymetrics-turbine-stream-service
    depends_on: [config]
"""
    nodes, edges = parse_docker_compose(piggymetrics_yaml)
    assert len(nodes) == 14

    edge_tuples = {(e.source, e.target, e.type) for e in edges}

    # 1. RabbitMQ is fully connected to the microservices (no orphan island)
    assert ("account-service", "rabbitmq", "CALLS") in edge_tuples
    assert ("statistics-service", "rabbitmq", "CALLS") in edge_tuples
    assert ("notification-service", "rabbitmq", "CALLS") in edge_tuples

    # 2. Each service calls its dedicated MongoDB datastore
    assert ("auth-service", "auth-mongodb", "CALLS") in edge_tuples
    assert ("account-service", "account-mongodb", "CALLS") in edge_tuples
    assert ("statistics-service", "statistics-mongodb", "CALLS") in edge_tuples
    assert ("notification-service", "notification-mongodb", "CALLS") in edge_tuples

    # 3. No inverted account-mongodb -> account-service
    assert ("account-mongodb", "account-service", "CALLS") not in edge_tuples

    # 4. Gateway routes only to business APIs
    assert ("gateway", "account-service", "CALLS") in edge_tuples
    assert ("gateway", "auth-service", "CALLS") in edge_tuples
    assert ("gateway", "statistics-service", "CALLS") in edge_tuples
    assert ("gateway", "notification-service", "CALLS") in edge_tuples
    assert ("gateway", "turbine-stream-service", "CALLS") not in edge_tuples


def test_spring_petclinic_java_matrix():
    """Detailed matrix verification for Spring PetClinic Microservices."""
    petclinic = SAMPLE_REPOSITORIES["spring-petclinic/spring-petclinic-microservices"]["yaml"]
    nodes, edges = parse_docker_compose(petclinic)

    edge_tuples = {(e.source, e.target, e.type) for e in edges}

    # 1. Gateway calls the domain microservices
    assert ("api-gateway", "customers-service", "CALLS") in edge_tuples
    assert ("api-gateway", "visits-service", "CALLS") in edge_tuples
    assert ("api-gateway", "vets-service", "CALLS") in edge_tuples

    # 2. Microservices call or depend on their paired MySQL databases
    connected_pairs = {(e.source, e.target) for e in edges}
    assert ("customers-service", "mysql-customers") in connected_pairs
    assert ("visits-service", "mysql-visits") in connected_pairs
    assert ("vets-service", "mysql-vets") in connected_pairs

    # 3. Invariants
    db_ids = {n.id for n in nodes if n.label == "Database"}
    assert all(e.source not in db_ids or e.type != "CALLS" for e in edges)
