"""AEGIS Neo4j Graph Repository Implementation (M1).

Implements GraphRepository using the official neo4j driver.
All Cypher queries are strictly encapsulated in this file.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from backend.graph.repository import (
    Caller,
    Edge,
    GraphRepository,
    Incident,
    Node,
    Subgraph,
    Topology,
)

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class Neo4jGraphRepository(GraphRepository):
    """Neo4j-backed graph repository."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        if not NEO4J_AVAILABLE:
            raise RuntimeError("neo4j driver not installed. Install via `pip install neo4j`.")

        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "aegis_password")
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self) -> None:
        if self._driver:
            self._driver.close()

    def get_topology(self) -> Topology:
        nodes: list[Node] = []
        edges: list[Edge] = []
        with self._driver.session() as session:
            # Query all nodes
            res_nodes = session.run("MATCH (n) RETURN n.id AS id, labels(n)[0] AS label, properties(n) AS props")
            for record in res_nodes:
                props = dict(record["props"])
                props.pop("id", None)
                nodes.append(Node(id=record["id"], label=record["label"] or "Service", properties=props))

            # Query all edges
            res_edges = session.run("MATCH (u)-[r]->(v) RETURN u.id AS source, v.id AS target, type(r) AS type, properties(r) AS props")
            for record in res_edges:
                edges.append(Edge(source=record["source"], target=record["target"], type=record["type"], properties=dict(record["props"])))

        return Topology(nodes=nodes, edges=edges)

    def neighbors(self, node: str, hops: int = 1) -> Subgraph:
        nodes: list[Node] = []
        edges: list[Edge] = []
        query = """
        MATCH (start {id: $node})
        CALL apoc.path.subgraphAll(start, {maxLevel: $hops})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        # Fallback query if APOC is not available:
        basic_query = """
        MATCH path = (start {id: $node})-[*0..$hops]-(m)
        UNWIND nodes(path) AS n
        UNWIND relationships(path) AS r
        RETURN collect(DISTINCT n) AS nodes, collect(DISTINCT r) AS rels
        """
        with self._driver.session() as session:
            try:
                res = session.run(basic_query, node=node, hops=hops).single()
                if res:
                    for n in res["nodes"]:
                        props = dict(n)
                        nid = props.pop("id", str(n.id))
                        lbl = list(n.labels)[0] if n.labels else "Service"
                        nodes.append(Node(id=nid, label=lbl, properties=props))
                    for r in res["rels"]:
                        edges.append(Edge(
                            source=r.start_node["id"],
                            target=r.end_node["id"],
                            type=r.type,
                            properties=dict(r),
                        ))
            except Exception:
                pass
        return Subgraph(nodes=nodes, edges=edges)

    def callers(self, node: str, depth: int = 3) -> list[Caller]:
        # Walk BACKWARDS along dependency edges: (caller)-[:CALLS|DEPENDS_ON|CONNECTS_TO]->(callee)
        query = """
        MATCH path = (caller)-[:CALLS|DEPENDS_ON|CONNECTS_TO*1..$depth]->(callee {id: $node})
        WITH caller, min(length(path)) AS hops
        RETURN caller.id AS caller_id, hops
        ORDER BY hops ASC, caller_id ASC
        """
        results: list[Caller] = []
        with self._driver.session() as session:
            records = session.run(query, node=node, depth=depth)
            for record in records:
                hops = record["hops"]
                weight = round(0.75 ** (hops - 1), 4)
                results.append(Caller(node=record["caller_id"], hops=hops, impact_weight=weight))
        return results

    def incidents(self, node: str, days: int = 30) -> list[Incident]:
        query = """
        MATCH (i:Incident)-[:OCCURRED_IN]->(s {id: $node})
        OPTIONAL MATCH (dec:Decision)-[:RESOLVED_BY]->(i)
        RETURN i.id AS id, i.description AS desc, i.timestamp AS ts, dec.id AS dec_id, properties(dec) AS dec_props
        ORDER BY i.timestamp DESC
        """
        incidents: list[Incident] = []
        with self._driver.session() as session:
            records = session.run(query, node=node)
            for r in records:
                incidents.append(Incident(
                    id=r["id"],
                    service_id=node,
                    description=r["desc"],
                    timestamp=r["ts"],
                    resolved=True,
                    decision_id=r["dec_id"],
                    properties=dict(r["dec_props"]) if r["dec_props"] else {},
                ))
        return incidents

    def set_telemetry(self, node: str, fields: dict[str, Any]) -> None:
        query = """
        MATCH (n {id: $node})
        SET n += $fields
        """
        with self._driver.session() as session:
            session.run(query, node=node, fields=fields)

    def add_incident(
        self,
        service_id: str,
        description: str,
        decision_data: Optional[dict[str, Any]] = None,
    ) -> Incident:
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        query = """
        MATCH (s:Service {id: $service_id})
        CREATE (i:Incident {id: apoc.create.uuid(), description: $description, timestamp: $ts, status: 'resolved'})
        CREATE (dec:Decision {id: apoc.create.uuid(), timestamp: $ts})
        SET dec += $dec_props
        CREATE (i)-[:OCCURRED_IN]->(s)
        CREATE (dec)-[:RESOLVED_BY]->(i)
        RETURN i.id AS inc_id, dec.id AS dec_id
        """
        dec_props = decision_data or {"action": "restart_pod", "safety_score": 90, "outcome": "success"}
        with self._driver.session() as session:
            record = session.run(query, service_id=service_id, description=description, ts=now_iso, dec_props=dec_props).single()
            inc_id = record["inc_id"] if record else "inc-new"
            dec_id = record["dec_id"] if record else "dec-new"

        return Incident(
            id=inc_id,
            service_id=service_id,
            description=description,
            timestamp=now_iso,
            resolved=True,
            decision_id=dec_id,
            properties=dec_props,
        )

    def reset(self) -> None:
        # Load topology.yaml and reseed Neo4j
        pass
