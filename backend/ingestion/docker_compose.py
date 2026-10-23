"""AEGIS Docker Compose Manifest Parser (Directive §3.B).

Parses docker-compose.yml files into normalized graph nodes and edges.
Distinguishes between declared manifest dependencies and inferred service relationships
using universal architectural conventions:
1. Database-Per-Service automated pairing (stem & convention matching).
2. Asynchronous Message Broker / Event Bus topology (AMQP, Kafka, etc.).
3. Strict directional invariants (Datastores never call application services).
4. Gateway boundary routing (only external domain APIs, excluding internal telemetry/infra).
5. Sanitized environment variable network inference.
"""

from __future__ import annotations

import re
from typing import Any
import yaml

from backend.ingestion.models import IngestedEdge, IngestedNode

DB_IMAGE_PATTERNS = [
    "postgres", "postgresql", "mysql", "mariadb", "redis",
    "mongo", "mongodb", "cassandra", "clickhouse", "couchdb",
    "dynamodb", "elasticsearch", "neo4j", "sqlite",
]

BROKER_PATTERNS = [
    "rabbitmq", "kafka", "activemq", "nats", "pulsar", "eventstore",
]

INFRA_EXCLUSIONS = (
    "config", "discovery", "registry", "admin", "prom", "prometheus",
    "grafana", "tracing", "zipkin", "jaeger", "turbine", "monitoring",
    "vault", "kibana",
)

ADDR_ENV_KEYS = (
    "URL", "URI", "HOST", "ADDR", "ENDPOINT", "TARGET",
    "SERVICE", "CONNECT", "BROKER", "SERVER", "DB_", "DATABASE",
)

IGNORED_ENV_KEYS = (
    "INIT_DUMP", "DUMP", "FILE", "SCRIPT", "LOG", "DEBUG", "TAG", "IMAGE", "PROFILE",
)


def is_database_service(service_name: str, service_def: dict[str, Any]) -> bool:
    """Heuristic to identify datastores from service name or image."""
    image = str(service_def.get("image", "")).lower()
    name = service_name.lower()
    for db in DB_IMAGE_PATTERNS:
        if db in image or db in name:
            return True
    return False


def is_broker_service(service_name: str, service_def: dict[str, Any]) -> bool:
    """Heuristic to identify message brokers / event buses from service name or image."""
    image = str(service_def.get("image", "")).lower()
    name = service_name.lower()
    for b in BROKER_PATTERNS:
        if b in image or b in name:
            return True
    return False


def stem_name(name: str) -> str:
    """Extract root domain stem by stripping standard infra/db prefixes and suffixes.
    
    Examples:
      'account-mongodb' -> 'account'
      'account-service' -> 'account'
      'postgres-payment' -> 'payment'
      'paymentservice' -> 'payment'
      'mysql-customers' -> 'customers'
      'customers-service' -> 'customers'
      'redis-cart' -> 'cart'
      'cartservice' -> 'cart'
    """
    clean = name.lower()
    # Strip prefixes like postgres-, mysql-, db-, etc.
    clean = re.sub(r"^(postgres|postgresql|mysql|mariadb|redis|mongo|mongodb|cassandra|db|database)[-_]?", "", clean)
    # Strip suffixes like -mongodb, -service, service, etc.
    clean = re.sub(r"[-_]?(postgres|postgresql|mysql|mariadb|redis|mongo|mongodb|cassandra|db|database|data|service|app|api|backend|svc)$", "", clean)
    return clean


def is_edge_gateway(name: str) -> bool:
    """Identify external edge gateways (excluding internal database or application names like postgres-ledger)."""
    n = name.lower()
    if any(k in n for k in ("gateway", "zuul", "ingress", "traefik", "envoy", "kong", "reverse-proxy")):
        return True
    return bool(re.search(r"(^|[-_])(edge[-_]gateway|edge[-_]router|edge)([-_]|$)", n))


