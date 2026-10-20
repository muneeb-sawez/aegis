# AEGIS — Autonomous Engineering Graph & Intelligence System

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![React Flow](https://img.shields.io/badge/@xyflow/react-12-FF0072.svg?logo=react&logoColor=white)](https://reactflow.dev/)
[![Graph Backend](https://img.shields.io/badge/Graph-NetworkX%20%7C%20Neo4j-orange.svg)](https://networkx.org/)
[![Tests](https://img.shields.io/badge/Tests-23%2F23%20Passing-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg)]()

**"See every risk before it ships. Heal every failure after it lands."**

*An autonomous, graph-grounded reliability intelligence system that predicts the architectural blast radius of pull requests before deployment, monitors distributed microservice health, simulates deterministic chaos faults, and feeds production incidents back into graph memory.*

[Features](#-core-capabilities) • [Architecture](#-closed-loop-architecture) • [Getting Started](#-getting-started) • [Algorithms](#-mathematical--algorithmic-formulation) • [Demo Walkthrough](#-demonstration-walkthrough)

</div>

---

## 📌 Executive Summary

Modern microservice architectures fail when small code changes or breaking API contracts propagate unforeseen cascade failures across deep dependency chains. 

**AEGIS** closes the loop between **Pre-Deployment Risk Prediction** and **Post-Deployment Incident Telemetry**:
1. **PREDICT:** Evaluates proposed software changes, builds an upstream reverse graph blast radius, computes contract diff breaking severity, detects cyclic deadlocks via Tarjan's SCC algorithm, and scores the change using a multi-factor risk model ($0.35B + 0.30C + 0.15D + 0.20H$).
2. **MONITOR:** Continuously probes endpoints with SSRF-protected health checks, accepts deterministic chaos injection (timeouts, elevated latency, 500 error cascades), and automatically records graph `Incident` nodes upon exceeding failure thresholds.
3. **LEARN (Closed Loop):** The incident committed in production immediately feeds back into the dependency graph, so subsequent risk scores on that service increase dynamically by **$+5.0$ points** ($0.20 \times 25.0$).

---

## ⚡ Core Capabilities

### 1. Change-Risk Engine (`PREDICT`)
- **Reverse Graph Walk:** Microservice calls flow $A \to B$. When $B$ changes, $A$ suffers the impact. AEGIS traverses graph predecessors with $0.75^{\text{hops}-1}$ distance attenuation.
- **Contract Diffing:** Differentiates breaking schema changes (deleted required fields, altered types $\to C=100.0$) from safe additive changes ($C=0.0$).
- **Cycle Detection:** Runs Tarjan's Strongly Connected Components algorithm to identify circular call chains ($\to D=100.0$).
- **Explainable Verdicts:** Provides human-readable component breakdowns and approval verdicts (`Approved`, `Warning`, `Blocked`).

### 2. Service Health & Chaos Engine (`MONITOR`)
- **Lightweight Async Health Probes:** Periodic HTTP checks recording status, HTTP codes, latency, and consecutive failures.
- **SSRF Defense:** Rejects private metadata destinations (e.g. AWS/GCP `169.254.169.254`) and dangerous local loopbacks.
- **Deterministic Fault Simulation:** Inject timeouts (`504 Gateway Timeout`), latency spikes (~2400 ms), or crash loops (`500 Internal Error`).
- **Automated Incident Creation:** Exceeding consecutive failure thresholds ($\ge 3$) automatically creates and links an incident record to the target node.
- **Self-Healing Recovery:** Resetting faults restores services to healthy state and resets failure counters.

### 3. Repository & Manifest Ingestion
- **Docker Compose Parser:** Ingests `docker-compose.yml` topologies, extracting services, ports, environment-derived call edges, and databases.
- **GitHub REST API Importer:** Introspects public/private repositories on-the-fly without cloning large git histories.
- **Pre-Bundled Test Repositories:** Includes 4 verified multi-tier microservice architectures for offline testing:
  - 🛒 `shop-sphere/ecommerce-core` (11 microservices + Stripe SaaS)
  - 💳 `fintech-nexus/ledger-core` (7 microservices + PostgreSQL vault)
  - ⚡ `data-mesh/streaming-pipeline` (6 services + Kafka & ClickHouse)
  - 🏥 `health-sync/telehealth-platform` (5 services + WebRTC relay)
- **External Vendor Registration:** Manually registers SaaS dependencies (Stripe, SendGrid, Auth0) and maps dependency edges.

### 4. Enterprise Mission Control UI
- Cyber-dark glassmorphism dashboard built with **React**, **Vite**, and **React Flow (`@xyflow/react`)**.
- Interactive topology canvas with pulsing crimson critical path highlights.
- Slide-over Blast Radius Inspector and streaming SSE Diagnostic Terminal.
- Bottom KPI metrics tracking graph nodes, risk factor breakdown, and live alert statuses.

---

## 🔄 Closed-Loop Architecture

```
                  ┌────────────────────────────────────────┐
                  │ 1. PREDICT: Pre-Deployment Risk Engine │
                  │  - Reverse BFS Blast Radius (B)        │
                  │  - Contract Breaking Severity (C)      │
                  │  - Tarjan Cycle Detection (D)          │
                  │  - Historical Incident Term (H)        │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │ 2. DEPLOY & MONITOR: Live Telemetry    │
                  │  - Periodic Async HTTP Health Probes   │
                  │  - SSRF-Protected Verification         │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │ 3. CHAOS: Deterministic Fault Injector │
                  │  - Timeouts (504) & Latency Spikes     │
                  │  - Threshold Breaches (≥ 3 Failures)   │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │ 4. LEARN: Incident Memory Feedback     │
                  │  - Commit Incident Node to Graph       │
                  │  - Next PR Risk Score Jumps by +5.0 pts│
                  └────────────────────────────────────────┘
```

---

## 📐 Mathematical & Algorithmic Formulation

### 1. Risk Scoring Formula
The composite risk score is bounded within $[0, 100]$:

$$\text{RiskScore} = 0.35 \times B + 0.30 \times C + 0.15 \times D + 0.20 \times H$$

Where:
- **$B$ (Blast Radius, $0–100$):** Attenuated dependency reach of upstream callers:
  $$B = \min\left(100, \frac{\sum_{c \in \text{Callers}} 0.75^{\text{hops}(c) - 1}}{\text{MAX\_BLAST}} \times 100\right)$$
- **$C$ (Contract Diff Severity, $0–100$):**
  - $C = 100.0$: Breaking change (deleted required field, changed field type).
  - $C = 50.0$: Added required field without default.
  - $C = 0.0$: Additive non-breaking / optional modification.
- **$D$ (Cycle Penalty, $0–100$):**
  - $D = 100.0$: Tarjan's algorithm detects service membership in a Strongly Connected Component ($\ge 2$ nodes).
  - $D = 0.0$: Graph remains a Directed Acyclic Graph (DAG).
- **$H$ (Historical Incident Penalty, $0–100$):**
  $$H = \min(100, \text{incidents\_last\_30\_days} \times 25.0)$$
  *(Each recorded incident raises $H$ by $+25.0$, adding $+5.0$ net points to future risk scores).*

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.11+**
- **Node.js 18+ & npm**
- Git

### 1. Clone & Set Up Backend

```bash
# Clone the repository
git clone https://github.com/muneeb-sawez/aegis.git
cd aegis

# Install Python dependencies
pip install fastapi uvicorn pydantic pyyaml networkx httpx pytest anyio
```

### 2. Set Up Frontend

```bash
cd frontend
npm install
```

### 3. Run the Application

#### Start the FastAPI Backend:
```bash
# From repository root
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Health Check: `http://localhost:8000/health`
- Interactive Swagger Documentation: `http://localhost:8000/docs`

#### Start the React Frontend:
```bash
# From frontend/ directory
npm run dev
```
- Mission Control Dashboard: `http://localhost:5173`

---

## 🧪 Automated Testing

AEGIS includes a comprehensive test suite covering graph traversals, risk scoring, cycle detection, ingestion, and closed-loop learning.

Run the test suite with:
```bash
python -m pytest backend/tests/ -v
```

### Test Coverage Highlights:
- `test_golden_loop_pr_142_learning`: Verifies that committing an incident increases PR #142 risk score by **exactly $+5.0$ points**.
- `test_edge_direction_and_callers`: Verifies caller-to-callee direction and reverse predecessor traversal.
- `test_cycle_detection_tarjan`: Verifies cycle detection on circular microservice topologies.
- `test_ssrf_protection`: Ensures dangerous internal IP addresses are blocked by the monitor.
- `test_sample_repos_catalog_and_ingestion`: Verifies instant offline ingestion of bundled test repositories.

---

## 📁 Repository Structure

```text
aegis/
├── backend/
│   ├── api/                     # FastAPI routing layer
│   │   ├── main.py              # Application entrypoint & CORS
│   │   ├── routes_predict.py    # PREDICT risk assessment endpoint
│   │   ├── routes_monitor.py    # Health check & fault injection endpoints
│   │   ├── routes_ingestion.py  # Repository & manifest ingestion endpoints
│   │   └── routes_graph.py      # Topology query endpoints
│   ├── graph/                   # Graph repository abstraction
│   │   ├── repository.py        # Abstract GraphRepository interface
│   │   ├── networkx_repo.py     # In-memory NetworkX implementation
│   │   ├── neo4j_repo.py        # Neo4j Cypher implementation
│   │   ├── seed.py              # 54-node / 142-edge topology generator
│   │   └── schema.cypher        # Cypher schema definitions
│   ├── sim/                     # Algorithmic risk computation
│   │   ├── blast_radius.py      # Predecessor BFS with hop attenuation
│   │   ├── contract_diff.py     # OpenAPI schema breaking change detector
│   │   ├── cycles.py            # Tarjan Strongly Connected Components
│   │   ├── risk.py              # Composite scoring formula
│   │   └── config.py            # Calibrated weights (0.35, 0.30, 0.15, 0.20)
│   ├── monitor/                 # Health & chaos telemetry
│   │   └── health_checker.py    # Async HTTP probes, SSRF defense & fault emulator
│   ├── ingestion/               # Repository & manifest parsers
│   │   ├── docker_compose.py    # Compose YAML AST parser
│   │   ├── github_fetcher.py    # GitHub REST API fetcher
│   │   ├── sample_repos.py      # Pre-bundled offline test repositories
│   │   └── service.py           # Idempotent graph upsert merger
│   └── tests/                   # 23 pytest integration & unit tests
├── frontend/                    # Mission Control React SPA
│   ├── src/
│   │   ├── App.tsx              # Main dashboard layout
│   │   ├── components/
│   │   │   ├── CustomNodes.tsx  # Critical nodes, VPC boundaries & IAM cards
│   │   │   ├── BlastRadiusPanel.tsx # Slide-over risk inspector
│   │   │   ├── BottomLayerCards.tsx # Bottom KPI summary cards
│   │   │   ├── PredictModal.tsx     # Change-risk simulation form
│   │   │   ├── MonitorModal.tsx     # Live health table & chaos controls
│   │   │   └── IngestionModal.tsx   # Sample repo browser & YAML parser
│   └── package.json
├── data/
│   ├── topology.yaml            # Seeded 54-node / 142-edge ground truth
│   └── prs/                     # Sample PR payload fixtures
└── docs/
    ├── DEMO-SCRIPT.md           # 4-Minute Review Presentation Guide
    ├── 02-CONTRACTS.md          # Architectural interface definitions
    └── 04-ALGORITHMS.md         # Detailed mathematical algorithm derivations
```

---

## 🎬 Demonstration Walkthrough

During your evaluation or presentation, follow this 4-step sequence (see [`docs/DEMO-SCRIPT.md`](docs/DEMO-SCRIPT.md) for full script):

1. **Inspect Active Topology:** Open `http://localhost:5173` to view the 54-node / 142-edge live service canvas.
2. **Ingest a Repository:** Click **"Ingest Repos"** &rarr; select **`shop-sphere/ecommerce-core`** &rarr; click **"Ingest Topology"** to watch the services merge into the graph dynamically.
3. **Run PREDICT Analysis:** Click **"Predict Risk"**, select `paymentservice`, choose `Breaking API Contract`, and run analysis. Observe that breaking contract severity ($C=100.0$) triggers a warning and highlights upstream callers (`checkoutservice`, `frontend`) in glowing orange.
4. **Trigger Fault & Automated Incident:** Click **"Monitor Health"**, select `emailservice`, choose `500 Failure`, and inject. Once failures hit the threshold ($\ge 3$), an automated **Incident Record** is created, raising future risk scores on that service by $+5.0$ points.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
