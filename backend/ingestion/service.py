"""AEGIS Ingestion Service (Directive §3.B).

Orchestrates repository fetching, manifest parsing, idempotent graph updating,
and manual external-service registration.
"""

from __future__ import annotations

from typing import Any
from backend.graph import get_repository
from backend.graph.repository import Edge, Node
from backend.ingestion.docker_compose import parse_docker_compose
from backend.ingestion.github_fetcher import find_and_fetch_compose_manifest, parse_github_repo_url
from backend.ingestion.models import (
    ExternalServiceRegistration,
    IngestedEdge,
    IngestedNode,
    IngestionRequest,
    IngestionResult,
)


def merge_ingested_elements(
    nodes: list[IngestedNode],
    edges: list[IngestedEdge],
) -> tuple[int, int, int]:
    """Idempotently merge nodes and edges into the active GraphRepository."""
    repo = get_repository()
    # In NetworkX repo or Neo4j repo, update underlying graph
    # Check if networkx repo
    if hasattr(repo, "_graph"):
        G = repo._graph
        nodes_added = 0
        nodes_updated = 0
        edges_added = 0

        for n in nodes:
            if G.has_node(n.id):
                nodes_updated += 1
                # Update properties
                G.nodes[n.id].update(n.properties)
                G.nodes[n.id]["provenance"] = n.provenance
            else:
                nodes_added += 1
                G.add_node(n.id, label=n.label, provenance=n.provenance, **n.properties)

        for e in edges:
            # Ensure target exists
            if not G.has_node(e.target):
                G.add_node(e.target, label="Service", provenance="inferred")
                nodes_added += 1

            # Check if edge already exists with same type
            edge_exists = False
            if G.has_edge(e.source, e.target):
                for attrs in G.get_edge_data(e.source, e.target).values():
                    if attrs.get("type") == e.type:
                        edge_exists = True
                        break

            if not edge_exists:
                edges_added += 1
                G.add_edge(e.source, e.target, type=e.type, provenance=e.provenance, **e.properties)

        return nodes_added, nodes_updated, edges_added

    return len(nodes), 0, len(edges)


async def ingest_repository_or_manifest(req: IngestionRequest) -> IngestionResult:
    """Ingest a repository from GitHub or directly parse provided YAML."""
    source_desc = "Direct YAML"
    yaml_content = req.compose_yaml_content

    if not yaml_content and req.repo_url:
        clean_url = req.repo_url.strip().lower()
        from backend.ingestion.sample_repos import SAMPLE_REPOSITORIES

        # Check if explicitly requested as a built-in sample repository
        matched_sample = None
        if clean_url.startswith("sample:"):
            sample_slug = clean_url.split("sample:", 1)[1].strip()
            matched_sample = SAMPLE_REPOSITORIES.get(sample_slug)
        elif clean_url in SAMPLE_REPOSITORIES:
            matched_sample = SAMPLE_REPOSITORIES[clean_url]

        if matched_sample:
            yaml_content = matched_sample["yaml"]
            source_desc = f"Sample Repo: {matched_sample['slug']}"
        else:
            # Query actual GitHub repository via REST API
            owner, repo_name = parse_github_repo_url(req.repo_url)
            source_desc = f"GitHub: {owner}/{repo_name}"
            manifest_filename, yaml_content = await find_and_fetch_compose_manifest(
                owner, repo_name, branch=req.branch
            )
            source_desc += f" ({manifest_filename})"

    if not yaml_content:
        raise ValueError("Either 'repo_url' or 'compose_yaml_content' must be provided.")

    parsed_nodes, parsed_edges = parse_docker_compose(yaml_content)
    nodes_added, nodes_updated, edges_added = merge_ingested_elements(parsed_nodes, parsed_edges)

    repo = get_repository()
    current_topo = repo.get_topology()

    return IngestionResult(
        status="success",
        message=f"Successfully ingested manifest from {source_desc}.",
        source=source_desc,
        nodes_added=nodes_added,
        nodes_updated=nodes_updated,
        edges_added=edges_added,
        total_graph_nodes=len(current_topo.nodes),
        total_graph_edges=len(current_topo.edges),
        services_discovered=[n.id for n in parsed_nodes],
    )


def register_external_service(reg: ExternalServiceRegistration) -> dict[str, Any]:
    """Manually register an external vendor or API (e.g. Stripe, SendGrid)."""
    repo = get_repository()
    ext_node_id = f"ext-{reg.name.lower().replace(' ', '-')}"

    ext_node = IngestedNode(
        id=ext_node_id,
        label="ExternalService",
        properties={
            "name": reg.name,
            "category": reg.category,
            "endpoint_url": reg.endpoint_url,
            "health_url": reg.health_url,
            "status": "healthy",
            "is_external": True,
            "description": reg.description,
        },
        provenance="manual",
    )

    dep_edge = IngestedEdge(
        source=reg.dependent_service_id,
        target=ext_node_id,
        type="DEPENDS_ON",
        properties={"criticality": "high", "is_external": True},
        provenance="manual",
    )

    nodes_added, _, edges_added = merge_ingested_elements([ext_node], [dep_edge])

    return {
        "status": "success",
        "external_service_id": ext_node_id,
        "dependent_service": reg.dependent_service_id,
        "nodes_added": nodes_added,
        "edges_added": edges_added,
        "message": f"External service '{reg.name}' registered and linked to '{reg.dependent_service_id}'.",
    }
