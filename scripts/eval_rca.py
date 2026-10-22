#!/usr/bin/env python3
"""Evaluate RCA accuracy for each fault type.

For each fault type (pool_exhaustion, pod_crash, latency_spike) the script:
  1. Resets the graph repository.
  2. Injects the fault ten times.
  3. Adds an incident reflecting the fault.
  4. Builds the context and runs the RCA diagnosis.
  5. Checks the result against the known ground‑truth root cause node and type.

The script prints a simple accuracy line per fault type, e.g.:
    pool_exhaustion: 8/10 (80.0%)
Only the measured numbers are printed, as requested.
"""

import sys
import os
from collections import defaultdict

# Ensure the project root is in the Python path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import internal modules (graph repo, fault injection, context builder, RCA engine)
from backend.graph import get_repository
from backend.api.routes_chaos import inject_fault
from backend.agent.context import build_context
from backend.agent.rca import diagnose_incident

# Mapping from fault ID to ground‑truth expectations.
# Each entry provides a function that, given the target service, returns a set of acceptable
# root‑cause node IDs, and a substring that must appear in the root_cause_type.
GROUND_TRUTH = {
    "pool_exhaustion": {
        "nodes": lambda svc: {f"postgres-{svc}" if svc != "paymentservice" else "postgres-payment"},
        "type_substr": "pool",
    },
    "pod_crash": {
        "nodes": lambda svc: {f"{svc}-pod-1", svc},  # fallback may return pod or service node
        "type_substr": "crash",
    },
    "latency_spike": {
        "nodes": lambda svc: {svc},
        "type_substr": "degraded",
    },
}

def evaluate_fault(fault_id: str, iterations: int = 10) -> tuple[int, int]:
    """Run *iterations* trials for *fault_id* and return (correct, total)."""
    correct = 0
    repo = get_repository()
    for i in range(iterations):
        # Reset the graph to a clean baseline before each injection.
        repo.reset()

        # Inject the fault; the request defaults to paymentservice if not supplied.
        req = type("Req", (), {"fault_id": fault_id, "target_service": None, "intensity": 1.0})()
        resp = inject_fault(req)

        # Create an incident that mirrors the fault description.
        inc = repo.add_incident(service_id=resp.target_service, description=resp.message)

        # Build the context for this incident.
        ctx = build_context(inc.id, repo=repo)

        # Run the RCA diagnosis.
        result = diagnose_incident(ctx)

        # Determine if the result matches ground truth.
        expected = GROUND_TRUTH.get(fault_id)
        if expected:
            valid_nodes = expected["nodes"](resp.target_service)
            type_ok = expected["type_substr"].lower() in result.root_cause_type.lower()
            node_ok = result.root_cause_node in valid_nodes
            if type_ok and node_ok:
                correct += 1
    return correct, iterations

def main():
    total_results = {}
    for fault in ["pool_exhaustion", "pod_crash", "latency_spike"]:
        correct, total = evaluate_fault(fault)
        total_results[fault] = (correct, total)

    # Print only the measured numbers.
    for fault, (correct, total) in total_results.items():
        accuracy = (correct / total) * 100 if total else 0.0
        print(f"{fault}: {correct}/{total} ({accuracy:.1f}%)")

if __name__ == "__main__":
    sys.exit(main())
