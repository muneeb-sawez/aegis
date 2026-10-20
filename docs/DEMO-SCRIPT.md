# AEGIS — Four-Day Review Demonstration Script & Technical Guide

This guide is designed for your undergraduate major project presentation-cum-review. It provides a step-by-step demonstration walkthrough, exact technical talking points, and verification commands.

---

## 1. Executive Summary for Examiners

> **Project Title:** AEGIS (Autonomous Engineering Graph & Intelligence System)  
> **Core Motto:** *"See every risk before it ships. Heal every failure after it lands."*  
> **Review Scope:** **PREDICT + MONITOR** (Closed-Loop Autonomous Architecture)  
> **Ground Truth Topology:** 54 services & infrastructure components, 142 directional dependency edges (`CALLS`, `DEPENDS_ON`, `CONNECTS_TO`).

### Key Technical Differentiators:
1. **Dynamic, Code-Calculated Risk Scoring:** Risk scores are never hardcoded. They are dynamically computed using graph algorithms (Reverse BFS blast radius attenuation, Tarjan Strongly Connected Components for circular dependencies, and OpenAPI contract diffing).
2. **Reverse Graph Traversal:** In microservices, dependencies flow `A -> B` (`A` calls `B`). When `B` is modified, upstream consumers (`A`) suffer the blast radius. AEGIS traverses predecessors backwards to calculate true dependency impact.
3. **Idempotent Ingestion:** Ingests live `docker-compose.yml` topologies and GitHub repositories via REST API, plus manual registration for un-introspectable third-party SaaS (e.g. Stripe, SendGrid).
4. **Resilient Monitoring & Fault Emulation:** Periodic asynchronous HTTP probes with built-in SSRF protection (blocking cloud metadata IPs) and deterministic fault injection (timeouts, elevated latency, 500 errors) that trip automated incident creation.

---

## 2. Quick Setup & Run Instructions

