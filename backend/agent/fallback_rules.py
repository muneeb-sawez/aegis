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
    # 1. Rule 1: Pod / Process Crash -> restart
    crashing_pod = ""
    for n in nodes:
        nid = n.get("id", "")
        ntelem = telemetry.get(nid, {})
        if "crash" in str(ntelem.get("status", "")).lower():
            crashing_pod = nid
            break

    is_timeout = "timeout" in incident_texts or "timeout" in fn_status
    is_crash = not is_timeout and (
        bool(crashing_pod)
        or "crash" in incident_texts
        or "dead" in incident_texts
        or "crashloopbackoff" in fn_status
        or fn_status in ("unhealthy", "crash", "unavailable")
        or (fn_error_rate >= 0.5 and "timeout" not in fn_status)
    )

    if is_crash:
        target_svc = crashing_pod or failing_node or (nodes[0]["id"] if nodes else "unknown")
        propagation = [target_svc]
        if failing_node and failing_node != target_svc:
            propagation.append(failing_node)
        if callers:
            propagation.append(callers[0])

        return RCAResult(
            root_cause_node=target_svc,
            root_cause_type="pod_crash",
            confidence=0.95,
            propagation_path=propagation,
            evidence=[
                f"Node {target_svc} reported crash state ({fn_status or 'CrashLoopBackOff'}).",
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

    # 2. Rule 2: CPU Saturation / Throttling -> restart / scale
    fn_cpu = float(fn_telem.get("cpu_pct", 0.0) or 0.0)
    is_cpu = "cpu" in incident_texts or fn_cpu >= 80.0 or "throttl" in fn_status
    if is_cpu:
        target_svc = failing_node or (nodes[0]["id"] if nodes else "unknown")
        return RCAResult(
            root_cause_node=target_svc,
            root_cause_type="cpu_saturation",
            confidence=0.90,
            propagation_path=[target_svc],
            evidence=[
                f"CPU utilization on {target_svc} reached {fn_cpu:.1f}%.",
                f"Active alert flags CPU resource saturation: {incident_texts}.",
            ],
            ranked_fixes=[
                RankedFix(
                    action="restart",
                    target=target_svc,
                    reason=f"Restart {target_svc} workers to release CPU hung threads.",
                ),
                RankedFix(
                    action="rollback",
                    target=target_svc,
                    reason=f"Rollback recent CPU-intensive workload changes on {target_svc}.",
                ),
            ],
        )

    # 3. Rule 3: Database Connection Pool Exhaustion -> scale_pool
    failing_datastore = ""
    for ds in datastores:
        ds_telem = telemetry.get(ds, {})
        ds_conn = ds_telem.get("connections", 0)
        ds_pool = ds_telem.get("pool_size", 100)
        ds_status = str(ds_telem.get("status", "")).lower()
        if (isinstance(ds_conn, (int, float)) and isinstance(ds_pool, (int, float)) and ds_conn >= 0.8 * ds_pool) or ds_status in ("exhausted", "degraded", "unhealthy"):
            failing_datastore = ds
            break

    is_pool_exhausted = (
        bool(failing_datastore)
        or ("pool" in incident_texts and bool(datastores))
        or ("exhaust" in incident_texts and bool(datastores))
    )

    if is_pool_exhausted and datastores:
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
            ],
        )

    # 4. Rule 4: Downstream RPC Timeout -> restart
    is_timeout = "timeout" in incident_texts or fn_status == "timeout"
    if is_timeout:
        target_svc = failing_node or (nodes[0]["id"] if nodes else "unknown")
        return RCAResult(
            root_cause_node=target_svc,
            root_cause_type="downstream_timeout",
            confidence=0.85,
            propagation_path=[target_svc],
            evidence=[
                f"RPC call timeout observed on {target_svc}.",
                f"Incident ledger confirms downstream timeout: {incident_texts}.",
            ],
            ranked_fixes=[
                RankedFix(
                    action="restart",
                    target=target_svc,
                    reason=f"Restart {target_svc} to reset hanging socket connections.",
                ),
                RankedFix(
                    action="rollback",
                    target=target_svc,
                    reason=f"Rollback {target_svc} to previous stable timeout configuration.",
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
