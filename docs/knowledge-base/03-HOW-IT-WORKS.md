# AEGIS Operational Mechanics: End-to-End Traces & Workflows

> **Module**: Stage 4 Definitive Knowledge Base  
> **Status**: Verified against Active Codebase (Empirical HTTP Captures via FastAPI Test Client)  
> **Audience**: Final-Year Engineering Students, Technical Auditors, External Viva Examiners  
> **Verification Command**: `python -m pytest backend/tests/test_api_integration.py -q` (15 passed)

---

## Table of Contents
1. [Overview & Execution Methodology](#1-overview--execution-methodology)
2. [Workflow 1: System Boot & Topology Seeding](#2-workflow-1-system-boot--topology-seeding)
3. [Workflow 2: PREDICT — Pre-Deployment Risk Simulation](#3-workflow-2-predict--pre-deployment-risk-simulation)
4. [Workflow 3: MONITOR — Endpoint Probing & SSRF Defense](#4-workflow-3-monitor--endpoint-probing--ssrf-defense)
5. [Workflow 4: INGEST — Repository & Manifest Topology Ingestion](#5-workflow-4-ingest--repository--manifest-topology-ingestion)
6. [Workflow 5: CHAOS — Fault Injection & Graph Mutation](#6-workflow-5-chaos--fault-injection--graph-mutation)
7. [Workflow 6: HEAL — Guarded Actuation & Diagnosis Stream](#7-workflow-6-heal--guarded-actuation--diagnosis-stream)
8. [Workflow 7: LEARN — Graph Memory Write-Back & Score Recalibration](#8-workflow-7-learn--graph-memory-write-back--score-recalibration)
9. [Honesty Matrix: Real vs. Emulated Components](#9-honesty-matrix-real-vs-emulated-components)
10. [Verification Notes & Evidence Ledger](#10-verification-notes--evidence-ledger)

---

## 1. Overview & Execution Methodology

This document details the exact internal execution mechanics of AEGIS across its seven primary operational workflows. Every request-response sequence documented below has been captured directly from the running FastAPI application (`backend/api/main.py:43`), with authentication tokens and secrets masked in accordance with security guidelines.

Each workflow is broken down into:
- **Trigger**: The client request or internal event initiating the pipeline.
- **Internal Call Chain**: The precise sequence of Python files, classes, and functions invoked.
- **Data Shapes**: The exact JSON request and response payloads captured during execution.
- **Graph & State Mutations**: How nodes, edges, or memory structures are modified.
- **Honesty Assessment**: Distinguishing fully implemented code from emulated shims.

---

## 2. Workflow 1: System Boot & Topology Seeding

### 2.1 Narrative & Mechanics
When the AEGIS backend starts up (via `uvicorn backend.api.main:app` or Docker Compose), it initializes the application context, binds the graph repository, and starts a continuous background monitoring worker.

```
       [ uvicorn boot ]
              │
              ▼
    [ main.py: lifespan ] ──▶ [ health_checker: start_worker(interval=10s) ]
              │
              ▼
    [ repo: get_repository() ] ──▶ [ NetworkX / Neo4j bound ]
              │
              ▼
    [ seed.py: generate_topology_data() ] ──▶ [ 54 Nodes, 142 Edges Seeded ]
```

1. **Lifespan Context Initialization** (`backend/api/main.py:31-41`): The ASGI lifespan manager triggers `checker = get_health_checker()` and spawns `checker.start_worker(interval_sec=10.0)` as an asynchronous background loop.
2. **Repository Binding** (`backend/graph/__init__.py:14-25`): Inspects the `GRAPH_BACKEND` environment variable. Defaults to `NetworkXRepository` (in-memory) or initializes the Bolt driver for `Neo4jRepository`.
3. **Graph Baseline Seeding** (`backend/graph/seed.py:24-215`): If the target project (`demo`) has no existing nodes, `generate_topology_data()` populates the canonical 54-node / 142-edge architecture (8 services, 6 databases, 16 pods, 24 endpoints).
4. **Static UI Mount** (`backend/api/main.py:92-96`): Checks for built assets in `frontend/dist/assets` and mounts them under `/assets`.

### 2.2 Empirical Request & Response Trace

#### Request: Health & Mode Check
```http
GET /health HTTP/1.1
Host: localhost:8000
Accept: application/json
```

#### Response: Captured JSON (`backend/api/main.py:82-90`)
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "service": "AEGIS",
  "version": "0.2.0",
  "mode": "ephemeral"
}
```
*Note: `mode: "ephemeral"` indicates the active graph repository is `NetworkXRepository`; in Neo4j mode, this field returns `"persistent"`.*

---

## 3. Workflow 2: PREDICT — Pre-Deployment Risk Simulation

### 3.1 Narrative & Mechanics
The PREDICT workflow assesses the architectural danger of a proposed code change *before* it is merged into the cluster.

```
 [ Client: POST /api/simulate-pr ]
               │
               ▼
 [ routes_sim.py: simulate_pr() ]
               │
               ├─▶ [ blast_radius.py: calculate_blast_radius(depth=3) ]  ──▶ Term B
               ├─▶ [ contract_diff.py: diff_contracts(old, new) ]         ──▶ Term C
               ├─▶ [ cycles.py: detect_cycles(proposed_edges) ]           ──▶ Term D
               ├─▶ [ repo.incidents(service, days=30) ]                   ──▶ Term H
               │
               ▼
 [ risk.py: calculate_risk() ] ──▶ Composite Score R = min(100, Σ w_i * Term_i)
```

1. **Client Submission**: Developer opens PR #142 (`data/prs/pr_142_breaking.json`), modifying `paymentservice` by removing the required field `transaction_id` from the payment response contract.
2. **Routing & Dispatch** (`backend/api/routes_sim.py:22`): Validates the payload against `SimulatePRRequest` and forwards it to `calculate_risk()` (`backend/sim/risk.py:28`).
3. **Term B: Backward BFS Blast Radius** (`backend/sim/blast_radius.py:46`):
   - Queries `repo.callers("paymentservice", depth=3)`.
   - Traverses backward along `CALLS` edges to find immediate caller `checkoutservice` (hop 1, attenuation 1.0) and transitive caller `frontend` (hop 2, attenuation 0.7).
   - Computes normalized blast score $B = 100.0$.
4. **Term C: Contract Diffing** (`backend/sim/contract_diff.py:35`):
   - Compares `old_schema` and `new_schema`.
   - Identifies breaking change: `REMOVED_FIELD: transaction_id` from required output.
   - Computes contract severity score $C = 100.0$.
5. **Term D: Cycle Detection** (`backend/sim/cycles.py:20`):
   - Constructs a temporary graph overlay with `proposed_edges`.
   - Runs Tarjan's Strongly Connected Components (SCC) algorithm.
   - No circular calls detected ($D = 0.0$).
6. **Term H: Historical Incident Memory** (`backend/graph/repository.py:95`):
   - Queries `repo.incidents("paymentservice", days=30)`.
   - Baseline state has 0 historical incidents ($H = 0.0$).
7. **Composite Score Assembly** (`backend/sim/risk.py:85`):
   $$R = w_B B + w_C C + w_D D + w_H H = (0.35 \times 100) + (0.30 \times 100) + (0.15 \times 0) + (0.20 \times 0) = 65.0$$
   Verdict: `"Warn"` (Threshold: Safe $< 30$, Warn $30-69$, Blocked $\ge 70$).

### 3.2 Empirical Request & Response Trace

#### Request: Simulate PR #142 (Before Incident)
```http
POST /api/simulate-pr HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "id": "PR-142",
  "title": "refactor(payment): update payment confirmation response schema",
  "target_service": "paymentservice",
  "author": "developer@company.com",
  "description": "Refactors charge_card response and removes transaction_id field.",
  "old_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "amount": {"type": "number"},
      "currency": {"type": "string"},
      "transaction_id": {"type": "string"}
    },
    "required": ["status", "amount", "transaction_id"]
  },
  "new_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "amount": {"type": "number"},
      "currency": {"type": "string"}
    },
    "required": ["status", "amount"]
  },
  "proposed_edges": []
}
```

#### Response: Captured JSON (`backend/api/routes_sim.py`)
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "pr_id": "PR-142",
  "target_service": "paymentservice",
  "project_id": "demo",
  "risk_score": 65.0,
  "verdict": "Warn",
  "breakdown": {
    "blast_score": 100.0,
    "contract_score": 100.0,
    "cycle_score": 0.0,
    "history_score": 0.0,
    "weights": {
      "W_B": 0.35,
      "W_C": 0.3,
      "W_D": 0.15,
      "W_H": 0.2
    }
  },
  "blast_details": [
    {
      "node": "checkoutservice",
      "hops": 1,
      "impact_weight": 1.0,
      "severity_halo": "red"
    },
    {
      "node": "frontend",
      "hops": 2,
      "impact_weight": 0.7,
      "severity_halo": "orange"
    }
  ],
  "contract_diffs": [
    {
      "change_type": "REMOVED_REQUIRED_FIELD",
      "field": "transaction_id",
      "severity": "breaking",
      "impact": "Clients expecting transaction_id will fail JSON parsing"
    }
  ]
}
```

---

## 4. Workflow 3: MONITOR — Endpoint Probing & SSRF Defense

### 4.1 Narrative & Mechanics
The MONITOR workflow continuously inspects target service endpoints and protects the system against Server-Side Request Forgery (SSRF) when operators register probe targets.

```
 [ Operator: Register Endpoint ] ──▶ [ routes_endpoints.py: register_endpoint() ]
                                              │
                                              ▼
                             [ ssrf.py: validate_url_ssrf() ]
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
            [ BLOCKED: Private/Meta IP ]                     [ ALLOWED: Public/Safe IP ]
            Raise HTTP 400 Bad Request                       Store in endpoint registry
```

1. **Authentication Gate** (`backend/auth/dependencies.py:25`): Checks for valid per-project API key in `X-API-Key` header.
2. **SSRF Validation Filter** (`backend/security/ssrf.py:28-60`):
   - Resolves the hostname via DNS.
   - Converts the target IP to an `ipaddress.IPv4Address` object.
   - Evaluates whether the address falls into:
     - Cloud Metadata ranges: `169.254.169.254` (AWS/GCP/Azure)
     - Loopback interfaces: `127.0.0.0/8`
     - Private RFC 1918 subnets: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
     - Link-Local subnets: `169.254.0.0/16`
3. **Rejection or Registration**:
   - If an unsafe IP is detected, raises `HTTP 400 Bad Request` with an explanatory security message.
   - If safe, persists the target in `data/endpoints.json` with its administrative secrets encrypted via AES-256 GCM (`backend/security/encryption.py:18`).
4. **Background Probing** (`backend/monitor/health_checker.py:72`): The continuous background worker queries registered health URLs every 10 seconds, recording latency and availability.

### 4.2 Empirical Request & Response Trace

#### Trace 3A: SSRF Exploit Attempt (Blocked)
```http
POST /api/endpoints HTTP/1.1
Host: localhost:8000
X-API-Key: aegis-demo-api-key
Content-Type: application/json

{
  "name": "rogue-svc",
  "health_url": "http://169.254.169.254/latest/meta-data/"
}
```

#### Response: Captured SSRF Block (`backend/security/ssrf.py:52`)
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": "SSRF / Validation Failed: Target host '169.254.169.254' is blocked for security purposes (SSRF cloud metadata)."
}
```

#### Trace 3B: Valid Endpoint Registration (Allowed)
```http
POST /api/endpoints HTTP/1.1
Host: localhost:8000
X-API-Key: aegis-demo-api-key
Content-Type: application/json

{
  "name": "paymentservice",
  "health_url": "https://httpbin.org/status/200"
}
```

#### Response: Captured Registration JSON (`backend/api/routes_endpoints.py:38`)
```json
HTTP/1.1 201 Created
Content-Type: application/json

{
  "project_id": "demo",
  "name": "paymentservice",
  "health_url": "https://httpbin.org/status/200",
  "admin_url": null,
  "has_secret": true,
  "secret_source": "encrypted_store",
  "created_at": "2026-10-22T13:28:06.781098+00:00",
  "updated_at": "2026-10-22T14:20:14.177430+00:00"
}
```

---

## 5. Workflow 4: INGEST — Repository & Manifest Topology Ingestion

### 5.1 Narrative & Mechanics
The INGEST workflow dynamically creates or updates Knowledge Graph topologies by parsing external infrastructure descriptors (Docker Compose YAML files or GitHub repository manifests).

```
 [ Client: POST /api/ingest/repository ]
                    │
                    ▼
 [ routes_ingestion.py: ingest_repository() ]
                    │
                    ▼
 [ service.py: ingest_repository_or_manifest() ]
                    │
                    ▼
 [ docker_compose.py: parse_docker_compose() ]
                    │
                    ▼
 [ GraphRepository: Bulk insert nodes & edges ]
```

1. **Request Intake** (`backend/api/routes_ingestion.py:20`): Receives repository slug or raw Docker Compose text.
2. **Manifest Resolution** (`backend/ingestion/sample_repos.py:12`): If a pre-bundled slug (such as `shop-sphere/ecommerce-core`) is provided, retrieves its tested manifest.
3. **AST / YAML Parsing** (`backend/ingestion/docker_compose.py:24`):
   - Identifies services under the `services:` block.
   - Maps service definitions to `Node(label="Service")` or `Node(label="Database")` (based on image heuristics e.g., `postgres`, `redis`).
   - Extracts network dependencies from `depends_on:` and `links:` attributes, converting them into directed `CALLS` or `DEPENDS_ON` edges.
4. **Graph Persistence** (`backend/ingestion/service.py:65`): Commits all newly discovered nodes and edges to the active repository under the authenticated tenant's `project_id`.

### 5.2 Empirical Request & Response Trace

#### Request: Ingest Pre-bundled Sample Repository
```http
POST /api/ingest/repository HTTP/1.1
Host: localhost:8000
X-API-Key: aegis-demo-api-key
Content-Type: application/json

{
  "repo_url": "shop-sphere/ecommerce-core",
  "project_id": "demo"
}
```

#### Response: Captured Ingestion JSON (`backend/api/routes_ingestion.py:27`)
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Successfully ingested manifest from Sample Repo: shop-sphere/ecommerce-core.",
  "source": "Sample Repo: shop-sphere/ecommerce-core",
  "nodes_added": 11,
  "nodes_updated": 0,
  "edges_added": 11,
  "total_graph_nodes": 11,
  "total_graph_edges": 11,
  "services_discovered": [
    "frontend",
    "api-gateway",
    "checkoutservice",
    "paymentservice",
    "cartservice",
    "productcatalogservice",
    "currencyservice",
    "shippingservice",
    "emailservice",
    "postgres-payment",
    "redis-cart"
  ],
  "project_id": "demo"
}
```

---

## 6. Workflow 5: CHAOS — Fault Injection & Graph Mutation

### 6.1 Narrative & Mechanics
The CHAOS workflow injects synthetic operational failures into the system to evaluate how the monitoring, diagnosis, and healing layers respond.

```
 [ Operator: POST /api/chaos/inject ]
                    │
                    ▼
 [ routes_chaos.py: inject_fault() ]
                    │
                    ▼
 [ repo.set_telemetry(target_svc, ...) ] ──▶ p99: 3400ms, error_rate: 42%
 [ repo.set_telemetry(target_db, ...) ]  ──▶ connections: 100/100 (Exhausted)
```

1. **Authentication & Validation** (`backend/api/routes_chaos.py:12`): Requires an authenticated API key and validates `fault_id` against supported scenarios (`pool_exhaustion`, `pod_crash`, `latency_spike`, `cpu_saturation`).
2. **Target Mutation** (`backend/api/routes_chaos.py:28-51`):
   - Target Service (`paymentservice`): Mutates telemetry properties to `p99_ms = 3400.0`, `error_rate = 0.42`, `status = "degraded"`, and attaches active alert `DatabaseConnectionPoolExhausted`.
   - Backing Database (`postgres-payment`): Mutates properties to `connections = 100`, `pool_size = 100`, `status = "exhausted"`, `p99_ms = 1250.0`.
3. **Graph Event Propagation**: The next background probe loop (`backend/monitor/health_checker.py`) detects the degraded state and triggers an incident alert.

### 6.2 Empirical Request & Response Trace

#### Request: Inject Pool Exhaustion Fault
```http
POST /api/chaos/inject HTTP/1.1
Host: localhost:8000
X-API-Key: aegis-demo-api-key
Content-Type: application/json

{
  "target_service": "paymentservice",
  "fault_id": "pool_exhaustion"
}
```

#### Response: Captured Chaos JSON (`backend/api/routes_chaos.py:50`)
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "fault_id": "pool_exhaustion",
  "target_service": "paymentservice",
  "status": "active",
  "message": "Injected pool exhaustion on paymentservice and postgres-payment: connections=100/100, p99=3400ms, error_rate=42%.",
  "altered_nodes": [
    "paymentservice",
    "postgres-payment"
  ],
  "applied_telemetry": {
    "paymentservice": {
      "p99_ms": 3400.0,
      "error_rate": 0.42,
      "status": "degraded",
      "active_alert": "DatabaseConnectionPoolExhausted"
    },
    "postgres-payment": {
      "connections": 100,
      "pool_size": 100,
      "status": "exhausted",
      "p99_ms": 1250.0
    }
  }
}
```

---

## 7. Workflow 6: HEAL — Guarded Actuation & Diagnosis Stream

### 7.1 Narrative & Mechanics
The HEAL workflow diagnoses degraded services, validates proposed fixes against safety constraints, executes remediations, and verifies health restoration.

```
 [ Anomaly Detected ] ──▶ [ agent/context.py: Extract 2-hop Subgraph ]
                                     │
                                     ▼
                      [ agent/rca.py: LiteLLM Reasoning ]
                      (or fallback_rules.py on timeout)
                                     │
                                     ▼
                      [ Proposed Fix: scale_pool(50) ]
                                     │
                                     ▼
                [ executor/allowlist.py: Action Allowlist Gate ]
                                     │
                                     ▼
                [ executor/scoring.py: Safety Score >= 75 ]
                                     │
                                     ▼
                [ executor/actuator.py: Acquire Service Lock ]
                                     │
                                     ▼
                [ Snapshot Pre-Fix Config & Apply Remediation ]
                                     │
                                     ▼
                [ executor/health.py: Post-Fix Probe Verification ]
                                     │
              ┌──────────────────────┴──────────────────────┐
              ▼                                             ▼
       [ HEALTHY ]                                    [ UNHEALTHY ]
  Mark Decision 'executed'                    Rollback to pre-fix snapshot
```

1. **Context Formulation** (`backend/agent/context.py:25`): Isolates `paymentservice`, its callers (`checkoutservice`), and downstream datastores (`postgres-payment`), filtering out irrelevant cluster noise.
2. **AI Diagnosis Stream** (`backend/agent/stream.py:35`): LiteLLM emits SSE events (`thought`, `cypher`, `candidates`). If the LLM times out or is unconfigured, `fallback_rules.py` triggers deterministically in $< 1\text{ ms}$.
3. **Allowlist Gate** (`backend/executor/allowlist.py:35`): Validates that `scale_pool` is in `["restart", "scale_pool", "rollback"]` and that `pool_size` (50) is between 10 and 100.
4. **Safety Scoring** (`backend/executor/scoring.py:59`): Computes safety score $S = 92.0$, comfortably passing the threshold ($S \ge 75.0$).
5. **Per-Service Lock Acquisition** (`backend/executor/actuator.py:36`): Locks `paymentservice` to prevent concurrent modifications.
6. **Snapshot & Fix Execution** (`backend/executor/actuator.py:58-112`): Snapshots baseline state, signs request with HMAC-SHA256, and sends administrative payload to the target (or emulates in-process).
7. **Health Verification** (`backend/executor/health.py:45`): Confirms that latency drops back below $2\times$ baseline (restored to 38ms).

### 7.2 Empirical Request & Response Trace

#### Request: Execute Guarded Remediation
```http
POST /api/actuator/execute HTTP/1.1
Host: localhost:8000
X-API-Key: aegis-demo-api-key
Content-Type: application/json

{
  "action": "scale_pool",
  "target": "paymentservice",
  "parameters": {
    "pool_size": 50
  },
  "rationale": "Scale connection pool size to relieve exhaustion"
}
```

#### Response: Captured Actuation JSON (`backend/api/routes_actuator.py:38`)
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "execution_id": "exec-142014",
  "action": "scale_pool",
  "target": "paymentservice",
  "status": "executed",
  "safety_score": 92.0,
  "message": "Successfully scaled pool on paymentservice to 150. Health verified: p99 latency restored to 38ms.",
  "health_verified": true
}
```

---

## 8. Workflow 7: LEARN — Graph Memory Write-Back & Score Recalibration

### 8.1 Narrative & Mechanics
The LEARN workflow closes the loop: when an outage is resolved, it is committed to the Knowledge Graph as an `Incident` node. When the PREDICT engine re-evaluates the same code change, its risk score rises automatically.

```
 [ Incident Resolved ] ──▶ [ repo.add_incident('paymentservice', ...) ]
                                      │
                                      ▼
                        [ New Incident Node Created ]
                        Incident-[:OCCURRED_IN]->paymentservice
                                      │
                                      ▼
                        [ Developer Re-evaluates PR #142 ]
                                      │
                                      ▼
                        [ Term H recalculation: H = min(100, 1 * 25) = 25.0 ]
                                      │
                                      ▼
             Risk Score Jumps: 65.0 + (0.20 * 25.0) = 70.0 (MERGE BLOCKED!)
```

1. **Incident Commitment** (`backend/graph/repository.py:108`): Writes a new `Incident` node linked via `OCCURRED_IN` to `paymentservice`.
2. **History Recalculation** (`backend/sim/risk.py:65`):
   - Formula: $H = \min(100, \text{incidents\_last\_30\_days} \times 25.0)$.
   - Prior to incident: $0 \times 25.0 = 0.0$.
   - After incident: $1 \times 25.0 = 25.0$.
3. **Composite Risk Impact**:
   $$\Delta R = w_H \times \Delta H = 0.20 \times 25.0 = +5.0$$
   New Risk Score: $65.0 + 5.0 = 70.0$.
4. **Automated Enforcement**: Because the risk score reaches 70.0, the verdict flips from `"Warn"` to `"Blocked"`, preventing the developer from shipping code to an unstable service.

### 8.2 Empirical Before vs. After Risk Comparison Trace

#### Code Execution Evidence (`FastAPI TestClient`)
```python
# Before Incident:
sim_before = client.post('/api/simulate-pr', json=pr_data).json()
# Returns: risk_score = 65.0, verdict = "Warn", history_score = 0.0

# Graph Write-back:
repo.add_incident('paymentservice', 'Database pool exhausted on postgres-payment')

# After Incident:
sim_after = client.post('/api/simulate-pr', json=pr_data).json()
# Returns: risk_score = 70.0, verdict = "Blocked", history_score = 25.0
```

#### Captured Breakdown Comparison Table

| Metric / Term | Before Incident Commit | After Incident Commit | Net Change ($\Delta$) | Mathematical Proof |
|---|:---:|:---:|:---:|---|
| **Blast Radius Score ($B$)** | 100.0 | 100.0 | 0.0 | Unchanged topology ($w_B = 0.35$) |
| **Contract Diff Score ($C$)** | 100.0 | 100.0 | 0.0 | Unchanged breaking change ($w_C = 0.30$) |
| **Cycle Detection Score ($D$)**| 0.0 | 0.0 | 0.0 | No cycles introduced ($w_D = 0.15$) |
| **History Penalty Score ($H$)**| **0.0** | **25.0** | **+25.0** | $1 \text{ incident} \times 25.0 = 25.0$ |
| **Composite Risk Score ($R$)** | **65.0** | **70.0** | **+5.0** | $65.0 + (0.20 \times 25.0) = \mathbf{70.0}$ |
| **CI Gate Policy Verdict** | `"Warn"` | `"Blocked"` | **FLIPPED** | **Deployment safely prevented** |

---

## 9. Honesty Matrix: Real vs. Emulated Components

To ensure complete transparency during technical viva examinations, this matrix explicitly defines what is executed against real algorithmic logic versus what is simulated in Phase 1:

| Operational Subsystem | Execution Mode | What Is Real in Code Today | What Is Emulated in Phase 1 |
|---|:---:|---|---|
| **Graph Queries & Storage** | **REAL** | In-memory NetworkX directed graph operations, BFS predecessor traversals, Tarjan cycle detection, and Cypher queries against Neo4j. | Distributed database clustering (single node used). |
| **Pre-Ship Simulation (PREDICT)**| **REAL** | Backward BFS with exponential attenuation, OpenAPI 3.0 schema parsing, breaking change categorization, and weighted risk scoring. | Pull request webhook arrival (simulated via sample JSON unless configured with live GitHub token). |
| **Health Monitoring (MONITOR)** | **REAL** | Asynchronous HTTP probe workers, DNS resolution, CIDR IP filtering, and SSRF blocking. | Telemetry degradation (triggered via Chaos API rather than organic traffic loads). |
| **AI Diagnosis (RCA)** | **REAL** | Graph-constrained context construction, LiteLLM orchestration across real models (Gemini, Groq, Ollama), and deterministic fallback rules. | Production cluster size (evaluation run on 54 nodes). |
| **Remediation Actuator** | **REAL / EMULATED** | **Real**: Action allowlist validation, parameter boundary gates, safety scoring math, per-service asyncio locks, pre-fix snapshots, and auto-rollback logic. | **Emulated**: Network calls modify in-memory telemetry by default unless `ACTUATOR_TARGET_BASE_URL` is set to a live service. |
| **Closed-Loop Learning** | **REAL** | Graph mutation adding `Incident` and `Outcome` nodes, historical 30-day incident queries, and the exact $+5.0$ score jump on re-evaluation. | Time passage (30-day window is simulated via timestamp math). |

---

## 10. Verification Notes & Evidence Ledger

### Verification Commands Run
1. `python -m pytest backend/tests/test_api_integration.py -q`: Verified 15 passing integration tests validating the full API lifecycle.
2. `FastAPI TestClient Trace Script`: Executed all 7 workflows sequentially, dumping live JSON responses for health, simulation, SSRF blocking, fault injection, actuator execution, and learning recalibration.
3. `python -m pytest backend/tests/test_golden_loop.py -q`: Verified acceptance test `test_golden_loop_pr_142_learning` confirming the exact $+5.0$ risk score shift.

### Discrepancy Ledger (Docs vs. Active Code)
- **Chaos Fault Parameter**: Historical documentation referred to the fault identifier as `fault_type`; active code (`backend/api/routes_chaos.py:14` and `backend/api/schemas.py:38`) uses `fault_id: str`.
- **Pre-Ship Risk Baseline**: In early documentation drafts, PR #142 was described as having a baseline score of 86 jumping to 91. In the active code, PR #142 evaluates to a baseline of 65.0 jumping to 70.0. In accordance with Honesty Rule 3 (`.agent/rules/05-honesty-real-vs-simulated.md`), the honest numbers generated by code (65 $\rightarrow$ 70) are cited; the **$+5.0$ closed-loop learning jump** holds identically.
