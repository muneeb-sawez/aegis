---
description: AEGIS Phase 1 — Week 3: Simulation v1 (backend + PR UI)
---
# Week 3 — Simulation v1 (backend + PR UI)

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** `POST /api/simulate-pr` returns a real score.

## Tasks
- **M4 (B):** contract diff; Tarjan SCC on a graph copy with the PR's new edges; risk = 0.35·B + 0.30·C + 0.15·D + 0.20·H with weights in `backend/sim/config.py`.
- **Calibration (needs human decision):** PR #142 should be ≈86 on a fresh graph **by code**. Naive inputs give ≈58. Compute the numbers for the options in `docs/04-ALGORITHMS.md` §6, present them, and **ask the human to choose**; record the choice in `docs/07-DECISIONS.md`. **Never hard-code 86.**
- **M2 (A):** create `data/prs/*.json` for Safe, Moderate, Breaking (#142), Cyclic PRs.
- **M9 (D):** PR dropdown, "Run Pre-Ship Simulation" button, radial risk gauge, blast-radius halos (amber/red by `impact_weight`).

## Integration
Click → API → halos on canvas.

## Exit test
All six hand-checked cases pass; UI colours match.
