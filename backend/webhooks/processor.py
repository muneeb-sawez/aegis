"""AEGIS Webhook Event Processor — Intelligent Breaking Change Analyzer.

Processes GitHub webhook events and runs the full AEGIS risk pipeline:

1. Fetches the LIVE unified git diff for any incoming PR via GitHub REST API.
2. Runs the Cohere Command A (OCI GenAI) three-stage reasoning brain to detect
   breaking changes dynamically from raw patch text — zero hardcoded assumptions.
3. Traverses the service topology graph (Reverse BFS) to compute blast radius.
4. Calculates composite risk score: Risk = 0.35·B + 0.30·C + 0.15·D + 0.20·H
5. Posts an intelligent, evidence-backed risk report as a GitHub PR comment.
6. Updates the idempotency store and Mission Control Dashboard.

Works on ANY PR on ANY repository — not limited to predefined scenarios.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional
import httpx

from backend.graph import get_repository
from backend.sim.blast_radius import calculate_blast_radius
from backend.sim.risk import PRPayload, assess_change_risk
from backend.webhooks.git_diff_analyzer import fetch_pr_file_diffs, resolve_github_token_for_project
from backend.webhooks.github_commenter import format_risk_comment, post_or_update_pr_comment
from backend.webhooks.store import get_delivery_store
from backend.config import settings

logger = logging.getLogger("aegis.webhooks")

# Idempotent write registry: (project_id, repo, pr_id) -> last assessment
_IDEMPOTENT_PR_ASSESSMENTS: dict[str, dict[str, Any]] = {}



def extract_changed_files(payload: dict[str, Any], event_type: str) -> list[str]:
    """Extract changed files list from GitHub webhook payload.

    Supports:
    - pull_request events (via changed_files_list, files, or head commit)
    - push events (via commits: added + modified + removed)
    - custom/test payload changed_files field
    """
    changed: set[str] = set()

    # 1. Direct changed_files field (common in tests & webhooks payloads)
    for key in ("changed_files_list", "changed_files"):
        if key in payload and isinstance(payload[key], list):
            changed.update(payload[key])

    # 2. Pull Request payload
    if event_type == "pull_request" or "pull_request" in payload:
        pr_obj = payload.get("pull_request", {})
        if isinstance(pr_obj, dict):
            for key in ("changed_files_list", "changed_files"):
                if key in pr_obj and isinstance(pr_obj[key], list):
                    changed.update(pr_obj[key])
            if "files" in pr_obj and isinstance(pr_obj["files"], list):
                for f in pr_obj["files"]:
                    filename = f.get("filename") if isinstance(f, dict) else str(f)
                    if filename:
                        changed.add(filename)

    # 3. Push payload commits
    commits = payload.get("commits", [])
    if isinstance(commits, list):
        for commit in commits:
            if isinstance(commit, dict):
                for key in ("added", "modified", "removed"):
                    files = commit.get(key, [])
                    if isinstance(files, list):
                        changed.update(files)

    return sorted(list(changed))


def map_files_to_services(changed_files: list[str], known_services: set[str]) -> dict[str, list[str]]:
    """Map changed file paths to corresponding microservice node IDs.

    Ignores unrelated files (docs, CI scripts, markdown) and only scans code/schema files.
    """
    service_files: dict[str, list[str]] = {}

    for file_path in changed_files:
        clean = file_path.replace("\\", "/").strip().lower()

        # Skip documentation and non-functional files
        if clean.endswith((".md", ".txt", ".png", ".jpg", ".svg", ".gitignore", ".editorconfig")):
            continue

        matched_svc: Optional[str] = None

        # Check path patterns: services/{service_name}/... or src/{service_name}/...
        parts = clean.split("/")
        for i, part in enumerate(parts):
            if part in ("services", "src", "apps", "microservices") and i + 1 < len(parts):
                candidate = parts[i + 1]
                if candidate in known_services:
                    matched_svc = candidate
                    break

        # Fallback: check if any known service name is in the path
        if not matched_svc:
            for svc in known_services:
                if svc.lower() in clean:
                    matched_svc = svc
                    break

        if matched_svc:
            if matched_svc not in service_files:
                service_files[matched_svc] = []
            service_files[matched_svc].append(file_path)

    return service_files


async def process_github_event(
    event_type: str,
    payload: dict[str, Any],
    delivery_id: str,
    project_id: str = "demo",
    github_client: Optional[httpx.AsyncClient] = None,
) -> dict[str, Any]:
    """Intelligent GitHub webhook processor.

    For pull_request events:
    1. Fetches the live PR diff via GitHub API (no hardcoded payloads).
    2. Runs the Cohere Command A three-stage reasoning brain on the raw patch.
    3. Computes blast radius via Reverse BFS graph traversal.
    4. Calculates composite risk score.
    5. Posts an enriched risk report comment to the GitHub PR.
    """
    store = get_delivery_store()
    logger.info(
        "PROCESSING_WEBHOOK event=%r delivery=%r project=%r",
        event_type, delivery_id, project_id,
    )

    # Handle Ping event
    if event_type == "ping":
        result = {"status": "pong", "zen": payload.get("zen", "Graph grounded resilience.")}
        store.update_delivery_result(delivery_id, "completed", result)
        return result

    # ── 1. Extract changed files list (for metadata only) ─────────────────────
    changed_files = extract_changed_files(payload, event_type)
    repo_graph = get_repository()
    topo = repo_graph.get_topology(project_id=project_id)
    known_services = {n.id for n in topo.nodes}

    # Map changed file paths to service names (for initial target_svc guess)
    service_file_map = map_files_to_services(changed_files, known_services)

    # ── 2. Resolve PR metadata ─────────────────────────────────────────────────
    pr_id = "PR-WEBHOOK"
    pr_title = "GitHub Webhook Change"
    target_svc = "unknown"
    pr_num_raw: Optional[int] = None

    repo_info = payload.get("repository", {})
    repo_full_name = repo_info.get("full_name", "") if isinstance(repo_info, dict) else ""
    if "/" in repo_full_name:
        owner, repo_name_only = repo_full_name.split("/", 1)
    else:
        owner = repo_info.get("owner", {}).get("login", "") if isinstance(repo_info.get("owner"), dict) else ""
        repo_name_only = repo_info.get("name", "") if isinstance(repo_info, dict) else ""

    if "pull_request" in payload and isinstance(payload["pull_request"], dict):
        pr_data = payload["pull_request"]
        number = pr_data.get("number", "0")
        pr_id = f"PR-{number}" if not str(number).startswith("PR-") else str(number)
        pr_title = pr_data.get("title", pr_title)
        pr_num_raw = int(number) if str(number).isdigit() else None

    # Initial service guess from changed files
    if service_file_map:
        target_svc = next(iter(service_file_map.keys()))
    elif payload.get("target_service") and payload["target_service"] in known_services:
        target_svc = payload["target_service"]

    # ── 3. Fetch live git diff from GitHub (the intelligence begins here) ──────
    # Lazy import here to avoid circular import at module load time:
    # webhooks/__init__ -> processor -> pr_reasoner -> git_diff_analyzer -> webhooks/__init__
    from backend.agent.pr_reasoner import reason_about_pr  # noqa: PLC0415

    reasoning_result = None
    file_diffs = []

    if pr_num_raw and owner and repo_name_only:
        github_token = resolve_github_token_for_project(
            project_id, repo_full_name, fallback_token=settings.GITHUB_TOKEN
        )
        if github_token:
            try:
                file_diffs = await fetch_pr_file_diffs(
                    owner=owner,
                    repo=repo_name_only,
                    pr_number=pr_num_raw,
                    token=github_token,
                    client=github_client,
                )
                logger.info("DIFF_FETCHED pr=%r files=%d", pr_id, len(file_diffs))
            except Exception as exc:
                logger.warning("DIFF_FETCH_FAILED pr=%r error=%s", pr_id, exc)

    # ── 4. Run graph blast radius first (needed as input to Stage 3) ──────────
    b_score, callers, caller_details = calculate_blast_radius(
        target_svc if target_svc != "unknown" else (next(iter(known_services), "demo")),
        repo_graph,
        project_id=project_id,
    )

    # ── 5. Run the Cohere Command A Reasoning Brain ────────────────────────────
    old_schema: Optional[dict] = payload.get("old_schema")
    new_schema: Optional[dict] = payload.get("new_schema")

    if file_diffs:
        try:
            reasoning_result = await reason_about_pr(
                file_diffs=file_diffs,
                pr_number=pr_num_raw or 0,
                repo=repo_full_name,
                target_service=target_svc,
                graph_callers=caller_details,
                client=github_client,
            )
            # Override target service if the brain inferred a better one
            if reasoning_result.target_service and reasoning_result.target_service != "unknown":
                target_svc = reasoning_result.target_service
            # Use LLM-extracted schemas (zero hardcoding)
            if reasoning_result.old_schema:
                old_schema = reasoning_result.old_schema
            if reasoning_result.new_schema:
                new_schema = reasoning_result.new_schema

            logger.info(
                "BRAIN_COMPLETE pr=%r breaking=%s severity=%.1f fallback=%s",
                pr_id, reasoning_result.is_breaking,
                reasoning_result.severity, reasoning_result.fallback_used,
            )
        except Exception as exc:
            logger.warning("BRAIN_FAILED pr=%r error=%s", pr_id, exc)

    # ── 6. Assess risk using the composite formula ─────────────────────────────
    pr_payload = PRPayload(
        id=pr_id,
        title=pr_title,
        target_service=target_svc,
        project_id=project_id,
        old_schema=old_schema,
        new_schema=new_schema,
    )
    assessment = assess_change_risk(pr_payload, repo=repo_graph)

    # ── 7. Idempotent write ────────────────────────────────────────────────────
    idempotent_key = f"{project_id}:{repo_full_name}:{pr_id}"
    assessment_data = assessment.model_dump()
    _IDEMPOTENT_PR_ASSESSMENTS[idempotent_key] = assessment_data

    # Build breaking changes list for the comment
    breaking_changes: list[str] = []
    annotated_blast_paths: list[dict] = []
    llm_reasoning = ""
    triage_summary: list[dict] = []
    fallback_used = True

    if reasoning_result:
        breaking_changes = [bc.description for bc in reasoning_result.all_breaking_changes]
        annotated_blast_paths = [p.model_dump() for p in reasoning_result.annotated_blast_paths]
        llm_reasoning = reasoning_result.llm_reasoning
        triage_summary = [t.model_dump() for t in reasoning_result.triage_summary]
        fallback_used = reasoning_result.fallback_used
    else:
        # Fallback: use contract_diff breaking changes from the formula result
        breaking_changes = [
            b.get("description", str(b)) if isinstance(b, dict) else str(b)
            for b in getattr(assessment.contract_diff, "breaking_changes", [])
        ]

    summary_result = {
        "status": "completed",
        "delivery_id": delivery_id,
        "pr_id": pr_id,
        "target_service": target_svc,
        "changed_files_count": len(changed_files),
        "changed_files": changed_files,
        "affected_services": list(service_file_map.keys()),
        "risk_score": assessment.risk_score,
        "verdict": assessment.verdict,
        "idempotent_key": idempotent_key,
        "breaking_changes_detected": len(breaking_changes),
        "llm_fallback_used": fallback_used,
        "files_analyzed": len(file_diffs),
    }

    # ── 8. Post enriched PR comment ────────────────────────────────────────────
    action = payload.get("action", "")
    is_pr_action = event_type == "pull_request" and (
        action in ("opened", "synchronize", "reopened") or not action
    )

    if is_pr_action and owner and repo_name_only and pr_num_raw is not None:
        try:
            blast_services = [
                d["node"] for d in assessment.blast_details
                if isinstance(d, dict) and "node" in d
            ]
            comment_body = format_risk_comment(
                pr_number=pr_num_raw,
                target_service=target_svc,
                risk_score=assessment.risk_score,
                blast_radius=blast_services,
                breaking_changes=breaking_changes,
                annotated_blast_paths=annotated_blast_paths,
                llm_reasoning=llm_reasoning,
                triage_summary=triage_summary,
                fallback_used=fallback_used,
                project_id=project_id,
            )
            comment_result = await post_or_update_pr_comment(
                owner=owner,
                repo=repo_name_only,
                pr_number=pr_num_raw,
                comment_body=comment_body,
                token=github_token,
                client=github_client,
            )
            summary_result["comment"] = comment_result
        except Exception as exc:
            logger.warning(
                "FAILED_PR_COMMENT owner=%r repo=%r pr=%r error=%s",
                owner, repo_name_only, pr_num_raw, exc,
            )
            summary_result["comment"] = {"status": "error", "error": str(exc)}

    store.update_delivery_result(delivery_id, "completed", summary_result)
    logger.info(
        "COMPLETED_WEBHOOK delivery=%r pr=%r risk=%.1f verdict=%r",
        delivery_id, pr_id, assessment.risk_score, assessment.verdict,
    )
    return summary_result




def get_pr_assessment(project_id: str, repo: str, pr_id: str) -> Optional[dict[str, Any]]:
    """Retrieve idempotent PR risk assessment."""
    key = f"{project_id}:{repo}:{pr_id}"
    return _IDEMPOTENT_PR_ASSESSMENTS.get(key)
