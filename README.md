# AEGIS — Autonomous Engineering Graph & Intelligence System

AEGIS is an open-source reliability intelligence system that models distributed microservice architectures as a Knowledge Graph. It bridges the gap between pre-deployment change validation and runtime incident response:
1. **Pre-Deployment Risk Prediction (`PREDICT`)**: Evaluates code changes, schema modifications, and dependency shifts before deployment to quantify blast radius, identify breaking API changes, detect circular dependency deadlocks, and generate explainable merge verdicts.
2. **Runtime Health Monitoring & Fault Simulation (`MONITOR` & `CHAOS`)**: Continuously verifies service health with SSRF-protected probers, simulates controlled chaos faults, and records failure metrics.
3. **Graph-Grounded Diagnostic Reasoning (`DIAGNOSE`)**: Ingests topological 2-hop sub-graphs into a Large Language Model (LLM) or deterministic fallback rules to diagnose root causes without hallucinating ungrounded infrastructure.
4. **Guarded Actuation & Rollback (`HEAL`)**: Filters proposed remediations through a frozen allowlist, takes pre-action snapshots, verifies recovery against a 10-second dead-man health watchdog, and automatically rolls back if health fails.
5. **Closed-Loop Graph Learning (`LEARN`)**: Records resolved incidents directly back into the Knowledge Graph as `(:Incident)` nodes, dynamically updating subsequent risk evaluations by an empirical $+5.0$ score penalty.

---

## ⚡ Quickstart — Running AEGIS in 3 Steps

### Prerequisites
- **Python 3.11+** (`python --version`)
- **Node.js 18+ & npm** (`node -v` & `npm -v`)

---

### Step 1: Environment Setup
In the project root, duplicate `.env.example` to `.env`:
```powershell
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux (Bash)
cp .env.example .env
```
> [!NOTE]
> By default, `GRAPH_BACKEND=networkx` is set in `.env`, allowing AEGIS to run immediately out-of-the-box with **zero external dependencies** (no Docker or Neo4j required).

---

### Step 2: Install Dependencies

#### A. Backend (Python)
From the project root, install required Python packages:
```bash
pip install -r requirements.txt
```

#### B. Frontend (Node.js)
Navigate to the `frontend` directory and install npm packages:
```bash
cd frontend
npm install
cd ..
```

---

### Step 3: Start the Application

Run the backend and frontend in **two separate terminal windows**:

#### Terminal 1 — Backend API
```powershell
# From the project root
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Base URL**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

#### Terminal 2 — Frontend UI
```powershell
cd frontend
npm run dev
```
- **Mission Control Web Dashboard**: [http://localhost:5173](http://localhost:5173) *(automatically proxies `/api` calls to port 8000)*

---

### 🛠️ Common Troubleshooting

| Error / Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'litellm'` | Dependencies were not installed in the active Python environment. | Run `pip install -r requirements.txt` (or `pip install litellm neo4j`). |
| `'vite' is not recognized as an internal or external command` | `node_modules` was not created yet. | Run `npm install` inside the `frontend` folder. |
| `Missing script: "install"` | Mistyped `npm run install` instead of `npm install`. | Use `npm install` directly inside `frontend/`. |
| `ConnectionRefusedError: [Errno 111]` on Neo4j | `GRAPH_BACKEND=neo4j` configured without Neo4j running. | Set `GRAPH_BACKEND=networkx` in `.env` for zero-dependency local operation. |
| LLM API Key Error / Rate Limit | No Gemini or Groq API key configured. | Set `DEMO_MODE=true` in `.env` to run fully scripted offline diagnoses without an LLM key. |

---

## 1. Project Overview

Modern microservice architectures frequently suffer from cascade outages caused by seemingly small modifications: an engineer modifies a field type, alters an enum, or introduces a transitive dependency that creates an architectural cycle. Traditional CI/CD pipelines run unit tests in isolation but lack architectural context. Conversely, production APM tools alert engineers only after an outage has propagated across client sessions.

