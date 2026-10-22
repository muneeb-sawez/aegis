"""AEGIS NetworkX Graph Repository Implementation (M1).

Provides an in-memory, zero-external-dependency implementation of GraphRepository.
Strictly respects:
- CALLS direction: caller -> callee
- Backwards BFS traversal for callers
- Project isolation: multi-tenant partitioned graphs per project_id (default 'demo')
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
    Outcome,
    Subgraph,
    Topology,
)
from backend.graph.seed import load_topology_yaml


class NetworkXGraphRepository(GraphRepository):
    """NetworkX-based multi-tenant implementation of GraphRepository."""

    def __init__(self, topology_path: Optional[str] = None):
        self.topology_path = topology_path
        self._graphs: dict[str, nx.MultiDiGraph] = {}
        self._incidents: list[Incident] = []
        self._decisions: list[dict[str, Any]] = []
        self._outcomes: list[Outcome] = []
        self._initial_data: Optional[dict[str, Any]] = None
        self.reset(project_id="demo")

    @property
    def _graph(self) -> nx.MultiDiGraph:
        """Backwards compatibility for tests or callers directly accessing ._graph for demo project."""
        if "demo" not in self._graphs:
            self.seed_project("demo")
        return self._graphs["demo"]

    def _get_project_graph(self, project_id: str) -> nx.MultiDiGraph:
        """Retrieve or initialize the isolated MultiDiGraph for project_id."""
        if project_id not in self._graphs:
            self.seed_project(project_id)
        return self._graphs[project_id]

    def seed_project(self, project_id: str = "demo", data: Optional[dict[str, Any]] = None) -> None:
        """Seed a project's isolated graph from data (or baseline topology)."""
        if data is None:
            if self._initial_data is None:
                self._initial_data = load_topology_yaml(self.topology_path) if self.topology_path else load_topology_yaml()
            data = copy.deepcopy(self._initial_data)

        G = nx.MultiDiGraph()

        for n in data.get("nodes", []):
            nid = n["id"]
            props = copy.deepcopy(n.get("properties", {}))
            props.pop("project_id", None)
            props.pop("label", None)
            G.add_node(
                nid,
                label=n.get("label", "Service"),
                project_id=project_id,
                **props,
            )

        for e in data.get("edges", []):
            u = e["source"]
            v = e["target"]
            props = copy.deepcopy(e.get("properties", {}))
            props.pop("project_id", None)
            props.pop("type", None)
            G.add_edge(
                u,
                v,
                type=e.get("type", "CALLS"),
                project_id=project_id,
                **props,
            )

        self._graphs[project_id] = G

    def reset(self, project_id: str = "demo") -> None:
        """Restore project graph to clean baseline topology from data/topology.yaml."""
        if project_id == "*":
            self._graphs.clear()
            self._incidents.clear()
            self._decisions.clear()
            self._outcomes.clear()
            self.seed_project("demo")
            return

        self._incidents = [i for i in self._incidents if i.project_id != project_id]
        self._decisions = [d for d in self._decisions if d.get("project_id") != project_id]
        self._outcomes = [o for o in self._outcomes if o.project_id != project_id]

        self.seed_project(project_id=project_id)

    def get_topology(self, project_id: str = "demo") -> Topology:
        """Return the complete active topology for the specified project."""
        G = self._get_project_graph(project_id)
        nodes: list[Node] = []
        for nid, attrs in G.nodes(data=True):
            label = attrs.get("label", "Service")
            props = {k: v for k, v in attrs.items() if k not in ("label", "project_id")}
            nodes.append(Node(id=nid, label=label, project_id=project_id, properties=props))

        edges: list[Edge] = []
        for u, v, attrs in G.edges(data=True):
            etype = attrs.get("type", "CALLS")
            props = {k: v for k, v in attrs.items() if k not in ("type", "project_id")}
            edges.append(Edge(source=u, target=v, type=etype, project_id=project_id, properties=props))

        return Topology(nodes=nodes, edges=edges)

    def neighbors(self, node: str, hops: int = 1, project_id: str = "demo") -> Subgraph:
        """Return the k-hop neighborhood around node (both directions) within project_id."""
        G = self._get_project_graph(project_id)
        if node not in G:
            return Subgraph(nodes=[], edges=[])

        visited = {node}
        current_layer = {node}

        for _ in range(hops):
            next_layer = set()
            for n in current_layer:
                neighbors_n = set(G.predecessors(n)) | set(G.successors(n))
                for nbr in neighbors_n:
                    if nbr not in visited:
                        visited.add(nbr)
                        next_layer.add(nbr)
            current_layer = next_layer

        sub_nodes: list[Node] = []
        for nid in visited:
            attrs = dict(G.nodes[nid])
            label = attrs.get("label", "Service")
            props = {k: v for k, v in attrs.items() if k not in ("label", "project_id")}
            sub_nodes.append(Node(id=nid, label=label, project_id=project_id, properties=props))

        sub_edges: list[Edge] = []
        for u in visited:
            for v in visited:
                if G.has_edge(u, v):
                    edge_dict = G.get_edge_data(u, v)
                    for _, attrs in edge_dict.items():
                        etype = attrs.get("type", "CALLS")
                        props = {k: v for k, v in attrs.items() if k not in ("type", "project_id")}
                        sub_edges.append(Edge(source=u, target=v, type=etype, project_id=project_id, properties=props))

        return Subgraph(nodes=sub_nodes, edges=sub_edges)

    def callers(self, node: str, depth: int = 3, project_id: str = "demo") -> list[Caller]:
        """Return upstream callers of node walking BACKWARDS along CALLS edges in project_id.

        Rule: CALLS is caller -> callee. Callers are predecessors.
        Depth attenuation: 0.75 per hop (hop 1 = 1.0, hop 2 = 0.75, hop 3 = 0.5625).
        """
        G = self._get_project_graph(project_id)
        if node not in G:
            return []

        callers_map: dict[str, int] = {}
        visited = {node}
        queue: list[tuple[str, int]] = [(node, 0)]

        while queue:
            curr, curr_hop = queue.pop(0)
            if curr_hop >= depth:
                continue

            for pred in G.predecessors(curr):
                edge_dict = G.get_edge_data(pred, curr)
                is_call = any(
                    attrs.get("type") in ("CALLS", "DEPENDS_ON", "CONNECTS_TO")
                    for attrs in edge_dict.values()
                )
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

    def incidents(self, node: str = "", days: int = 30, project_id: str = "demo") -> list[Incident]:
        """Return incidents associated with node within last `days` days in project_id."""
        now = datetime.now(timezone.utc)
        matching: list[Incident] = []
        for inc in self._incidents:
            if inc.project_id != project_id:
                continue
            if not node or node == "*" or inc.service_id == node:
                try:
                    inc_time = datetime.fromisoformat(inc.timestamp.replace("Z", "+00:00"))
                    diff_days = (now - inc_time).total_seconds() / 86400.0
                    if diff_days <= days:
                        matching.append(inc)
                except Exception:
                    matching.append(inc)
        return matching

    def set_telemetry(self, node: str, fields: dict[str, Any], project_id: str = "demo") -> None:
        """Update telemetry/metric properties on a given node in project_id."""
        G = self._get_project_graph(project_id)
        if node in G:
            for k, v in fields.items():
                G.nodes[node][k] = v
            G.nodes[node]["project_id"] = project_id

    def add_incident(
        self,
        service_id: str,
        description: str,
        decision_data: Optional[dict[str, Any]] = None,
        project_id: str = "demo",
    ) -> Incident:
        """Create an Incident node, Decision node, and link them to graph in project_id."""
        G = self._get_project_graph(project_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        proj_inc_count = len([i for i in self._incidents if i.project_id == project_id]) + 1
        proj_dec_count = len([d for d in self._decisions if d.get("project_id") == project_id]) + 1

        inc_id = f"inc-{proj_inc_count:04d}"
        dec_id = f"dec-{proj_dec_count:04d}"

        # 1. Add Incident node
        G.add_node(
            inc_id,
            label="Incident",
            service_id=service_id,
            description=description,
            timestamp=now_iso,
            status="resolved",
            project_id=project_id,
        )

        # 2. Add Decision node
        raw_dec_props = decision_data or {
            "action": "restart_pod",
            "safety_score": 90,
            "outcome": "success",
        }
        dec_props = {
            k: v for k, v in raw_dec_props.items()
            if k not in ("project_id", "label", "timestamp")
        }
        G.add_node(
            dec_id,
            label="Decision",
            timestamp=now_iso,
            project_id=project_id,
            **dec_props,
        )

        # 3. Add edges within project graph
        if service_id in G:
            G.add_edge(inc_id, service_id, type="OCCURRED_IN", timestamp=now_iso, project_id=project_id)

        G.add_edge(dec_id, inc_id, type="RESOLVED_BY", timestamp=now_iso, project_id=project_id)

        incident_obj = Incident(
            id=inc_id,
            service_id=service_id,
            description=description,
            timestamp=now_iso,
            project_id=project_id,
            resolved=True,
            decision_id=dec_id,
            properties=dec_props,
        )

        self._incidents.append(incident_obj)
        self._decisions.append({"id": dec_id, "project_id": project_id, **dec_props})

        return incident_obj

    def add_outcome(
        self,
        decision_id: str,
        incident_id: str,
        service_id: str,
        fault_type: str,
        action: str,
        status: str,
        safety_score: float,
        composite_score: float,
        project_id: str = "demo",
    ) -> Outcome:
        """Create an Outcome node and Decision-[:RESULTED_IN]->Outcome edge in project_id."""
        G = self._get_project_graph(project_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        proj_out_count = len([o for o in self._outcomes if o.project_id == project_id]) + 1
        out_id = f"out-{proj_out_count:04d}"

        G.add_node(
            out_id,
            label="Outcome",
            decision_id=decision_id,
            incident_id=incident_id,
            service_id=service_id,
            fault_type=fault_type,
            action=action,
            status=status,
            safety_score=safety_score,
            composite_score=composite_score,
            timestamp=now_iso,
            project_id=project_id,
        )

        if decision_id in G:
            G.add_edge(decision_id, out_id, type="RESULTED_IN", timestamp=now_iso, project_id=project_id)

        if service_id in G:
            G.add_edge(out_id, service_id, type="OCCURRED_IN", timestamp=now_iso, project_id=project_id)

        outcome = Outcome(
            id=out_id,
            decision_id=decision_id,
            incident_id=incident_id,
            service_id=service_id,
            fault_type=fault_type,
            action=action,
            status=status,
            safety_score=safety_score,
            composite_score=composite_score,
            timestamp=now_iso,
            project_id=project_id,
        )
        self._outcomes.append(outcome)
        return outcome

    def get_outcomes(
        self,
        fault_type: str = "",
        action: str = "",
        days: int = 90,
        project_id: str = "demo",
    ) -> list[Outcome]:
        """Return Outcome objects for project_id within `days` days."""
        now = datetime.now(timezone.utc)
        results: list[Outcome] = []
        for out in self._outcomes:
            if out.project_id != project_id:
                continue
            try:
                out_time = datetime.fromisoformat(out.timestamp.replace("Z", "+00:00"))
                diff_days = (now - out_time).total_seconds() / 86400.0
                if diff_days > days:
                    continue
            except Exception:
                pass
            if fault_type and out.fault_type != fault_type:
                continue
            if action and out.action != action:
                continue
            results.append(out)
        return results

    def get_all_incidents_with_descriptions(self, days: int = 90, project_id: str = "demo") -> list[dict[str, Any]]:
        """Return all incidents as dicts for similarity search in project_id."""
        all_inc = self.incidents(node="", days=days, project_id=project_id)
        return [
            {
                "id": inc.id,
                "service_id": inc.service_id,
                "description": inc.description,
                "timestamp": inc.timestamp,
                "project_id": inc.project_id,
            }
            for inc in all_inc
        ]
