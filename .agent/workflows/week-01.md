---
description: AEGIS Phase 1 — Week 1: Foundations and contracts
---
# Week 1 — Foundations and contracts

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** everyone can run the project; contracts frozen.

## Tasks
- **M0 (D):** create repos (`aegis`, `aegis-testbed`), GitHub Projects board with a card per module, branch protection, CI skeleton (ruff, pytest, `npm run build`), `docker-compose.yml` with Neo4j + API + UI. Publish **OpenAPI with stub responses** for all endpoints in `docs/02-CONTRACTS.md`.
- **M1 (A):** write the schema doc and the `GraphRepository` interface; Neo4j constraints in `backend/graph/schema.cypher`.
- **M2 (A):** draft `data/topology.yaml` format (8 services, 6 datastores, 40 endpoints/pods).
- **M4 (B):** write the six test cases on paper first (safe, moderate, breaking #142, cyclic, leaf-service, gateway) with expected blast radius and score computed **by hand** → save in `backend/tests/cases/`.
- **M6 (C):** get a free LLM key (Gemini or Groq), install Ollama + a small model, write a 20-line LiteLLM script that returns text. Confirms the free path works.
- Pin Python/Node versions (`.tool-versions` or README); add `.env.example`.

## Integration
UI shows the **stub** topology from the stub API.

## Exit test
A teammate who did not set it up clones the repo and runs it in **under 15 minutes**.