def parse_docker_compose(yaml_content: str, app_name: str | None = None) -> tuple[list[IngestedNode], list[IngestedEdge]]:
    """Parse docker-compose YAML content and return normalized nodes and edges with universal topology reasoning."""
    try:
        data = yaml.safe_load(yaml_content)
    except Exception as e:
        raise ValueError(f"Invalid Docker Compose YAML: {e}")

    if not isinstance(data, dict) or "services" not in data:
        raise ValueError("Docker Compose file must contain a 'services' root block.")

    services_dict = data.get("services", {})
    if not isinstance(services_dict, dict):
        raise ValueError("'services' block must be a dictionary.")

    nodes: list[IngestedNode] = []
    edges: list[IngestedEdge] = []
    existing_edges: set[tuple[str, str]] = set()
    service_names = set(services_dict.keys())

    def add_edge_safe(src: str, tgt: str, etype: str, props: dict[str, Any], prov: str = "inferred") -> None:
        if src != tgt and (src, tgt) not in existing_edges:
            existing_edges.add((src, tgt))
            edges.append(
                IngestedEdge(
                    source=src,
                    target=tgt,
                    type=etype,
                    properties=props,
                    provenance=prov,
                )
            )

    # 1. Build Nodes
    for s_name, s_def in services_dict.items():
        if not isinstance(s_def, dict):
            s_def = {}

        is_db = is_database_service(s_name, s_def)
        is_broker = is_broker_service(s_name, s_def)
        label = "Database" if is_db else "Service"

        ports = s_def.get("ports", [])
        image = s_def.get("image", "custom-build")

        node_props = {
            "name": s_name,
            "image": str(image),
            "ports": [str(p) for p in ports] if isinstance(ports, list) else [str(ports)],
            "status": "healthy",
            "baseline_p99_ms": 10.0 if (is_db or is_broker) else 35.0,
            "p99_ms": 10.0 if (is_db or is_broker) else 35.0,
            "error_rate": 0.001,
        }

        # Detect tech stack
        img_lower = str(image).lower()
        name_lower = s_name.lower()
        is_java = any(k in img_lower or k in name_lower for k in ("spring", "petclinic", "java", "jvm", "boot"))
        if is_java:
            node_props["technology"] = "Java / Spring Boot"
            node_props["language"] = "Java"
            node_props["framework"] = "Spring Cloud"

        nodes.append(
            IngestedNode(
                id=s_name,
                label=label,
                properties=node_props,
                provenance="manifest",
            )
        )

        # 2. Declared manifest dependencies via depends_on
        deps = s_def.get("depends_on", [])
        dep_list: list[str] = []
        if isinstance(deps, list):
            dep_list = [str(d) for d in deps]
        elif isinstance(deps, dict):
            dep_list = list(deps.keys())

        for dep_target in dep_list:
            if dep_target in service_names:
                add_edge_safe(
                    src=s_name,
                    tgt=dep_target,
                    etype="DEPENDS_ON",
                    props={"source_field": "depends_on"},
                    prov="manifest",
                )

        # 3. Environment Variable Inference (Sanitized)
        # Invariant: Databases NEVER initiate outbound CALLS
        if not is_db:
            env = s_def.get("environment", {})
            if isinstance(env, dict):
                env_items = list(env.items())
            elif isinstance(env, list):
                env_items = []
                for item in env:
                    if isinstance(item, str) and "=" in item:
                        k, v = item.split("=", 1)
                        env_items.append((k, v))
            else:
                env_items = []

            for env_key, env_val in env_items:
                k_upper = str(env_key).upper()
                if any(ign in k_upper for ign in IGNORED_ENV_KEYS):
                    continue

                v_str = str(env_val)
                is_addr_key = any(ak in k_upper for ak in ADDR_ENV_KEYS)
                has_net_syntax = any(proto in v_str for proto in ("http://", "https://", "grpc://", "amqp://", ":"))

                if is_addr_key or has_net_syntax:
                    for other_svc in service_names:
                        if other_svc != s_name and other_svc in v_str:
                            add_edge_safe(
                                src=s_name,
                                tgt=other_svc,
                                etype="CALLS",
                                props={"inferred_from_env": env_key, "protocol": "HTTP/gRPC"},
                                prov="inferred",
                            )

    # 4. Universal Database-Per-Service Pairing
    db_services = {s: s_def for s, s_def in services_dict.items() if is_database_service(s, s_def)}
    app_services = {
        s: s_def for s, s_def in services_dict.items()
        if not is_database_service(s, s_def) and not is_broker_service(s, s_def) and not any(inf in s.lower() for inf in INFRA_EXCLUSIONS)
    }

    for db_name, db_def in db_services.items():
        db_stem = stem_name(db_name)
        for app_name in app_services:
            app_stem = stem_name(app_name)
            if db_stem == app_stem and db_stem:
                add_edge_safe(
                    src=app_name,
                    tgt=db_name,
                    etype="CALLS",
                    props={"protocol": "Database Driver", "relationship": "datastore", "inferred_by": "naming_convention"},
                    prov="inferred",
                )

    # 5. Universal Message Broker / Event Bus Topology
    brokers = [s for s, s_def in services_dict.items() if is_broker_service(s, s_def)]
    for b in brokers:
        for app_name, app_def in app_services.items():
            if any(sfx in app_name.lower() for sfx in ("service", "app", "backend", "core", "worker", "processor", "consumer", "producer")):
                add_edge_safe(
                    src=app_name,
                    tgt=b,
                    etype="CALLS",
                    props={"protocol": "AMQP/Kafka", "relationship": "event_broker", "inferred_by": "event_bus_pattern"},
                    prov="inferred",
                )

    # 6. Universal Gateway Boundary Routing
    # Gateways only route public traffic to external-facing domain services, never internal telemetry/infra
    for s_name in service_names:
        if is_database_service(s_name, services_dict.get(s_name, {})) or is_broker_service(s_name, services_dict.get(s_name, {})):
            continue
        if is_edge_gateway(s_name):
            for target in app_services:
                if target != s_name and not any(inf in target.lower() for inf in INFRA_EXCLUSIONS):
                    add_edge_safe(
                        src=s_name,
                        tgt=target,
                        etype="CALLS",
                        props={"protocol": "HTTP/REST", "inferred_route": f"/api/{target}"},
                        prov="inferred",
                    )

    # 7. Internal Observability & Telemetry Stream Linking
    for s_name in service_names:
        if any(mon in s_name.lower() for mon in ("monitor", "monitoring", "grafana", "dashboard")):
            for t in service_names:
                if t != s_name and any(agg in t.lower() for agg in ("turbine", "prom", "prometheus", "zipkin", "jaeger")):
                    add_edge_safe(
                        src=s_name,
                        tgt=t,
                        etype="CALLS",
                        props={"protocol": "Stream/HTTP", "relationship": "telemetry_stream", "inferred_by": "observability_pattern"},
                        prov="inferred",
                    )

    # 8. Monolith Host Application Reasoning
    # When a repository's docker-compose only defines auxiliary datastores (e.g. mysql, postgres),
    # the repository itself is the host application service that communicates with them.
    app_nodes = [n for n in nodes if n.label != "Database" and not is_broker_service(n.id, services_dict.get(n.id, {}))]
    if not app_nodes and nodes:
        host_app_id = (app_name or "application").lower().replace("_", "-")
        host_title = (app_name or "Application").replace("-", " ").replace("_", " ").title()
        nodes.append(
            IngestedNode(
                id=host_app_id,
                label="Service",
                properties={
                    "name": f"{host_title} Service",
                    "status": "healthy",
                    "baseline_p99_ms": 35.0,
                    "p99_ms": 35.0,
                    "error_rate": 0.001,
                    "technology": "Application Service",
                    "is_host_application": True,
                },
                provenance="inferred",
            )
        )
        for db_node in [n for n in nodes if n.id != host_app_id]:
            add_edge_safe(
                src=host_app_id,
                tgt=db_node.id,
                etype="CALLS",
                props={"protocol": "Database Driver", "relationship": "datastore", "inferred_by": "monolith_host_pattern"},
                prov="inferred",
            )

    return nodes, edges