### Step 1: Start the Backend API (FastAPI)
```bash
# From workspace root
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload
```
*Health check:* [http://localhost:8000/health](http://localhost:8000/health)  
*Swagger API Docs:* [http://localhost:8000/docs](http://localhost:8000/docs)

### Step 2: Start the Frontend UI (React + Vite + React Flow)
```bash
cd frontend
npm run dev
```
*Mission Control Dashboard:* [http://localhost:5173](http://localhost:5173)

### Step 3: Run the Full Test Suite
```bash
python -m pytest backend/tests/ -v
```
*(All 22 unit & integration tests run in under 2 seconds.)*

---

## 3. Four-Minute Live Demonstration Walkthrough

Follow this sequence during your review demonstration:

### Step 1: Mission Control Overview (30 seconds)
1. Open the dashboard at [http://localhost:5173](http://localhost:5173).
2. Point out the interactive React Flow canvas showing the microservice dependency architecture.
3. Show the **Topology Metrics** in the header: **54 Nodes**, **142 Edges**, NetworkX in-memory graph repository.
4. Point out the bottom KPI cards:
   - **Service Topology:** Microservice nodes, databases, cloud resources.
   - **Risk Breakdown:** Formula components ($0.35B + 0.30C + 0.15D + 0.20H$).
   - **Incident & Health:** Active alerts and health probe statuses.

### Step 2: Ingestion & External Vendor Registration (45 seconds)
1. Click the **"Ingest Repository"** button in the top navigation.
2. **Demonstrate Docker Compose Parsing:**
   - In the "Import Manifest" tab, click **"Use Sample Microservice Compose"** to populate a multi-tier microservice architecture (`frontend`, `api-gateway`, `userservice`, `postgres`).
   - Click **"Parse & Ingest Manifest"**.
   - Show the success response: Services and dependencies parsed and idempotently merged into the graph.
3. **Demonstrate External Service Registration:**
   - Switch to the "Add External Service" tab.
   - Register a third-party vendor (e.g., `Stripe Payment Gateway`, Category: `Payment Processor`, Dependent Service: `paymentservice`).
   - Click **"Register External Service"**.
   - Show that the node and dependency edge are immediately persisted into the graph.

### Step 3: PREDICT — Change-Risk Analysis (75 seconds)
1. Click the **"Predict Risk"** button in the header.
2. **Scenario A — Safe Additive Change:**
   - Target Service: `paymentservice`
   - Change Type: `Additive (Non-Breaking) API`
   - Description: `Add optional metadata field to payment response`
   - Click **"Run Impact Analysis"**.
   - Observe Result: **Low Risk** (~13.4 / 100), Verdict: **Approved**. Breaking contract severity $C = 0.0$.
3. **Scenario B — Breaking API Contract Change:**
   - Target Service: `paymentservice`
   - Change Type: `Breaking API Contract`
   - Description: `Remove charge_id and change currency format`
   - Click **"Run Impact Analysis"**.
   - Observe Result: **Moderate/High Risk** (~43.4 / 100), Verdict: **Warning / Blocked**.
   - Explain to the examiner:
     - Notice that **$C = 100.0$** contributing $+30.0$ to the risk score.
     - Notice the **Impacted Upstream Services**: `checkoutservice`, `frontend`, `loadgenerator`. AEGIS automatically performed a reverse BFS graph walk to find every service that depends on `paymentservice`.
4. **Scenario C — Circular Dependency (Tarjan Algorithm):**
   - Change Type: `Introduce Circular Dependency`
   - Click **"Run Impact Analysis"**.
   - Observe Result: Cycle Penalty **$D = 100.0$**, adding $+15.0$ penalty and triggering an immediate architecture warning.

### Step 4: MONITOR — Health Probes & Fault Simulation (60 seconds)
1. Click the **"Monitor Health"** button in the header.
2. Show the real-time health table tracking endpoints, status codes, and response times.
3. Click **"Run Health Check Now"** to execute asynchronous probes.
4. **Demonstrate Deterministic Fault Injection:**
   - In the "Simulate Fault" section, select `cartservice`.
   - Fault Type: `Elevated Latency (Degraded)`.
   - Click **"Inject Fault"**.
   - Observe that `cartservice` status immediately transitions to **Degraded** with ~2400 ms simulated latency.
5. **Demonstrate Consecutive Failure Threshold & Incident Trigger:**
   - Select `emailservice`.
   - Fault Type: `HTTP 500 Failure (Crash/Unavailable)`.
   - Click **"Inject Fault"**.
   - Show the active alerts table below: Because consecutive failures exceeded the threshold ($\ge 3$), an automated **Incident Record** is created and linked to `emailservice`.
6. **Demonstrate Recovery:**
   - Select `emailservice` and click **"Clear Fault (Recover)"**.
   - Status returns to **Healthy (200 OK)** and consecutive failures reset to 0.

### Step 5: Closed-Loop Verification (Golden Loop) (30 seconds)
1. Remind the reviewers of the AEGIS core thesis: **"Predict $\to$ Deploy $\to$ Monitor $\to$ Learn"**.
2. When an incident occurs in production, it is written back to the graph.
3. When the engineer later proposes another PR against that service, the historical incident term $H$ increases by $+25.0$, raising the overall risk score by **$+5.0$ points** ($0.20 \times 25.0 = 5.0$).
4. Highlight that this closed-loop behavior is verified by automated test `test_golden_loop_pr_142_learning` in `backend/tests/test_sim.py`.

---

## 4. Architectural Summary

| Layer | Implementation | File Path |
|---|---|---|
| **Graph Interface** | `GraphRepository` Protocol | [`backend/graph/repository.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/repository.py) |
| **In-Memory Engine** | NetworkX Directed Graph (`DiGraph`) | [`backend/graph/networkx_repo.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/networkx_repo.py) |
| **Blast Radius** | Predecessor BFS with $0.75^{\text{hops}-1}$ attenuation | [`backend/sim/blast_radius.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/blast_radius.py) |
| **Cycle Detection** | Tarjan's Strongly Connected Components | [`backend/sim/cycles.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/cycles.py) |
| **Risk Formula** | $0.35B + 0.30C + 0.15D + 0.20H \in [0, 100]$ | [`backend/sim/risk.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/risk.py) |
| **Ingestion** | Docker Compose YAML & GitHub REST API | [`backend/ingestion/`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/ingestion/) |
| **Health Monitor** | Async HTTP probes + SSRF defense + Fault Emulation | [`backend/monitor/health_checker.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/monitor/health_checker.py) |
| **Mission Control** | React + TypeScript + React Flow (`@xyflow/react`) | [`frontend/src/`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/) |
