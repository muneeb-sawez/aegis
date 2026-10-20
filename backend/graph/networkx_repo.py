"""AEGIS NetworkX Graph Repository Implementation (M1).

Provides an in-memory, zero-external-dependency implementation of GraphRepository.
Strictly respects:
- CALLS direction: caller -> callee
- Backwards BFS traversal for callers
- Frozen interface contracts in docs/02-CONTRACTS.md §3
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Optional
import networkx as nx

from backend.graph.repository import (
    Caller,
    Edge,
    GraphRepository,
    Incident,
    Node,
    Subgraph,
    Topology,
)
from backend.graph.seed import load_topology_yaml


class NetworkXGraphRepository(GraphRepository):
    """NetworkX-based implementation of GraphRepository."""

    def __init__(self, topology_path: Optional[str] = None):
        self.topology_path = topology_path
        self._graph = nx.MultiDiGraph()
        self._incidents: list[Incident] = []
        self._decisions: list[dict[str, Any]] = []
        self._initial_data: Optional[dict[str, Any]] = None
        self.reset()

    def reset(self) -> None:
        """Restore graph to clean baseline topology from data/topology.yaml."""
        if self._initial_data is None:
            self._initial_data = load_topology_yaml(self.topology_path) if self.topology_path else load_topology_yaml()

        self._graph.clear()
        self._incidents.clear()
        self._decisions.clear()

        # Deep copy to ensure fresh state
        data = copy.deepcopy(self._initial_data)

        for n in data.get("nodes", []):
            self._graph.add_node(n["id"], label=n["label"], **n.get("properties", {}))

        for e in data.get("edges", []):
            self._graph.add_edge(
                e["source"],
                e["target"],
                type=e["type"],
                **e.get("properties", {}),
            )

    def get_topology(self) -> Topology:
        """Return the complete active topology."""
        nodes: list[Node] = []
        for nid, attrs in self._graph.nodes(data=True):
            props = dict(attrs)
            label = props.pop("label", "Service")
            nodes.append(Node(id=nid, label=label, properties=props))

        edges: list[Edge] = []
        for u, v, attrs in self._graph.edges(data=True):
            props = dict(attrs)
            etype = props.pop("type", "CALLS")
            edges.append(Edge(source=u, target=v, type=etype, properties=props))

        return Topology(nodes=nodes, edges=edges)

    def neighbors(self, node: str, hops: int = 1) -> Subgraph:
        """Return the k-hop neighborhood around node (both in- and out-edges)."""
        if node not in self._graph:
            return Subgraph(nodes=[], edges=[])

        # Undirected traversal to find connected node set within k hops
        visited = {node}
        current_layer = {node}

        for _ in range(hops):
            next_layer = set()
            for n in current_layer:
                # Predecessors and successors
                neighbors_n = set(self._graph.predecessors(n)) | set(self._graph.successors(n))
                for nbr in neighbors_n:
                    if nbr not in visited:
                        visited.add(nbr)
                        next_layer.add(nbr)
            current_layer = next_layer

        # Build subgraph containing visited nodes and all edges between them
        sub_nodes: list[Node] = []
        for nid in visited:
            attrs = dict(self._graph.nodes[nid])
            label = attrs.pop("label", "Service")
            sub_nodes.append(Node(id=nid, label=label, properties=attrs))

        sub_edges: list[Edge] = []
        for u in visited:
            for v in visited:
                if self._graph.has_edge(u, v):
                    edge_dict = self._graph.get_edge_data(u, v)
                    for _, attrs in edge_dict.items():
                        props = dict(attrs)
                        etype = props.pop("type", "CALLS")
                        sub_edges.append(Edge(source=u, target=v, type=etype, properties=props))

        return Subgraph(nodes=sub_nodes, edges=sub_edges)

    def callers(self, node: str, depth: int = 3) -> list[Caller]:
        """Return upstream callers of node walking BACKWARDS along CALLS edges.

        Rule: CALLS is caller -> callee.
        Therefore, callers of B are predecessors A where edge (A, B) has type 'CALLS'.
        Depth attenuation: 0.75 per hop (hop 1 = 1.0, hop 2 = 0.75, hop 3 = 0.5625).
        """
        if node not in self._graph:
            return []

        callers_map: dict[str, int] = {}  # caller_id -> minimum hops
        visited = {node}
        queue: list[tuple[str, int]] = [(node, 0)]

        while queue:
            curr, curr_hop = queue.pop(0)
            if curr_hop >= depth:
                continue

            # Look at predecessors: nodes that have an edge directed into curr
            for pred in self._graph.predecessors(curr):
                edge_dict = self._graph.get_edge_data(pred, curr)
                # Verify at least one edge is of type 'CALLS'
                is_call = any(attrs.get("type") == "CALLS" for attrs in edge_dict.values())
                if is_call:
                    next_hop = curr_hop + 1
                    if pred not in callers_map or next_hop < callers_map[pred]:
                        callers_map[pred] = next_hop
                    if pred not in visited:
                        visited.add(pred)
                        queue.append((pred, next_hop))

        results: list[Caller] = []
        for caller_id, hops in sorted(callers_map.items(), key=lambda x: (x[1], x[0])):
            impact_weight = round(0.75 ** (hops - 1), 4)
            results.append(Caller(node=caller_id, hops=hops, impact_weight=impact_weight))

        return results

    def incidents(self, node: str, days: int = 30) -> list[Incident]:
        """Return incidents associated with node within the last `days` days."""
        # Check direct service match or incidents linking to node
        now = datetime.now(timezone.utc)
        matching: list[Incident] = []
        for inc in self._incidents:
            if inc.service_id == node:
                try:
                    inc_time = datetime.fromisoformat(inc.timestamp.replace("Z", "+00:00"))
                    diff_days = (now - inc_time).total_seconds() / 86400.0
                    if diff_days <= days:
                        matching.append(inc)
                except Exception:
                    # If timestamp parsing fails, include it
                    matching.append(inc)
        return matching

    def set_telemetry(self, node: str, fields: dict[str, Any]) -> None:
        """Update telemetry/metric properties on a given node."""
        if node in self._graph:
            for k, v in fields.items():
                self._graph.nodes[node][k] = v

    def add_incident(
        self,
        service_id: str,
        description: str,
        decision_data: Optional[dict[str, Any]] = None,
    ) -> Incident:
        """Create an Incident node, Decision node, and link them to the graph."""
        now_iso = datetime.now(timezone.utc).isoformat()
        inc_id = f"inc-{len(self._incidents) + 1:04d}"
        dec_id = f"dec-{len(self._decisions) + 1:04d}"

        # 1. Add Incident node
        self._graph.add_node(
            inc_id,
            label="Incident",
            service_id=service_id,
            description=description,
            timestamp=now_iso,
            status="resolved",
        )

        # 2. Add Decision node
        dec_props = decision_data or {
            "action": "restart_pod",
            "safety_score": 90,
            "outcome": "success",
        }
        self._graph.add_node(
            dec_id,
            label="Decision",
            timestamp=now_iso,
            **dec_props,
        )

        # 3. Add edges:
        # Incident -[:OCCURRED_IN]-> Service
        if service_id in self._graph:
            self._graph.add_edge(inc_id, service_id, type="OCCURRED_IN", timestamp=now_iso)

        # Decision -[:RESOLVED_BY]-> Incident
        self._graph.add_edge(dec_id, inc_id, type="RESOLVED_BY", timestamp=now_iso)

        incident_obj = Incident(
            id=inc_id,
            service_id=service_id,
            description=description,
            timestamp=now_iso,
            resolved=True,
            decision_id=dec_id,
            properties=dec_props,
        )

        self._incidents.append(incident_obj)
        self._decisions.append({"id": dec_id, **dec_props})

        return incident_obj
