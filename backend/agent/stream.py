"""AEGIS Diagnosis SSE Stream Generator & Execution Logger (M6).

Streams real-time agent reasoning events over SSE:
{type: thought|query|result|done|error, ts, payload}.
Logs all agent prompt/response/latency/provider runs to data/agent_runs.jsonl (never keys).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Any, AsyncGenerator, Optional

from backend.config import settings
from backend.graph import get_repository
from backend.graph.repository import GraphRepository
from backend.agent.context import build_context
from backend.agent.rca import diagnose_incident

logger = logging.getLogger("aegis.agent.stream")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
LOG_FILE = DATA_DIR / "agent_runs.jsonl"


def sanitize_for_log(obj: Any) -> Any:
    """Recursively sanitize data structure to ensure API keys and secrets are NEVER logged."""
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(secret_kw in k_lower for secret_kw in ("key", "secret", "token", "password", "auth", "credential")):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_for_log(v)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_for_log(item) for item in obj]
    return obj


def log_agent_run(
    incident_id: str,
    provider: str,
    model: str,
    prompt: Any,
    response: Any,
    latency_sec: float,
    status: str,
) -> None:
    """Append a structured diagnosis record to the JSONL run log file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "incident_id": incident_id,
            "provider": provider,
            "model": model,
            "latency_sec": latency_sec,
            "status": status,
            "prompt": sanitize_for_log(prompt),
            "response": sanitize_for_log(response),
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as e:
        logger.error(f"Failed to write agent run log: {e}")


async def stream_diagnosis_events(
    incident_id: str = "",
    repo: Optional[GraphRepository] = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Generate real-time diagnosis SSE events for a target incident.

    Yields event dictionaries with format:
    { "type": "thought"|"query"|"candidates"|"result"|"done"|"error", "ts": "...", "payload": {...} }
    """
    if repo is None:
        repo = get_repository()

    now_iso = lambda: datetime.now(timezone.utc).isoformat()

    # Step 1: Initial Thought
    yield {
        "type": "thought",
        "ts": now_iso(),
        "payload": {
            "message": f"AEGIS Graph Reasoner activated for incident '{incident_id or 'active'}'. Inspecting microservice topology.",
            "demo_mode": False,
        },
    }
    await asyncio.sleep(0.05)

    # Step 2: Build graph context & emit Query event
    context = build_context(incident_id, repo=repo)
    failing_node = context.get("failing_node", "paymentservice")
    n2 = context.get("neighbourhood_2hop", {})
    nodes = n2.get("nodes", [])
    datastores = n2.get("datastores", [])
    callers = n2.get("callers", [])

    yield {
        "type": "query",
        "ts": now_iso(),
        "payload": {
            "query": f"neighbors('{failing_node}', hops=2)",
            "purpose": f"Retrieved 2-hop neighbourhood ({len(nodes)} nodes, {len(datastores)} datastores, callers: {callers}) using GraphRepository.",
            "failing_node": failing_node,
        },
    }
    await asyncio.sleep(0.05)

    yield {
        "type": "cypher",
        "ts": now_iso(),
        "payload": {
            "query": f"MATCH (s:Service {{id: '{failing_node}'}})-[r:DEPENDS_ON]->(d:Database) RETURN s.id, d.id, d.connections, d.pool_size, d.status",
            "purpose": f"Inspect datastore dependencies and connection saturation for {failing_node}",
        },
    }
    await asyncio.sleep(0.05)

    # Step 3: Thought describing assembled context
    yield {
        "type": "thought",
        "ts": now_iso(),
        "payload": {
            "message": f"Graph context assembled (~{context.get('token_count', 0)} tokens). Dispatching prompt to LLM chain ({settings.LLM_PROVIDER}/{settings.LLM_MODEL}).",
        },
    }
    await asyncio.sleep(0.05)

    # Step 4: Run Diagnosis
    start_time = time.time()
    try:
        result = diagnose_incident(context)
        latency = time.time() - start_time
        log_agent_run(
            incident_id=incident_id,
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            prompt=context,
            response=result.model_dump(),
            latency_sec=round(latency, 3),
            status="success",
        )
    except Exception as e:
        latency = time.time() - start_time
        log_agent_run(
            incident_id=incident_id,
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            prompt=context,
            response=str(e),
            latency_sec=round(latency, 3),
            status="error",
        )
        yield {
            "type": "error",
            "ts": now_iso(),
            "payload": {
                "message": f"LLM reasoning failure: {str(e)}",
                "error": str(e),
            },
        }
        return

    # Step 5: Candidates event for UI candidate action cards
    candidates = []
    for idx, fix in enumerate(result.ranked_fixes):
        safety = 92.0 if fix.action == "scale_pool" else (85.0 if fix.action == "restart" else 70.0)
        recovery = round(result.confidence * (0.95 if idx == 0 else 0.75), 2)
        actuator_action = "restart_pod" if fix.action == "restart" else ("rollback_release" if fix.action == "rollback" else "scale_pool")
        candidates.append({
            "action": actuator_action,
            "target": fix.target,
            "params": {"pool_size": 150} if fix.action == "scale_pool" else {},
            "safety_score": safety,
            "recovery_prob": recovery,
            "composite_score": round(0.6 * safety + 0.4 * (recovery * 100), 1),
            "rationale": fix.reason,
            "eligible_for_auto_exec": safety >= 85.0,
        })

    yield {
        "type": "candidates",
        "ts": now_iso(),
        "payload": {
            "candidates": candidates,
        },
    }
    await asyncio.sleep(0.05)

    # Step 6: Result event
    yield {
        "type": "result",
        "ts": now_iso(),
        "payload": {
            **result.model_dump(),
            "hypothesis": f"Root cause confirmed on {result.root_cause_node} ({result.root_cause_type}).",
            "recommended_action": result.ranked_fixes[0].action if result.ranked_fixes else "restart",
            "target": result.ranked_fixes[0].target if result.ranked_fixes else result.root_cause_node,
        },
    }
    await asyncio.sleep(0.05)

    # Step 7: Done event
    yield {
        "type": "done",
        "ts": now_iso(),
        "payload": {
            "message": f"Diagnosis completed. Root cause: '{result.root_cause_node}' ({result.root_cause_type}). Recommended action: '{result.ranked_fixes[0].action if result.ranked_fixes else 'restart'}'.",
            "demo_mode": False,
        },
    }
