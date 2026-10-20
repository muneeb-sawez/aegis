---
description: AEGIS Phase 1 — Week 8: Closed loop (the learning claim)
---
# Week 8 — Closed loop (the learning claim)

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** healing changes the next risk score.

## Tasks
- **M8 (C):** `commit_incident()` writes `(:Incident)-[:OCCURRED_IN]->(:Service)`, `(:Decision)`, outcome; `H = min(100, 25 × incidents_in_30_days)` ⇒ one incident adds +25 to H ⇒ **+5 total**.
- **M4 (B):** ensure history is read through `incidents(node, days)`.
- **M9 (D):** timeline scrubber (Baseline → Fault → Healing → Learned) driven by a saved event log; incident node appears on canvas with animation.
- **M10 (D):** auto-postmortem card from the decision log.
- **Friday (everyone):** first full 4-minute script run → `/verify-loop`.

## Exit test
PR #142 scores X before the incident and X+5 after (**produced by code**), and `POST /api/reset` restores X. (Target example: 86 → 91; use the honest number.)