AEGIS addresses this disconnect by treating software architecture as a living, shared graph:
- **Upstream Blast Propagation**: Services do not fail in isolation; upstream callers suffer cascading latency and errors.
- **Explainable Merge Gates**: Instead of binary pass/fail test runs, pull requests receive a composite risk score backed by topological evidence.
- **Safe-by-Construction Remediation**: Autonomous incident mitigation must never have arbitrary execution privileges; all actions are gated by strict allowlists, parameter constraints, and automated rollbacks.

```
                    ┌────────────────────────────────────────────────────────┐
                    │                      PREDICT                           │
                    │   Pull Request Risk Score & Upstream Blast Radius      │
                    └───────────────────────────┬────────────────────────────┘
                                                │ (Approved / Reviewed)
                                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                                   LEARN                                    │
│   Knowledge Graph Memory (+5.0 Risk Recalibration on Healed Incidents)     │
└───────────────────────────────────────▲────────────────────────────────────┘
                                        │
                                        │ (Resolution Persisted)
┌───────────────────────────────────────┴────────────────────────────────────┐
│                                   HEAL                                     │
│   Guarded Allowlist Gate • Pre-Action Snapshot • 10s Rollback Watchdog    │
└───────────────────────────────────────▲────────────────────────────────────┘
                                        │
                                        │ (Ranked Proposal)
┌───────────────────────────────────────┴────────────────────────────────────┐
│                                 DIAGNOSE                                   │
│   Graph-Grounded LLM Reasoning (LiteLLM) • Streamed Thought Progression    │
└───────────────────────────────────────▲────────────────────────────────────┘
                                        │
                                        │ (Threshold Exceeded)
┌───────────────────────────────────────┴────────────────────────────────────┐
│                                  MONITOR                                   │
│   Async HTTP Probes • SSRF Defense • Chaos Fault Injection                 │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Capabilities

### PREDICT: Pre-Merge Change-Risk Engine
- **Backward Blast Radius ($B$)**: Traverses incoming `CALLS` dependencies backward from the modified service using Breadth-First Search (BFS) with an exponential hop attenuation decay ($\gamma = 0.75^{\text{hops}-1}$).
- **Contract Difference Analysis ($C$)**: Performs Abstract Syntax Tree (AST) dictionary diffing over OpenAPI specifications to identify breaking modifications (field removals, type mutations, added required parameters).
- **Cycle Detection ($D$)**: Applies Tarjan's Strongly Connected Components (SCC) algorithm to verify whether proposed edges introduce dependency deadlocks.
- **Historical Vulnerability ($H$)**: Factors the trailing 30-day incident frequency of the target service directly from the Knowledge Graph.
- **Explainable Verdicts**: Classifies changes into `Approved` ($R < 40$), `Warn` ($40 \le R < 70$), or `Blocked` ($R \ge 70$).

### MONITOR: Probing & Chaos Engine
- **Asynchronous Health Probers**: Background worker evaluates HTTP/HTTPS endpoints, recording HTTP status codes, latency, and consecutive failures.
- **SSRF Defense**: Validates every probe destination, blocking cloud metadata IP ranges (`169.254.169.254`), local loopbacks (`127.0.0.1`, `::1`), and private subnets.
- **Deterministic Chaos Simulation**: Injects synthetic latency spikes, connection pool exhaustion, or service crashes to validate system observability.

### Ingestion Pipeline
- **Docker Compose Parser**: Parses `docker-compose.yml` declarations, extracting service nodes, ports, datastores, and inter-service call edges from environment variables.
- **GitHub Repository Ingestion**: Introspects public GitHub repository trees to build architectural dependency graphs on-the-fly.
- **Pre-Bundled Topologies**: Includes four verified multi-tier architectures (e-commerce, fintech ledger, streaming pipeline, telehealth).

### DIAGNOSE & HEAL: Autonomous Remediation
- **Context-Grounded LLM Reasoning**: Ingests only the 2-hop topological neighborhood around degraded nodes, eliminating ungrounded hallucinations.
- **Server-Sent Events (SSE)**: Streams diagnostic thought progression (`thought`, `cypher`, `candidates`, `result`, `done`) in real time.
- **Guarded Allowlist Gate**: Restricts actuator actions to a frozen, non-destructive set: `restart`, `scale_pool`, `rollback`. Rejects unlisted actions immediately.
- **Dead-Man Rollback Switch**: Verifies target recovery for 10 seconds post-remediation; automatically restores pre-action state if health checks fail.
- **Closed-Loop Recalibration**: Appends an `Incident` node and `Outcome` edge to the graph upon resolution, automatically increasing subsequent risk scores on that service by $+5.0$ points ($H$ increases by $25.0 \times 0.20$).

---

## 3. Architecture

AEGIS is built as a modular monorepo containing a FastAPI Python backend and a React TypeScript frontend:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                              │
│   React 18 • TypeScript • Vite • TailwindCSS • React Flow (@xyflow)    │
│   Views: Topology, Predict, Monitor, Chaos, Actuator, Ingest, Projects │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON & Server-Sent Events (SSE)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        API Gateway & Security                          │
│   FastAPI • Pydantic v2 • API Key Auth (agk_*) • SSRF Guard • Webhooks │
│   AES-256 GCM Secret Encryption • Request Signing (HMAC-SHA256)        │
└───────────────────┬───────────────────────────────┬────────────────────┘
                    │                               │
┌───────────────────▼──────────────┐  ┌─────────────▼────────────────────┐
│      Change-Risk Engine          │  │       Autonomous Healing         │
│   Backward BFS Blast Radius      │  │   LiteLLM Diagnostic Reasoner    │
│   AST Schema Contract Diffing    │  │   Deterministic Fallback Rules   │
│   Tarjan SCC Cycle Detection     │  │   Guarded Allowlist Gate         │
│   Composite Risk Scoring         │  │   Pre-Fix Snapshot & Rollback    │
└───────────────────┬──────────────┘  └─────────────┬────────────────────┘
                    │                               │
┌───────────────────▼───────────────────────────────▼────────────────────┐
│                     Graph & Data Access Layer                          │
│   GraphRepository Interface (7 Methods)                                │
│   ├─ NetworkXRepository: In-memory, zero external dependencies         │
│   └─ Neo4jRepository: Parameterized Cypher queries for persistence     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                      Storage & Infrastructure                          │
│   data/topology.yaml (54 nodes, 142 edges) • Docker Compose • Render   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. How PREDICT Works

The Change-Risk Engine evaluates proposed pull requests against four distinct terms:
$$R = \min\left(100.0, \, \max\left(0.0, \, W_B \cdot B + W_C \cdot C + W_D \cdot D + W_H \cdot H\right)\right)$$

Where weights $W_i$ sum to $1.0$:
- **Blast Radius Weight ($W_B = 0.35$)**: Structural footprint across upstream services.
- **Contract Diff Weight ($W_C = 0.25$)**: Breaking API changes and schema incompatibilities.
- **Cycle Penalty Weight ($W_D = 0.20$)**: Circular call chains and deadlock vulnerabilities.
- **Historical Volatility Weight ($W_H = 0.20$)**: Past 30-day incident frequency on the target node.

### Term Formulations
1. **Blast Radius ($B \in [0, 100]$)**:
   Traverses incoming predecessor edges from the target node up to depth 3. Direct callers receive impact weight $1.0$, secondary callers $0.75$, and tertiary callers $0.5625$. The sum is normalized against a saturation cap of $5.0$:
   $$B = \min\left(100.0, \, \frac{\sum 0.75^{\text{hops}-1}}{5.0} \times 100.0\right)$$
2. **Contract Diff ($C \in \{0, 100\}$)**:
   Returns $100.0$ if any required field is deleted, an existing field changes data type, or a new mandatory parameter is added without a default. Safe additive changes return $0.0$.
3. **Cycle Penalty ($D \in \{0, 100\}$)**:
   Constructs a directed graph containing existing edges plus proposed additions. Tarjan's algorithm isolates strongly connected components. If any component has $\ge 2$ nodes, $D = 100.0$, otherwise $0.0$.
4. **Historical Term ($H \in [0, 100]$)**:
   Queries the Knowledge Graph for incidents recorded on the service within the last 30 days:
   $$H = \min(100.0, \, \text{incident\_count} \times 25.0)$$

### Gate Verdicts
- **Approved** ($R < 40.0$): Low blast radius, safe additive changes; eligible for automated release.
- **Warn** ($40.0 \le R < 70.0$): Moderate blast radius or architectural modifications; requires peer SRE review.
- **Blocked** ($R \ge 70.0$): High blast radius, breaking contract changes, or circular dependencies; release blocked.

---

## 5. How MONITOR Works

The monitoring engine operates an asynchronous background worker (`backend/monitor/health_checker.py`):
1. **Periodic Probing**: Every 10 seconds, the worker checks all registered HTTP/HTTPS service URLs.
2. **SSRF Guard**: Destination URLs pass through `validate_url_ssrf()` before socket resolution, rejecting private, link-local, loopback, or cloud metadata IP addresses.
3. **Consecutive Failure Tracking**: If a service fails $\ge 2$ consecutive probes (HTTP error, connection timeout, or 5xx code), its health state transitions to `DEGRADED` or `DOWN`.
4. **Automated Incident Logging**: Persistent failures automatically instantiate an `Incident` node in the Knowledge Graph, marking the service for diagnostic investigation.
5. **Simulated Telemetry**: In Phase 1, metric attributes (latency percentiles, connection pool utilization, CPU load) are programmatically generated and updated in graph node properties.

---

## 6. Technology Stack

- **Backend Runtime**: Python 3.11+ / 3.14 compatible
- **API Framework**: FastAPI, Pydantic v2, Uvicorn, Starlette
- **Graph Engines**: NetworkX 3.2+ (in-memory default), Neo4j Community 5.18+ (Docker persistent backend)
- **AI & LLM Gateway**: LiteLLM (Google Gemini Free Tier, Groq, local Ollama)
- **Frontend Stack**: React 18, TypeScript 5.x, Vite 5.x, TailwindCSS
- **Graph UI Visualization**: React Flow (`@xyflow/react`)
- **Cryptography & Security**: PBKDF2-HMAC-SHA256, AES-256 GCM, constant-time HMAC comparison
- **Testing & Quality**: Pytest, Pytest-Asyncio, Ruff, TypeScript strict mode

---

## 7. Project Structure

```
aegis/
├── backend/                  # Python backend application
│   ├── agent/                # Diagnostic reasoning (LiteLLM, prompts, schemas)
│   ├── api/                  # FastAPI routers, schemas, and main entrypoint
│   ├── auth/                 # Multi-tenant API key authentication and store
│   ├── chaos/                # Synthetic fault injection and telemetry generator
│   ├── executor/             # Guarded actuator, allowlist, scoring, and rollback
│   ├── feedback/             # Closed-loop incident writer and memory recalibration
│   ├── graph/                # GraphRepository (NetworkX & Neo4j implementations)
│   ├── ingestion/            # Docker Compose and GitHub repository parsers
│   ├── monitor/              # Async health prober and SSRF defense
│   ├── security/             # AES-256 secret encryption and URL validators
│   ├── sim/                  # Blast radius, contract diff, cycles, and risk engine
│   ├── tests/                # 15 test suites (174 collected test items)
│   └── webhooks/             # GitHub PR webhook verification and commenter
├── data/                     # Seed topology, PR scenarios, and configuration
│   ├── executor_config.json  # Allowlist definitions and actuator thresholds
│   ├── prs/                  # Test pull request JSON scenarios (PR #142, etc.)
│   └── topology.yaml         # 54-node / 142-edge baseline microservice topology
├── docs/                     # Technical specifications and architecture guides
│   ├── ALGORITHMS.md         # Mathematical definitions for B, C, D, H, and scoring
│   ├── API.md                # Complete REST endpoint and SSE reference
│   ├── ARCHITECTURE.md       # Layered system architecture and invariants
│   ├── CONFIGURATION.md      # Environment variables and fallback hierarchies
│   ├── DEPLOYMENT.md         # Deployment guide (Render, Docker, local)
│   ├── EVAL.md               # Empirical benchmarks and ablation study
│   ├── LIMITATIONS.md        # Real vs. simulated boundaries and Phase 2 roadmap
│   ├── SECURITY.md           # Threat model, SSRF defenses, and secret audits
│   └── STATUS.md             # Verified implementation status and test results
├── frontend/                 # React TypeScript frontend
│   ├── src/                  # Components, pages, hooks, and configuration
│   ├── package.json          # Dependencies and scripts
│   └── vite.config.ts        # Vite build and proxy configuration
├── scripts/                  # Operational scripts
│   ├── run_eval.py           # 5-fault × 10-trial automated evaluation harness
│   └── security_audit.py     # OSV package auditor and secret scanner
├── Dockerfile                # Multi-stage production container build
├── pyproject.toml            # Python packaging and tool configurations
└── render.yaml               # Render.com cloud deployment specification
```

---

## 8. Prerequisites

- **Python**: Version `3.11`, `3.12`, or `3.14`
- **Node.js**: Version `18.0` or higher (`20+` recommended)
- **Package Managers**: `pip` (Python) and `npm` (Node.js)
- **Optional**: Docker / Docker Compose (only required if running the persistent Neo4j backend)

---

## 9. Installation & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/muneeb-sawez/aegis.git
cd aegis
```

