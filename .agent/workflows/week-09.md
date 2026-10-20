---
description: AEGIS Phase 1 — Week 9: Hardening, cases and deployment
---
# Week 9 — Hardening, cases and deployment

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** it survives bad conditions.

## Tasks
- **M0 (D):** deploy API to Render/Fly free tier and UI to Vercel/Netlify; document cold-start (wake API 5 min before demo); `render.yaml`/Dockerfile checked in.
- **All:** go through `docs/05-FAILURE-CASES.md`; every row gets a test or a written procedure.
- **M6 (C):** prompt-injection test (put "ignore your rules" in an incident name; allowlist must hold).
- **M3 (A):** optional stretch — Online Boutique as a second canvas view.
- **M10 (D):** record backup demo video (OBS); write report sections (architecture, algorithms, limitations).

## Exit test
Demo runs with **Wi-Fi off** (local mode), **LLM key disabled** (fallback mode), and **Neo4j stopped** (NetworkX mode).
