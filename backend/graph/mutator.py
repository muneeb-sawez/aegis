"""AEGIS Graph Mutation and Dynamic Topology Persistence Service.

Provides atomic, thread-safe graph mutations (add/update/delete nodes and edges)
and handles automatic disk synchronization to data/graphs/{project_id}.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from backend.graph import get_repository
from backend.graph.networkx_repo import NetworkXGraphRepository
from backend.graph.repository import Edge, Node

logger = logging.getLogger("aegis.graph.mutator")


class GraphMutator:
    """Manages dynamic graph mutations and file persistence for multi-tenant topologies."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (Path("data") / "graphs")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_networkx_graph(self, project_id: str = "demo"):
        """Retrieve the NetworkX MultiDiGraph for the given project."""
        repo = get_repository()
        if hasattr(repo, "_get_project_graph"):
            return repo._get_project_graph(project_id)
        if hasattr(repo, "_graph"):
            return repo._graph
        return None

    def add_node(
        self,
        project_id: str,
        node_id: str,
        label: str = "Service",
        properties: Optional[dict[str, Any]] = None,
        persist: bool = True,
    ) -> Node:
        """Add or update a node in the graph and optionally persist to disk."""
        clean_id = node_id.strip()
        props = properties.copy() if properties else {}
        props.setdefault("status", "healthy")
        props.setdefault("provenance", "ai-copilot")

        repo = get_repository()
        G = self._get_networkx_graph(project_id)
        if G is not None:
            clean_props = {
                k: v for k, v in props.items()
                if k not in ("label", "project_id")
            }
            if G.has_node(clean_id):
                G.nodes[clean_id].update(clean_props)
                G.nodes[clean_id]["label"] = label
                G.nodes[clean_id]["project_id"] = project_id
            else:
                G.add_node(clean_id, label=label, project_id=project_id, **clean_props)

        if persist:
            self.save_project_graph(project_id)

        return Node(id=clean_id, label=label, project_id=project_id, properties=props)

    def update_node(
        self,
        project_id: str,
        node_id: str,
        label: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
        persist: bool = True,
    ) -> Node:
        """Update properties and/or label of an existing node."""
        clean_id = node_id.strip()
        G = self._get_networkx_graph(project_id)
        if G is None:
            raise RuntimeError("Underlying graph repository does not support direct mutation")

        if not G.has_node(clean_id):
            # If node does not exist, create it
            return self.add_node(
                project_id=project_id,
                node_id=clean_id,
                label=label or "Service",
                properties=properties,
                persist=persist,
            )

        current_attrs = dict(G.nodes[clean_id])
        current_label = label or current_attrs.get("label", "Service")
        new_props = {k: v for k, v in current_attrs.items() if k not in ("label", "project_id")}
        if properties:
            new_props.update(properties)

        clean_props = {k: v for k, v in new_props.items() if k not in ("label", "project_id")}
        G.nodes[clean_id].update(clean_props)
        G.nodes[clean_id]["label"] = current_label
        G.nodes[clean_id]["project_id"] = project_id

        if persist:
            self.save_project_graph(project_id)

        return Node(id=clean_id, label=current_label, project_id=project_id, properties=new_props)

    def delete_node(self, project_id: str, node_id: str, persist: bool = True) -> bool:
        """Remove a node and its incident edges from the project graph."""
        clean_id = node_id.strip()
        G = self._get_networkx_graph(project_id)
        if G is None or not G.has_node(clean_id):
            return False

        G.remove_node(clean_id)

        if persist:
            self.save_project_graph(project_id)

        return True

    def add_edge(
        self,
        project_id: str,
        source: str,
        target: str,
        edge_type: str = "CALLS",
        properties: Optional[dict[str, Any]] = None,
        persist: bool = True,
    ) -> Edge:
        """Connect source node to target node with the given edge type."""
        src = source.strip()
        tgt = target.strip()
        props = properties.copy() if properties else {}
        props.setdefault("provenance", "ai-copilot")

        G = self._get_networkx_graph(project_id)
        if G is not None:
            # Ensure endpoints exist
            if not G.has_node(src):
                G.add_node(src, label="Service", project_id=project_id, provenance="ai-inferred", status="healthy")
            if not G.has_node(tgt):
                G.add_node(tgt, label="Service", project_id=project_id, provenance="ai-inferred", status="healthy")

            # Check if matching edge already exists
            exists = False
            if G.has_edge(src, tgt):
                for attrs in G.get_edge_data(src, tgt).values():
                    if attrs.get("type") == edge_type:
                        attrs.update(props)
                        exists = True
                        break

            if not exists:
                clean_props = {k: v for k, v in props.items() if k not in ("type", "project_id")}
                G.add_edge(src, tgt, type=edge_type, project_id=project_id, **clean_props)

        if persist:
            self.save_project_graph(project_id)

        return Edge(source=src, target=tgt, type=edge_type, project_id=project_id, properties=props)

    def update_edge(
        self,
        project_id: str,
        source: str,
        old_target: str,
        new_target: Optional[str] = None,
        new_type: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
        persist: bool = True,
    ) -> Edge:
        """Update or rewire an edge: change target, change relationship type, or update properties."""
        src = source.strip()
        old_tgt = old_target.strip()
        target = (new_target or old_tgt).strip()

        G = self._get_networkx_graph(project_id)
        if G is None:
            raise RuntimeError("Underlying graph repository not available")

        # Capture old edge properties if present
        existing_props: dict[str, Any] = {}
        detected_type = "CALLS"
        if G.has_edge(src, old_tgt):
            edge_data = G.get_edge_data(src, old_tgt)
            if edge_data:
                first_key = next(iter(edge_data))
                first_attrs = edge_data[first_key]
                detected_type = first_attrs.get("type", "CALLS")
                existing_props = {
                    k: v for k, v in first_attrs.items()
                    if k not in ("type", "project_id")
                }

        # If re-routing target or replacing type
        final_type = new_type or detected_type
        if properties:
            existing_props.update(properties)

        # Remove old edge
        self.delete_edge(project_id=project_id, source=src, target=old_tgt, edge_type=None, persist=False)

        # Add updated edge
        new_edge = self.add_edge(
            project_id=project_id,
            source=src,
            target=target,
            edge_type=final_type,
            properties=existing_props,
            persist=persist,
        )
        return new_edge

    def delete_edge(
        self,
        project_id: str,
        source: str,
        target: str,
        edge_type: Optional[str] = None,
        persist: bool = True,
    ) -> bool:
        """Delete edge(s) matching source, target, and optional edge type."""
        src = source.strip()
        tgt = target.strip()

        G = self._get_networkx_graph(project_id)
        if G is None or not G.has_edge(src, tgt):
            return False

        if edge_type is None:
            G.remove_edge(src, tgt)
            # Remove any remaining parallel edges between src and tgt
            while G.has_edge(src, tgt):
                G.remove_edge(src, tgt)
        else:
            edge_data = G.get_edge_data(src, tgt)
            keys_to_remove = [
                k for k, attrs in edge_data.items()
                if attrs.get("type") == edge_type
            ]
            for k in keys_to_remove:
                G.remove_edge(src, tgt, key=k)

        if persist:
            self.save_project_graph(project_id)

        return True

    def save_project_graph(self, project_id: str) -> str:
        """Persist current in-memory topology to data/graphs/{project_id}.json."""
        G = self._get_networkx_graph(project_id)
        if G is None:
            return ""

        nodes_list = []
        for nid, attrs in G.nodes(data=True):
            n_attrs = dict(attrs)
            n_label = n_attrs.pop("label", "Service")
            n_attrs.pop("project_id", None)
            nodes_list.append({
                "id": str(nid),
                "label": str(n_label),
                "project_id": project_id,
                "properties": n_attrs,
            })

        edges_list = []
        for u, v, attrs in G.edges(data=True):
            e_attrs = dict(attrs)
            e_type = e_attrs.pop("type", "CALLS")
            e_attrs.pop("project_id", None)
            edges_list.append({
                "source": str(u),
                "target": str(v),
                "type": str(e_type),
                "project_id": project_id,
                "properties": e_attrs,
            })

        out_path = self.data_dir / f"{project_id}.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"nodes": nodes_list, "edges": edges_list}, f, indent=2)
            logger.info("Persisted project graph '%s' (%d nodes, %d edges) to %s", project_id, len(nodes_list), len(edges_list), out_path)
            return str(out_path)
        except Exception as e:
            logger.error("Failed persisting project graph '%s': %s", project_id, e)
            return ""


_mutator_instance: Optional[GraphMutator] = None


def get_graph_mutator() -> GraphMutator:
    """Return singleton GraphMutator instance."""
    global _mutator_instance
    if _mutator_instance is None:
        _mutator_instance = GraphMutator()
    return _mutator_instance
