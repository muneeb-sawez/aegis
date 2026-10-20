---
description: AEGIS Phase 1 — Week 6: RCA agent v1 (streaming)
---
# Week 6 — RCA agent v1 (streaming)

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** real graph-grounded LLM diagnosis on screen.

## Tasks
- **M6 (C):** system prompt (reason only over supplied JSON, cite node IDs, structured JSON output); three read-only tools `query_graph`, `simulate_fix`, `propose_action` (agent only *proposes*); stream via SSE with the event envelope; **log every prompt/response to disk**; validate with Pydantic — retry once on invalid JSON, then fall back.
- **M6 (C):** `fallback_rules.py` — deterministic rules (e.g. `connections ≥ 95% pool` ⇒ pool exhaustion) so the demo works with no LLM.
- **M9 (D):** typewriter terminal rendering `thought` and `cypher` events differently.
- Develop with Ollama/free API; cache each successful run into `data/cached_rca/`.
- **Review:** A reviews the prompt guardrails.

## Exit test
3 fault types × 10 runs; record accuracy. Target **≥ 8/10 per type**; lower triggers a prompt-fix day next week.
