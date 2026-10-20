"""AEGIS Topology Generator and Seed Loader (M2).

Generates and validates the canonical 54-node / 142-edge microservice graph
as specified in docs/02-CONTRACTS.md §1:
- 8 Services
- 6 Datastores
- 16 Pods
- 24 APIEndpoints
Total Nodes: 54
Total Edges: 142
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import yaml

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TOPOLOGY_FILE = DATA_DIR / "topology.yaml"


def generate_topology_data() -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # 1. 8 Services
    services_spec = [
        ("frontend", "Frontend Web Gateway", 35.0, 0.002, "presentation"),
        ("checkoutservice", "Checkout Service", 45.0, 0.005, "core"),
        ("orderservice", "Order Processing Service", 50.0, 0.003, "core"),
        ("paymentservice", "Payment Gateway Service", 38.0, 0.001, "critical"),
        ("emailservice", "Email Notification Service", 25.0, 0.001, "utility"),
        ("shippingservice", "Shipping & Fulfillment Service", 40.0, 0.002, "core"),
        ("cartservice", "Shopping Cart Service", 20.0, 0.001, "core"),
        ("recommendationservice", "Product Recommendation Service", 30.0, 0.004, "support"),
    ]

    for sid, sname, p99, err, tier in services_spec:
        nodes.append({
            "id": sid,
            "label": "Service",
            "properties": {
                "name": sname,
                "baseline_p99_ms": p99,
                "p99_ms": p99,
                "error_rate": err,
                "status": "healthy",
                "tier": tier,
            },
        })

    # 2. 6 Datastores
    datastores_spec = [
        ("postgres-payment", "PostgreSQL Payment DB", "postgresql", 5.0, 25, 100),
        ("postgres-order", "PostgreSQL Orders DB", "postgresql", 6.0, 30, 100),
        ("redis-cart", "Redis Cart Cache", "redis", 1.5, 15, 200),
        ("redis-cache", "Redis Product Cache", "redis", 1.2, 12, 200),
        ("mongodb-shipping", "MongoDB Shipping DB", "mongodb", 8.0, 18, 150),
        ("kafka-cluster", "Kafka Event Bus (Demo Node)", "kafka", 10.0, 40, 500),
    ]

    for did, dname, engine, p99, conns, pool in datastores_spec:
        nodes.append({
            "id": did,
            "label": "Database",
            "properties": {
                "name": dname,
                "engine": engine,
                "baseline_p99_ms": p99,
                "p99_ms": p99,
                "connections": conns,
                "pool_size": pool,
                "status": "healthy",
            },
        })

    # 3. 16 Pods (2 per service) & INSTANCE_OF edges (16 edges)
    for sid, _, p99, _, _ in services_spec:
        for pidx in (1, 2):
            pid = f"{sid}-pod-{pidx}"
            nodes.append({
                "id": pid,
                "label": "Pod",
                "properties": {
                    "name": f"{sid} worker instance {pidx}",
                    "service_id": sid,
                    "status": "Running",
                    "cpu_pct": 25.0,
                    "memory_mb": 256.0,
                    "baseline_p99_ms": p99,
                    "p99_ms": p99,
                },
            })
            # Pod -[:INSTANCE_OF]-> Service
            edges.append({
                "source": pid,
                "target": sid,
                "type": "INSTANCE_OF",
                "properties": {"weight": 1.0},
            })

    # 4. 24 APIEndpoints (3 per service) & EXPOSES edges (24 edges)
    ep_names = {
        "frontend": ["get_index", "post_login", "get_cart_view"],
        "checkoutservice": ["place_order", "get_checkout_status", "cancel_checkout"],
        "orderservice": ["create_order", "get_order", "list_orders"],
        "paymentservice": ["charge_card", "refund_card", "verify_token"],
        "emailservice": ["send_order_confirmation", "send_shipping_update", "send_alert"],
        "shippingservice": ["ship_order", "track_package", "calculate_rates"],
        "cartservice": ["get_items", "add_item", "empty_cart"],
        "recommendationservice": ["get_recommendations", "track_impression", "get_trending"],
    }

    for sid, eps in ep_names.items():
        for ep in eps:
            epid = f"{sid}:{ep}"
            nodes.append({
                "id": epid,
                "label": "APIEndpoint",
                "properties": {
                    "name": ep,
                    "service_id": sid,
                    "path": f"/api/v1/{ep.replace('_', '-')}",
                    "method": "POST" if any(w in ep for w in ["create", "charge", "place", "send", "ship", "add", "refund"]) else "GET",
                    "status": "active",
                },
            })
            # Service -[:EXPOSES]-> APIEndpoint
            edges.append({
                "source": sid,
                "target": epid,
                "type": "EXPOSES",
                "properties": {"protocol": "HTTP/2"},
            })

    # Total so far: 16 (INSTANCE_OF) + 24 (EXPOSES) = 40 edges.
    # Target total edges: 142. Remaining: 102 edges.

    # 5. Service DEPENDS_ON Datastore (8 edges)
    service_db_deps = [
        ("paymentservice", "postgres-payment"),
        ("orderservice", "postgres-order"),
        ("cartservice", "redis-cart"),
        ("recommendationservice", "redis-cache"),
        ("shippingservice", "mongodb-shipping"),
        ("checkoutservice", "kafka-cluster"),
        ("orderservice", "kafka-cluster"),
        ("emailservice", "kafka-cluster"),
    ]
    for s_source, d_target in service_db_deps:
        edges.append({
            "source": s_source,
            "target": d_target,
            "type": "DEPENDS_ON",
            "properties": {"pool_limit": 100, "confidence": 1.0},
        })

    # 6. Pod DEPENDS_ON Datastore (16 edges: 2 pods per service with DB dependency)
    for s_source, d_target in service_db_deps:
        for pidx in (1, 2):
            edges.append({
                "source": f"{s_source}-pod-{pidx}",
                "target": d_target,
                "type": "DEPENDS_ON",
                "properties": {"conns_active": 5, "confidence": 1.0},
            })

    # Total so far: 40 + 8 + 16 = 64 edges. Remaining: 78 edges.

    # 7. Service-to-Service CALLS (12 edges)
    # CALLS is ALWAYS caller -> callee.
    service_calls = [
        ("frontend", "checkoutservice", 45.0, "gRPC"),
        ("frontend", "cartservice", 20.0, "gRPC"),
        ("frontend", "recommendationservice", 30.0, "gRPC"),
        ("checkoutservice", "orderservice", 50.0, "gRPC"),
        ("checkoutservice", "paymentservice", 38.0, "gRPC"),
        ("checkoutservice", "shippingservice", 40.0, "gRPC"),
        ("checkoutservice", "emailservice", 25.0, "gRPC"),
        ("checkoutservice", "cartservice", 20.0, "gRPC"),
        ("orderservice", "paymentservice", 38.0, "gRPC"),
        ("orderservice", "shippingservice", 40.0, "gRPC"),
        ("orderservice", "emailservice", 25.0, "gRPC"),
        ("cartservice", "recommendationservice", 30.0, "gRPC"),
    ]
    for src, tgt, lat, proto in service_calls:
        edges.append({
            "source": src,
            "target": tgt,
            "type": "CALLS",
            "properties": {"latency_p99": lat, "protocol": proto, "confidence": 0.98},
        })

    # Total so far: 64 + 12 = 76 edges. Remaining: 66 edges.

    # 8. Pod-to-Service CALLS (24 edges: pods of caller calling the target service)
    # e.g., frontend-pod-1 & pod-2 call checkoutservice, cartservice, recommendationservice (6 edges)
    # checkoutservice pods (2) call orderservice, paymentservice, shippingservice, emailservice (8 edges)
    # orderservice pods (2) call paymentservice, shippingservice, emailservice (6 edges)
    # cartservice pods (2) call recommendationservice (2 edges)
    # frontend pods (2) call orderservice (2 edges)
    pod_svc_calls = [
        ("frontend-pod-1", "checkoutservice"), ("frontend-pod-2", "checkoutservice"),
        ("frontend-pod-1", "cartservice"), ("frontend-pod-2", "cartservice"),
        ("frontend-pod-1", "recommendationservice"), ("frontend-pod-2", "recommendationservice"),
        ("checkoutservice-pod-1", "orderservice"), ("checkoutservice-pod-2", "orderservice"),
        ("checkoutservice-pod-1", "paymentservice"), ("checkoutservice-pod-2", "paymentservice"),
        ("checkoutservice-pod-1", "shippingservice"), ("checkoutservice-pod-2", "shippingservice"),
        ("checkoutservice-pod-1", "emailservice"), ("checkoutservice-pod-2", "emailservice"),
        ("orderservice-pod-1", "paymentservice"), ("orderservice-pod-2", "paymentservice"),
        ("orderservice-pod-1", "shippingservice"), ("orderservice-pod-2", "shippingservice"),
        ("orderservice-pod-1", "emailservice"), ("orderservice-pod-2", "emailservice"),
        ("cartservice-pod-1", "recommendationservice"), ("cartservice-pod-2", "recommendationservice"),
        ("frontend-pod-1", "orderservice"), ("frontend-pod-2", "orderservice"),
    ]
    for src, tgt in pod_svc_calls:
        edges.append({
            "source": src,
            "target": tgt,
            "type": "CALLS",
            "properties": {"latency_p99": 35.0, "protocol": "gRPC", "confidence": 0.95},
        })

    # Total so far: 76 + 24 = 100 edges. Remaining: 42 edges.

    # 9. Service-to-Endpoint CALLS (24 edges: services calling specific API endpoints)
    svc_ep_calls = [
        ("frontend", "checkoutservice:place_order"),
        ("frontend", "checkoutservice:get_checkout_status"),
        ("frontend", "cartservice:get_items"),
        ("frontend", "cartservice:add_item"),
        ("frontend", "recommendationservice:get_recommendations"),
        ("frontend", "recommendationservice:get_trending"),
        ("checkoutservice", "orderservice:create_order"),
        ("checkoutservice", "orderservice:get_order"),
        ("checkoutservice", "paymentservice:charge_card"),
        ("checkoutservice", "paymentservice:verify_token"),
        ("checkoutservice", "shippingservice:ship_order"),
        ("checkoutservice", "shippingservice:calculate_rates"),
        ("checkoutservice", "emailservice:send_order_confirmation"),
        ("checkoutservice", "cartservice:empty_cart"),
        ("orderservice", "paymentservice:charge_card"),
        ("orderservice", "paymentservice:refund_card"),
        ("orderservice", "shippingservice:ship_order"),
        ("orderservice", "shippingservice:track_package"),
        ("orderservice", "emailservice:send_order_confirmation"),
        ("orderservice", "emailservice:send_shipping_update"),
        ("cartservice", "recommendationservice:get_recommendations"),
        ("frontend", "orderservice:list_orders"),
        ("frontend", "shippingservice:track_package"),
        ("emailservice", "orderservice:get_order"),
    ]
    for src, tgt in svc_ep_calls:
        edges.append({
            "source": src,
            "target": tgt,
            "type": "CALLS",
            "properties": {"latency_p99": 35.0, "protocol": "HTTP/2", "confidence": 0.96},
        })

    # Total so far: 100 + 24 = 124 edges. Remaining: 18 edges.

    # 10. Endpoint-to-Endpoint CALLS (18 edges: internal endpoint execution chains)
    ep_ep_calls = [
        ("checkoutservice:place_order", "orderservice:create_order"),
        ("checkoutservice:place_order", "paymentservice:charge_card"),
        ("checkoutservice:place_order", "shippingservice:ship_order"),
        ("checkoutservice:place_order", "emailservice:send_order_confirmation"),
        ("checkoutservice:place_order", "cartservice:empty_cart"),
        ("orderservice:create_order", "paymentservice:charge_card"),
        ("orderservice:create_order", "shippingservice:ship_order"),
        ("orderservice:create_order", "emailservice:send_order_confirmation"),
        ("orderservice:get_order", "shippingservice:track_package"),
        ("frontend:get_cart_view", "cartservice:get_items"),
        ("frontend:get_cart_view", "recommendationservice:get_recommendations"),
        ("frontend:post_login", "cartservice:get_items"),
        ("frontend:get_index", "recommendationservice:get_trending"),
        ("shippingservice:ship_order", "emailservice:send_shipping_update"),
        ("paymentservice:charge_card", "paymentservice:verify_token"),
        ("checkoutservice:cancel_checkout", "paymentservice:refund_card"),
        ("checkoutservice:cancel_checkout", "emailservice:send_alert"),
        ("orderservice:list_orders", "orderservice:get_order"),
    ]
    for src, tgt in ep_ep_calls:
        edges.append({
            "source": src,
            "target": tgt,
            "type": "CALLS",
            "properties": {"latency_p99": 20.0, "protocol": "in-process/gRPC", "confidence": 0.99},
        })

    # Total: 124 + 18 = 142 edges!

    return {"nodes": nodes, "edges": edges}


def validate_topology(data: dict[str, Any]) -> tuple[bool, str]:
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if len(nodes) != 54:
        return False, f"Expected 54 nodes, got {len(nodes)}"
    if len(edges) != 142:
        return False, f"Expected 142 edges, got {len(edges)}"

    node_ids = {n["id"] for n in nodes}
    if len(node_ids) != 54:
        return False, f"Duplicate node IDs detected: {54 - len(node_ids)} duplicates"

    for idx, e in enumerate(edges):
        if e["source"] not in node_ids:
            return False, f"Edge {idx} source '{e['source']}' does not exist in nodes"
        if e["target"] not in node_ids:
            return False, f"Edge {idx} target '{e['target']}' does not exist in nodes"

    return True, "Topology validation passed: exactly 54 nodes and 142 edges, all references resolved."


def save_topology_yaml(filepath: Path | str = TOPOLOGY_FILE) -> None:
    data = generate_topology_data()
    valid, msg = validate_topology(data)
    if not valid:
        raise ValueError(f"Topology generation failed: {msg}")

    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)


def load_topology_yaml(filepath: Path | str = TOPOLOGY_FILE) -> dict[str, Any]:
    p = Path(filepath)
    if not p.exists():
        save_topology_yaml(p)
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    valid, msg = validate_topology(data)
    if not valid:
        raise ValueError(f"Invalid topology file: {msg}")
    return data


if __name__ == "__main__":
    save_topology_yaml()
    data = load_topology_yaml()
    valid, msg = validate_topology(data)
    print(msg)
