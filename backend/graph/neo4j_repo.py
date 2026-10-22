"""AEGIS Neo4j Graph Repository Implementation (M1).

Implements GraphRepository using the official neo4j driver.
All Cypher queries are strictly encapsulated in this file.
"""

from __future__ import annotations

import re
from typing import Any, Optional
import uuid

from backend.config import settings
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

        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        if not self.password:
            raise ValueError("NEO4J_PASSWORD is required when connecting to Neo4j.")

        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def verify_connectivity(self) -> None:
        """Verify that Neo4j instance is reachable."""
        if self._driver:
            self._driver.verify_connectivity()

    def is_empty(self) -> bool:
        """Check whether the Neo4j database contains zero nodes."""
        with self._driver.session() as session:
            res = session.run("MATCH (n) RETURN count(n) AS cnt").single()
            return bool(res and res["cnt"] == 0)

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

    def incidents(self, node: str = "", days: int = 30) -> list[Incident]:
        from datetime import datetime, timezone, timedelta
        cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        if node and node != "*":
            query = """
            MATCH (i:Incident)-[:OCCURRED_IN]->(s {id: $node})
            WHERE i.timestamp >= $cutoff
            OPTIONAL MATCH (dec:Decision)-[:RESOLVED_BY]->(i)
            RETURN i.id AS id, s.id AS service_id, i.description AS desc, i.timestamp AS ts, dec.id AS dec_id, properties(dec) AS dec_props
            ORDER BY i.timestamp DESC
            """
            params: dict[str, Any] = {"node": node, "cutoff": cutoff_iso}
        else:
            query = """
            MATCH (i:Incident)-[:OCCURRED_IN]->(s)
            WHERE i.timestamp >= $cutoff
            OPTIONAL MATCH (dec:Decision)-[:RESOLVED_BY]->(i)
            RETURN i.id AS id, s.id AS service_id, i.description AS desc, i.timestamp AS ts, dec.id AS dec_id, properties(dec) AS dec_props
            ORDER BY i.timestamp DESC
            """
            params = {"cutoff": cutoff_iso}

        incidents: list[Incident] = []
        with self._driver.session() as session:
            records = session.run(query, **params)
            for r in records:
                incidents.append(Incident(
                    id=r["id"],
                    service_id=r["service_id"] if "service_id" in r and r["service_id"] else node,
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
        inc_id = f"inc-{uuid.uuid4().hex[:8]}"
        dec_id = f"dec-{uuid.uuid4().hex[:8]}"

        query = """
        MATCH (s {id: $service_id})
        CREATE (i:Incident {id: $inc_id, description: $description, timestamp: $ts, status: 'resolved'})
        CREATE (dec:Decision {id: $dec_id, timestamp: $ts})
        SET dec += $dec_props
        CREATE (i)-[:OCCURRED_IN]->(s)
        CREATE (dec)-[:RESOLVED_BY]->(i)
        RETURN i.id AS inc_id, dec.id AS dec_id
        """
        dec_props = decision_data or {"action": "restart_pod", "safety_score": 90, "outcome": "success"}
        with self._driver.session() as session:
            session.run(
                query,
                service_id=service_id,
                description=description,
                ts=now_iso,
                dec_props=dec_props,
                inc_id=inc_id,
                dec_id=dec_id,
            )

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
        """Clear graph and reseed baseline topology from data/topology.yaml."""
        from backend.graph.seed import load_topology_yaml

        data = load_topology_yaml()
        with self._driver.session() as session:
            # 1. Clear existing graph
            session.run("MATCH (n) DETACH DELETE n")

            # 2. Reseed nodes
            for n in data.get("nodes", []):
                label = re.sub(r"[^A-Za-z0-9_]", "", n.get("label", "Service"))
                session.run(
                    f"CREATE (n:{label} {{id: $id}}) SET n += $props",
                    id=n["id"],
                    props=dict(n.get("properties", {})),
                )

            # 3. Reseed edges
            for e in data.get("edges", []):
                etype = re.sub(r"[^A-Za-z0-9_]", "", e.get("type", "CALLS"))
                session.run(
                    f"""
                    MATCH (u {{id: $src}}), (v {{id: $tgt}})
                    CREATE (u)-[r:{etype}]->(v)
                    SET r += $props
                    """,
                    src=e["source"],
                    tgt=e["target"],
                    props=dict(e.get("properties", {})),
                )
