---
description: AEGIS Phase 1 — Week 2: Graph and canvas
---
# Week 2 — Graph and canvas

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** the 54-node ecosystem exists in the database and on screen.

## Tasks
- **M1 (A):** implement Neo4j and NetworkX repositories; one shared pytest suite parametrized over both. Include the **direction test** (caller → callee).
- **M2 (A):** finish `topology.yaml`; write `seed.py` using `MERGE` (idempotent); assert **54 nodes / 142 edges**. Include realistic latencies and the **PaymentService → Postgres** dependency.
- **M9 (D):** React Flow canvas with `ServiceNode`, `DatabaseNode`, `PodNode`, dark theme, auto layout (dagre or elkjs).
- **M4 (B):** BFS blast radius on top of `callers()`; depth attenuation 0.75 per hop (`docs/04-ALGORITHMS.md` §1).

## Integration
`GET /api/graph/topology` serves real data from M1; the UI renders it.

## Exit test
Open canvas, click PaymentService, the flyout shows real metadata from the DB.
