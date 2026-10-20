---
description: AEGIS Phase 1 — Week 5: Chaos and telemetry emulator
---
# Week 5 — Chaos and telemetry emulator

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** the system can become unhealthy on command.

## Tasks
- **M5 (B):** fault catalogue as JSON in `data/faults/`: DB pool exhaustion, pod crash, CPU saturation, latency injection. Each defines which nodes' telemetry changes and how (e.g. Payment p99 38→3400 ms, Postgres `connections=100/100`, error rate 0.4).
- **M5 (B):** telemetry emulator updating nodes via `set_telemetry()` with small random noise; threshold detector (p99 > 3× baseline for 3 ticks) raises exactly one anomaly event. No ML.
- **M9 (D):** Tab 2 shell, "Inject Failure" control, traffic dots on edges turning crimson, KPI bar reading live telemetry.
- **M6 (C):** `agent/context.py` — 2-hop subgraph around the alerting node as compact JSON (nodes, edges, telemetry, past incidents). Unit-test size **< ~3,000 tokens**.

## Integration
inject → telemetry change → anomaly event → UI turns red.

## Exit test
Inject each of the four faults; each produces **exactly one** event.
