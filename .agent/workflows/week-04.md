---
description: AEGIS Phase 1 — Week 4: CI gate, drift view and ingestion-lite
---
# Week 4 — CI gate, drift view and ingestion-lite

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** finish Pillar A (pre-ship prediction) and prove the graph can be built from real files.

## Tasks
- **M4 (B):** merge-gate rule (block ≥70, warn 40–69, approve <40); category breakdown (breaking contract, cycle, history, blast).
- **M9 (D):** GitHub-style status-check card (Approved/Warn/Blocked), contract diff viewer.
- **M3 (A):** fork Online Boutique into `aegis-testbed`; parse its Kubernetes YAML per `docs/09-INGESTION-LITE-REFERENCE.md`; write edges with `source='static'`, `confidence=0.6` in a **separate namespace** (`graph='boutique'`) so the 54-node demo graph is untouched.
- **M3 (A):** hand-write the ground-truth edge list; script prints precision and recall.

## Exit test
Pillar A demo works start to finish; ingestion-lite reports P/R numbers (any honest number is acceptable).