### 2. Configure Environment Variables
Copy the template configuration:
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

### 3. Backend Setup
Create and activate a virtual environment, then install dependencies:

**Windows PowerShell**:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Linux / macOS**:
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Frontend Setup
Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

---

## 10. Configuration

Key environment variables in `.env`:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `GRAPH_BACKEND` | `networkx` | Set to `networkx` for zero-dependency in-memory graph; set to `neo4j` for persistent Docker database. |
| `LLM_PROVIDER` | `gemini` | Model provider (`gemini`, `groq`, `ollama`, or `mock`). |
| `LLM_MODEL` | `gemini/gemini-1.5-flash` | Model identifier string. |
| `GEMINI_API_KEY` | *(None)* | API key for Google Gemini (Free Tier supported). Optional if `DEMO_MODE=true`. |
| `DEMO_MODE` | `false` | When `true`, uses local deterministic diagnosis rules without external network calls. |
| `PORT` | `8000` | Port bound by the FastAPI server. |

For detailed descriptions and fallback hierarchies, refer to [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

---

## 11. Running the Application

### Development Mode (Two Terminals)

**Terminal 1 — Backend API**:
```powershell
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Server: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/health`

**Terminal 2 — Frontend Client**:
```powershell
cd frontend
npm run dev
```
- Mission Control Web UI: `http://localhost:5173` (proxies `/api` requests to port 8000)

### Unified Production Mode
Build the frontend assets and serve everything from a single FastAPI process:
```bash
cd frontend && npm run build && cd ..
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000` to view the unified application.

---

## 12. Testing & Verification

Run the automated test suite across all modules:
```bash
python -m pytest backend/tests/ -v
```

### Measured Test Results
- **Collected Tests**: 174
- **Passing**: **169 passed**
- **Skipped**: **5 skipped** (Neo4j integration tests skip cleanly when Docker Neo4j is offline)
- **Failures**: **0**
- **Execution Time**: ~30.9 seconds

Verify the frontend build and type checks:
```bash
cd frontend
npm run build
```
- **Result**: `✓ built in ~330ms` with zero TypeScript errors.

Run the automated security audit:
```bash
python scripts/security_audit.py
```
- **Result**: 0 unmitigated secret leaks, 0 npm vulnerabilities.

---

## 13. API Overview

The backend exposes 37 OpenAPI endpoints grouped by subsystem:

- **Topology & Graph**: `GET /api/graph/topology`, `POST /api/graph/reset`, `GET /api/graph/services`
- **Change Risk (`PREDICT`)**: `POST /api/sim/evaluate`, `POST /api/predict/analyze`, `GET /api/sim/prs`
- **Health & Chaos (`MONITOR`)**: `GET /api/monitor/status`, `POST /api/monitor/check-now`, `POST /api/chaos/inject`
- **Autonomous Remediation (`HEAL`)**: `GET /api/heal/stream` (SSE), `POST /api/heal/execute`, `GET /api/actuator/actions`
- **Incident Memory (`LEARN`)**: `POST /api/memory/commit`, `GET /api/memory/incidents`
- **Multi-Tenancy & Endpoints**: `GET /api/projects`, `POST /api/projects`, `GET /api/endpoints`
- **GitHub Integrations**: `POST /api/webhooks/github`

For complete schema models and interactive testing, open `http://localhost:8000/docs`. Comprehensive reference available in [docs/API.md](docs/API.md).

---

## 14. Real versus Simulated Functionality

To maintain strict academic and engineering honesty, Phase 1 capabilities are explicitly classified:

| Capability | Real Implementation | Simulated / Emulated in Phase 1 |
| :--- | :--- | :--- |
| **Graph Database** | 100% real NetworkX and Neo4j graph storage with 54 nodes, 142 edges, and Cypher queries. | No real microservice pods or physical servers exist. |
| **Risk Prediction** | Real backward BFS decay, real AST schema diffing, real Tarjan SCC cycles, real composite formula. | Evaluates structured change payloads rather than raw multi-language git diffs. |
| **Monitoring Prober**| Real asynchronous `httpx` prober with live SSRF IP validation. | Telemetry metric drift (latency, error rate, pool saturation) is mathematically simulated in-memory. |
| **Diagnostic Reasoner**| Real LiteLLM API invocations (Gemini / Groq / Ollama) with Pydantic validation and retry logic. | Reasons over graph metric attributes rather than scraping live distributed Linux log files. |
| **Remediation Actuator**| Real allowlist gate, per-service concurrency locks, pre-action snapshots, and 10s rollback watchdog. | Modifies graph telemetry attributes rather than dispatching `kubectl` calls to a cloud cluster. |
| **Closed-Loop Learning**| Real `(:Incident)` nodes written to the graph, causing subsequent risk scores to measurably increase by $+5.0$. | Operates in-process on the active Knowledge Graph. |

Detailed boundaries documented in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

---

## 15. Limitations and Roadmap

### Present Limitations
1. **Schema-Level Changes Only**: Pre-merge risk analysis operates on JSON/YAML API specifications rather than multi-language source code ASTs.
2. **Process-Local Locks**: The actuator lock registry uses `asyncio.Lock`. Multi-instance horizontal scaling requires an external Redis lock manager (`Redlock`).
3. **Simulated Telemetry**: Metrics are programmatically generated for demonstration; integration with real Prometheus/OpenTelemetry daemons is scheduled for Phase 2.

### Phase 2 Roadmap
- **Live Kubernetes Actuation**: Official `kubernetes-client` integration executing rolling restarts and HPA scaling against real clusters.
- **Chaos Mesh & LitmusChaos**: Real container-level packet drop and CPU stress injection via Kubernetes Custom Resource Definitions (CRDs).
- **OpenTelemetry Pipeline**: Dynamic extraction of `CALLS` edges from distributed trace spans to weight graph dependencies by empirical request volume.
- **Machine Learning Calibration**: Replacing static risk formula weights with an empirical logistic regression model trained on historical repository post-mortems.

---

## 16. Security & Responsible Operation

- **Allowlist Gate**: The actuator enforces a fail-closed allowlist (`restart`, `scale_pool`, `rollback`). Destructive shell commands (e.g., `rm -rf`, `DROP TABLE`) are rejected at the validator layer before socket initialization.
- **SSRF Defense**: Outbound probers parse all target URLs and block link-local metadata addresses (`169.254.169.254`), loopbacks (`127.0.0.1`), and unroutable destinations (`0.0.0.0`).
- **Encrypted Secrets**: Registered endpoint secrets are authenticated-encrypted at rest using AES-256 GCM with PBKDF2-derived keys. Secrets are never exposed across public API models.
- **Request Signing**: Outbound remediation requests are cryptographically signed with HMAC-SHA256 (`X-AEGIS-Signature`), allowing target services to verify message integrity.
- **Safe Webhooks**: Incoming GitHub webhook payloads are validated using constant-time `hmac.compare_digest` against the configured secret.

Detailed security architecture documented in [docs/SECURITY.md](docs/SECURITY.md).

---

## 17. License & Attribution

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Developed as a Final-Year Engineering Capstone Project by **Muneeb Sawez** and contributors.
