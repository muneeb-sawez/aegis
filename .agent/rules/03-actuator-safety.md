---
trigger: glob
globs: backend/executor/**, backend/agent/tools.py
description: Safety rules for the guarded actuator and agent tools
---
# Actuator & agent-tool safety (highest-scrutiny code)
- Allowlist is exactly: `restart_pod`, `scale_pool` (or replicas), `rollback_release`. Each has a parameter validator and a **simulated** effect function that changes emulated telemetry.
- Anything outside the allowlist, or with invalid params, **must be refused** and logged. Write a test that tries and fails to run a non-allowlisted action.
- Execute a candidate only if **Safety ≥ 75**. Candidate score `F = 0.6·Safety + 0.4·Recovery`.
- Snapshot state before acting. Health probe after **2 s**; if p99 is not back under **2× baseline** within the window, **restore the snapshot** (dead-man rollback). Test the rollback path *before* the happy path.
- The agent has exactly three read-only tools: `query_graph`, `simulate_fix`, `propose_action`. It can only **propose**; execution happens only via `POST /api/actuator/execute` through the allowlist.
- Review rule: the person who writes `executor/` does not review it. Flag the PR for the Simulation owner (B).
- Never run shell commands, kubectl, or anything real in Phase 1.
