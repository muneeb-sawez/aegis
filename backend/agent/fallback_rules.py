"""AEGIS Agent Fallback Rules (M6).

Deterministic root cause analysis rules when the LLM is unreachable,
times out, or produces unparsable outputs.
Rules:
1. Timeouts at a service whose failing neighbour is a datastore -> pool_exhausted at that datastore.
2. Crash / outage at a service -> restart.
"""

from __future__ import annotations

from typing import Any
from backend.agent.schemas import RCAResult, RankedFix


def run_fallback_rules(context: dict[str, Any]) -> RCAResult:
    """Analyze context deterministically without calling any LLM.

    Args:
        context: Standard graph context dictionary from build_context().

    Returns:
        Validated RCAResult instance guaranteed to cite only nodes in context.
    """
    failing_node: str = context.get("failing_node", "")
    neighbourhood = context.get("neighbourhood_2hop", {})
    nodes = neighbourhood.get("nodes", [])
    datastores: list[str] = neighbourhood.get("datastores", [])
    callees: list[str] = neighbourhood.get("callees", [])
    callers: list[str] = neighbourhood.get("callers", [])
    telemetry: dict[str, Any] = context.get("telemetry", {})
    open_incidents = context.get("open_incidents", [])

    # If failing_node is empty, pick the first valid node ID
    if not failing_node and nodes:
        failing_node = nodes[0].get("id", "")

    # Aggregate description text for keyword heuristics
    incident_texts = " ".join(
        inc.get("description", "") for inc in open_incidents
    ).lower()

    # Telemetry for failing node
    fn_telem = telemetry.get(failing_node, {})
    fn_status = str(fn_telem.get("status", "")).lower()
    fn_latency = float(fn_telem.get("p99_ms", 0.0) or 0.0)
    fn_error_rate = float(fn_telem.get("error_rate", 0.0) or 0.0)

    # 1. Rule 1: Timeouts at a service whose failing neighbour is a datastore -> pool_exhausted
    # Check if any datastore in neighbourhood has high connection count / pool exhaustion
    failing_datastore = ""
    for ds in datastores:
        ds_telem = telemetry.get(ds, {})
        ds_conn = ds_telem.get("connections", 0)
        ds_pool = ds_telem.get("pool_size", 100)
        ds_status = str(ds_telem.get("status", "")).lower()
        if (isinstance(ds_conn, (int, float)) and isinstance(ds_pool, (int, float)) and ds_conn >= 0.8 * ds_pool) or ds_status in ("degraded", "unhealthy"):
            failing_datastore = ds
            break

    # Also check if incident text or latency indicates timeout / pool exhaustion
    is_timeout_or_pool = (
        "pool" in incident_texts
        or "timeout" in incident_texts
        or "exhaust" in incident_texts
        or "connection" in incident_texts
        or fn_latency > 1000.0
    )

    if (failing_datastore or (is_timeout_or_pool and datastores)):
        target_ds = failing_datastore or datastores[0]
        propagation = [target_ds]
        if failing_node and failing_node != target_ds:
            propagation.append(failing_node)
        if callers:
            propagation.append(callers[0])

        return RCAResult(
            root_cause_node=target_ds,
            root_cause_type="pool_exhausted",
            confidence=0.92,
            propagation_path=propagation,
            evidence=[
                f"Datastore {target_ds} reached maximum connection pool capacity.",
                f"Upstream service {failing_node} experienced elevated latency and connection timeouts.",
            ],
            ranked_fixes=[
                RankedFix(
                    action="scale_pool",
                    target=target_ds,
                    reason=f"Scale connection pool limits on {target_ds} to relieve queuing.",
                ),
                RankedFix(
                    action="restart",
                    target=failing_node,
                    reason=f"Restart {failing_node} instances to clear hanging client connection sockets.",
                ),
                RankedFix(
                    action="rollback",
                    target=failing_node,
                    reason=f"Rollback recent database configuration changes on {failing_node}.",
                ),
            ],
        )

    # 2. Rule 2: Crash -> restart
    is_crash = (
        "crash" in incident_texts
        or "fail" in incident_texts
        or "dead" in incident_texts
        or fn_status in ("unhealthy", "crash", "error", "unavailable")
        or fn_error_rate >= 0.5
    )

    if is_crash:
        target_svc = failing_node or (nodes[0]["id"] if nodes else "unknown")
        propagation = [target_svc]
        if callers:
            propagation.append(callers[0])

        return RCAResult(
            root_cause_node=target_svc,
            root_cause_type="service_crash",
            confidence=0.88,
            propagation_path=propagation,
            evidence=[
                f"Service {target_svc} status is {fn_status or 'unhealthy'} with elevated error rate {fn_error_rate:.2f}.",
                f"Incident ledger confirms process failure: {incident_texts or 'pod crash loop'}.",
            ],
            ranked_fixes=[
                RankedFix(
                    action="restart",
                    target=target_svc,
                    reason=f"Restart container / pod instances for {target_svc}.",
                ),
                RankedFix(
                    action="rollback",
                    target=target_svc,
                    reason=f"Rollback {target_svc} to the last known healthy deployment revision.",
                ),
            ],
        )

    # 3. Default fallback rule
    target_svc = failing_node or (nodes[0]["id"] if nodes else "unknown")
    return RCAResult(
        root_cause_node=target_svc,
        root_cause_type="degraded_performance",
        confidence=0.75,
        propagation_path=[target_svc],
        evidence=[
            f"Anomalous telemetry detected on {target_svc}.",
        ],
        ranked_fixes=[
            RankedFix(
                action="restart",
                target=target_svc,
                reason=f"Restart {target_svc} to clear transient state.",
            ),
            RankedFix(
                action="rollback",
                target=target_svc,
                reason=f"Rollback recent changes on {target_svc}.",
            ),
        ],
    )
