"""AEGIS Neo4j Graph Repository Implementation (M1).

Implements GraphRepository using the official neo4j driver with multi-tenant project_id isolation.
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
    Outcome,
    Subgraph,
    Topology,
)

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class Neo4jGraphRepository(GraphRepository):
    """Neo4j-backed graph repository with project_id isolation."""

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

    def get_topology(self, project_id: str = "demo") -> Topology:
        nodes: list[Node] = []
        edges: list[Edge] = []
        with self._driver.session() as session:
            # Query nodes for this project
            res_nodes = session.run(
                """
                MATCH (n {project_id: $project_id})
                RETURN n.id AS id, labels(n)[0] AS label, properties(n) AS props
                """,
                project_id=project_id,
            )
            for record in res_nodes:
                props = dict(record["props"])
                props.pop("id", None)
                nodes.append(Node(id=record["id"], label=record["label"] or "Service", project_id=project_id, properties=props))

            # Query edges for this project
            res_edges = session.run(
                """
                MATCH (u {project_id: $project_id})-[r {project_id: $project_id}]->(v {project_id: $project_id})
                RETURN u.id AS source, v.id AS target, type(r) AS type, properties(r) AS props
                """,
                project_id=project_id,
            )
            for record in res_edges:
                edges.append(Edge(source=record["source"], target=record["target"], type=record["type"], project_id=project_id, properties=dict(record["props"])))

        return Topology(nodes=nodes, edges=edges)

    def neighbors(self, node: str, hops: int = 1, project_id: str = "demo") -> Subgraph:
        nodes: list[Node] = []
        edges: list[Edge] = []
        basic_query = """
        MATCH path = (start {id: $node, project_id: $project_id})-[*0..$hops]-(m {project_id: $project_id})
        UNWIND nodes(path) AS n
        UNWIND relationships(path) AS r
        WHERE r.project_id = $project_id
        RETURN collect(DISTINCT n) AS nodes, collect(DISTINCT r) AS rels
        """
        with self._driver.session() as session:
            try:
                res = session.run(basic_query, node=node, hops=hops, project_id=project_id).single()
                if res:
                    for n in res["nodes"]:
                        props = dict(n)
                        nid = props.pop("id", str(n.id))
                        lbl = list(n.labels)[0] if n.labels else "Service"
                        nodes.append(Node(id=nid, label=lbl, project_id=project_id, properties=props))
                    for r in res["rels"]:
                        edges.append(Edge(
                            source=r.start_node["id"],
                            target=r.end_node["id"],
                            type=r.type,
                            project_id=project_id,
                            properties=dict(r),
                        ))
            except Exception:
                pass
        return Subgraph(nodes=nodes, edges=edges)

    def callers(self, node: str, depth: int = 3, project_id: str = "demo") -> list[Caller]:
        query = """
        MATCH path = (caller {project_id: $project_id})-[:CALLS|DEPENDS_ON|CONNECTS_TO*1..$depth]->(callee {id: $node, project_id: $project_id})
        WHERE ALL(r IN relationships(path) WHERE r.project_id = $project_id)
        WITH caller, min(length(path)) AS hops
        RETURN caller.id AS caller_id, hops
        ORDER BY hops ASC, caller_id ASC
        """
        results: list[Caller] = []
        with self._driver.session() as session:
            records = session.run(query, node=node, depth=depth, project_id=project_id)
            for record in records:
                hops = record["hops"]
                weight = round(0.75 ** (hops - 1), 4)
                results.append(Caller(node=record["caller_id"], hops=hops, impact_weight=weight))
        return results

    def incidents(self, node: str = "", days: int = 30, project_id: str = "demo") -> list[Incident]:
        from datetime import datetime, timezone, timedelta
        cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        if node and node != "*":
            query = """
            MATCH (i:Incident {project_id: $project_id})-[:OCCURRED_IN {project_id: $project_id}]->(s {id: $node, project_id: $project_id})
            WHERE i.timestamp >= $cutoff
            OPTIONAL MATCH (dec:Decision {project_id: $project_id})-[:RESOLVED_BY {project_id: $project_id}]->(i)
            RETURN i.id AS id, s.id AS service_id, i.description AS desc, i.timestamp AS ts, dec.id AS dec_id, properties(dec) AS dec_props
            ORDER BY i.timestamp DESC
            """
            params: dict[str, Any] = {"node": node, "cutoff": cutoff_iso, "project_id": project_id}
        else:
            query = """
            MATCH (i:Incident {project_id: $project_id})-[:OCCURRED_IN {project_id: $project_id}]->(s {project_id: $project_id})
            WHERE i.timestamp >= $cutoff
            OPTIONAL MATCH (dec:Decision {project_id: $project_id})-[:RESOLVED_BY {project_id: $project_id}]->(i)
            RETURN i.id AS id, s.id AS service_id, i.description AS desc, i.timestamp AS ts, dec.id AS dec_id, properties(dec) AS dec_props
            ORDER BY i.timestamp DESC
            """
            params = {"cutoff": cutoff_iso, "project_id": project_id}

        incidents: list[Incident] = []
        with self._driver.session() as session:
            records = session.run(query, **params)
            for r in records:
                incidents.append(Incident(
                    id=r["id"],
                    service_id=r["service_id"] if "service_id" in r and r["service_id"] else node,
                    description=r["desc"],
                    timestamp=r["ts"],
                    project_id=project_id,
                    resolved=True,
                    decision_id=r["dec_id"],
                    properties=dict(r["dec_props"]) if r["dec_props"] else {},
                ))
        return incidents

    def set_telemetry(self, node: str, fields: dict[str, Any], project_id: str = "demo") -> None:
        query = """
        MATCH (n {id: $node, project_id: $project_id})
        SET n += $fields
        """
        with self._driver.session() as session:
            session.run(query, node=node, fields=fields, project_id=project_id)

    def add_incident(
        self,
        service_id: str,
        description: str,
        decision_data: Optional[dict[str, Any]] = None,
        project_id: str = "demo",
    ) -> Incident:
        now_iso = datetime.now(timezone.utc).isoformat()
        inc_id = f"inc-{uuid.uuid4().hex[:8]}"
        dec_id = f"dec-{uuid.uuid4().hex[:8]}"

        query = """
        MATCH (s {id: $service_id, project_id: $project_id})
        CREATE (i:Incident {id: $inc_id, description: $description, timestamp: $ts, status: 'resolved', project_id: $project_id})
        CREATE (dec:Decision {id: $dec_id, timestamp: $ts, project_id: $project_id})
        SET dec += $dec_props
        CREATE (i)-[:OCCURRED_IN {project_id: $project_id}]->(s)
        CREATE (dec)-[:RESOLVED_BY {project_id: $project_id}]->(i)
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
                project_id=project_id,
            )

        return Incident(
            id=inc_id,
            service_id=service_id,
            description=description,
            timestamp=now_iso,
            project_id=project_id,
            resolved=True,
            decision_id=dec_id,
            properties=dec_props,
        )

    def reset(self, project_id: str = "demo") -> None:
        """Clear graph for project_id and reseed baseline topology from data/topology.yaml."""
        from backend.graph.seed import load_topology_yaml

        data = load_topology_yaml()
        with self._driver.session() as session:
            # 1. Clear existing graph for this project
            session.run("MATCH (n {project_id: $project_id}) DETACH DELETE n", project_id=project_id)

            # 2. Reseed nodes
            for n in data.get("nodes", []):
                label = re.sub(r"[^A-Za-z0-9_]", "", n.get("label", "Service"))
                props = dict(n.get("properties", {}))
                props["project_id"] = project_id
                session.run(
                    f"CREATE (n:{label} {{id: $id, project_id: $project_id}}) SET n += $props",
                    id=n["id"],
                    project_id=project_id,
                    props=props,
                )

            # 3. Reseed edges
            for e in data.get("edges", []):
                etype = re.sub(r"[^A-Za-z0-9_]", "", e.get("type", "CALLS"))
                props = dict(e.get("properties", {}))
                props["project_id"] = project_id
                session.run(
                    f"""
                    MATCH (u {{id: $src, project_id: $project_id}}), (v {{id: $tgt, project_id: $project_id}})
                    CREATE (u)-[r:{etype} {{project_id: $project_id}}]->(v)
                    SET r += $props
                    """,
                    src=e["source"],
                    tgt=e["target"],
                    project_id=project_id,
                    props=props,
                )

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
        """Create an Outcome node and link it via Decision-[:RESULTED_IN]->Outcome."""
        now_iso = datetime.now(timezone.utc).isoformat()
        out_id = f"out-{uuid.uuid4().hex[:8]}"

        query = """
        MATCH (dec:Decision {id: $dec_id, project_id: $project_id})
        MATCH (s:Service {id: $service_id, project_id: $project_id})
        CREATE (o:Outcome {
            id: $out_id,
            decision_id: $dec_id,
            incident_id: $inc_id,
            service_id: $service_id,
            fault_type: $fault_type,
            action: $action,
            status: $status,
            safety_score: $safety_score,
            composite_score: $composite_score,
            timestamp: $ts,
            project_id: $project_id
        })
        CREATE (dec)-[:RESULTED_IN {project_id: $project_id}]->(o)
        CREATE (o)-[:OCCURRED_IN {project_id: $project_id}]->(s)
        RETURN o.id AS out_id
        """
        with self._driver.session() as session:
            session.run(
                query,
                dec_id=decision_id,
                service_id=service_id,
                out_id=out_id,
                inc_id=incident_id,
                fault_type=fault_type,
                action=action,
                status=status,
                safety_score=safety_score,
                composite_score=composite_score,
                ts=now_iso,
                project_id=project_id,
            )

        return Outcome(
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

    def get_outcomes(
        self,
        fault_type: str = "",
        action: str = "",
        days: int = 90,
        project_id: str = "demo",
    ) -> list[Outcome]:
        """Return Outcome nodes optionally filtered by fault_type and/or action for project_id."""
        query = """
        MATCH (o:Outcome {project_id: $project_id})
        WHERE ($fault_type = '' OR o.fault_type = $fault_type)
          AND ($action = '' OR o.action = $action)
        RETURN o.id AS id, o.decision_id AS decision_id, o.incident_id AS incident_id,
               o.service_id AS service_id, o.fault_type AS fault_type, o.action AS action,
               o.status AS status, o.safety_score AS safety_score,
               o.composite_score AS composite_score, o.timestamp AS timestamp
        ORDER BY o.timestamp DESC
        """
        with self._driver.session() as session:
            result = session.run(query, fault_type=fault_type, action=action, project_id=project_id)
            records = result.data()

        now = datetime.now(timezone.utc)
        outcomes = []
        for r in records:
            ts_str = r.get("timestamp") or ""
            try:
                out_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if (now - out_time).total_seconds() / 86400.0 > days:
                    continue
            except Exception:
                pass
            outcomes.append(
                Outcome(
                    id=r["id"],
                    decision_id=r.get("decision_id", ""),
                    incident_id=r.get("incident_id", ""),
                    service_id=r.get("service_id", ""),
                    fault_type=r.get("fault_type", ""),
                    action=r.get("action", ""),
                    status=r.get("status", ""),
                    safety_score=float(r.get("safety_score", 0.0)),
                    composite_score=float(r.get("composite_score", 0.0)),
                    timestamp=ts_str,
                    project_id=project_id,
                )
            )
        return outcomes

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
