"""AEGIS Agent Context Builder (M6).

Assembles graph-grounded diagnostic context for the LLM reasoning agent.
Rules:
- Uses ONLY GraphRepository interface methods (no raw Cypher or graph internals).
- Includes:
  1. Failing node ID
  2. 2-hop neighbourhood (callers, callees, datastores, nodes, edges)
  3. Latest telemetry per node
  4. Open incidents on these nodes
  5. Last 5 past incidents on these nodes
- Strict token cap: ~3000 tokens maximum (truncates oldest incidents first).
"""

from __future__ import annotations

import json
from typing import Any, Optional

from backend.graph import get_repository
from backend.graph.repository import GraphRepository

MAX_CONTEXT_TOKENS: int = 3000


def count_tokens(text: str) -> int:
    """Calculate token count using tiktoken (cl100k_base) with 4-char fallback."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def _serialize_payload(payload: dict[str, Any]) -> str:
    """Format payload dictionary to compact JSON string for token counting."""
    return json.dumps(payload, default=str, separators=(",", ":"))


def build_context(
    incident_id: str,
    repo: Optional[GraphRepository] = None,
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> dict[str, Any]:
    """Construct token-capped graph context for an incident using only GraphRepository.

    Args:
        incident_id: ID of the incident (or direct failing service ID).
        repo: GraphRepository instance (defaults to get_repository()).
        max_tokens: Upper bound on estimated prompt tokens (default: 3000).

    Returns:
        dict containing failing_node, neighbourhood_2hop, telemetry,
        open_incidents, past_incidents, and token_count.
    """
    if repo is None:
        repo = get_repository()

    # 1. Resolve failing node and active incident using GraphRepository
    all_incidents = repo.incidents(days=365)
    matched_incident = next((inc for inc in all_incidents if inc.id == incident_id), None)

    if matched_incident is not None:
        failing_node = matched_incident.service_id
    elif incident_id:
        # Check if incident_id matches a node ID directly in the graph
        topology = repo.get_topology()
        existing_node = next((n for n in topology.nodes if n.id == incident_id), None)
        if existing_node is not None:
            failing_node = existing_node.id
        else:
            failing_node = incident_id
    else:
        # No incident_id provided: resolve to most recent incident or default to paymentservice
        if all_incidents:
            failing_node = all_incidents[-1].service_id
            incident_id = all_incidents[-1].id
        else:
            topology = repo.get_topology()
            failing_node = "paymentservice" if any(n.id == "paymentservice" for n in topology.nodes) else (topology.nodes[0].id if topology.nodes else "")
            incident_id = "inc-default"

    # 2. Extract 2-hop neighbourhood via GraphRepository.neighbors(hops=2)
    subgraph = repo.neighbors(failing_node, hops=2)

    # Filter topology nodes: exclude Incident / Decision ledger nodes from structural topology
    topology_nodes = [
        n for n in subgraph.nodes
        if n.label not in ("Incident", "Decision") and not n.id.startswith(("inc-", "dec-"))
    ]
    topology_edges = [
        e for e in subgraph.edges
        if not (e.source.startswith(("inc-", "dec-")) or e.target.startswith(("inc-", "dec-")))
        and e.type not in ("OCCURRED_IN", "RESOLVED_BY")
    ]

    neighbourhood_node_ids = {n.id for n in topology_nodes}
    if failing_node and failing_node not in neighbourhood_node_ids:
        neighbourhood_node_ids.add(failing_node)

    # Callers walking backwards along CALLS edges via GraphRepository.callers(depth=2)
    caller_records = repo.callers(failing_node, depth=2)
    callers = [c.node for c in caller_records]
    # Also include any upstream nodes that have direct edges to failing_node in topology_edges
    for edge in topology_edges:
        if edge.target == failing_node and edge.source != failing_node:
            if edge.source not in callers:
                callers.append(edge.source)

    # Callees (downstream services/datastores directed away from failing_node)
    callees = sorted(list({
        edge.target
        for edge in topology_edges
        if edge.source == failing_node and edge.target != failing_node
    }))

    # Datastores in the 2-hop neighbourhood
    datastores = sorted(list({
        n.id
        for n in topology_nodes
        if n.label in ("Database", "Datastore")
        or any(db_kw in n.id.lower() for db_kw in ("postgres", "redis", "mongo", "sql", "db"))
    }))

    neighbourhood_nodes = [
        {"id": n.id, "label": n.label, "properties": n.properties}
        for n in topology_nodes
    ]
    neighbourhood_edges = [
        {"source": e.source, "target": e.target, "type": e.type, "properties": e.properties}
        for e in topology_edges
    ]

    # 3. Latest telemetry per node in neighbourhood
    telemetry: dict[str, dict[str, Any]] = {}
    for n in topology_nodes:
        telemetry[n.id] = dict(n.properties)

    # If failing_node was missing from topology nodes, populate from get_topology()
    if failing_node and failing_node not in telemetry:
        topo = repo.get_topology()
        fn_node = next((n for n in topo.nodes if n.id == failing_node), None)
        if fn_node:
            telemetry[failing_node] = dict(fn_node.properties)
            neighbourhood_nodes.append(
                {"id": fn_node.id, "label": fn_node.label, "properties": fn_node.properties}
            )

    # 4. Open and Past incidents on these nodes
    relevant_incidents = [
        inc for inc in all_incidents
        if inc.service_id in neighbourhood_node_ids
    ]

    # Open incidents (unresolved)
    open_incidents = [
        inc.model_dump() for inc in relevant_incidents if not inc.resolved
    ]

    # Past incidents (resolved, last 5, sorted newest first)
    resolved_incidents = [
        inc for inc in relevant_incidents if inc.resolved
    ]
    # Sort descending by timestamp (newest first, oldest at the end)
    resolved_incidents.sort(key=lambda x: x.timestamp, reverse=True)
    past_incidents = [inc.model_dump() for inc in resolved_incidents[:5]]

    # 5. Cap to max_tokens (~3000 tokens), truncating oldest incidents first
    ctx: dict[str, Any] = {
        "incident_id": incident_id,
        "failing_node": failing_node,
        "neighbourhood_2hop": {
            "nodes": neighbourhood_nodes,
            "edges": neighbourhood_edges,
            "callers": callers,
            "callees": callees,
            "datastores": datastores,
        },
        "telemetry": telemetry,
        "open_incidents": open_incidents,
        "past_incidents": past_incidents,
    }

    # Measure tokens
    serialized = _serialize_payload(ctx)
    tokens = count_tokens(serialized)

    # Stage 1: Truncate oldest past incidents first until within token cap
    while tokens > max_tokens and ctx["past_incidents"]:
        # Pop oldest incident (last in newest-first list)
        ctx["past_incidents"].pop(-1)
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 2: If still exceeding cap, truncate open incidents (oldest first)
    while tokens > max_tokens and ctx["open_incidents"]:
        ctx["open_incidents"].pop(-1)
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 3: If still exceeding cap, trim long description strings from incidents
    if tokens > max_tokens:
        for inc_list in (ctx["past_incidents"], ctx["open_incidents"]):
            for inc in inc_list:
                if len(inc.get("description", "")) > 80:
                    inc["description"] = inc["description"][:80] + "..."
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 4: If still exceeding cap, strip node properties from neighbourhood nodes
    # (telemetry dictionary already contains the metrics)
    if tokens > max_tokens:
        for node_item in ctx["neighbourhood_2hop"]["nodes"]:
            node_item.pop("properties", None)
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 5: If still exceeding cap, strip edge properties
    if tokens > max_tokens:
        ctx["neighbourhood_2hop"]["edges"] = [
            {"source": e["source"], "target": e["target"], "type": e["type"]}
            for e in ctx["neighbourhood_2hop"]["edges"]
        ]
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 6: If still exceeding cap, prune edges to CALLS and DEPENDS_ON
    if tokens > max_tokens:
        ctx["neighbourhood_2hop"]["edges"] = [
            e for e in ctx["neighbourhood_2hop"]["edges"]
            if e.get("type") in ("CALLS", "DEPENDS_ON")
        ]
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 7: If still exceeding cap, prune edges to direct connections
    if tokens > max_tokens:
        ctx["neighbourhood_2hop"]["edges"] = [
            e for e in ctx["neighbourhood_2hop"]["edges"]
            if e.get("source") == failing_node or e.get("target") == failing_node
        ]
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 8: If still exceeding cap, prune telemetry properties to essential metrics and priority services
    if tokens > max_tokens:
        priority_nodes = set(callers).union(set(callees)).union(set(datastores)).union({failing_node})
        ctx["telemetry"] = {
            k: {pk: pv for pk, pv in v.items() if pk in ("p99_ms", "baseline_p99_ms", "error_rate", "status", "connections", "pool_size")}
            for k, v in ctx["telemetry"].items()
            if k in priority_nodes and not ("-pod-" in k or ":" in k)
        }
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 9: If still exceeding cap, prune nodes to priority core services and datastores
    if tokens > max_tokens:
        priority_nodes = set(callers).union(set(callees)).union(set(datastores)).union({failing_node})
        ctx["neighbourhood_2hop"]["nodes"] = [
            n for n in ctx["neighbourhood_2hop"]["nodes"]
            if n["id"] in priority_nodes and not ("-pod-" in n["id"] or ":" in n["id"])
        ]
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    # Stage 10: If still exceeding cap, keep only immediate callers and callees
    if tokens > max_tokens:
        ctx["neighbourhood_2hop"]["callers"] = [
            c for c in ctx["neighbourhood_2hop"]["callers"]
            if not ("-pod-" in c or ":" in c)
        ][:5]
        ctx["neighbourhood_2hop"]["callees"] = [
            c for c in ctx["neighbourhood_2hop"]["callees"]
            if not ("-pod-" in c or ":" in c)
        ][:5]
        serialized = _serialize_payload(ctx)
        tokens = count_tokens(serialized)

    ctx["token_count"] = tokens
    return ctx
