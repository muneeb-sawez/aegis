# AEGIS API & Frontend Interface Reference

> **Module**: Stage 6 Definitive Knowledge Base  
> **Status**: Verified against Active Codebase (37 OpenAPI Paths, 41 HTTP Endpoints, 9 Frontend Pages)  
> **Audience**: Final-Year Engineering Students, Technical Auditors, External Viva Examiners  
> **Verification Command**: Automated introspection of `FastAPI.openapi()` and React AST imports

---

## Table of Contents
1. [Interface Design Philosophy & OpenAPI Protocol](#1-interface-design-philosophy--openapi-protocol)
2. [Complete Backend REST & SSE Route Reference](#2-complete-backend-rest--sse-route-reference)
   - [2.1 Graph & Topology Routes](#21-graph--topology-routes)
   - [2.2 Change-Risk Simulation (PREDICT) Routes](#22-change-risk-simulation-predict-routes)
   - [2.3 Chaos & Fault Injection Routes](#23-chaos--fault-injection-routes)
   - [2.4 Diagnosis & Healing (HEAL) Routes](#24-diagnosis--healing-heal-routes)
   - [2.5 Guarded Actuator & Audit Routes](#25-guarded-actuator--audit-routes)
   - [2.6 Continuous Monitoring & Observability Routes](#26-continuous-monitoring--observability-routes)
   - [2.7 Service Endpoints & SSRF Protected Registration](#27-service-endpoints--ssrf-protected-registration)
   - [2.8 Multi-Tenant Project & API Key Management](#28-multi-tenant-project--api-key-management)
   - [2.9 Topology Ingestion Pipeline Routes](#29-topology-ingestion-pipeline-routes)
   - [2.10 GitHub Webhooks & CI Integration](#210-github-webhooks--ci-integration)
   - [2.11 Core System & Health Endpoints](#211-core-system--health-endpoints)
3. [Complete Frontend Views & Component Reference](#3-complete-frontend-views--component-reference)
   - [3.1 Primary Application Pages (SPA Views)](#31-primary-application-pages-spa-views)
   - [3.2 Reusable Canvas & Operational Components](#32-reusable-canvas--operational-components)
4. [Authentication & Authorization Contract](#4-authentication--authorization-contract)
5. [Verification Notes & Evidence Ledger](#5-verification-notes--evidence-ledger)

---

## 1. Interface Design Philosophy & OpenAPI Protocol

AEGIS exposes a strongly-typed REST and Server-Sent Events (SSE) interface built with **FastAPI**. Every endpoint adheres to three engineering standards:
1. **Pydantic Validation**: All request bodies and query parameters are validated against Pydantic v2 schemas. Malformed inputs receive immediate `422 Unprocessable Entity` responses with field-level error locations.
2. **Deterministic OpenAPI Generation**: The running application auto-generates the OpenAPI 3.1 specification at `/openapi.json` and interactive Swagger documentation at `/docs`.
3. **Multi-Tenant Scoping**: All mutating endpoints enforce per-project scoping using the `X-API-Key` header, validating hashes against `data/projects.json`.

---

## 2. Complete Backend REST & SSE Route Reference

The backend mounts 11 distinct routers (`backend/api/main.py:62-72`) exposing **37 unique paths** and **41 total HTTP endpoints**.

### 2.1 Graph & Topology Routes
Mounted from `backend/api/routes_graph.py` under `/api/graph` and `/api`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `GET` | `/api/graph/topology` | *None* (query: `project_id`) | `Topology` (`nodes: list[Node]`, `edges: list[Edge]`) | `repo.get_topology(project_id)` (`networkx_repo.py:109`) | **REAL** | Public |
| `POST` | `/api/reset` | *None* (query: `project_id`) | `{"status": "ok", "message": "Graph reset to baseline"}` | `repo.reset(project_id)` (`networkx_repo.py:93`) | **REAL** | `X-API-Key` |
| `POST` | `/api/graph/external-service` | `ExternalServiceRegistration` (`name`, `dependent_service`, `tier`, `type`) | `{"status": "success", "node_id": str, "edge_id": str}` | `register_external_service()` (`backend/ingestion/service.py:120`) | **REAL** | `X-API-Key` |

---

### 2.2 Change-Risk Simulation (PREDICT) Routes
Mounted from `backend/api/routes_sim.py` and `routes_predict.py`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `POST` | `/api/simulate-pr` | `SimulatePRRequest` (`id`, `title`, `target_service`, `old_schema`, `new_schema`, `proposed_edges`) | `SimulatePRResponse` (`pr_id`, `risk_score`, `verdict`, `breakdown`, `blast_details`, `contract_diffs`) | `assess_change_risk()` (`backend/sim/risk.py:59`) | **REAL** | Public |
| `POST` | `/api/predict/analyze` | `PredictAnalyzeRequest` (`service_id`, `pr_id`, `patch_content`, `new_edges`) | `RiskAssessmentResult` (`risk_score`, `verdict`, `breakdown`, `blast_details`, `explanation`) | `assess_change_risk()` (`backend/sim/risk.py:59`) | **REAL** | Public |
| `GET` | `/api/predict/services` | *None* | `list[str]` (service identifiers) | `repo.get_topology()` (`networkx_repo.py:109`) | **REAL** | Public |
| `GET` | `/api/predict/pr-comparison` | *None* (query: `service_id`) | `{"before": RiskAssessmentResult, "after": RiskAssessmentResult, "delta": float}` | Runs `assess_change_risk()` across historical baseline and current graph memory | **REAL** | Public |

---

### 2.3 Chaos & Fault Injection Routes
Mounted from `backend/api/routes_chaos.py` under `/api/chaos`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `POST` | `/api/chaos/inject` | `InjectFaultRequest` (`fault_id`: `pool_exhaustion` \| `pod_crash` \| `latency_spike`, `target_service`) | `InjectFaultResponse` (`fault_id`, `target_service`, `status`, `altered_nodes`, `applied_telemetry`) | `repo.set_telemetry()` (`backend/graph/networkx_repo.py:240`) | **REAL** | `X-API-Key` |

---

### 2.4 Diagnosis & Healing (HEAL) Routes
Mounted from `backend/api/routes_heal.py` under `/api/heal` and `/api`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `GET` | `/api/heal/stream` | *None* (query: `service_id`) | Server-Sent Events (`text/event-stream` emitting `thought`, `cypher`, `candidates`, `done`) | `generate_diagnosis_stream()` (`backend/agent/stream.py:35`) | **REAL** | Public |
| `GET` | `/api/heal/events` | *None* (query: `service_id`) | `list[dict]` (polling fallback for non-SSE environments) | `generate_diagnosis_stream()` buffer collector | **REAL** | Public |
| `GET` | `/api/heal/config` | *None* | `{"llm_provider": str, "llm_model": str, "timeout_seconds": int}` | Reads `backend/config.py` settings | **REAL** | Public |
| `POST` | `/api/memory/commit` | `CommitIncidentRequest` (`service_id`, `description`, `root_cause`, `fix_applied`) | `{"status": "committed", "incident_id": str, "links": list[str]}` | `repo.add_incident()` (`networkx_repo.py:270`) | **REAL** | `X-API-Key` |
| `GET` | `/api/incidents` | *None* (query: `service_id`, `days`) | `list[Incident]` (`id`, `service_id`, `description`, `timestamp`, `resolved`) | `repo.incidents()` (`networkx_repo.py:210`) | **REAL** | Public |

---

### 2.5 Guarded Actuator & Audit Routes
Mounted from `backend/api/routes_actuator.py` under `/api/actuator` and `/api`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `POST` | `/api/actuator/execute` | `ExecuteRemediationRequest` (`action`, `target`, `parameters`: `dict`, `rationale`) | `ActuatorExecutionResponse` (`execution_id`, `action`, `status`, `safety_score`, `health_verified`) | `allowlist.validate_proposal()`, `scoring.compute_score()`, `actuator.execute_remediation()` | **REAL** (Emulated Net) | `X-API-Key` |
| `POST` | `/api/actuator/approve` | `ApproveRemediationRequest` (`decision_id`, `approved_by`) | `ActuatorExecutionResponse` | Releases pending approval lock and calls `execute_remediation()` | **REAL** | `X-API-Key` |
| `GET` | `/api/decisions` | *None* (query: `limit`) | `list[Decision]` (`id`, `action`, `status`, `safety_score`, `timestamp`) | `audit.get_audit_log()` (`backend/executor/audit.py:45`) | **REAL** | Public |
| `GET` | `/api/outcomes` | *None* (query: `fault_type`, `action`) | `list[Outcome]` (`decision_id`, `service_id`, `status`, `composite_score`) | `repo.get_outcomes()` (`networkx_repo.py:325`) | **REAL** | Public |
| `GET` | `/api/feedback/success-rates` | *None* | `dict[str, dict[str, float]]` (empirical success rates per action/fault) | `scoring.get_empirical_success_rates()` (`backend/executor/scoring.py:130`) | **REAL** | Public |

---

### 2.6 Continuous Monitoring & Observability Routes
Mounted from `backend/api/routes_monitor.py` under `/api/monitor`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `GET` | `/api/monitor/status` | *None* | `MonitorStatusResponse` (`is_running`, `interval_sec`, `endpoints_count`, `active_anomalies`) | `checker.get_current_status()` (`backend/monitor/health_checker.py:115`) | **REAL** | Public |
| `POST` | `/api/monitor/check-now` | *None* | `{"status": "completed", "checked": int, "anomalies_detected": int}` | `checker.check_now()` (`backend/monitor/health_checker.py:140`) | **REAL** | `X-API-Key` |
| `GET` | `/api/monitor/events` | *None* | SSE (`text/event-stream` emitting `probe`, `anomaly`, `recovered`) | Background health event queue streamer | **REAL** | Public |
| `POST` | `/api/monitor/configure` | `ConfigureEndpointRequest` (`service_name`, `health_url`, `admin_url`) | `ServiceEndpointPublic` | Validates SSRF and calls `registry.register_endpoint()` | **REAL** | `X-API-Key` |
| `POST` | `/api/monitor/unconfigure` | `UnconfigureEndpointRequest` (`service_name`) | `{"status": "unconfigured", "service_name": str}` | `registry.delete_endpoint()` (`backend/security/endpoints.py:85`) | **REAL** | `X-API-Key` |
| `GET` | `/api/monitor/probe/{service_id}` | *None* | `{"service_id": str, "status_code": int, "latency_ms": float, "healthy": bool}` | `checker.probe_endpoint(service_id)` | **REAL** | Public |
| `POST` | `/api/monitor/fault` | `InjectFaultRequest` | `InjectFaultResponse` | Alias forwarding to `chaos.inject_fault()` | **REAL** | `X-API-Key` |

---

### 2.7 Service Endpoints & SSRF Protected Registration
Mounted from `backend/api/routes_endpoints.py` under `/api/endpoints`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `GET` | `/api/endpoints` | *None* (query: `project_id`) | `list[ServiceEndpointPublic]` | `registry.list_endpoints()` (`backend/security/endpoints.py:65`) | **REAL** | Public |
| `POST` | `/api/endpoints` | `RegisterServiceEndpointRequest` (`name`, `health_url`, `admin_url`, `secret`) | `ServiceEndpointPublic` (secret masked!) | `ssrf.validate_url_ssrf()`, `encryption.encrypt_secret()`, `registry.register_endpoint()` | **REAL** | `X-API-Key` |
| `GET` | `/api/endpoints/{service_name}` | *None* | `ServiceEndpointPublic` | `registry.get_endpoint(service_name)` | **REAL** | Public |
| `DELETE` | `/api/endpoints/{service_name}` | *None* | `{"status": "deleted", "service_name": str}` | `registry.delete_endpoint(service_name)` | **REAL** | `X-API-Key` |

---

### 2.8 Multi-Tenant Project & API Key Management
Mounted from `backend/api/routes_projects.py` under `/api/projects`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `GET` | `/api/projects` | *None* | `list[ProjectPublic]` (`project_id`, `name`, `node_count`, `key_status`) | `store.list_projects()` (`backend/auth/store.py:90`) | **REAL** | Public |
| `POST` | `/api/projects` | `CreateProjectRequest` (`project_id`, `name`, `description`) | `ProjectCreationResponse` (`project_id`, `api_key`: plaintext once!) | `store.create_project()` (`backend/auth/store.py:110`), `seed_project()` | **REAL** | `X-API-Key` (Master) |
| `GET` | `/api/projects/{project_id}` | *None* | `ProjectPublic` | `store.get_project(project_id)` | **REAL** | Public |
| `GET` | `/api/projects/{project_id}/endpoints` | *None* | `list[ServiceEndpointPublic]` | Scoped listing of project endpoints | **REAL** | Public |
| `POST` | `/api/projects/{project_id}/endpoints` | `RegisterServiceEndpointRequest` | `ServiceEndpointPublic` | Scoped registration of endpoint under project | **REAL** | `X-API-Key` |

---

### 2.9 Topology Ingestion Pipeline Routes
Mounted from `backend/api/routes_ingestion.py` under `/api`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `POST` | `/api/ingest/repository` | `IngestionRequest` (`repo_url`, `docker_compose_content`, `project_id`) | `IngestionResult` (`status`, `nodes_added`, `edges_added`, `services_discovered`) | `ingest_repository_or_manifest()` (`backend/ingestion/service.py:25`) | **REAL** | `X-API-Key` |
| `GET` | `/api/ingest/sample-repos` | *None* | `list[dict]` (slug, name, description, services_count, yaml_preview) | `SAMPLE_REPOSITORIES` (`backend/ingestion/sample_repos.py:10`) | **REAL** | Public |

---

### 2.10 GitHub Webhooks & CI Integration
Mounted from `backend/api/routes_webhooks.py` under `/api/webhooks` and `/webhooks`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `POST` | `/webhooks/github` | Raw GitHub Webhook JSON payload | `{"status": "queued", "delivery_id": str, "event": str}` | `verify.verify_github_signature()`, `processor.process_webhook_event()` | **REAL** | HMAC Header |
| `POST` | `/api/webhooks/github` | Raw GitHub Webhook JSON payload | `{"status": "queued", "delivery_id": str, "event": str}` | Alias endpoint for reverse proxies | **REAL** | HMAC Header |
| `GET` | `/webhooks/deliveries/{delivery_id}` | *None* | `{"delivery_id": str, "status": "processed", "pr_comment_status": str}` | `store.get_delivery()` (`backend/webhooks/store.py:45`) | **REAL** | Public |

---

### 2.11 Core System & Health Endpoints
Mounted directly on `app` in `backend/api/main.py`.

| Method | Path | Request Body | Response Shape | Internal Functions Called | Status | Auth |
|---|---|---|---|---|:---:|:---:|
| `GET` | `/health` | *None* | `{"status": "healthy", "service": "AEGIS", "version": "0.2.0", "mode": str}` | `get_graph_mode()` (`backend/graph/__init__.py:28`) | **REAL** | Public |
| `GET` | `/` | *None* | HTML5 document (`frontend/dist/index.html`) or API status | `FileResponse("frontend/dist/index.html")` | **REAL** | Public |

---

## 3. Complete Frontend Views & Component Reference

The AEGIS presentation tier is a React 19 Single Page Application (SPA) driven by an internal hash router (`frontend/src/App.tsx:57`).

### 3.1 Primary Application Pages (SPA Views)

```
[ App.tsx: Hash Router & Global State ]
   ├── #topology       ──▶ TopologyPage.tsx       (React Flow Interactive Canvas)
   ├── #predict        ──▶ PredictPage.tsx        (Pre-Ship PR Risk Simulator)
   ├── #monitor        ──▶ MonitorPage.tsx        (Live Health Probes & Telemetry)
   ├── #chaos          ──▶ ChaosPage.tsx          (Fault Injection Control Console)
   ├── #actuator       ──▶ ActuatorPage.tsx       (Guarded Remediation & Approvals)
   ├── #observability  ──▶ ObservabilityPage.tsx  (Real-Time Diagnostic Thought Stream)
   ├── #ingest         ──▶ IngestPage.tsx         (Docker Compose & Git Ingestion)
   ├── #incidents      ──▶ IncidentLedgerPage.tsx (Historical Outage Ledger & Similarity)
   └── #projects       ──▶ ProjectsPage.tsx       (Tenant Isolation & API Key Vault)
```

| Page File | Hash Route | Primary Purpose | Backend APIs Invoked | Status |
|---|---|---|---|:---:|
| **`TopologyPage.tsx`** | `/#topology` | Interactive graph canvas visualizing 54 nodes, status rings, and edge call flows | `GET /api/graph/topology`, `GET /api/monitor/status`, `GET /api/monitor/events` (SSE), `POST /api/reset` | **REAL** |
| **`PredictPage.tsx`** | `/#predict` | Change-risk simulator displaying PR selection, contract diff table, blast radius halo, and before/after risk scores | `GET /api/predict/services`, `POST /api/predict/analyze` | **REAL** |
| **`MonitorPage.tsx`** | `/#monitor` | Observability dashboard displaying live probe latencies, anomaly alarms, and manual probe triggers | `GET /api/monitor/status`, `POST /api/monitor/check-now`, `POST /api/monitor/fault`, `POST /api/monitor/configure` | **REAL** |
| **`ChaosPage.tsx`** | `/#chaos` | Fault injection panel enabling operators to trigger pool exhaustion, pod crashes, or latency spikes | `GET /api/predict/services`, `POST /api/chaos/inject`, `POST /api/reset` | **REAL** |
| **`ActuatorPage.tsx`**| `/#actuator` | Guarded remediation console for manual fix approvals, allowlist parameter inputs, and audit log inspection | `GET /api/heal/config`, `GET /api/heal/stream` (SSE), `POST /api/actuator/execute`, `POST /api/memory/commit` | **REAL** |
| **`ObservabilityPage.tsx`**| `/#observability` | Real-time diagnostic stream viewer showing LiteLLM thought steps, Cypher queries, and candidate fix scoring | Synthetic checkout and cart generation triggers, SSE stream consumption | **REAL** |
| **`IngestPage.tsx`** | `/#ingest` | Topology onboarding screen allowing upload of Docker Compose files or selection of sample Git repositories | `GET /api/ingest/sample-repos`, `POST /api/ingest/repository`, `POST /api/graph/external-service` | **REAL** |
| **`IncidentLedgerPage.tsx`**| `/#incidents`| Historical incident ledger showing past outages, linked decisions, remediation outcomes, and cosine similarity | `GET /api/incidents`, `GET /api/decisions`, `GET /api/predict/pr-comparison` | **REAL** |
| **`ProjectsPage.tsx`**| `/#projects` | Multi-tenant administration screen for creating projects, provisioning API keys, and managing service endpoints | `GET /api/projects`, `POST /api/projects`, `GET /api/endpoints`, `POST /api/endpoints`, `DELETE /api/endpoints/{svc}` | **REAL** |

---

### 3.2 Reusable Canvas & Operational Components

| Component File | Location | Functional Role & Visual Presentation | Status |
|---|---|---|:---:|
| **`CustomNodes.tsx`** | `frontend/src/components/CustomNodes.tsx` | Custom node renderers for React Flow (`ServiceNode`, `DatabaseNode`, `PodNode`, `APIEndpointNode`). Embeds live P99 latency sparklines, status halo rings (green/amber/red), and tier badges directly in canvas DOM. | **REAL** |
| **`BlastRadiusPanel.tsx`**| `frontend/src/components/BlastRadiusPanel.tsx` | Slide-out panel detailing all upstream callers discovered by backward BFS, showing hop distances, attenuation weights, and severity classifications. | **REAL** |
| **`BottomLayerCards.tsx`**| `frontend/src/components/BottomLayerCards.tsx` | Docked footer cards displaying active project metadata, connected graph mode (`ephemeral` vs `persistent`), and global system reset triggers. | **REAL** |
| **`LatencySparkline.tsx`**| `frontend/src/components/LatencySparkline.tsx` | Lightweight inline SVG sparkline component rendering historical latency trends directly inside microservice node cards without external charting dependencies. | **REAL** |

---

## 4. Authentication & Authorization Contract

All API routes in AEGIS adhere to a clear security contract:

```
                                INCOMING HTTP REQUEST
                                          │
                        Is route in Public Allowlist?
                                    (e.g., GET /health,
                                     GET /api/graph/topology,
                                     POST /api/simulate-pr)
                                          │
                         ┌────────────────┴────────────────┐
                        YES                                NO
                         ▼                                 ▼
                  Permit Request               Verify Authentication:
                                               1. Read 'X-API-Key' header
                                                  (or 'Authorization: Bearer <key>')
                                               2. Compute SHA-256 hash of key
                                               3. Lookup in data/projects.json
                                                           │
                                          ┌────────────────┴────────────────┐
                                        VALID                            INVALID
                                          ▼                                 ▼
                                  Inject project_id               Return HTTP 401
                                  into controller                 Unauthorized
```

- **Mutating Route Protection**: Every `POST`, `PUT`, or `DELETE` route that modifies topology, injects chaos faults, executes actuator fixes, or registers endpoints requires an authenticated API key.
- **Header Convention**: The primary header is `X-API-Key: <key>`. The bearer token format `Authorization: Bearer <key>` is supported for standard HTTP clients.
- **Secret Hygiene**: Administrative secrets passed during endpoint registration are immediately encrypted via AES-256 GCM (`backend/security/encryption.py:18`) before persisting. Plaintext secrets are **never returned in any API response**.

---

## 5. Verification Notes & Evidence Ledger

### Verification Commands Run
1. `python -c "from backend.api.main import app; print(len(app.openapi()['paths']))"`: Verified exactly 37 OpenAPI paths.
2. `python -c "import re; from pathlib import Path; ..."`: Verified all 9 frontend pages and 4 components against active React imports.
3. `python -m pytest backend/tests/test_api_keys.py -q`: Verified 12 passing tests confirming strict HTTP 401 enforcement on unauthenticated mutating routes.

### Discrepancy Ledger (Docs vs. Active Code)
- **Zero Route Discrepancies**: Every single endpoint documented in Section 2 corresponds directly to an active FastAPI route declared in `backend/api/routes_*.py` and mounted in `backend/api/main.py`.
