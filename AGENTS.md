# AEGIS — Agent Context (read this first, every session)

AEGIS is a graph-grounded system that (1) predicts the risk of a code change before it ships, (2) detects and diagnoses a failing service with an LLM that reasons only over graph data, (3) heals it through a guarded, allowlisted actuator with automatic rollback, and (4) writes the incident back into the graph so the next risk score changes.
Loop: **Predict → Deploy → Monitor → Diagnose → Heal → Learn**.

## Current scope: PHASE 1 only (Weeks 1–10, "Review 2: Mission Control with real brains")
Build a deployed, demo-able system on a **54-node / 142-edge** seeded graph with real algorithms, a real LLM, and **emulated** telemetry and actuation.
**Do NOT build Phase 2 items** (real Kubernetes/kind, live Git webhooks, PR comments, OpenTelemetry, LitmusChaos, kubectl actuator, evaluation baselines). They are parked in `docs/phase2-parked/` for later. If a task seems to need them, stop and ask.

### Phase 1 success definition (the acceptance test for everything)
A reviewer picks **PR #142**, sees the risk score **computed by code (never hard-coded)**, injects a **pool-exhaustion** fault, watches the LLM reason over graph data (streamed), sees the fix applied or auto-rolled-back, then re-runs PR #142 and sees the score rise **because an Incident node now exists** (one incident ⇒ H +25 ⇒ total +5).

## Tech stack (free tier only — nothing may require a credit card)
- Backend: **Python 3.11, FastAPI, Pydantic, pytest, uvicorn, ruff**. Python ONLY (no Go/Java).
- Graph: **Neo4j Community (Docker)** behind a `GraphRepository` interface; **NetworkX** fallback implementation (`GRAPH_BACKEND=neo4j|networkx`).
- LLM: **LiteLLM** abstraction. Providers via env var: Gemini free / Groq free → Ollama (local) → `fallback_rules.py` → cached run.
- Frontend: **React + TypeScript + Vite + Tailwind + React Flow (`@xyflow/react`)**, dagre or elkjs for layout. (Not Cytoscape.)
- Infra: Docker Compose; deploy API on Render/Fly free, UI on Vercel/Netlify.
- No real Kafka. Kafka exists only as a *node* in the demo topology.

## Repo layout (monorepo `aegis/`)
```
backend/
  graph/     repository.py(interface) neo4j_repo.py networkx_repo.py seed.py queries.py schema.cypher
  sim/       blast_radius.py risk.py cycles.py contract_diff.py config.py
  chaos/     faults.py telemetry.py
  agent/     context.py prompts/ rca.py tools.py fallback_rules.py
  executor/  allowlist.py actuator.py health.py rollback.py
  feedback/  writer.py
  api/       main.py routes_*.py schemas.py
  tests/
frontend/    src/components/...
data/        topology.yaml  prs/*.json  faults/*.json  cached_rca/*.json
deploy/      docker-compose.yml  render.yaml
docs/
.agent/      rules/  workflows/
```
A second repo, `aegis-testbed` (fork of Google Online Boutique), is used from Week 4/6 for ingestion-lite only.

## Non-negotiable rules (full detail in `.agent/rules/`)
1. **Edge direction:** `CALLS` always points **caller → callee**. Blast radius walks **backwards** (callers of the changed service). Most bugs will be direction confusion — test it explicitly.
2. **No Cypher outside `backend/graph/`.** Everyone else uses only the `GraphRepository` methods.
3. **Never hard-code the demo numbers** (86, 91, 54/142 are *targets that must come out of code/data*). If the honest number differs, report it; don't fudge it.
4. **Actuator safety:** only 3 allowlisted actions; validate params; refuse anything else; rollback path is tested *before* the happy path. The LLM can only *propose*, never execute.
5. **LLM output is untrusted:** validate with Pydantic, reject node IDs not in the supplied context, retry once, then fall back to rules.
6. **Honesty:** label emulator metrics as "simulated / emulator time". Never present an unmeasured number as a result.
7. **Contracts are frozen** after Week 1 (`docs/02-CONTRACTS.md`). Never change a contract silently — propose the change and ask the human.
8. **`main` stays runnable.** Short branches, CI green (ruff + pytest + `npm run build`).
9. **Every module is "done" only when its exit test passes** (`docs/03-MODULES.md`). Write the test first where possible.

## How to work with the human
- The human will tell you their **role (A/B/C/D)** and the **module / week** they are on. Stay inside that module's files unless told otherwise (ownership in `docs/01-TEAM-AND-PROCESS.md`).
- Before coding: restate the task, list the files you will touch, and the exit test. Then implement, run the tests, and report results.
- When something is ambiguous or conflicts with a contract: **ask, don't guess**. Log decisions in `docs/07-DECISIONS.md`.
- Weekly workflows live in `.agent/workflows/week-NN.md` (invoke as slash commands, e.g. `/week-03`).

## Doc map
| File | Contents |
|---|---|
| `docs/00-START-HERE.md` | How to set up Antigravity, first prompts |
| `docs/01-TEAM-AND-PROCESS.md` | Roles, ownership, cadence, git rules |
| `docs/02-CONTRACTS.md` | Graph schema, repository interface, API, SSE envelope |
| `docs/03-MODULES.md` | M0–M10 scope and "done when" |
| `docs/04-ALGORITHMS.md` | Blast radius, contract diff, Tarjan, risk, candidate scoring, anomaly, H term |
| `docs/05-FAILURE-CASES.md` | Case matrix, fallbacks, cut line |
| `docs/06-REAL-VS-SIMULATED.md` | What is real vs emulated |
| `docs/07-DECISIONS.md` | Resolved conflicts + open decisions |
| `docs/08-TESTING.md` | Test strategy and targets |
| `docs/09-INGESTION-LITE-REFERENCE.md` | Online Boutique manifest parsing + precision/recall (Weeks 4, 9) |
| `docs/phase2-parked/` | Webhook, scanners, traces, kubectl material — NOT for Phase 1 |
