"""AEGIS Docker Compose Manifest Parser (Directive §3.B).

Parses docker-compose.yml files into normalized graph nodes and edges.
Distinguishes between declared manifest dependencies and inferred service relationships.
"""

from __future__ import annotations

import re
from typing import Any
import yaml

from backend.ingestion.models import IngestedEdge, IngestedNode

DB_IMAGE_PATTERNS = ["postgres", "mysql", "mariadb", "redis", "mongo", "cassandra", "kafka", "rabbitmq"]


def is_database_service(service_name: str, service_def: dict[str, Any]) -> bool:
    """Heuristic to identify datastores from service name or image."""
    image = str(service_def.get("image", "")).lower()
    name = service_name.lower()
    for db in DB_IMAGE_PATTERNS:
        if db in image or db in name:
            return True
    return False


def parse_docker_compose(yaml_content: str) -> tuple[list[IngestedNode], list[IngestedEdge]]:
    """Parse docker-compose YAML content and return normalized nodes and edges."""
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
    service_names = set(services_dict.keys())

    for s_name, s_def in services_dict.items():
        if not isinstance(s_def, dict):
            s_def = {}

        is_db = is_database_service(s_name, s_def)
        label = "Database" if is_db else "Service"

        ports = s_def.get("ports", [])
        image = s_def.get("image", "custom-build")
        env = s_def.get("environment", {})

        # Build node properties
        node_props = {
            "name": s_name,
            "image": str(image),
            "ports": [str(p) for p in ports] if isinstance(ports, list) else [str(ports)],
            "status": "healthy",
            "baseline_p99_ms": 10.0 if is_db else 35.0,
            "p99_ms": 10.0 if is_db else 35.0,
            "error_rate": 0.001,
        }

        nodes.append(
            IngestedNode(
                id=s_name,
                label=label,
                properties=node_props,
                provenance="manifest",
            )
        )

        # 1. Declared manifest dependencies via depends_on
        deps = s_def.get("depends_on", [])
        dep_list: list[str] = []
        if isinstance(deps, list):
            dep_list = [str(d) for d in deps]
        elif isinstance(deps, dict):
            dep_list = list(deps.keys())

        for dep_target in dep_list:
            edges.append(
                IngestedEdge(
                    source=s_name,
                    target=dep_target,
                    type="DEPENDS_ON",
                    properties={"source_field": "depends_on"},
                    provenance="manifest",
                )
            )

        # 2. Inferred dependencies from environment variables (e.g. PAYMENT_SERVICE_HOST=paymentservice)
        if isinstance(env, dict):
            env_items = env.items()
        elif isinstance(env, list):
            env_items = []
            for item in env:
                if isinstance(item, str) and "=" in item:
                    k, v = item.split("=", 1)
                    env_items.append((k, v))
        else:
            env_items = []

        for env_key, env_val in env_items:
            val_str = str(env_val)
            for other_svc in service_names:
                if other_svc != s_name and other_svc in val_str:
                    # Inferred CALLS relationship: s_name calls other_svc
                    # Ensure we don't duplicate if already in depends_on
                    if other_svc not in dep_list:
                        edges.append(
                            IngestedEdge(
                                source=s_name,
                                target=other_svc,
                                type="CALLS",
                                properties={"inferred_from_env": env_key, "protocol": "HTTP/gRPC"},
                                provenance="inferred",
                            )
                        )

    return nodes, edges
