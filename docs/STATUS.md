# AEGIS System Audit & Honest Status Report

**Generated Date**: 2026-10-22  
**Platform**: Windows (win32) — Python 3.14.6 / Node.js Vite 8.3.4  
**Audit Scope**: Monorepo root, `backend/`, `frontend/`, `docs/`, `data/`, test suites, and running services.  
**Strict Policy**: Evidence-grounded. Zero code alterations made during this assessment.

---

## 1. Executive Summary & Test Suite Results

### Automated Test Verification
- **Test Command**: `python -m pytest backend/tests -v`
- **Result**: **44 passed, 0 failed, 1 warning** in 11.81s.
- **Warning**: `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` in [backend/tests/conftest.py:1](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/tests/conftest.py#L1).
- **Integration Script**: `python -m backend.tests.verify_all` executed with **exit code 0** (100% pass across PREDICT numerical validation, Docker Compose ingestion, health probing, fault injection/recovery, and SSRF defense).

### Active Service Verification
- **Backend API**: Started via `uvicorn backend.api.main:app --host 127.0.0.1 --port 8000` — **RUNNING** on `http://127.0.0.1:8000`.
- **Frontend App**: Started via `npm run dev` in `frontend/` — **RUNNING** on `http://localhost:5173/` (Vite v8.3.4 proxying `/api` requests to port 8000).

---

## 2. Comprehensive Feature Audit Table

| Feature / UI Component | Status | Evidence (file:line) | What is Needed |
| :--- | :--- | :--- | :--- |
| **Graph Interface & NetworkX Backend** | **REAL** | [backend/graph/repository.py:53-98](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/repository.py#L53-L98)<br>[backend/graph/networkx_repo.py:29-239](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/networkx_repo.py#L29-L239) | Complete in-memory graph repository. Implements all 7 methods, backwards BFS traversal for callers, incident addition, and telemetry mutators. Fully operational. |
| **Graph Interface Neo4j Backend** | **PARTIAL** | [backend/graph/neo4j_repo.py:29-187](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L29-L187) | `reset()` is an empty `pass` ([neo4j_repo.py:184-186](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L184-L186)). `add_incident()` hardcodes `apoc.create.uuid()` without fallback ([neo4j_repo.py:161-162](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L161-L162)). Needs topology reload in `reset()` and pure Cypher/Python UUID generation. |
| **Seed Topology (54 Nodes, 142 Edges)** | **REAL** | [data/topology.yaml:1-689](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/data/topology.yaml#L1-L689)<br>[backend/graph/seed.py:20-64](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/seed.py#L20-L64) | Exact 54 nodes and 142 edges seeded into graph. Validated by [test_graph.py:15-32](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/tests/test_graph.py#L15-L32). |
| **PREDICT Risk Formula Engine** | **REAL** | [backend/sim/risk.py:54-135](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/risk.py#L54-L135)<br>[backend/sim/config.py:11-33](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/config.py#L11-L33) | Real mathematical implementation: $W_B \cdot B + W_C \cdot C + W_D \cdot D + W_H \cdot H$ (weights: 0.35, 0.30, 0.15, 0.20). Validated in unit and regression tests. |
| **PREDICT Backward Blast Radius (B)** | **REAL** | [backend/sim/blast_radius.py:14-41](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/blast_radius.py#L14-L41) | Backward BFS over caller dependencies with $0.75^{(\text{hops}-1)}$ attenuation factor. |
| **PREDICT Schema Contract Diff (C)** | **REAL** | [backend/sim/contract_diff.py:44-118](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/contract_diff.py#L44-L118) | AST/JSON schema difference analyzer identifying breaking required-field removals vs backward-compatible additions. |
| **PREDICT Tarjan Cycle Detection (D)** | **REAL** | [backend/sim/cycles.py:22-58](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/cycles.py#L22-L58) | Tarjan Strongly Connected Components (SCC) algorithm detecting circular dependency injection. |
| **PREDICT API Endpoints** | **REAL** | [backend/api/routes_predict.py:23-140](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_predict.py#L23-L140)<br>[backend/api/routes_sim.py:15-68](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_sim.py#L15-L68) | `/api/predict/services`, `/api/predict/analyze`, and `/api/simulate-pr` are backed by real logic. |
| **PREDICT UI: `PredictPage.tsx`** | **REAL** | [frontend/src/pages/PredictPage.tsx:25-70](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/PredictPage.tsx#L25-L70) | Interactively calls `GET /api/predict/services` and `POST /api/predict/analyze`. Renders score cards, 4-factor formula breakdown, blast path list, and contract diff. |
| **PREDICT UI: `PredictModal.tsx`** | **ORPHANED / REAL LOGIC** | [frontend/src/components/PredictModal.tsx:42-77](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/components/PredictModal.tsx#L42-L77) | Fully functional modal calling `/api/predict/services` and `/api/predict/analyze`, but is not imported or rendered anywhere in the application. |
| **Blast Radius Panel: `BlastRadiusPanel.tsx`** | **ORPHANED** | [frontend/src/components/BlastRadiusPanel.tsx:31-450](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/components/BlastRadiusPanel.tsx#L31-L450) | Legacy drawer containing the 4-step demo flow (simulate PR, inject fault, guarded heal, commit incident). Not imported or rendered by any page in `frontend/src/`. |
| **MONITOR Probing Engine & SSRF Defense** | **REAL** | [backend/monitor/health_checker.py:102-255](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/monitor/health_checker.py#L102-L255) | Real asynchronous probing using `httpx.AsyncClient`. Validates IP ranges to block loopback/RFC1918/link-local metadata SSRF attacks. Background worker periodically checks configured services. |
| **MONITOR API Endpoints** | **REAL** | [backend/api/routes_monitor.py:22-74](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_monitor.py#L22-L74) | Implements `/api/monitor/status`, `/api/monitor/check-now`, `/api/monitor/fault`, `/api/monitor/configure`, `/api/monitor/unconfigure`, `/api/monitor/probe/{id}`. |
| **MONITOR UI: `MonitorPage.tsx`** | **REAL** | [frontend/src/pages/MonitorPage.tsx:32-120](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/MonitorPage.tsx#L32-L120) | Interactively calls all 5 monitor endpoints. Real live polling with auto-refresh every 4s, immediate check button, simulated fault injection, and dynamic endpoint configuration. |
| **MONITOR UI: `MonitorModal.tsx`** | **ORPHANED / REAL LOGIC** | [frontend/src/components/MonitorModal.tsx:54-118](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/components/MonitorModal.tsx#L54-L118) | Fully functional modal calling `/api/monitor/*`, but not imported or mounted by any page. |
| **INGESTION Docker Compose & GitHub Parser** | **REAL** | [backend/ingestion/docker_compose.py:36-95](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/ingestion/docker_compose.py#L36-L95)<br>[backend/ingestion/github_fetcher.py:43-77](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/ingestion/github_fetcher.py#L43-L77)<br>[backend/ingestion/service.py:40-108](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/ingestion/service.py#L40-L108) | Real YAML manifest parsing, service and dependency edge extraction from environment variables, GitHub HTTP fetching, and topology node insertion. |
| **INGESTION UI: `IngestPage.tsx`** | **REAL** | [frontend/src/pages/IngestPage.tsx:60-190](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/IngestPage.tsx#L60-L190) | Connects to `/api/ingest/sample-repos`, `POST /api/ingest/repository` (sample, GitHub, raw YAML), and `POST /api/graph/external-service`. |
| **INGESTION UI: `IngestionModal.tsx`** | **ORPHANED / REAL LOGIC** | [frontend/src/components/IngestionModal.tsx:68-150](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/components/IngestionModal.tsx#L68-L150) | Fully functional modal with identical ingestion API integration, but orphaned (not imported). |
| **CHAOS Studio API & Engine** | **PARTIAL** | [backend/api/routes_chaos.py:10-85](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_chaos.py#L10-L85) | `POST /api/chaos/inject` mutates in-memory graph telemetry properties (`p99_ms`, `error_rate`, `connections`, `pool_size`, `status`). It does not run container-level faults (as expected for Phase 1 emulated chaos). |
| **CHAOS Studio UI: `ChaosPage.tsx`** | **REAL** | [frontend/src/pages/ChaosPage.tsx:54-97](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/ChaosPage.tsx#L54-L97) | Connected to `POST /api/chaos/inject` and `POST /api/reset`. Allows selecting fault types, target service, and displays telemetry impacts. |
| **Streaming Reasoner Terminal Backend** | **STUB** | [backend/api/routes_heal.py:22-126](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_heal.py#L22-L126) | `get_demo_diagnosis_events()` returns hardcoded mock dictionaries (`thought`, `cypher`, `candidates`, `result`, `done`). No LLM reasoning or graph inspection occurs. |
| **Streaming Reasoner Terminal UI** | **STUB / ARTIFICIAL** | [frontend/src/pages/ActuatorPage.tsx:39-48](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/ActuatorPage.tsx#L39-L48) | The UI does **not** use `EventSource` or SSE. It calls `fetch('/api/heal/events')`, receives all events statically, and simulates streaming via a client-side `setTimeout(..., 450)` loop. |
| **LLM Graph Reasoner Module (`agent/`)** | **MISSING** | Directory does not exist in `backend/` | Phase 1 M5/M6 requires an LLM reasoner with LiteLLM (`gemini` / `groq` / `ollama`), tool calling over `GraphRepository`, and Pydantic validation. Currently absent. |
| **Autonomous Actuator Module (`executor/`)** | **PARTIAL / MISPLACED** | [backend/api/routes_heal.py:135-223](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_heal.py#L135-L223) | No `backend/executor/` directory exists. Allowlisted action validation and rollback simulation are hardcoded inline in `routes_heal.py`. Needs extraction into `backend/executor/` with formal rollback snapshotting. |
| **Actuator UI Execution & Rollback** | **REAL** | [frontend/src/pages/ActuatorPage.tsx:63-91](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/ActuatorPage.tsx#L63-L91) | Calls `POST /api/actuator/execute`. Properly tests both the valid path (`pool_size=150`) and deliberate bad fix rollback (`pool_size=20`). |
| **Closed-Loop Feedback Module (`feedback/`)** | **PARTIAL / MISPLACED** | [backend/api/routes_heal.py:225-251](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_heal.py#L225-L251) | No `backend/feedback/` directory exists. Memory commit endpoint `POST /api/memory/commit` calls `repo.add_incident()` directly in `routes_heal.py`. The graph update works, but lacks dedicated feedback package. |
| **Incident Ledger UI: `IncidentLedgerPage.tsx`** | **STUB** | [frontend/src/pages/IncidentLedgerPage.tsx:13-44](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/IncidentLedgerPage.tsx#L13-L44) | Displays hardcoded incidents (`inc-9481a`, `inc-8120b`, `inc-7049c`) and fixed KPI metrics ("MTTR 7.4s", "100% healing"). Does not query live incidents from the graph repository. |
| **OpenTelemetry Observability UI: `ObservabilityPage.tsx`** | **STUB** | [frontend/src/pages/ObservabilityPage.tsx:17-113](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/ObservabilityPage.tsx#L17-L113) | Displays hardcoded mock traces (`trace-4f9b8c2d1e`) and waterfall spans. Marked as Phase 2. Zero backend endpoints called. |
| **Topology Explorer: `TopologyPage.tsx`** | **REAL** | [frontend/src/pages/TopologyPage.tsx:54-175](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/TopologyPage.tsx#L54-L175) | Fetches `GET /api/graph/topology` and `POST /api/reset`. Renders interactive React Flow graph, filters by layer, searches nodes, and inspects connections. |
| **Global Command Bar & Baseline Reset** | **REAL** | [frontend/src/App.tsx:97-135](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/App.tsx#L97-L135) | Live polling of topology count (`/api/graph/topology`), active page routing, and "Reset Baseline" action invoking `POST /api/reset`. |

---

## 3. Specific Investigation Questions

### (a) What is the streaming terminal connected to?
1. **Frontend Call**: In [frontend/src/pages/ActuatorPage.tsx:39](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/ActuatorPage.tsx#L39), the terminal triggers `handleStartDiagnosis()` which executes:
   ```typescript
   const resp = await fetch('/api/heal/events');
   const events: any[] = await resp.json();
   for (let i = 0; i < events.length; i++) {
     await new Promise((r) => setTimeout(r, 450));
     setStreamEvents((prev) => [...prev, events[i]]);
   }
   ```
2. **Backend Implementation**: In [backend/api/routes_heal.py:22-104](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_heal.py#L22-L104), both `/api/heal/events` and `/api/heal/stream` return `get_demo_diagnosis_events()`.
3. **Verdict**: **STUB**. It is connected to hardcoded static mock diagnosis events; the streaming animation in the browser is produced by a client-side JavaScript delay loop. No LLM or dynamic graph inspection is connected.

### (b) Does `neo4j_repo.py` implement every method in `repository.py`?
1. `get_topology()`: **Yes**, implemented in [backend/graph/neo4j_repo.py:50](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L50).
2. `neighbors()`: **Yes**, implemented in [backend/graph/neo4j_repo.py:68](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L68).
3. `callers()`: **Yes**, implemented in [backend/graph/neo4j_repo.py:104](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L104).
4. `incidents()`: **Partial**, implemented in [backend/graph/neo4j_repo.py:121](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L121) (signature accepts `days: int = 30`, but query does not filter by timestamp).
5. `set_telemetry()`: **Yes**, implemented in [backend/graph/neo4j_repo.py:143](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L143).
6. `add_incident()`: **Fragile**, implemented in [backend/graph/neo4j_repo.py:151](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L151) using `apoc.create.uuid()` in Cypher without fallback. If Neo4j lacks APOC, it crashes with Cypher syntax errors.
7. `reset()`: **NO / STUB**, lines 184–186 are empty:
   ```python
   def reset(self) -> None:
       # Load topology.yaml and reseed Neo4j
       pass
   ```
8. **Verdict**: **PARTIAL**. `reset()` is completely unimplemented, and `add_incident()` relies on unverified APOC functions.

### (c) Does any module named `agent/`, `executor/` or `feedback/` exist?
- **Inspection**: Directory listing of `backend/` yields only `api/`, `graph/`, `ingestion/`, `monitor/`, `sim/`, `tests/`.
- **Verdict**: **MISSING**. None of `agent/`, `executor/`, or `feedback/` exist.
- **Where logic currently resides**:
  - Actuator allowlisting & rollback logic is embedded directly in [backend/api/routes_heal.py:135-223](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_heal.py#L135-L223).
  - Feedback write-back logic is embedded directly in [backend/api/routes_heal.py:225-251](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_heal.py#L225-L251).
  - Reasoner logic does not exist beyond mock data.

---

## 4. Environment Variables & Hardcoded Secrets / URLs

### Environment Variables Read by Code
1. `PORT`: [backend/api/main.py:101](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/main.py#L101) (`os.environ.get("PORT", 8000)`)
2. `GRAPH_BACKEND`: [backend/graph/__init__.py:22](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/__init__.py#L22) (`os.getenv("GRAPH_BACKEND", "networkx")`)
3. `NEO4J_URI`: [backend/graph/neo4j_repo.py:41](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L41) (`os.getenv("NEO4J_URI", "bolt://localhost:7687")`)
4. `NEO4J_USER`: [backend/graph/neo4j_repo.py:42](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L42) (`os.getenv("NEO4J_USER", "neo4j")`)
5. `NEO4J_PASSWORD`: [backend/graph/neo4j_repo.py:43](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L43) (`os.getenv("NEO4J_PASSWORD", "aegis_password")`)
6. `GITHUB_TOKEN`: [backend/ingestion/github_fetcher.py:46](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/ingestion/github_fetcher.py#L46) (`os.getenv("GITHUB_TOKEN")`)

*Discrepancies against [.env.example](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/.env.example):*
- `.env.example` declares `LLM_PROVIDER`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OLLAMA_BASE_URL`, `LLM_MODEL`, and `HOST`. None of these are read anywhere in the codebase.
- `GITHUB_TOKEN` is read in `github_fetcher.py`, but missing from `.env.example`.

### Hardcoded Secrets, Default Passwords & URLs
1. **Default Password**:
   - [backend/graph/neo4j_repo.py:43](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L43): `"aegis_password"` as default fallback.
2. **Hardcoded URLs**:
   - [backend/graph/neo4j_repo.py:41](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py#L41): `"bolt://localhost:7687"` default Neo4j connection URI.
   - [frontend/vite.config.ts:12](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/vite.config.ts#L12): `'http://127.0.0.1:8000'` Vite dev server proxy target.
   - [frontend/src/pages/MonitorPage.tsx:23](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/MonitorPage.tsx#L23): `'http://127.0.0.1:8000/health'` default service health check endpoint.
   - [frontend/src/components/MonitorModal.tsx:47](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/components/MonitorModal.tsx#L47): `'http://127.0.0.1:8000/health'` default health check endpoint.
   - [frontend/src/pages/IngestPage.tsx:21](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/IngestPage.tsx#L21): `'GoogleCloudPlatform/microservices-demo'` default repository URL input.
   - [backend/ingestion/github_fetcher.py:53](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/ingestion/github_fetcher.py#L53): `"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"` raw GitHub content endpoint.
